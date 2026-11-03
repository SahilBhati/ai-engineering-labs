#!/usr/bin/env python3
"""Claude Code usage tracker: reads local Claude Code logs, no API calls, no dependencies.

Usage:
  python3 usage.py                      summary: current 5-hour window, last 7 days, by project, by model
  python3 usage.py --json               same data as JSON
  python3 usage.py calibrate --weekly 42 [--session 30]
                                        record what /usage shows right now, so later runs can
                                        estimate % used and project when you'd hit the limit

Subscription limits aren't exposed by any API. This tool measures your token use from
~/.claude/projects/**/*.jsonl and, once calibrated, estimates limits from it.
"""
import argparse, glob, json, os, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

LOG_GLOB = os.path.expanduser("~/.claude/projects/*/*.jsonl")
CALIB_FILE = os.path.expanduser("~/.claude/usage-calibration.json")
WINDOW = timedelta(hours=5)

# Approximate API list prices, USD per million tokens: (input, output, cache read).
# Used only as a weighting unit ("API-equivalent cost"); it's not your bill.
# Cache writes are priced at 1.25x input (5-minute) and 2x input (1-hour); that's an assumption.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-opus-5": (5.00, 25.00, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-sonnet-5": (2.00, 10.00, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
    "claude-fable-5-1": (10.00, 50.00, 0.25),
}
DEFAULT_PRICE = PRICES["claude-opus-5-5"]


def load_events():
    """One event per API response, de-duplicated (streamed responses are logged more than once)."""
    seen, events = set(), []
    for path in glob.glob(LOG_GLOB):
        fallback = os.path.basename(os.path.dirname(path))
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                msg = d.get("message")
                if d.get("type") != "assistant" or not isinstance(msg, dict) or "usage" not in msg:
                    continue
                key = msg.get("id") or d.get("requestId") or d.get("uuid")
                if key in seen:
                    continue
                seen.add(key)
                try:
                    ts = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
                except (KeyError, ValueError):
                    continue
                u = msg["usage"]
                cc = u.get("cache_creation") or {}
                events.append({
                    "ts": ts, "project": (d.get("cwd") or fallback).replace(os.path.expanduser("~"), "~"),
                    "model": msg.get("model", "unknown"),
                    "input": u.get("input_tokens", 0) or 0,
                    "output": u.get("output_tokens", 0) or 0,
                    "cache_read": u.get("cache_read_input_tokens", 0) or 0,
                    "cache_write_5m": cc.get("ephemeral_5m_input_tokens", 0) or 0,
                    "cache_write_1h": cc.get("ephemeral_1h_input_tokens", 0) or 0,
                })
    events.sort(key=lambda e: e["ts"])
    return events


def cost(e):
    pin, pout, pread = PRICES.get(e["model"], DEFAULT_PRICE)
    return (e["input"] * pin + e["output"] * pout + e["cache_read"] * pread
            + e["cache_write_5m"] * pin * 1.25 + e["cache_write_1h"] * pin * 2.0) / 1e6


def tokens(e):
    return e["input"] + e["output"] + e["cache_read"] + e["cache_write_5m"] + e["cache_write_1h"]


def windows(events):
    """Estimated 5-hour windows: a window starts at the first response after the previous one ends."""
    out, start, acc = [], None, []
    for e in events:
        if start is None or e["ts"] >= start + WINDOW:
            if acc:
                out.append((start, acc))
            start, acc = e["ts"], []
        acc.append(e)
    if acc:
        out.append((start, acc))
    return out


def agg(evts):
    return {"responses": len(evts), "tokens": sum(map(tokens, evts)),
            "output": sum(e["output"] for e in evts), "cost": round(sum(map(cost, evts)), 2)}


def summarize(events, now):
    week = [e for e in events if e["ts"] >= now - timedelta(days=7)]
    wins = windows(events)
    cur = None
    if wins and now < wins[-1][0] + WINDOW:
        start, evts = wins[-1]
        elapsed_h = max((now - start).total_seconds() / 3600, 0.1)
        cur = dict(agg(evts), start=start.isoformat(), resets=(start + WINDOW).isoformat(),
                   burn_cost_per_hour=round(agg(evts)["cost"] / elapsed_h, 2))
    days = defaultdict(list)
    for e in week:
        days[e["ts"].astimezone().strftime("%a %m-%d")].append(e)
    by = lambda k: {key: agg(v) for key, v in sorted(_group(week, k).items(), key=lambda kv: -sum(map(cost, kv[1])))}
    return {"now": now.isoformat(), "current_window": cur, "last_7_days": agg(week),
            "by_day": {d: agg(v) for d, v in days.items()}, "by_project": by("project"), "by_model": by("model")}


def _group(evts, key):
    g = defaultdict(list)
    for e in evts:
        g[e[key]].append(e)
    return g


def estimate(summary):
    try:
        c = json.load(open(CALIB_FILE))
    except (OSError, ValueError):
        return None
    est = {}
    for kind, used_now in (("weekly", summary["last_7_days"]["cost"]),
                           ("session", (summary["current_window"] or {}).get("cost", 0))):
        cal = c.get(kind)
        if cal and cal["pct"] > 0 and cal["cost"] > 0:
            capacity = cal["cost"] / (cal["pct"] / 100)
            est[kind] = {"est_pct_used": round(100 * used_now / capacity), "est_capacity_cost": round(capacity, 2),
                         "calibrated_at": cal["at"]}
    return est or None


def fmt_tokens(n):
    return f"{n/1e6:.1f}M" if n >= 1e6 else f"{n/1e3:.0f}k"


def print_summary(s, est):
    print("\nClaude Code usage (from local logs; cost = approximate API-equivalent, not your bill)\n")
    cw = s["current_window"]
    if cw:
        reset = datetime.fromisoformat(cw["resets"]).astimezone().strftime("%H:%M")
        print(f"Current 5-hour window (estimated): {cw['responses']} responses, {fmt_tokens(cw['tokens'])} tokens, "
              f"${cw['cost']:.2f}, burning ${cw['burn_cost_per_hour']:.2f}/h, resets ~{reset}")
    else:
        print("Current 5-hour window: idle (next message starts a new one)")
    w = s["last_7_days"]
    print(f"Last 7 days: {w['responses']} responses, {fmt_tokens(w['tokens'])} tokens, ${w['cost']:.2f}")
    if est:
        for kind, v in est.items():
            print(f"  ~{v['est_pct_used']}% of {kind} limit used (estimated; calibrated {v['calibrated_at'][:16]})")
    else:
        print("  Not calibrated: run `usage.py calibrate --weekly <pct from /usage>` to estimate % used.")
    for title, key in (("By day", "by_day"), ("By project", "by_project"), ("By model", "by_model")):
        print(f"\n{title}")
        for k, v in s[key].items():
            print(f"  {k[:44]:<44} {v['responses']:>5} resp  {fmt_tokens(v['tokens']):>7}  ${v['cost']:>7.2f}")
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    cal = sub.add_parser("calibrate", help="record the %% that /usage shows now")
    cal.add_argument("--weekly", type=float)
    cal.add_argument("--session", type=float)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    s = summarize(load_events(), now)
    if args.cmd == "calibrate":
        try:
            c = json.load(open(CALIB_FILE))
        except (OSError, ValueError):
            c = {}
        if args.weekly is not None:
            c["weekly"] = {"pct": args.weekly, "cost": s["last_7_days"]["cost"], "at": now.isoformat()}
        if args.session is not None:
            c["session"] = {"pct": args.session, "cost": (s["current_window"] or {}).get("cost", 0), "at": now.isoformat()}
        json.dump(c, open(CALIB_FILE, "w"), indent=2)
        print(f"Calibration saved to {CALIB_FILE}")
        return
    est = estimate(s)
    if args.json:
        print(json.dumps(dict(s, estimate=est), indent=2))
    else:
        print_summary(s, est)


if __name__ == "__main__":
    sys.exit(main())

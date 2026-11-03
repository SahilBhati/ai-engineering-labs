# usage-tracker

**See how much Claude Code you've used (current 5-hour window, last 7 days, per project, per model) from your local logs. No API key, no network, no dependencies.**

Claude subscription limits (the 5-hour and weekly windows) aren't exposed by any
API. Claude Code does log every response locally with exact token counts, so this
tool reads those logs and, after a one-time calibration against `/usage`,
estimates how much of your limit you've used.

## Run

```bash
python3 usage.py            # summary
python3 usage.py --json     # machine-readable
```

Example output:

```
Current 5-hour window (estimated): 162 responses, 28.9M tokens, $12.96, burning $3.53/h, resets ~18:22
Last 7 days: 162 responses, 28.9M tokens, $12.96
```

## Calibrate (optional, for % estimates)

Run `/usage` in Claude Code, then record what it shows:

```bash
python3 usage.py calibrate --weekly 42 --session 30
```

Later runs then report "~N% of weekly limit used". Recalibrate now and then:
limits change, and the estimate assumes usage scales with API-equivalent cost.

## How it works

- Reads `~/.claude/projects/*/*.jsonl` and keeps one record per API response
  (streamed responses are logged more than once).
- **Cost** is an approximate *API-equivalent* price, used only as a weighting unit
  that reflects model and token type. It's not your bill. Cache-write prices
  (1.25× input for 5-minute, 2× for 1-hour) are an assumption.
- **5-hour windows** are estimated: a window starts at the first response after
  the previous window ends.
- Calibration is stored in `~/.claude/usage-calibration.json`.

## Limits

- Counts only Claude Code on this machine: not claude.ai chats, other devices,
  or cloud sessions.
- Estimates, not the official meter. `/usage` is the source of truth.

// learner-sim runner: capture a lesson, run the simulated learner, score it.
//   node tools/learner-sim/run.mjs prepare <lesson> [--runs 3]   -> prints the new run folder
//   node tools/learner-sim/run.mjs sim <folder> [--runs 3] [--model sonnet]
//   node tools/learner-sim/run.mjs score <folder>
//   node tools/learner-sim/run.mjs all <lesson>                   prepare + sim + score
// Pipeline: the browser and file work lives here; the scoring logic is pure (lib/score.mjs).
import fs from "node:fs";
import path from "node:path";
import {spawn} from "node:child_process";
import {serve, launch} from "../shared/cdp.mjs";
import {makePacket} from "./lib/packet.mjs";
import {scoreRun, aggregate, diff, toMarkdown} from "./lib/score.mjs";

const HERE = import.meta.dirname, ROOT = path.resolve(HERE, "../.."), SITE = path.join(ROOT, "site");
const RUNS = path.join(HERE, "runs");
const read = f => JSON.parse(fs.readFileSync(f, "utf8"));
const write = (f, x) => { fs.mkdirSync(path.dirname(f), {recursive: true}); fs.writeFileSync(f, typeof x === "string" ? x : JSON.stringify(x, null, 2) + "\n"); };
const bankOf = n => read(path.join(SITE, `quiz/banks/l${n}.json`));
const lessonOf = dir => +path.basename(dir).match(/-L(\d+)/)[1];
const opt = (name, dflt) => { const i = process.argv.indexOf("--" + name); return i > 0 ? process.argv[i + 1] : dflt; };

// runs/<date>-L<n>, then -r2, -r3 ... for later runs the same day.
function newRunDir(n){
  const t = new Date(), base = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}-L${n}`;
  for(let k = 1; ; k++){ const d = path.join(RUNS, k === 1 ? base : `${base}-r${k}`); if(!fs.existsSync(d)) return d; }
}
const order = name => { const m = name.match(/^(\d{4}-\d{2}-\d{2})-L\d+(?:-r(\d+))?$/); return m ? m[1] + String(m[2] || 1).padStart(3, "0") : ""; };

// Every step of the lesson: its text (with "Go deeper" open) and a screenshot of the step card.
async function capture(n, dir){
  const bank = bankOf(n), srv = await serve(SITE), chrome = await launch();
  const lessonPath = new URL(bank.url, srv.base + "/quiz/").pathname;
  try{
    const tab = await chrome.open();
    await tab.send("Emulation.setDeviceMetricsOverride", {width: 1280, height: 900, deviceScaleFactor: 1, mobile: false});
    await tab.send("Emulation.setEmulatedMedia", {features: [{name: "prefers-reduced-motion", value: "reduce"}, {name: "prefers-color-scheme", value: "light"}]});
    await tab.goto(srv.base + lessonPath);
    const meta = await tab.evaluate(`(async () => {
      for(let t = 0; t < 50 && !document.querySelector("#tocList [data-go]"); t++) await new Promise(r => setTimeout(r, 100));
      const chs = [...document.querySelectorAll("#chapters button")].map(b => b.dataset.ch);
      return [...document.querySelectorAll("#tocList .grp")].flatMap((g, gi) => [...g.querySelectorAll("[data-go]")]
        .map(a => ({go: +a.dataset.go, ch: chs[gi], title: a.lastElementChild.textContent})));
    })()`);
    const steps = [];
    for(const [i, m] of meta.sort((a, b) => a.go - b.go).entries()){
      const id = "S" + String(i + 1).padStart(2, "0");
      const box = await tab.evaluate(`(async () => {
        document.querySelector('[data-go="${m.go}"]').click();
        await new Promise(r => setTimeout(r, 400));
        document.querySelectorAll("#card details").forEach(d => d.open = true);
        // Fixed and sticky bars (step nav, header) would paint over the card in a full-height capture.
        const c0 = document.querySelector("#card");
        document.querySelectorAll("body *").forEach(e => { if(!c0.contains(e) && /fixed|sticky/.test(getComputedStyle(e).position)) e.style.visibility = "hidden"; });
        await new Promise(r => setTimeout(r, 200));
        const c = document.querySelector("#card"), r = c.getBoundingClientRect();
        return {text: c.innerText, x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height};
      })()`);
      const shot = await tab.send("Page.captureScreenshot", {format: "png", captureBeyondViewport: true,
        clip: {x: box.x, y: box.y, width: box.w, height: box.h, scale: 1}});
      fs.mkdirSync(path.join(dir, "steps"), {recursive: true});
      fs.writeFileSync(path.join(dir, "steps", id + ".png"), Buffer.from(shot.data, "base64"));
      steps.push({id, ch: m.ch, title: m.title, teaching: !["V", "✓"].includes(m.ch), shot: `steps/${id}.png`, text: box.text});
    }
    if(tab.errors.length) console.error("page errors:", tab.errors);
    await tab.close();
    return steps;
  } finally { await chrome.close(); srv.close(); }
}

async function prepare(n, runs){
  const dir = newRunDir(n), bank = bankOf(n);
  const steps = await capture(n, dir);
  write(path.join(dir, "steps.json"), {lesson: n, title: bank.title, steps});
  for(let k = 1; k <= runs; k++){
    const p = makePacket(bank, n * 1000 + k);   // seeded per run: different order and option letters each run
    write(path.join(dir, `run-${k}`, "packet", "questions.json"), p.questions);
    write(path.join(dir, `run-${k}`, "packet", "options-only.json"), p.optionsOnly);
    write(path.join(dir, "keys", `map-${k}.json`), p.map);
  }
  console.log(path.relative(ROOT, dir));
  return dir;
}

// One fresh `claude -p` per run, in parallel: no run sees another's context.
async function sim(dir, runs, model){
  const one = k => new Promise((res, rej) => {
    const rel = path.relative(ROOT, dir);   // relative: keeps local home paths out of logs
    const prompt = `Lesson folder: ${rel}\nYour run folder: ${rel}/run-${k}\nFollow your instructions exactly.`;
    const p = spawn("claude", ["-p", "--agent", "learner-sim", "--model", model, "--allowedTools", "Read", "Glob", "Grep", "Bash", "--", prompt],
      {cwd: ROOT, stdio: ["ignore", "pipe", "pipe"]});
    let out = ""; p.stdout.on("data", d => out += d); p.stderr.on("data", d => out += d);
    p.on("close", code => { write(path.join(dir, `run-${k}`, "log.txt"), out);
      const ok = fs.existsSync(path.join(dir, `run-${k}`, "answers.json"));
      console.log(`run-${k}: exit ${code}, answers ${ok ? "written" : "MISSING"}`); ok ? res() : rej(new Error(`run-${k} wrote no answers`)); });
  });
  await Promise.all(Array.from({length: runs}, (_, i) => one(i + 1)));
}

function score(dir){
  const n = lessonOf(dir), bank = bankOf(n), {steps} = read(path.join(dir, "steps.json"));
  const runDirs = fs.readdirSync(dir).filter(d => /^run-\d+$/.test(d) && fs.existsSync(path.join(dir, d, "answers.json"))).sort();
  const runs = runDirs.map(d => {
    const k = d.split("-")[1], f = name => path.join(dir, d, name);
    return scoreRun({bank, steps, map: read(path.join(dir, "keys", `map-${k}.json`)),
      options: fs.existsSync(f("options-only.json")) ? read(f("options-only.json")) : {},
      answers: fs.existsSync(f("answers.json")) ? read(f("answers.json")) : {}});
  });
  const closedFile = path.join(HERE, "disputes.json");
  const closed = fs.existsSync(closedFile) ? (read(closedFile)[`L${n}`] || {}) : {};
  const card = aggregate({bank, steps, runs, closedDisputes: closed});
  const name = path.basename(dir);
  const prevName = fs.readdirSync(RUNS).filter(d => new RegExp(`-L${n}(-r\\d+)?$`).test(d) && order(d) < order(name)
    && fs.existsSync(path.join(RUNS, d, "scorecard.json"))).sort((a, b) => order(a).localeCompare(order(b))).pop();
  const prev = prevName ? read(path.join(RUNS, prevName, "scorecard.json")) : null;
  const d = diff(prev, card);
  write(path.join(dir, "scorecard.json"), {...card, previous: prevName || null, diff: d});
  write(path.join(dir, "scorecard.md"), toMarkdown(card, d, `Lesson ${n}, ${bank.title} (${name}${prevName ? ", vs " + prevName : ""})`));
  console.log(fs.readFileSync(path.join(dir, "scorecard.md"), "utf8"));
}

const [cmd, arg] = process.argv.slice(2), runs = +opt("runs", 3), model = opt("model", "sonnet");
const dirOf = a => path.resolve(fs.existsSync(a) ? a : path.join(RUNS, a));
if(cmd === "prepare") await prepare(+arg, runs);
else if(cmd === "sim") await sim(dirOf(arg), runs, model);
else if(cmd === "score") score(dirOf(arg));
else if(cmd === "all"){ const dir = await prepare(+arg, runs); await sim(dir, runs, model); score(dir); }
else { console.error("usage: run.mjs prepare <lesson> | sim <folder> | score <folder> | all <lesson>  [--runs 3] [--model sonnet]"); process.exit(2); }

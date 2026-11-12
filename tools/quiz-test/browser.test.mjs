// Drives /quiz/?lesson=N in headless Chrome over HTTP, with storage available and with it blocked.
// Answers even-numbered questions right and skips odd ones, then checks the scorecard and the stored boxes.
// Run: node tools/quiz-test/browser.test.mjs   (Node 22+, Chrome)
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import {spawn} from "node:child_process";

const SITE = path.resolve(import.meta.dirname, "../../site");
const CHROMES = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/chromium"];
const TYPES = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json"};

const server = http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if(p.endsWith("/")) p += "index.html";
  const f = path.join(SITE, p);
  if(!f.startsWith(SITE) || !fs.existsSync(f)){ res.writeHead(404); return res.end(); }
  res.writeHead(200, {"content-type": TYPES[path.extname(f)] || "application/octet-stream"}); fs.createReadStream(f).pipe(res);
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;

const profile = fs.mkdtempSync(path.join(os.tmpdir(), "quiz-test-"));
const chrome = spawn(CHROMES.find(fs.existsSync), ["--headless=new", "--disable-gpu", "--no-first-run", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"], {stdio: ["ignore", "ignore", "pipe"]});
const port = await new Promise((res, rej) => { let b = ""; const t = setTimeout(() => rej(new Error("Chrome did not start")), 15000);
  chrome.stderr.on("data", d => { b += d; const m = b.match(/DevTools listening on ws:\/\/[^:]+:(\d+)/); if(m){ clearTimeout(t); res(m[1]); } }); });

async function open(){
  const t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, {method: "PUT"})).json();
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener("open", r, {once: true}));
  let id = 0; const pend = new Map(), errors = [];
  ws.addEventListener("message", ev => { const m = JSON.parse(ev.data);
    if(m.id && pend.has(m.id)){ const p = pend.get(m.id); pend.delete(m.id); m.error ? p.rej(new Error(m.error.message)) : p.res(m.result); }
    if(m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
    if(m.method === "Runtime.consoleAPICalled" && m.params.type === "error") errors.push(m.params.args.map(a => a.value).join(" ")); });
  const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pend.set(i, {res, rej}); ws.send(JSON.stringify({id: i, method, params})); });
  await send("Page.enable"); await send("Runtime.enable");
  const evaluate = async expr => { const r = await send("Runtime.evaluate", {expression: expr, awaitPromise: true, returnByValue: true});
    if(r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text); return r.result.value; };
  return {send, evaluate, errors, close: async () => { ws.close(); await fetch(`http://127.0.0.1:${port}/json/close/${t.id}`).catch(() => {}); }};
}

// Runs inside the page: answer every question (even index right, odd skipped), return what happened.
const PLAY = `(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  for(let t = 0; t < 50 && !document.querySelector(".qprompt"); t++) await sleep(100);
  const banks = await Promise.all([1,2,3].map(n => fetch("banks/l"+n+".json").then(r => r.json())));
  const all = banks.flatMap(b => b.questions);
  const shown = [];
  for(let i = 0; i < 10; i++){
    const prompt = document.querySelector(".qprompt").textContent;
    const q = all.find(x => x.prompt === prompt); shown.push(q.id);
    if(i % 2 === 0){
      if(q.kind === "number"){ const inp = document.querySelector(".numq input"); inp.value = String(q.answer[0]); inp.dispatchEvent(new Event("input")); }
      else q.answer.forEach(ai => { const inp = document.querySelector('.opts input[value="'+ai+'"]'); inp.click(); });
      const next = [...document.querySelectorAll(".actions .btn.primary")].pop();
      if(next.disabled) return {error: "Next disabled after answering " + q.id};
      next.click();
    } else {
      [...document.querySelectorAll(".actions button")].find(b => b.textContent === "I don't know").click();
    }
    await sleep(20);
  }
  const res = window.__quizResults || [];
  let stored = null; try{ stored = JSON.parse(localStorage.getItem("ael-quiz-v1")); }catch(e){ stored = "blocked"; }
  return {shown, ids: res.map(r => r.q.id), lessons: res.map(r => r.q.lesson), correct: res.map(r => r.correct),
    score: document.querySelector(".score b")?.textContent, warn: !!document.querySelector(".note.warn"),
    study: [...document.querySelectorAll(".study a")].map(a => a.getAttribute("href")),
    review: document.querySelectorAll(".rv").length, stored};
})()`;

let failures = 0;
const check = (cond, msg) => { console.log((cond ? "  ok   " : "  FAIL ") + msg); if(!cond) failures++; };

for(const blocked of [false, true]){
  for(const lesson of [1, 2, 3]){
    console.log(`lesson ${lesson}, storage ${blocked ? "BLOCKED" : "available"}`);
    const p = await open();
    if(blocked) await p.send("Page.addScriptToEvaluateOnNewDocument", {source:
      `Object.defineProperty(window, "localStorage", {get(){ throw new DOMException("blocked", "SecurityError"); }});`});
    await p.send("Page.navigate", {url: `${base}/quiz/?lesson=${lesson}`});
    await new Promise(r => setTimeout(r, 400));
    const r = await p.evaluate(PLAY);
    check(!r.error, r.error || "every question answerable");
    check(r.ids.length === 10, "10 results");
    check(new Set(r.ids).size === 10, "no repeats within the attempt");
    check(JSON.stringify(r.shown) === JSON.stringify(r.ids), "results match the questions shown, in order");
    const own = r.lessons.filter(l => l === lesson).length;
    check(lesson === 1 ? own === 10 : own === 7 && r.lessons.filter(l => l < lesson).length === 3, `mix: ${own} from lesson ${lesson}, ${10 - own} earlier`);
    check(r.correct.every((c, i) => c === (i % 2 === 0)), "even answered right, odd skipped → missed");
    check(r.score === "5 / 10", "scorecard shows 5 / 10");
    check(r.review === 10, "every question reviewed with its why");
    check(r.study.length > 0 && r.study.every(h => /^\.\.\/lessons\/llm-foundations-\d\/#ch-/.test(h)), "study-more links point at lesson chapters");
    if(blocked){
      check(r.warn, "page says storage is blocked");
      check(r.stored === "blocked", "storage really was blocked");
    } else {
      check(!r.warn, "no storage warning");
      check(r.ids.every((id, i) => r.stored[id] && r.stored[id].box === (i % 2 === 0 ? 2 : 1)), "boxes stored: right → 2, missed → 1");
    }
    check(p.errors.length === 0, "no JS errors" + (p.errors.length ? ": " + p.errors.join(" | ") : ""));
    await p.close();
  }
}

// Second attempt in the same browser: box moves continue (right twice → 3, missed then right → 2).
{
  console.log("lesson 1 twice, storage available: box moves across attempts");
  const p = await open();
  await p.send("Page.navigate", {url: `${base}/quiz/?lesson=1`});
  await new Promise(r => setTimeout(r, 400));
  const before = await p.evaluate(`JSON.parse(localStorage.getItem("ael-quiz-v1"))`);
  const r = await p.evaluate(PLAY);
  const ok = r.ids.every((id, i) => {
    const prev = before[id] ? before[id].box : 1, want = i % 2 === 0 ? Math.min(prev + 1, 4) : 1;
    return r.stored[id].box === want;
  });
  check(ok, "each box moved one up when right, back to 1 when missed");
  await p.close();
}

chrome.kill(); server.close();
await new Promise(r => chrome.once("exit", r));
try{ fs.rmSync(profile, {recursive: true, force: true, maxRetries: 5}); }catch(e){}
console.log(failures ? `${failures} failing` : "all passed");
process.exit(failures ? 1 : 0);

// Minimal headless Chrome over the DevTools protocol, plus a static server for site/. Node 22+, no dependencies.
// Same approach as tools/site-qe/qe.mjs and tools/quiz-test/browser.test.mjs.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import {spawn} from "node:child_process";

const CHROMES = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/chromium"];
const TYPES = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png"};

export async function serve(root){
  const server = http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
    if(p.endsWith("/")) p += "index.html";
    const f = path.join(root, p);
    if(!f.startsWith(root) || !fs.existsSync(f)){ res.writeHead(404); return res.end(); }
    res.writeHead(200, {"content-type": TYPES[path.extname(f)] || "application/octet-stream"}); fs.createReadStream(f).pipe(res);
  });
  await new Promise(r => server.listen(0, "127.0.0.1", r));
  return {base: `http://127.0.0.1:${server.address().port}`, close: () => server.close()};
}

export async function launch(){
  const exe = CHROMES.find(fs.existsSync); if(!exe) throw new Error("Chrome not found");
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "cdp-"));
  const chrome = spawn(exe, ["--headless=new", "--disable-gpu", "--no-first-run", "--hide-scrollbars", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "about:blank"], {stdio: ["ignore", "ignore", "pipe"]});
  const port = await new Promise((res, rej) => { let b = ""; const t = setTimeout(() => rej(new Error("Chrome did not start")), 15000);
    chrome.stderr.on("data", d => { b += d; const m = b.match(/DevTools listening on ws:\/\/[^:]+:(\d+)/); if(m){ clearTimeout(t); res(m[1]); } }); });

  async function open(){
    const t = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, {method: "PUT"})).json();
    const ws = new WebSocket(t.webSocketDebuggerUrl);
    await new Promise(r => ws.addEventListener("open", r, {once: true}));
    let id = 0; const pend = new Map(), errors = [];
    ws.addEventListener("message", ev => { const m = JSON.parse(ev.data);
      if(m.id && pend.has(m.id)){ const p = pend.get(m.id); pend.delete(m.id); m.error ? p.rej(new Error(m.error.message)) : p.res(m.result); }
      if(m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text); });
    const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pend.set(i, {res, rej}); ws.send(JSON.stringify({id: i, method, params})); });
    await send("Page.enable"); await send("Runtime.enable");
    const evaluate = async expr => { const r = await send("Runtime.evaluate", {expression: expr, awaitPromise: true, returnByValue: true});
      if(r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text); return r.result.value; };
    const goto = async url => { const loaded = new Promise(r => { const h = ev => { if(JSON.parse(ev.data).method === "Page.loadEventFired"){ ws.removeEventListener("message", h); r(); } }; ws.addEventListener("message", h); });
      await send("Page.navigate", {url}); await loaded; };
    return {send, evaluate, goto, errors, close: async () => { ws.close(); await fetch(`http://127.0.0.1:${port}/json/close/${t.id}`).catch(() => {}); }};
  }
  const exited = new Promise(r => chrome.on("exit", r));
  return {open, close: async () => { chrome.kill(); await exited;
    try{ fs.rmSync(profile, {recursive: true, force: true, maxRetries: 3}); }catch(e){} }};
}

#!/usr/bin/env node
// site-qe: behavior tests for a static site in real headless Chrome, driven over the DevTools
// protocol. No dependencies: Node >= 22 (built-in WebSocket) and Chrome or Chromium.
//
// It catches what screenshots miss: what goes wrong while scrolling, clicking, toggling or
// stepping through a page. Every page runs twice: normally, and with reduced motion emulated.
//
//   node qe.mjs SITE_DIR                 test every .html page under SITE_DIR
//   node qe.mjs SITE_DIR -p index.html   test one page (repeatable)
//   node qe.mjs SITE_DIR --json          machine-readable report
// Exit code 1 if any check fails.
//
// Checks: width-use (no narrow centered column with big empty sides) · js-errors · cls (<= 0.1 over the first 1.5 s, before any interaction) · h-overflow · pinned (sticky/fixed stay put to the end of the
// page) · fonts (controls use the body font) · names (buttons have accessible names) · toggles
// (#themeBtn #navBtn #tocBtn change state + aria, and toggle back; collapsing the nav widens the content) · lesson-walk (every step of a
// #next stepper renders without errors, Next above the fold) · links (internal hrefs resolve) ·
// reduced-motion (nothing animating after interactions when reduced motion is on).
import { spawn } from "node:child_process";
import { existsSync, readFileSync, readdirSync, statSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const CHROMES = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"];

const HEAD = `window.__qe={errors:[],cls:0};addEventListener('error',e=>__qe.errors.push(String(e.message||e)));
addEventListener('unhandledrejection',e=>__qe.errors.push('promise: '+String(e.reason)));
try{new PerformanceObserver(l=>{for(const e of l.getEntries()){if(!e.hadRecentInput)__qe.cls+=e.value}}).observe({type:'layout-shift',buffered:true})}catch(e){}`;

// Runs inside the page; returns the results object.
const PROBE = `(async()=>{
const R={}, sleep=ms=>new Promise(r=>setTimeout(r,ms)), root=document.documentElement;
const fail=(k,m)=>{(R[k]=R[k]||{ok:true,notes:[]}); R[k].ok=false; R[k].notes.push(m)}, pass=k=>{R[k]=R[k]||{ok:true,notes:[]}};
await sleep(1500);
const clsLoad = __qe.cls;  // CLS is a load-time metric; scripted clicks below would otherwise count as shifts
R.reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
pass('h-overflow'); if(root.scrollWidth > innerWidth + 1) fail('h-overflow','page is '+root.scrollWidth+'px wide in a '+innerWidth+'px viewport');
pass('fonts'); pass('names');
const bodyFont = getComputedStyle(document.body).fontFamily.split(',')[0].trim();
document.querySelectorAll('button, input, select, textarea').forEach(el=>{
  const f = getComputedStyle(el).fontFamily.split(',')[0].trim();
  if(f !== bodyFont && !/mono|courier|menlo|consolas/i.test(f)) fail('fonts', (el.id||el.tagName.toLowerCase())+' uses '+f+' (body: '+bodyFont+')');
});
document.querySelectorAll('button').forEach(b=>{ if(!(b.getAttribute('aria-label')||b.textContent.trim()||b.title)) fail('names','button without a name: '+b.outerHTML.slice(0,80)); });
// width-use: on desktop, content shouldn't sit in a narrow centered column with large unused space on both sides.
pass('width-use');
{ const col = document.querySelector('main .wrap') || document.querySelector('main');
  if(col && innerWidth >= 1280){ const r = col.getBoundingClientRect(), right = innerWidth - r.right;
    if(r.left > 300 && right > 300) fail('width-use', 'content is a '+Math.round(r.width)+'px column with '+Math.round(r.left)+'px left and '+Math.round(right)+'px right unused at '+innerWidth+'px'); } }
pass('pinned');
const pinned = [...document.querySelectorAll('body *')].filter(el=>{ const p=getComputedStyle(el).position, r=el.getBoundingClientRect(); return (p==='sticky'||p==='fixed') && r.width>0 && r.height>0; });
const H = root.scrollHeight - innerHeight;
if(H > 40) for(const el of pinned){
  const cs=getComputedStyle(el), topPx=parseFloat(cs.top);
  const name=el.tagName.toLowerCase()+(typeof el.className==='string'&&el.className?'.'+el.className.split(' ')[0]:'')+(el.id?'#'+el.id:'');
  if(isNaN(topPx)) continue;
  scrollTo({top:0,behavior:'instant'}); await sleep(80);
  const start=el.getBoundingClientRect().top;
  for(const f of [0.25,0.5,0.75,1]){
    scrollTo({top:Math.round(H*f),behavior:'instant'}); await sleep(250);
    // Re-read the intended position each step: CSS top plus any transform (e.g. a header sliding away on purpose).
    const now=getComputedStyle(el), nowTop=parseFloat(now.top), ty = now.transform && now.transform!=='none' ? new DOMMatrix(now.transform).m42 : 0;
    const t=el.getBoundingClientRect().top, expect = now.position==='fixed' ? nowTop+ty : Math.min(start, nowTop+ty);
    if(Math.abs(t-expect) > 2) fail('pinned', name+' at top='+Math.round(t)+' at '+Math.round(f*100)+'% scroll; should be pinned at '+Math.round(expect));
  }
}
scrollTo({top:0,behavior:'instant'}); await sleep(150);
pass('toggles');
async function toggle(id, read){
  const b=document.getElementById(id); if(!b || b.offsetParent===null) return;
  const a0=read(), x0=b.getAttribute('aria-expanded')??b.getAttribute('aria-pressed');
  b.click(); await sleep(500);
  const a1=read(), x1=b.getAttribute('aria-expanded')??b.getAttribute('aria-pressed');
  if(a0===a1) fail('toggles','#'+id+' did not change state');
  if(x0!==null && x0===x1) fail('toggles','#'+id+' aria state did not update');
  b.click(); await sleep(500);
  if(read()!==a0) fail('toggles','#'+id+' did not toggle back');
}
await toggle('themeBtn', ()=>root.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));  // effective theme, not the raw attribute
await toggle('navBtn', ()=>String(root.classList.contains('nav-collapsed')));
// Collapsing the side nav must give the content real extra width, not just hide the nav.
{ const nb=document.getElementById('navBtn'), w=document.querySelector('main .wrap');
  if(nb && w && nb.offsetParent!==null && innerWidth>=1200){
    const before=w.getBoundingClientRect().width; nb.click(); await sleep(500);
    const after=w.getBoundingClientRect().width; nb.click(); await sleep(500);
    if(after - before < 150) fail('toggles','#navBtn collapsed the nav but content only grew '+Math.round(after-before)+'px ('+Math.round(before)+' → '+Math.round(after)+')');
  } }
await toggle('tocBtn', ()=>String(root.classList.contains('toc-collapsed')));
const next=document.getElementById('next');
if(next){
  pass('lesson-walk');
  const first=document.querySelector('[data-go="0"]'); if(first){ first.click(); await sleep(400); }
  let steps=0, guard=0;
  while(guard++ < 80){
    steps++;
    const card=document.getElementById('card');
    if(!card || !card.textContent.trim()) fail('lesson-walk','step '+steps+' rendered empty');
    const nb=next.getBoundingClientRect(); if(nb.bottom > innerHeight+1) fail('lesson-walk','step '+steps+': Next below the fold ('+Math.round(nb.bottom)+' > '+innerHeight+')');
    card.querySelectorAll('.visual button').forEach(b=>{ try{b.click()}catch(e){} });
    card.querySelectorAll('.visual input[type=range]').forEach(r=>{ r.value=r.max; r.dispatchEvent(new Event('input')); });
    if(next.disabled) break;
    const before=card.textContent; next.click(); await sleep(450);
    if(document.getElementById('card').textContent===before) fail('lesson-walk','step '+steps+': Next did not advance');
  }
  R['lesson-walk'].notes.push(steps+' steps walked');
}
if(R.reduced){
  pass('reduced-motion'); await sleep(100);
  const run=document.getAnimations().filter(a=>a.playState==='running');
  if(run.length) fail('reduced-motion', run.length+' animation(s) running: '+run.slice(0,3).map(a=>a.animationName||a.transitionProperty||a.constructor.name).join(', '));
}
pass('js-errors'); __qe.errors.forEach(e=>fail('js-errors',e));
pass('cls'); R.clsValue=+clsLoad.toFixed(4); if(clsLoad>0.1) fail('cls','CLS '+clsLoad.toFixed(4)+' > 0.1 during load');
return JSON.stringify(R);
})()`;

function chromePath(){ const c = CHROMES.find(existsSync); if(!c){ console.error("site-qe: Chrome or Chromium not found"); process.exit(2); } return c; }

async function launch(){
  const profile = mkdtempSync(path.join(tmpdir(), "site-qe-"));
  const proc = spawn(chromePath(), ["--headless=new","--disable-gpu","--no-first-run","--remote-debugging-port=0",`--user-data-dir=${profile}`,"--window-size=1600,1000","about:blank"], {stdio:["ignore","ignore","pipe"]});
  const wsUrl = await new Promise((res, rej)=>{ let buf=""; const t=setTimeout(()=>rej(new Error("Chrome did not start")),15000);
    proc.stderr.on("data", d=>{ buf+=d; const m=buf.match(/DevTools listening on (ws:\/\/\S+)/); if(m){ clearTimeout(t); res(m[1]); } }); });
  return { proc, profile, port: new URL(wsUrl).port };
}

function cdp(ws){
  let id = 0; const pending = new Map(), listeners = [];
  ws.addEventListener("message", ev=>{ const m = JSON.parse(ev.data);
    if(m.id && pending.has(m.id)){ const {res,rej}=pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); }
    else listeners.forEach(l=>l(m)); });
  return { send:(method, params={})=>new Promise((res,rej)=>{ const i=++id; pending.set(i,{res,rej}); ws.send(JSON.stringify({id:i, method, params})); }),
           once:(method)=>new Promise(res=>{ const l=m=>{ if(m.method===method){ listeners.splice(listeners.indexOf(l),1); res(m.params); } }; listeners.push(l); }) };
}

async function runPage(port, file, reduced){
  const target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, {method:"PUT"})).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej)=>{ ws.addEventListener("open", res, {once:true}); ws.addEventListener("error", rej, {once:true}); });
  const c = cdp(ws);
  try{
    await c.send("Page.enable"); await c.send("Runtime.enable");
    await c.send("Emulation.setDeviceMetricsOverride", {width:1600, height:1000, deviceScaleFactor:1, mobile:false});
    await c.send("Emulation.setEmulatedMedia", {features:[{name:"prefers-reduced-motion", value: reduced ? "reduce" : "no-preference"}]});
    await c.send("Page.addScriptToEvaluateOnNewDocument", {source: HEAD + ";try{localStorage.clear()}catch(e){}"});
    const loaded = c.once("Page.loadEventFired");
    await c.send("Page.navigate", {url: "file://" + path.resolve(file)});
    await Promise.race([loaded, new Promise(r=>setTimeout(r,15000))]);
    const r = await c.send("Runtime.evaluate", {expression: PROBE, awaitPromise:true, returnByValue:true, timeout:120000});
    if(r.exceptionDetails) return {probe:{ok:false, notes:["probe threw: "+(r.exceptionDetails.exception?.description||r.exceptionDetails.text)]}};
    return JSON.parse(r.result.value);
  } finally { ws.close(); await fetch(`http://127.0.0.1:${port}/json/close/${target.id}`).catch(()=>{}); }
}

function checkLinks(file){
  const res = {ok:true, notes:[]}, s = readFileSync(file, "utf8");
  for(const [, h0] of s.matchAll(/href="([^"']+)"/g)){
    if(/^(https?:|mailto:|tel:|#|data:)/.test(h0) || h0.includes("+")) continue;
    const h = h0.split("#")[0].split("?")[0]; if(!h) continue;
    let t = path.normalize(path.join(path.dirname(file), h));
    if(h.endsWith("/") || (existsSync(t) && statSync(t).isDirectory())) t = path.join(t, "index.html");
    if(!existsSync(t)){ res.ok=false; res.notes.push("broken: "+h0); }
  }
  return res;
}

function htmlFiles(dir){ const out=[]; for(const e of readdirSync(dir,{withFileTypes:true})){ const p=path.join(dir,e.name);
  if(e.isDirectory()) out.push(...htmlFiles(p)); else if(e.name.endsWith(".html") && !e.name.startsWith(".qe-")) out.push(p); } return out; }

const args = process.argv.slice(2), site = args[0];
if(!site){ console.error("usage: node qe.mjs SITE_DIR [-p page.html]... [--json]"); process.exit(2); }
const pages = []; for(let i=1;i<args.length;i++) if(args[i]==="-p") pages.push(path.join(site, args[++i]));
const files = pages.length ? pages : htmlFiles(site).sort();
const json = args.includes("--json");
const {proc, profile, port} = await launch();
const report = {}; let failed = 0;
try{
  for(const f of files){
    const rel = path.relative(site, f);
    // Hard limit per page run: a hung page is a failure, not a stall.
    const limit = (p, label) => Promise.race([p, new Promise(res=>setTimeout(()=>res({probe:{ok:false, notes:[label+": no result within 90 s (page hung)"]}}), 90000))]);
    if(!json) process.stderr.write(`  testing ${rel} …\n`);
    const normal = await limit(runPage(port, f, false), "normal"), reduced = await limit(runPage(port, f, true), "reduced motion");
    const checks = Object.fromEntries(Object.entries(normal).filter(([,v])=>v && typeof v==="object"));
    if(reduced["reduced-motion"]) checks["reduced-motion"] = reduced["reduced-motion"];
    for(const k of ["js-errors","lesson-walk","pinned","toggles"]) if(reduced[k] && !reduced[k].ok) checks[k+" (reduced motion)"] = reduced[k];
    checks.links = checkLinks(f);
    report[rel] = {cls: normal.clsValue, checks};
    failed += Object.values(checks).filter(c=>!c.ok).length;
  }
} finally {
  await new Promise(res=>{ proc.once("exit", res); proc.kill(); setTimeout(res, 3000); });
  try{ rmSync(profile, {recursive:true, force:true, maxRetries:5, retryDelay:200}); }catch(e){}
}
if(json) console.log(JSON.stringify(report, null, 2));
else {
  for(const [rel, r] of Object.entries(report)){
    const bad = Object.entries(r.checks).filter(([,c])=>!c.ok);
    console.log(`${bad.length ? "FAIL" : "pass"}  ${rel}  (CLS ${r.cls})`);
    for(const [k,c] of Object.entries(r.checks)) if(!c.ok || k==="lesson-walk") for(const n of c.notes.slice(0,6)) console.log(`      ${k}: ${n}`);
  }
  console.log(`\n${Object.keys(report).length} pages, ${failed} failing check(s)`);
}
process.exit(failed ? 1 : 0);

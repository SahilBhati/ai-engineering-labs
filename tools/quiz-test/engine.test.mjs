// Scripted checks for site/assets/quiz/engine.js and the banks. Run: node tools/quiz-test/engine.test.mjs
// No dependencies (node:test, node:assert).
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {createRequire} from "node:module";

const root = path.resolve(import.meta.dirname, "../..");
const Quiz = createRequire(import.meta.url)(path.join(root, "site/assets/quiz/engine.js"));
const banks = [1, 2, 3].map(n => JSON.parse(fs.readFileSync(path.join(root, `site/quiz/banks/l${n}.json`), "utf8")));

// A Storage stand-in, and one that throws on every call (storage blocked).
const memStorage = () => { const m = new Map(); return {getItem: k => m.has(k) ? m.get(k) : null, setItem: (k, v) => m.set(k, String(v))}; };
const blocked = {getItem(){ throw new Error("SecurityError"); }, setItem(){ throw new Error("SecurityError"); }};

test("banks follow the interface", () => {
  const ids = new Set();
  for(const b of banks){
    for(const k of ["lesson", "title", "url", "concepts", "questions"]) assert.ok(k in b, k);
    for(const q of b.questions){
      assert.ok(!ids.has(q.id), "duplicate id " + q.id); ids.add(q.id);
      assert.ok(b.concepts[q.concept], q.id + " concept");
      assert.ok(["single", "multi", "number"].includes(q.kind), q.id);
      assert.ok(q.why && q.prompt, q.id);
      if(q.kind !== "number") assert.ok(q.answer.every(i => i >= 0 && i < q.options.length), q.id);
    }
  }
});

test("no repeats within an attempt, 7 own + 3 earlier", () => {
  for(let seed = 1; seed <= 500; seed++){
    for(const lesson of [2, 3]){
      const a = Quiz.buildAttempt(banks, lesson, {store: Quiz.createStore(memStorage()), rng: Quiz.seededRng(seed)});
      assert.equal(a.length, 10);
      assert.equal(new Set(a.map(q => q.id)).size, 10, "repeat at seed " + seed);
      assert.equal(a.filter(q => q.lesson === lesson).length, 7);
      assert.equal(a.filter(q => q.lesson < lesson).length, 3);
    }
  }
});

test("lesson 1 draws all 10 from its own bank", () => {
  for(let seed = 1; seed <= 100; seed++){
    const a = Quiz.buildAttempt(banks, 1, {rng: Quiz.seededRng(seed)});
    assert.equal(a.length, 10);
    assert.ok(a.every(q => q.lesson === 1));
    assert.equal(new Set(a.map(q => q.id)).size, 10);
  }
});

test("Leitner box moves: correct up one (cap 4), wrong back to 1", () => {
  const s = Quiz.createStore(memStorage());
  assert.equal(s.box("x"), 0);              // never seen
  assert.equal(s.record("x", true), 2);     // first sight counts as box 1, correct → 2
  assert.equal(s.record("x", true), 3);
  assert.equal(s.record("x", true), 4);
  assert.equal(s.record("x", true), 4);     // capped
  assert.equal(s.record("x", false), 1);    // wrong → box 1
  assert.equal(s.record("y", false), 1);
});

test("memory persists through storage and survives a reload", () => {
  const st = memStorage();
  Quiz.createStore(st).record("L1-tokens-01", true);
  assert.equal(Quiz.createStore(st).box("L1-tokens-01"), 2);
});

test("works with storage blocked", () => {
  const s = Quiz.createStore(blocked);
  assert.equal(s.persistent, false);
  assert.equal(s.record("x", true), 2);     // still tracked in memory for this page
  const a = Quiz.buildAttempt(banks, 3, {store: s, rng: Quiz.seededRng(7)});
  assert.equal(new Set(a.map(q => q.id)).size, 10);
  const nullStore = Quiz.createStore(null);
  assert.equal(nullStore.persistent, false);
});

test("draw is weighted by box: box1 8, box2 4, box3 2, box4 1, unseen 6", () => {
  const pool = ["b1", "b2", "b3", "b4", "new"].map(id => ({id}));
  const st = memStorage(), s = Quiz.createStore(st);
  s.record("b1", false); s.record("b2", true);
  s.record("b3", true); s.record("b3", true);
  s.record("b4", true); s.record("b4", true); s.record("b4", true);
  assert.deepEqual(["b1", "b2", "b3", "b4", "new"].map(id => s.box(id)), [1, 2, 3, 4, 0]);
  const rng = Quiz.seededRng(42), counts = {}, N = 42000;
  for(let i = 0; i < N; i++){ const [q] = Quiz.leitnerStrategy(pool, 1, {store: s, rng}); counts[q.id] = (counts[q.id] || 0) + 1; }
  const expect = {b1: 8, b2: 4, b3: 2, b4: 1, new: 6}, total = 21;
  for(const k in expect) assert.ok(Math.abs(counts[k] / N - expect[k] / total) < 0.01, k + " " + counts[k] / N);
});

test("a custom strategy plugs in without touching the UI", () => {
  const firstN = (pool, n) => pool.slice(0, n);
  const a = Quiz.buildAttempt(banks, 2, {strategy: firstN, rng: Quiz.seededRng(1)});
  const ids = a.map(q => q.id).sort();
  const expect = banks[1].questions.slice(0, 7).map(q => q.id).concat(banks[0].questions.slice(0, 3).map(q => q.id)).sort();
  assert.deepEqual(ids, expect);
});

test("number tolerance is relative", () => {
  const q = {kind: "number", answer: [2.68], tol: 0.08};
  assert.ok(Quiz.grade(q, "2.68"));
  assert.ok(Quiz.grade(q, "2.5"));          // GiB answer, within 8%
  assert.ok(!Quiz.grade(q, "2.4"));
  assert.ok(Quiz.grade({kind: "number", answer: [8002000], tol: 0.05}, "8,000,000"));
  assert.ok(Quiz.grade({kind: "number", answer: [5], tol: 0}, " 5 "));
  assert.ok(!Quiz.grade({kind: "number", answer: [5], tol: 0}, "5.1"));
  assert.ok(Quiz.grade({kind: "number", answer: [0], tol: 0}, "0"));
  assert.ok(!Quiz.grade({kind: "number", answer: [5]}, "five"));
  assert.ok(!Quiz.grade({kind: "number", answer: [5]}, ""));
  assert.ok(Quiz.grade({kind: "number", answer: [6.3], tol: 0.03}, "6.3e0"));
});

test("single and multi grading; multi is all or nothing", () => {
  assert.ok(Quiz.grade({kind: "single", answer: [2]}, [2]));
  assert.ok(!Quiz.grade({kind: "single", answer: [2]}, [1]));
  assert.ok(!Quiz.grade({kind: "single", answer: [2]}, []));
  assert.ok(Quiz.grade({kind: "multi", answer: [0, 1, 2]}, [2, 0, 1]));
  assert.ok(!Quiz.grade({kind: "multi", answer: [0, 1, 2]}, [0, 1]));
  assert.ok(!Quiz.grade({kind: "multi", answer: [0, 1, 2]}, [0, 1, 2, 3]));
});

test("scorecard: by lesson, by concept, study-more links, copy prompt", () => {
  const a = Quiz.buildAttempt(banks, 3, {rng: Quiz.seededRng(3)});
  const results = a.map((q, i) => ({q, response: i < 4 ? [] : q.answer.slice(), correct: i >= 4}));
  results.forEach(r => { if(r.q.kind === "number") r.response = r.correct ? String(r.q.answer[0]) : ""; });
  const sc = Quiz.scorecard(results, banks);
  assert.equal(sc.right, 6); assert.equal(sc.total, 10);
  assert.equal(sc.byLesson.reduce((s, l) => s + l.total, 0), 10);
  assert.equal(sc.byConcept.reduce((s, c) => s + c.total, 0), 10);
  // Every concept with a miss is in study-more, and only those.
  assert.deepEqual(sc.studyMore.map(c => c.lesson + ":" + c.concept).sort(),
    sc.byConcept.filter(c => c.right < c.total).map(c => c.lesson + ":" + c.concept).sort());
  for(const c of sc.studyMore) assert.match(c.href, /^\.\.\/lessons\/llm-foundations-\d\/#ch-[a-z0-9-]+$/);
  const p = Quiz.copyPrompt(results, banks);
  assert.match(p, /small worked example/);
  assert.equal((p.match(/My answer:/g) || []).length, 4);
  assert.equal((p.match(/Right answer:/g) || []).length, 4);
  assert.equal(Quiz.copyPrompt(results.map(r => ({...r, correct: true})), banks), "");
});

test("every concept anchor exists in its lesson page", () => {
  for(const b of banks){
    const html = fs.readFileSync(path.join(root, "site/quiz", b.url, "index.html"), "utf8");
    const chs = JSON.parse(html.match(/const CHS = (\[.*?\]);/)[1]).map(c => "ch-" + c[0].toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
    for(const [k, c] of Object.entries(b.concepts)) assert.ok(chs.includes(c.anchor), b.lesson + " " + k + " → " + c.anchor);
  }
});

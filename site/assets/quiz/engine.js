// Quiz engine: draw, score, remember. Knows nothing about LLMs; question banks are data.
//
// Bank format (a fixed interface; new lessons add banks, never change this shape):
//   { lesson, title, url, concepts: { key: { label, anchor } },
//     questions: [ { id, concept, kind: "single"|"multi"|"number", prompt, options?, answer, tol?, unit?, why } ] }
//   answer: option indices for single/multi, [value] for number. tol: relative tolerance (0.05 = within 5%).
//   Question IDs are stable forever: the memory store is keyed by them.
//
// Patterns: the draw policy is a Strategy (any function (pool, n, ctx) -> questions), so a later
// scheduler can replace Leitner without touching the UI. The memory store is an Adapter over
// localStorage that falls back to an in-memory map when storage is blocked.
(function(root){
  "use strict";

  const BOX_MAX = 4;
  // Draw weight per Leitner box; 0 = never seen. Missed questions come back most often.
  const LEITNER_WEIGHTS = {0:6, 1:8, 2:4, 3:2, 4:1};

  // ---------- memory store ----------
  function createStore(storage, key){
    key = key || "ael-quiz-v1";
    let data = {}, persistent = false;
    try{
      if(storage){ data = JSON.parse(storage.getItem(key) || "{}") || {}; persistent = true; }
    }catch(e){ data = {}; persistent = false; }
    const save = () => {
      if(!persistent) return;
      try{ storage.setItem(key, JSON.stringify(data)); }catch(e){ persistent = false; }
    };
    return {
      get persistent(){ return persistent; },
      box(id){ return data[id] ? data[id].box : 0; },
      // Leitner rule: correct moves up one box (first sight counts as box 1), wrong goes back to box 1.
      record(id, correct){
        const b = data[id] ? data[id].box : 1;
        data[id] = {box: correct ? Math.min(b + 1, BOX_MAX) : 1, seen: ((data[id] && data[id].seen) || 0) + 1};
        save();
        return data[id].box;
      },
      reset(){ data = {}; save(); },
      dump(){ return JSON.parse(JSON.stringify(data)); }
    };
  }

  // ---------- draw strategies ----------
  // Weighted random without replacement: no question can appear twice in one draw.
  function weightedSample(pool, n, weightOf, rng){
    const left = pool.slice(), out = [];
    while(out.length < n && left.length){
      const w = left.map(weightOf), total = w.reduce((a, b) => a + b, 0);
      let r = rng() * total, i = 0;
      while(i < left.length - 1 && r >= w[i]){ r -= w[i]; i++; }
      out.push(left.splice(i, 1)[0]);
    }
    return out;
  }
  function leitnerStrategy(pool, n, ctx){
    return weightedSample(pool, n, q => LEITNER_WEIGHTS[ctx.store.box(q.id)] || 1, ctx.rng);
  }

  // ---------- attempt ----------
  // Lesson N: `own` questions from its bank, the rest from earlier lessons' banks pooled.
  // Lesson 1 (or too few earlier questions) fills from its own bank.
  function buildAttempt(banks, lesson, opts){
    opts = opts || {};
    const size = opts.size || 10, own = Math.min(opts.own || 7, size);
    const strategy = opts.strategy || leitnerStrategy;
    const ctx = {store: opts.store || createStore(null), rng: opts.rng || Math.random};
    const tag = b => b.questions.map(q => Object.assign({lesson: b.lesson}, q));
    const mine = banks.filter(b => b.lesson === lesson).flatMap(tag);
    const earlier = banks.filter(b => b.lesson < lesson).flatMap(tag);
    const fromEarlier = strategy(earlier, Math.min(size - own, earlier.length), ctx);
    const fromMine = strategy(mine, size - fromEarlier.length, ctx);
    const picked = fromMine.concat(fromEarlier);
    // Defensive: a custom strategy must not break the no-repeat promise.
    const seen = new Set();
    return shuffle(picked.filter(q => !seen.has(q.id) && seen.add(q.id)), ctx.rng);
  }

  function shuffle(a, rng){
    a = a.slice();
    for(let i = a.length - 1; i > 0; i--){ const j = Math.floor(rng() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a;
  }

  // ---------- scoring ----------
  // Accepts "2,700", "2700", "2.7e3", " 2 700 ". Returns NaN for anything else.
  function parseNumber(s){
    const t = String(s == null ? "" : s).replace(/[,\s_]/g, "");
    return /^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i.test(t) ? parseFloat(t) : NaN;
  }
  // response: array of option indices (single/multi) or the typed string (number).
  function grade(q, response){
    if(q.kind === "number"){
      const x = parseNumber(response), want = q.answer[0], tol = q.tol == null ? 0 : q.tol;
      return Number.isFinite(x) && Math.abs(x - want) <= tol * Math.abs(want) + 1e-12;
    }
    const got = (response || []).slice().sort((a, b) => a - b), want = q.answer.slice().sort((a, b) => a - b);
    if(q.kind === "single") return got.length === 1 && got[0] === want[0];
    return got.length === want.length && got.every((v, i) => v === want[i]); // multi: all or nothing
  }

  // ---------- scorecard ----------
  // results: [{q, response, correct}] in the order asked.
  function scorecard(results, banks){
    const bankOf = l => banks.find(b => b.lesson === l);
    const byLesson = {}, byConcept = {};
    results.forEach(r => {
      const l = r.q.lesson, b = bankOf(l), c = b.concepts[r.q.concept] || {label: r.q.concept};
      const L = byLesson[l] = byLesson[l] || {lesson: l, title: b.title, right: 0, total: 0};
      L.total++; if(r.correct) L.right++;
      const k = l + ":" + r.q.concept;
      const C = byConcept[k] = byConcept[k] || {lesson: l, concept: r.q.concept, label: c.label,
        href: b.url + (c.anchor ? "#" + c.anchor : ""), right: 0, total: 0};
      C.total++; if(r.correct) C.right++;
    });
    const concepts = Object.values(byConcept).sort((a, b) => a.lesson - b.lesson || a.label.localeCompare(b.label));
    return {
      right: results.filter(r => r.correct).length, total: results.length,
      byLesson: Object.values(byLesson).sort((a, b) => a.lesson - b.lesson),
      byConcept: concepts,
      studyMore: concepts.filter(c => c.right < c.total)
    };
  }

  // ---------- copy prompt ----------
  function answerText(q, response){
    if(q.kind === "number") return response == null || String(response).trim() === "" ? "(no answer)" : String(response).trim() + (q.unit ? " " + q.unit : "");
    const picked = (response || []).map(i => q.options[i]);
    return picked.length ? picked.join("; ") : "(no answer)";
  }
  function rightText(q){
    if(q.kind === "number") return q.answer[0].toLocaleString("en-US") + (q.unit ? " " + q.unit : "") + (q.tol ? " (within " + Math.round(q.tol * 100) + "%)" : "");
    return q.answer.map(i => q.options[i]).join("; ");
  }
  function copyPrompt(results, banks){
    const missed = results.filter(r => !r.correct);
    if(!missed.length) return "";
    const lines = [
      "I'm learning how large language models work and took a self-test. I got these questions wrong.",
      "For each one, explain the mechanism behind the right answer with a small worked example in small numbers,",
      "then say exactly what my answer gets wrong. Keep each explanation short and concrete.",
      ""
    ];
    missed.forEach((r, i) => {
      const b = banks.find(x => x.lesson === r.q.lesson), c = b.concepts[r.q.concept];
      lines.push((i + 1) + ". [Lesson " + r.q.lesson + " · " + (c ? c.label : r.q.concept) + "] " + r.q.prompt);
      if(r.q.options && r.q.kind !== "number") lines.push("   Options: " + r.q.options.join(" | "));
      lines.push("   My answer: " + answerText(r.q, r.response));
      lines.push("   Right answer: " + rightText(r.q));
      lines.push("");
    });
    return lines.join("\n").trim() + "\n";
  }

  // Seeded RNG for repeatable tests (mulberry32).
  function seededRng(seed){
    let a = seed >>> 0;
    return function(){ a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }

  const Quiz = {LEITNER_WEIGHTS, BOX_MAX, createStore, leitnerStrategy, weightedSample, buildAttempt,
    shuffle, parseNumber, grade, scorecard, answerText, rightText, copyPrompt, seededRng};
  if(typeof module !== "undefined" && module.exports) module.exports = Quiz; else root.Quiz = Quiz;
})(typeof window !== "undefined" ? window : this);

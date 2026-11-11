// Pure scoring for learner-sim runs: no files, no browser, no clock. Every input is plain data,
// so the whole module is unit-tested (score.test.mjs).
//
// Shapes (see README.md for the full contract):
//   steps:   [{id: "S03", ch, title, teaching, text}]
//   bank:    the quiz bank JSON (site/quiz/banks/lN.json)
//   map:     {Q01: {id: "L3-mask-01", perm: [2,0,3,1]}}   perm[shownIndex] = bank option index
//   options: {Q01: ["B"]}                                  options-only pass (choice questions)
//   answers: {answers: {Q01: {answer: ["B"] | "2700" | null, cites: [{step, quote, visual?}], dispute?}},
//             flags: [{step, kind, note}]}
import {createRequire} from "node:module";
import path from "node:path";

const Quiz = createRequire(import.meta.url)(path.resolve(import.meta.dirname, "../../../site/assets/quiz/engine.js"));

// Options-only is reported, not gated: a model that knows the subject spots the true option without
// the stem, so it says little about a beginner. Key-is-longest is the gated, model-free cue check.
export const TARGETS = {grounded: 1, agreement: 1, openDisputes: 0, optionsOnly: 0.1, keyLongest: 0.35, coverage: 1, viewed: 1};

// Model-free cue check: is the single-choice key the strictly longest option? Chance is 1/k (25% with 4).
export function keyIsLongest(q){
  if(q.kind !== "single") return false;
  const len = q.options.map(o => o.length), k = len[q.answer[0]];
  return len.every((l, i) => i === q.answer[0] || l < k);
}
export const FLAG_KINDS = ["term-before-taught", "unclear-visual", "inconsistent-highlight",
  "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12"];
const LETTERS = "ABCDEFGH";

// Lowercase, no quote marks, words only: a quote survives line breaks, curly or straight quotes and dashes.
export function normalize(s){
  return String(s == null ? "" : s).toLowerCase()
    .replace(/[‘’“”"'`]/g, "").replace(/[‐-―−]/g, "-")
    .replace(/[^a-z0-9.%+\-→]+/g, " ").replace(/\s+/g, " ").trim();
}

// A text cite counts only if its quote is really on that step, found verbatim, and specific enough:
// at least 4 words, or a numeric fragment like "0.5 → 0.69" (2+ tokens, a digit, 8+ characters).
export function quoteOnStep(step, quote){
  const q = normalize(quote), n = q.split(" ").length;
  const specific = n >= 4 || (n >= 2 && /\d/.test(q) && q.length >= 8);
  return specific && normalize(step.text).includes(q);
}

// Letters the actor picked -> bank option indices, through the run's shuffle.
export function toBankIndices(letters, perm){
  if(!Array.isArray(letters)) return null;
  const out = [];
  for(const l of letters){
    const i = LETTERS.indexOf(String(l).trim().toUpperCase());
    if(i < 0 || i >= perm.length) return null;
    out.push(perm[i]);
  }
  return out.sort((a, b) => a - b);
}

// The response in the engine's own format, so grading is exactly what a learner gets.
export function response(q, raw, perm){
  if(raw == null) return null;
  return q.kind === "number" ? String(raw) : toBankIndices(raw, perm);
}

export function sameAnswer(q, a, b){
  if(a == null || b == null) return false;
  if(q.kind === "number"){
    const x = Quiz.parseNumber(a), y = Quiz.parseNumber(b);
    return Number.isFinite(x) && Number.isFinite(y) && Math.abs(x - y) <= (q.tol || 0) * Math.max(Math.abs(x), Math.abs(y)) + 1e-12;
  }
  return a.length === b.length && a.every((v, i) => v === b[i]);
}

const rate = (n, d) => d ? n / d : 1;

// One run: each question graded, its cites checked against the step text.
export function scoreRun({bank, steps, map, options = {}, answers}){
  const byId = new Map(bank.questions.map(q => [q.id, q])), stepById = new Map(steps.map(s => [s.id, s]));
  const given = (answers && answers.answers) || {};
  const questions = Object.entries(map).map(([qid, {id, perm}]) => {
    const q = byId.get(id); if(!q) throw new Error(`map names unknown question ${id}`);
    const a = given[qid] || {}, resp = response(q, a.answer, perm);
    const correct = resp != null && Quiz.grade(q, resp);
    const cites = (Array.isArray(a.cites) ? a.cites : []).map(c => {
      const s = stepById.get(c && c.step);
      const valid = !!(s && s.teaching && (c.visual ? normalize(c.quote).length > 0 : quoteOnStep(s, c.quote)));
      return {step: c && c.step, visual: !!(c && c.visual), valid};
    });
    const validSteps = [...new Set(cites.filter(c => c.valid).map(c => c.step))];
    const oo = q.kind === "number" ? null : (options[qid] == null ? null : toBankIndices(options[qid], perm));
    return {qid, id, concept: q.concept, kind: q.kind, response: resp, answered: resp != null, correct,
      cited: validSteps.length > 0, grounded: correct && validSteps.length > 0, steps: validSteps,
      visualOnly: validSteps.length > 0 && cites.filter(c => c.valid).every(c => c.visual),
      dispute: a.dispute ? String(a.dispute) : null,
      optionsOnlyCorrect: oo == null ? (q.kind === "number" ? null : false) : Quiz.grade(q, oo)};
  });
  const flags = (Array.isArray(answers && answers.flags) ? answers.flags : [])
    .filter(f => f && stepById.has(f.step) && FLAG_KINDS.includes(f.kind))
    .map(f => ({step: f.step, kind: f.kind, note: String(f.note || "")}));
  // The actor must look at every teaching step's screenshot and say what its visual shows.
  const seen = (answers && answers.visuals) || {}, teach = steps.filter(s => s.teaching);
  const viewed = rate(teach.filter(s => normalize(seen[s.id]).split(" ").length >= 4).length, teach.length);
  return {questions, flags, viewed};
}

const atLeast = (k, runs) => k >= Math.ceil(runs * 2 / 3); // "2 of 3", generalised

// All runs of one lesson -> the scorecard. closedDisputes: ids a human reviewed and kept the key for.
export function aggregate({bank, steps, runs, closedDisputes = {}}){
  const R = runs.length, qs = bank.questions;
  const per = new Map(qs.map(q => [q.id, runs.map(r => r.questions.find(x => x.id === q.id)).filter(Boolean)]));
  const rows = qs.map(q => {
    const rs = per.get(q.id), g = rs.filter(r => r.grounded).length;
    const agree = rs.length === R && rs.every(r => sameAnswer(q, r.response, rs[0].response));
    return {id: q.id, concept: q.concept, kind: q.kind, grounded: g, correct: rs.filter(r => r.correct).length,
      agree, steps: [...new Set(rs.flatMap(r => r.steps))].sort(),
      disputes: rs.filter(r => r.dispute).map(r => r.dispute),
      optionsOnly: q.kind === "number" ? null : rs.filter(r => r.optionsOnlyCorrect).length};
  });
  const choice = rows.filter(r => r.optionsOnly != null);
  const weak = choice.filter(r => atLeast(r.optionsOnly, R));
  const disputes = rows.filter(r => r.disputes.length && !closedDisputes[r.id]);
  const singles = qs.filter(q => q.kind === "single"), longest = singles.filter(keyIsLongest);

  // A flag is confirmed when most runs raise the same kind on the same step.
  const fl = new Map();
  runs.forEach((r, i) => r.flags.forEach(f => { const k = f.step + " " + f.kind;
    if(!fl.has(k)) fl.set(k, {step: f.step, kind: f.kind, runs: new Set(), notes: []});
    fl.get(k).runs.add(i); fl.get(k).notes.push(f.note); }));
  const flags = [...fl.values()].map(f => ({step: f.step, kind: f.kind, runs: f.runs.size, confirmed: atLeast(f.runs.size, R), notes: f.notes}))
    .sort((a, b) => a.step.localeCompare(b.step) || a.kind.localeCompare(b.kind));

  // Coverage: a concept (or teaching step) is covered when a question on it is grounded in most runs.
  const solid = rows.filter(r => atLeast(r.grounded, R));
  const concepts = Object.keys(bank.concepts), coveredC = new Set(solid.map(r => r.concept));
  const teach = steps.filter(s => s.teaching && s.ch !== "R"), coveredS = new Set(solid.flatMap(r => r.steps));

  const groundedRate = rate(rows.reduce((n, r) => n + r.grounded, 0), qs.length * R);
  const metrics = {
    grounded: groundedRate,
    agreement: rate(rows.filter(r => r.agree).length, qs.length),
    openDisputes: disputes.length,
    optionsOnly: rate(weak.length, choice.length),
    keyLongest: rate(longest.length, singles.length),
    confirmedFlags: flags.filter(f => f.confirmed).length,
    coverage: rate(concepts.filter(c => coveredC.has(c)).length, concepts.length),
    stepCoverage: rate(teach.filter(s => coveredS.has(s.id)).length, teach.length),
    viewed: Math.min(...runs.map(r => r.viewed ?? 0)),
    visualOnlyCites: rate(runs.flatMap(r => r.questions).filter(q => q.visualOnly).length, runs.flatMap(r => r.questions).filter(q => q.cited).length || 1)
  };
  const pass = {grounded: metrics.grounded >= TARGETS.grounded, agreement: metrics.agreement >= TARGETS.agreement,
    openDisputes: metrics.openDisputes <= TARGETS.openDisputes, keyLongest: metrics.keyLongest <= TARGETS.keyLongest,
    coverage: metrics.coverage >= TARGETS.coverage, viewed: metrics.viewed >= TARGETS.viewed};
  return {lesson: bank.lesson, runs: R, questions: qs.length, metrics, pass, gate: Object.values(pass).every(Boolean),
    notGrounded: rows.filter(r => r.grounded < R).map(r => ({id: r.id, grounded: r.grounded, correct: r.correct})),
    ambiguous: rows.filter(r => !r.agree).map(r => r.id),
    disputes: disputes.map(r => ({id: r.id, reasons: r.disputes})),
    weakDistractors: weak.map(r => ({id: r.id, right: r.optionsOnly})),
    keyLongestIds: longest.map(q => q.id),
    uncoveredConcepts: concepts.filter(c => !coveredC.has(c)),
    uncoveredSteps: teach.filter(s => !coveredS.has(s.id)).map(s => s.id),
    flags, rows};
}

// What changed since the last scorecard of the same lesson.
export function diff(prev, cur){
  if(!prev) return null;
  const metrics = Object.fromEntries(Object.keys(cur.metrics).map(k => [k, {before: prev.metrics[k], after: cur.metrics[k]}]));
  const was = new Set(prev.notGrounded.map(r => r.id)), now = new Set(cur.notGrounded.map(r => r.id));
  return {metrics, nowGrounded: [...was].filter(id => !now.has(id) && cur.rows.some(r => r.id === id)),
    lostGrounding: [...now].filter(id => !was.has(id))};
}

const pct = x => x == null ? "–" : Math.round(x * 100) + "%";
const fmt = (k, x) => ["openDisputes", "confirmedFlags"].includes(k) ? String(x ?? "–") : pct(x);
const LABEL = {grounded: "Grounded", agreement: "Agreement", openDisputes: "Key disputes (open)", optionsOnly: "Options-only guess", keyLongest: "Key is the longest option",
  confirmedFlags: "Lesson flags (confirmed)", coverage: "Coverage (concepts)", stepCoverage: "Coverage (teaching steps)", viewed: "Screenshots viewed (worst run)", visualOnlyCites: "Visual-only cites"};
const GOAL = {grounded: "100%", agreement: "100%", openDisputes: "0", optionsOnly: "info", keyLongest: "≤35%", confirmedFlags: "→ 0", coverage: "100%", stepCoverage: "info", viewed: "100%", visualOnlyCites: "info"};

export function toMarkdown(card, d, title){
  const L = [`# Learner-sim scorecard: ${title || "Lesson " + card.lesson}`, "",
    `${card.runs} runs, ${card.questions} questions. Gate: **${card.gate ? "PASS" : "FAIL"}**.`, "",
    "| Metric | Value | Target |" + (d ? " Before |" : ""), "| --- | --- | --- |" + (d ? " --- |" : "")];
  for(const k of Object.keys(LABEL)) L.push(`| ${LABEL[k]} | ${fmt(k, card.metrics[k])} | ${GOAL[k]} |` + (d ? ` ${fmt(k, d.metrics[k].before)} |` : ""));
  const list = (h, xs, f) => { if(xs.length){ L.push("", `## ${h}`, ""); xs.forEach(x => L.push("- " + f(x))); } };
  list("Not grounded in every run", card.notGrounded, r => `${r.id}: grounded ${r.grounded}/${card.runs}, correct ${r.correct}/${card.runs}`);
  list("Ambiguous (runs disagree)", card.ambiguous, id => id);
  list("Key disputes (human review)", card.disputes, r => `${r.id}: ${r.reasons.join(" / ")}`);
  list("Weak distractors (right from options alone)", card.weakDistractors, r => `${r.id}: ${r.right}/${card.runs} runs`);
  list("Uncovered", [...card.uncoveredConcepts.map(c => "concept " + c), ...card.uncoveredSteps.map(s => "step " + s)], x => x);
  list("Confirmed lesson flags", card.flags.filter(f => f.confirmed), f => `${f.step} ${f.kind} (${f.runs}/${card.runs}): ${f.notes[0]}`);
  if(d){ list("Since last run", [...d.nowGrounded.map(id => "now grounded: " + id), ...d.lostGrounding.map(id => "lost grounding: " + id)], x => x); }
  return L.join("\n") + "\n";
}

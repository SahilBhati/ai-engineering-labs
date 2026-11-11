// Unit tests for the pure learner-sim core. Run: node --test tools/learner-sim/score.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import {keyIsLongest, normalize, quoteOnStep, toBankIndices, scoreRun, aggregate, diff, toMarkdown} from "./lib/score.mjs";
import {makePacket} from "./lib/packet.mjs";

// A two-concept bank: one choice question, one number question with 5% tolerance.
const bank = {lesson: 9, title: "T", url: "", concepts: {mask: {label: "Mask"}, cost: {label: "Cost"}},
  questions: [
    {id: "L9-mask-01", concept: "mask", kind: "single", prompt: "Which?", options: ["wrong", "right", "wring", "wrung"], answer: [1], why: ""},
    {id: "L9-cost-01", concept: "cost", kind: "number", prompt: "How many?", answer: [100], tol: 0.05, why: ""}]};
const steps = [
  {id: "S01", ch: "R", title: "Recap", teaching: true, text: "Recap text about the earlier lesson."},
  {id: "S02", ch: "9.1", title: "Mask", teaching: true, text: "The causal mask hides every “future” token\nfrom the query."},
  {id: "S03", ch: "9.2", title: "Cost", teaching: true, text: "Cost grows with n squared: 10 tokens make 100 pairs."},
  {id: "S04", ch: "✓", title: "Questions", teaching: false, text: "Check yourself: why does the mask hide tokens?"}];
// Identity shuffle keeps letters readable: A=0, B=1 ...
const map = {Q01: {id: "L9-mask-01", perm: [0, 1, 2, 3]}, Q02: {id: "L9-cost-01", perm: []}};
const good = {answers: {
  Q01: {answer: ["B"], cites: [{step: "S02", quote: "the causal mask hides every \"future\" token"}]},
  Q02: {answer: "100", cites: [{step: "S03", quote: "10 tokens make 100 pairs"}]}}, flags: [],
  visuals: {S01: "no visual, text recap only", S02: "a grid with the upper triangle greyed", S03: "a curve rising as n squared"}};

test("normalize survives curly quotes, dashes and line breaks", () => {
  assert.equal(normalize("A “future”\n token — here"), "a future token - here");
});

test("a quote counts only if it is on that step and specific enough", () => {
  assert.ok(quoteOnStep(steps[1], "every \"future\" token from the"));
  assert.ok(!quoteOnStep(steps[1], "causal mask"), "too short to prove anything");
  assert.ok(!quoteOnStep(steps[2], "the causal mask hides every"), "quote from another step");
  assert.ok(quoteOnStep(steps[2], "make 100 pairs"), "short numeric fragment");
  assert.ok(!quoteOnStep(steps[2], "n squared"), "short and no number");
});

test("key-is-longest cue", () => {
  assert.ok(keyIsLongest({kind: "single", options: ["a", "bbbb", "cc"], answer: [1]}));
  assert.ok(!keyIsLongest({kind: "single", options: ["aaaa", "bbbb", "cc"], answer: [1]}), "tie is not a cue");
  assert.ok(!keyIsLongest({kind: "multi", options: ["a", "bbbb"], answer: [1]}));
});

test("letters map back through the shuffle", () => {
  assert.deepEqual(toBankIndices(["B", "a"], [3, 1, 0, 2]), [1, 3]);
  assert.equal(toBankIndices(["E"], [0, 1, 2, 3]), null);
  assert.equal(toBankIndices("B", [0, 1]), null);
});

test("grounded = correct and a verified cite", () => {
  const r = scoreRun({bank, steps, map, answers: good});
  assert.deepEqual(r.questions.map(q => [q.correct, q.grounded]), [[true, true], [true, true]]);
});

test("correct without a valid cite is not grounded", () => {
  const ans = {answers: {
    Q01: {answer: ["B"], cites: [{step: "S04", quote: "why does the mask hide tokens"}]}, // questions step doesn't teach
    Q02: {answer: "104", cites: [{step: "S03", quote: "something the page never says"}]}}};
  const r = scoreRun({bank, steps, map, answers: ans});
  assert.deepEqual(r.questions.map(q => [q.correct, q.grounded]), [[true, false], [true, false]]);
});

test("number answers use the engine's tolerance; wrong answers are never grounded", () => {
  const ans = {answers: {Q01: {answer: ["C"], cites: good.answers.Q01.cites}, Q02: {answer: "106", cites: good.answers.Q02.cites}}};
  const r = scoreRun({bank, steps, map, answers: ans});
  assert.deepEqual(r.questions.map(q => q.grounded), [false, false]);
});

test("visual cites need a description and a teaching step", () => {
  const ans = {answers: {Q01: {answer: ["B"], cites: [{step: "S02", visual: true, quote: "grid greys out the upper triangle"}]}}};
  const q = scoreRun({bank, steps, map, answers: ans}).questions[0];
  assert.ok(q.grounded && q.visualOnly);
});

test("viewed = teaching steps with a real visual note", () => {
  assert.equal(scoreRun({bank, steps, map, answers: good}).viewed, 1);
  const lazy = {...good, visuals: {S02: "grid", S03: "a curve rising as n squared"}};
  assert.equal(scoreRun({bank, steps, map, answers: lazy}).viewed, 1 / 3);
});

test("unknown flag kinds and steps are dropped", () => {
  const r = scoreRun({bank, steps, map, answers: {answers: {}, flags: [
    {step: "S02", kind: "C3", note: "two terms undefined"}, {step: "S99", kind: "C3"}, {step: "S02", kind: "vibes"}]}});
  assert.equal(r.flags.length, 1);
});

const three = (a, b, c) => [a, b, c].map(ans => scoreRun({bank, steps, map, options: ans.oo || {}, answers: ans}));

test("aggregate: all good -> gate passes", () => {
  const card = aggregate({bank, steps, runs: three(good, good, good)});
  assert.equal(card.metrics.grounded, 1);
  assert.equal(card.metrics.agreement, 1);
  assert.equal(card.metrics.coverage, 1);
  assert.equal(card.metrics.stepCoverage, 1, "recap is not counted as a teaching step to cover");
  assert.ok(card.gate);
});

test("aggregate: disagreement, disputes, weak distractors, confirmed flags", () => {
  const flagged = {...good, flags: [{step: "S02", kind: "unclear-visual", note: "grid has no legend"}]};
  const other = {answers: {...good.answers, Q01: {answer: ["C"], cites: [], dispute: "B and C both fit"}}, flags: [], oo: {Q01: ["B"]}};
  const card = aggregate({bank, steps, runs: three({...flagged, oo: {Q01: ["B"]}}, flagged, other)});
  assert.deepEqual(card.ambiguous, ["L9-mask-01"]);
  assert.equal(card.metrics.openDisputes, 1);
  assert.deepEqual(card.weakDistractors, [{id: "L9-mask-01", right: 2}]);
  assert.equal(card.metrics.optionsOnly, 1);
  assert.deepEqual(card.flags.map(f => [f.step, f.confirmed]), [["S02", true]]);
  assert.equal(card.metrics.grounded, 5 / 6);
  assert.ok(!card.gate);
  // A human kept the key: the dispute closes.
  assert.equal(aggregate({bank, steps, runs: three(good, good, other), closedDisputes: {"L9-mask-01": "key right"}}).metrics.openDisputes, 0);
});

test("number agreement uses the tolerance", () => {
  const near = {answers: {...good.answers, Q02: {...good.answers.Q02, answer: "102"}}};
  assert.equal(aggregate({bank, steps, runs: three(good, good, near)}).metrics.agreement, 1);
});

test("coverage drops when a concept is grounded in only one run", () => {
  const miss = {answers: {Q01: good.answers.Q01}};
  const card = aggregate({bank, steps, runs: three(good, miss, miss)});
  assert.deepEqual(card.uncoveredConcepts, ["cost"]);
  assert.equal(card.metrics.coverage, 0.5);
  assert.deepEqual(card.uncoveredSteps, ["S03"]);
});

test("diff and markdown", () => {
  const before = aggregate({bank, steps, runs: three(good, {answers: {}}, {answers: {}})});
  const after = aggregate({bank, steps, runs: three(good, good, good)});
  const d = diff(before, after);
  assert.deepEqual(d.nowGrounded.sort(), ["L9-cost-01", "L9-mask-01"]);
  assert.equal(diff(null, after), null);
  const md = toMarkdown(after, d, "Lesson 9");
  assert.match(md, /Gate: \*\*PASS\*\*/);
  assert.match(md, /now grounded: L9-mask-01/);
});

test("packet: deterministic, opaque, no answers leak", () => {
  const a = makePacket(bank, 7), b = makePacket(bank, 7);
  assert.deepEqual(a, b);
  const text = JSON.stringify([a.questions, a.optionsOnly]);
  assert.doesNotMatch(text, /answer|why|L9-|mask-01|concept/);
  assert.equal(a.optionsOnly.length, 1);
  assert.ok(!("prompt" in a.optionsOnly[0]));
  // Shown letters map back to the bank's options.
  const q = a.questions.find(x => x.kind === "single");
  const letter = Object.keys(q.options).find(k => q.options[k] === "right");
  assert.deepEqual(toBankIndices([letter], a.map[q.qid].perm), [1]);
});

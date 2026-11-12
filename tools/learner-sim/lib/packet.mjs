// Builds one run's exam packet from a bank: opaque ids (Q01…), questions and options shuffled by a seed,
// no answers, no "why", no concept names. Pure: same bank + seed -> same packet.
import {createRequire} from "node:module";
import path from "node:path";

const Quiz = createRequire(import.meta.url)(path.resolve(import.meta.dirname, "../../../site/assets/quiz/engine.js"));
const LETTERS = "ABCDEFGH";

export function makePacket(bank, seed){
  const rng = Quiz.seededRng(seed);
  const order = Quiz.shuffle(bank.questions.slice(), rng);
  const map = {}, questions = [];
  order.forEach((q, i) => {
    const qid = "Q" + String(i + 1).padStart(2, "0");
    const perm = q.options ? Quiz.shuffle(q.options.map((_, j) => j), rng) : [];
    map[qid] = {id: q.id, perm};
    const item = {qid, kind: q.kind, prompt: q.prompt};
    if(q.options) item.options = Object.fromEntries(perm.map((j, k) => [LETTERS[k], q.options[j]]));
    if(q.unit) item.unit = q.unit;
    questions.push(item);
  });
  // The options-only pass sees choice questions in a different order, without their prompts.
  const optionsOnly = Quiz.shuffle(questions.filter(q => q.kind !== "number"), rng)
    .map(({qid, kind, options}) => ({qid, kind, options}));
  return {map, questions, optionsOnly};
}

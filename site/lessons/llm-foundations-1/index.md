# LLM Foundations 1: Tokens, Embeddings, Attention

Course: LLM Foundations for engineers. Interactive version: index.html

1. **Models read numbers, not text** (1.1): A tokenizer cuts text into pieces from a fixed list, then swaps each piece for its ID. Type anything.
2. **Choose the size of the pieces** (1.1): Small pieces make long sequences. Big pieces need a huge vocabulary. Subwords sit in between.
3. **The model never sees letters** (1.1): Ask a model to count the r's in “strawberry”. Flip to what the model actually receives.
4. **Other languages pay more** (1.1): The tokenizer learned its pieces from mostly English text, then was frozen. Text it rarely saw falls back to raw bytes.
5. **Each ID picks a row** (1.2): The embedding table has one row of numbers per token. “Embedding a token” just means reading its row. Tap a word.
6. **Training moves similar words together** (1.2): Rows start as random numbers. Every training correction nudges them. Words used in similar sentences get similar nudges, so they drift together. Drag the slider.
7. **Close means similar, and that is how it generalizes** (1.2): Distance between two rows is a number you can compute. Tap two words.
8. **Position: order changes meaning** (1.2): Embeddings say what each token is, not where it is. Without position, these two sentences look identical.
9. **Training writes. Using only reads.** (1.2): When you use a model, its tables are frozen. Each request copies rows out, computes with the copies, and throws them away. Run some requests.
10. **A vector is just a list of numbers** (B): Two numbers can be drawn as an arrow: first number = how far right, second = how far up. Move the sliders.
11. **Dot product: how well two lists match** (B): Multiply the numbers in matching positions, then add. Same direction gives a big score, a right angle gives 0, opposite gives a negative score. Move the arrows.
12. **Softmax: turn scores into percentages** (B): Scores can be any numbers. Softmax turns them into shares that are never negative and always add up to 100%. Bigger scores take a much bigger share. Drag the scores.
13. **Weighted average: blend by the percentages** (B): Mix several vectors using the percentages as the recipe. Slide the recipe and watch the blend move between them.
14. **Gradient: how training nudges each number** (B): Training wants a higher score. Each column is nudged in proportion to its influence: what it gets multiplied by. Press Train step a few times, then set a multiplier to 0.
15. **bank has one row, but two meanings** (1.3): Same row in both sentences. Attention mixes in information from earlier tokens, so bank ends up meaning the right thing. Switch it on.
16. **The three basics, running together** (1.3): bank asks the same question in every sentence: its query. Each earlier word answers with its key. Score, softmax, blend. Switch the sentence.
17. **Who does each token listen to?** (1.3): Tap any word. Arc thickness is how much it listens to each earlier word. Later words are greyed: a token only looks backward (why comes with training, in 1.7).
18. **Several heads: one blend per need** (1.3): bank needs two things: its setting (from “river”) and its grammar (from “the”). One head has one softmax, so one blend has to split between both needs. Compare.
19. **Cost grows with the square of the context** (1.3): Every token scores every token it can see. Drag the slider: double the tokens, about four times the work.

## Check yourself

- Why do LLMs use subword tokens instead of characters or whole words? What breaks at each extreme?
- Why can't an LLM reliably count the r's in “strawberry”?
- Why does the same paragraph cost more in Hindi than in English, and why can't training the model fix it?
- Why can't a token ID be fed to the model as a plain number?
- Nobody labels cat and dog as related. How do their rows end up close, and why does that help the model?
- What breaks without position information? Give one example about order and one about distance.
- Which numbers change during training, which during use? How can RoPE work if use changes nothing?
- Walk through one attention step for “bank”: query, keys, scores, weights, values, result.
- Why use three separate vectors (query, key, value) instead of the token's embedding for everything?
- Who decides a token's query, and how does it get good at finding useful words?
- What does softmax do to a list of scores, and why must the results add up to 100%?
- During training, how does one column of an embedding row get changed? Why does one column move a lot while another doesn't move at all?
- Why do models run several attention heads instead of one, when the total width is the same?
- Context goes from 8k to 16k tokens. What happens to attention's work, and which backend operation is this like?
- A tokenizer has no piece for four spaces. What happens to cost and context when you send it Python code, and why?
- Hallucination: how does “an LLM is a function, not a lookup table” explain it?

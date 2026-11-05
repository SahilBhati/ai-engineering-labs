# LLM Foundations 1: Tokens, Embeddings, Attention

Course: LLM Foundations for engineers. Interactive version: index.html

1. **The whole machine, then zoom in** (M): An LLM does one thing: given the tokens so far, score every possible next token. This lesson covers the first three boxes.
2. **Models read numbers, not text** (1.1): A tokenizer cuts text into pieces from a fixed list (the vocabulary) and swaps each piece for its ID. Type anything.
3. **Choose the size of the pieces** (1.1): Small pieces make long sequences; big pieces need a huge vocabulary. Subwords (pieces between a letter and a word) sit in between.
4. **The model never sees letters** (1.1): The model sees token IDs, not letters, so it can't reliably count the r's in “strawberry”. Switch to what it actually receives.
5. **Other languages pay more** (1.1): In this toy, the same sentence costs 4 tokens in English and 36 in Hindi, because it has no Hindi pieces at all. Real tokenizers do better, but other languages still cost more.
6. **A vector is just a list of numbers** (1.2): A vector is a list of numbers; two numbers draw as an arrow (how far right, how far up). Embeddings are vectors. Move the sliders.
7. **Each ID picks a row** (1.2): The embedding table has one row of numbers per token. “Embedding a token” just means reading its row. Tap a word.
8. **Training moves similar words together** (1.2): Training pulls words used in similar sentences close together. Rows start random; every correction nudges them. Drag the slider.
9. **Close means similar, and that is how it generalizes** (1.2): Nearby rows give nearly the same output, so what the model learns about cat carries over to dog. Tap two words to measure their distance.
10. **Position: order changes meaning** (1.2): Embeddings say what a token is, not where it is, and attention by itself compares contents, not places. Without position, “dog bites man” and “man bites dog” hand attention the same three vectors.
11. **Training writes. Using only reads.** (1.2): Weights (the stored tables) never change when you use a model; activations (copies computed per request) are thrown away. Run some requests.
12. **Dot product: how well two lists match** (B): A dot product scores how well two lists match: multiply matching positions, then add. Same direction scores high, a right angle 0, opposite negative. Move B.
13. **Softmax: turn scores into percentages** (B): Softmax turns any scores into positive shares that add up to 100%; bigger scores take a much bigger share. Drag the scores.
14. **Weighted average: blend by the percentages** (B): Mix several vectors using the percentages as the recipe. Slide the recipe and watch the blend move between them.
15. **Gradient: how training nudges each number** (B): Training nudges each number in bank's row in proportion to what it's multiplied by. Here bank's score for “flooded” should be 2 but is −1.3. Press Train step, then set the multiplier to 0.
16. **bank has one row, but two meanings** (1.3): Attention shifts bank's meaning to fit its sentence; its row never changes. Switch attention on, then change the sentence.
17. **The three basics, running together** (1.3): Attention is the three basics in a row: score, softmax, blend. bank asks the same question (its query) in every sentence; each earlier word answers with its key. Press Play, then switch the sentence.
18. **Who does each token listen to?** (1.3): Each token blends earlier tokens; arc thickness shows how much. Tap any word. Later words are greyed: a token only looks backward (why comes in 1.7).
19. **Several heads: one blend per need** (1.3): A head is one copy of attention with its own softmax. One head's shares must add to 100%, so it can't focus sharply on two words at once. bank needs “river” (setting) and “the” (grammar). Compare.
20. **Cost grows with the square of the context** (1.3): Every token scores every token it can see. Drag the slider: double the tokens, about four times the work.

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

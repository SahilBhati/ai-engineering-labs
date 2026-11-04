# LLM Foundations 2: The Block, Sampling, the KV Cache

Course: LLM Foundations for engineers. Interactive version: index.html

1. **Where Lesson 1 left off** (1.4): So far one token travels: text → token ID → embedding row → attention blends earlier tokens. Weights stay frozen; activations are computed per request. Tap each stage.
2. **After attention, each token thinks on its own** (1.4): After attention, each token passes through its own small network, the MLP, whose neurons act as detectors. Slide bank's water-ness and watch which ones fire.
3. **The residual stream: add, don't replace** (1.4): Each block adds its result to the token's vector instead of overwriting it. Toggle the residual connection and watch how much of the original token survives 12 blocks.
4. **Stack the blocks: where the parameters live** (1.4): A model is the same block repeated; each block has about 12 × width² parameters (the weights from Lesson 1), 2 bytes each at 16-bit. Move the width and depth.
5. **The last vector scores every token in the vocabulary** (1.5): After the last block, the final vector is compared with a row for every vocabulary token (a dot product). Those scores are the logits; softmax turns them into probabilities. Switch the context.
6. **Temperature: how sharp the choice is** (1.5): Before softmax, the logits are divided by the temperature. Low temperature sharpens toward the top token, high temperature flattens. Drag it.
7. **Sampling: roll the dice, but cut the tail** (1.5): The next token is drawn at random by these probabilities. Top-p keeps only the most likely tokens that together reach p, so unlikely ones can't be picked. Sample 50 times.
8. **Generation is a loop: one token per pass** (1.6): The model only ever predicts one next token. To write more, it appends that token and runs again. Press Generate 1 token and watch how much work each pass repeats.
9. **Without a cache, work grows with the square of the length** (1.6): Recomputing every earlier token on every pass adds up fast. Move the prompt and output lengths and compare.
10. **The KV cache: compute keys and values once, keep them** (1.6): Earlier tokens' keys and values never change, so the model stores them. Each new token computes only its own query, key and value, then reads the rest from the cache. Step through.
11. **Prefill and decode are two different jobs** (1.6): The prompt is processed in one parallel pass (prefill), which sets the time to first token. Then tokens come out one at a time (decode), which sets the speed per token. Move the lengths.
12. **How big is the KV cache?** (1.6): The KV cache, not the weights, often decides how many users fit on a GPU. Each layer stores one key and one value per KV head (a group of heads sharing them) for every token.
13. **Why context windows have a limit** (1.6): Three costs grow with context: KV memory grows in line with it, attention work in prefill grows with its square, and the model only learned positions up to the length it was trained on. Drag the context.

## Check yourself

- Why do LLMs use subword tokens instead of characters or whole words?
- Who decides a token's query, and how does it get good at finding useful words?
- What does softmax do to a list of scores, and why must the results add up to 100%?
- Why run several attention heads instead of one at the same total width?
- Context goes from 8k to 16k tokens. What happens to attention's work in prefill, and why?
- What does the MLP do that attention doesn't?
- What is the residual stream, and what would break without it?
- Estimate the parameters and the 16-bit memory of a model with width 4,096 and 32 layers. Show the formula.
- How does the final vector become a probability for every token in the vocabulary?
- What does temperature do, mechanically? What happens as it approaches 0?
- What does top-p do, and why would you use it?
- Why does generating without a cache take work that grows with the square of the output length?
- What exactly does the KV cache store, and why can it be reused?
- Prefill vs decode: which sets time to first token, which sets time per token, and why are they different kinds of work?
- Compute the KV cache per token and per 8K-token request for 80 layers, 8 KV heads, head size 128, 16-bit.
- A 70B model on two 80 GB GPUs: why do only a handful of 8K-context requests fit at once? Name two ways to fit more.
- Every request to a chatbot starts with the same 2,000-token system prompt. How could the server avoid redoing that work?
- Which backend pattern is the KV cache like, and which is the residual stream like?

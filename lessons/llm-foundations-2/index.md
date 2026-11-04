# LLM Foundations 2: The Block, Sampling, the KV Cache

Course: LLM Foundations for engineers. Interactive version: index.html

3. **Two kinds of work: talk, then think** (1.4): Attention lets words share information with each other. Then each word, on its own, works with what it now knows: that's the MLP. Switch between them.
4. **A neuron: a dot product with a threshold** (1.4): An MLP is built from neurons. A neuron scores the word's vector with a dot product (from Basics) and fires only if the score passes its threshold. Slide bank's water-ness.
5. **The MLP: many neurons write new notes about the word** (1.4): Run several neurons on bank's vector and each one that fires adds a new fact about the word. Slide bank's water-ness.
6. **The residual stream: a notepad each layer adds to** (1.4): Each word carries a notepad: its vector. Every attention and MLP step adds a note and never erases. Run the layers, then try overwriting instead.
7. **Stack the blocks: each layer sharpens the guess** (1.4): A model is the same kind of block repeated, each with its own weights. Early blocks work out what words are; later ones what should come next. Drag the depth.
8. **The last vector scores every token in the vocabulary** (1.5): After the last block, the final vector is compared with a row for every vocabulary token (a dot product). Those scores are the logits; softmax turns them into probabilities. Switch the context.
9. **Temperature: how sharp the choice is** (1.5): Before softmax, the logits are divided by the temperature. Low temperature sharpens toward the top token, high temperature flattens. Drag it.
10. **Sampling: roll the dice, but cut the tail** (1.5): The next token is drawn at random by these probabilities. Top-p keeps only the most likely tokens that together reach p, so unlikely ones can't be picked. Sample 50 times.
11. **Generation is a loop: one token per pass** (1.6): The model only ever predicts one next token. To write more, it appends that token and runs again. Press Generate 1 token and watch how much work each pass repeats.
12. **Without a cache, work grows with the square of the length** (1.6): Recomputing every earlier token on every pass adds up fast. Move the prompt and output lengths and compare.
13. **The KV cache: compute keys and values once, keep them** (1.6): Earlier tokens' keys and values never change, so the model stores them. Each new token computes only its own query, key and value, then reads the rest from the cache. Step through.
14. **Prefill and decode are two different jobs** (1.6): The prompt is processed in one parallel pass (prefill), which sets the time to first token. Then tokens come out one at a time (decode), which sets the speed per token. Move the lengths.
15. **How big is the KV cache?** (1.6): The KV cache, not the weights, often decides how many users fit on a GPU. Each layer stores one key and one value per KV head (a group of heads sharing them) for every token.
16. **Why context windows have a limit** (1.6): Three costs grow with context: KV memory grows in line with it, attention work in prefill grows with its square, and the model only learned positions up to the length it was trained on. Drag the context.

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

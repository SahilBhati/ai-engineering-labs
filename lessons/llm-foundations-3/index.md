# LLM Foundations 3: Training, Post-training, Inference Economics

Course: LLM Foundations for engineers. Interactive version: index.html

3. **Every position in a text is a training example** (3.1): Training turns plain text into quiz questions: at every position, guess the next token. “The river bank flooded” gives three questions for free. Press Play.
4. **Loss: how surprised the model was by the right answer** (3.1): The loss is −log of the probability the model gave the correct token. Confident and right: near 0. Unsure: large. Train a step and watch the gradient push “flooded” up and the loss fall.
5. **The causal mask: no peeking at the answer** (3.1): Training feeds the whole sentence at once, so “bank” could simply look at “flooded” and copy it. The causal mask blocks every later position, so each token only looks backward. Toggle the mask.
6. **Scale: about 6 operations per parameter per token** (3.1): Training compute ≈ 6 × parameters × training tokens: 2 for the forward pass, about 4 for the backward pass. Pick a model and token count and see how many GPUs and days it takes.
7. **A base model only continues text** (3.2): Pre-training makes a base model: it continues text the way the internet would, which isn't the same as answering. Post-training turns it into an assistant. Ask both the same question.
8. **Supervised fine-tuning: same loss, curated answers** (3.2): Supervised fine-tuning (SFT) reuses 3.1's next-token loss on example conversations written by people, but scores only the answer tokens. The model learns to answer, not to write questions. Toggle what gets scored.
9. **Preference tuning: learn from a better and a worse answer** (3.2): People find it easier to pick the better of two answers than to write a perfect one. Preference tuning raises the chosen answer's probability and lowers the rejected one. Train on the pair.
10. **Two latencies you can feel: TTFT and TPOT** (3.3): A user feels two waits: the time to first token (prefill) and the time per output token after it (decode). End-to-end = TTFT + (output tokens − 1) × TPOT. Stream a response.
11. **Batching: more tokens per second, each user a bit slower** (3.3): Batching lets many users share each read of the weights, so total throughput climbs fast. Each tick also reads every user's cache, so per-user TPOT creeps up, until KV memory says stop. Drag the batch.
12. **Why output tokens cost more than input tokens** (3.3): Input tokens are processed all at once in prefill, keeping the GPU's math busy. Output tokens come one tick at a time, each tick reading all the weights. Per token, GPU time differs 5–300×. Drag the batch.
13. **Cost per million tokens: the GPU bill divided by tokens** (3.3): A GPU costs the same per hour whether busy or idle, so cost per token = GPU dollars per hour ÷ tokens produced per hour. Raise the batch or the traffic and the price per token falls.
14. **Prompt caching: reuse the stored KV prefix** (3.3): When many requests start with the same tokens, the server can keep that prefix's KV cache and skip recomputing it. Only the new suffix needs prefill. Send five requests, then edit the system prompt.
15. **Quantization: fewer bytes per weight** (3.3): Quantization stores each weight in fewer bits. Half the bytes means each decode tick reads half as much, and the freed memory holds more users' caches. Switch precision and watch both effects.
16. **Lab: size a deployment** (3.3): Put it together: pick a model, GPUs, precision, batch and request shape, and read off TTFT, TPOT, throughput and cost per million tokens. The memory check tells you if it even fits.

## Check yourself

- What does the MLP do that attention doesn't?
- What does temperature do to the logits, mechanically, and what happens as it approaches 0?
- What exactly does the KV cache store, and why is it safe to reuse?
- Why is prefill compute-bound and decode memory-bound?
- Compute the KV cache per token for 80 layers, 8 KV heads, head size 128, 16-bit. Show the formula.
- How many training examples does a 1,000-token document give, and how can the model learn from all of them in one forward pass?
- The model gives the correct token 50%. What's the loss? At 1%? Why use −log instead of 1 − p?
- What would the model learn if you trained without the causal mask, and why would it fail at generation time?
- Estimate the training compute for a 70B model on 15T tokens, and the days on 8,192 H100s at 40% utilization. Show your steps.
- Name three ways training infrastructure differs from serving infrastructure.
- Base model vs chat model: what does supervised fine-tuning change, and what stays exactly the same?
- Why does SFT score only the answer tokens? What would go wrong if it scored the prompt too?
- RLHF vs DPO: what does each need, and why did DPO spread quickly?
- TTFT is 0.3 s and TPOT is 25 ms. How long until a 401-token answer finishes? Which number would a chat user notice first?
- You raise the batch from 1 to 64. What happens to total tokens per second and to each user's TPOT, and what eventually stops you adding users?
- Derive why an output token costs more GPU time than an input token. When would the gap shrink?
- Two GPUs at $4 per GPU-hour produce 1,000 output tokens per second. What is the cost per million output tokens? What if they're busy only half the time?
- Your app sends a 3,000-token system prompt plus a short user message. How does prompt caching change TTFT and cost, and how should you order the prompt to keep hits?
- A 70B model on 2 H100s at 16-bit misses your TPOT target and fits only a few users. Rank three fixes and the trade-off each brings.
- Quantization speeds up decode a lot but prefill much less. Why? What would make prefill faster too?
- Which backend patterns are prompt caching, decode batching, and the causal mask like?

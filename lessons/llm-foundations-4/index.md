# LLM Foundations 4: Give the Model Knowledge, RAG, Vector Search and Evals

Course: LLM Foundations for engineers. Interactive version: index.html

1. **Where Lessons 1–3 left off: similar meaning, similar direction** (recap): Lesson 1: an embedding turns a token into a vector, and similar meanings point in similar directions. Cosine similarity (dot product ÷ both lengths) scores how alike two directions are. Pick a word.
2. **Two limits: frozen knowledge and a finite context** (recap): Lesson 3: the weights are frozen after training, so your private docs were never in them. Lesson 2: the context window is finite, and Lesson 3: every input token costs money. Drag the size of your docs.
3. **This lesson's two questions** (recap): You build a docs bot for your team's API. A user asks: “How often can I call search per minute?” The answer, 100, is only in your private docs. Make two guesses; chapter 4.1 answers the first, chapter 4.3 the second.
4. **Closed book: the model guesses a plausible number** (4.1): The model writes the next token from its frozen weights. With no passage in the prompt, nothing in the weights holds your limit, so the probabilities spread over plausible numbers. Put the passage in the prompt.
5. **RAG: retrieve, then generate** (4.1): RAG (retrieval-augmented generation) finds the passages most like the question, pastes the top k into the prompt, and asks the model to answer only from them. Change k, the number of passages sent.
6. **Chunking: cut the docs into passages** (4.1): Retrieval returns whole chunks, so the docs are first cut into pieces. Too small and a fact loses its subject; too big and one chunk mixes topics and costs more tokens. Change the size.
7. **RAG, long context, or fine-tuning?** (4.1): Three ways to give a model your docs: paste them all (long context), retrieve a few passages (RAG), or train them into the weights (fine-tuning). Change the docs size and how often they change.
8. **Embed every chunk once, the question at ask time** (4.2): An embedding model turns each chunk into one vector, once, ahead of time: that's the index. At ask time it embeds the question the same way, and the nearest vectors win. Pick a question.
9. **Keyword search, vector search, and both together** (4.2): Vector search matches meaning, so “call” finds “requests”, but it blurs exact words like /search or E1042. Keyword search matches exact words and misses synonyms. Hybrid search merges both rankings. Switch method and question.
10. **Approximate search: check a few regions, not every vector** (4.2): Exact search compares the question with every vector: fine for 8 chunks, slow for 100 million. An approximate index groups vectors into regions and checks only the regions nearest the question. Change how many regions it checks.
11. **Nearest isn't always relevant: a score floor** (4.2): Vector search always returns its top k, even when nothing in the docs answers the question. A score floor drops passages below a minimum similarity, so the bot can say “not in the docs”. Move the floor.
12. **A golden set: questions with known right passages** (4.3): To know if retrieval works, write down real questions and, for each one, the passage that answers it: a golden set. Then count how often the right passage lands in the top k: recall@k. Change k.
13. **Retrieval miss or answer miss? Score them separately** (4.3): A wrong answer has two possible causes: the right passage never arrived (retrieval miss), or it arrived and the model didn't use it faithfully (answer miss). They need different fixes. Change k and the prompt.
14. **LLM-as-judge: grade free-text answers at scale** (4.3): Answers are free text, so exact matching fails on “100 requests per minute.” vs the reference. An LLM judge reads the question, the reference answer and the response, and grades it. Check every grader against human labels. Switch graders.
15. **Lab: change one thing, re-run the golden set** (4.3): Evals are a regression gate: a change ships only if it doesn't lower the score. Today's bot: vector search, k = 3. Try hybrid search or a different k and see if it passes the gate.

## Check yourself

- Why does pre-training need no human labels?
- What does the causal mask stop the model from doing during training?
- Why does an output token cost more GPU time than an input token?
- What does prompt caching reuse, and when does it hit?
- Why does a model asked about your private docs produce a confident, plausible wrong answer instead of nothing?
- Walk through the three stages of RAG for “How often can I call search per minute?”. What does the model actually receive?
- With k = 1 the bot answered “10”. Was the model unfaithful? Where was the bug?
- Chunks of 6 words vs 48 words: name the failure each causes, and what overlap fixes.
- Long context, RAG, fine-tuning: which would you pick for a 50K-token doc set? A 2M-token set edited daily? Why?
- What is embedded ahead of time, what at ask time, and why must both use the same embedding model?
- Give one question where keyword search beats vector search and one where it loses. How does hybrid search merge them?
- 100 million vectors of 1,024 numbers: how many multiply-adds does exact search do per question? What does an approximate index trade for speed?
- What does a bot with no score floor do on a question the docs can't answer? What goes wrong if the floor is too high?
- Right-passage ranks for six golden questions are 2, 1, 2, 3, 1, 1. Compute recall@1, recall@2 and recall@3.
- A wrong answer comes back. How do you tell a retrieval miss from an answer miss, and what fixes each?
- When is exact match a good grader, and when do you need an LLM judge? How do you know the judge can be trusted?
- Hybrid search with k = 2 vs vector search with k = 3: which ships, by what gate, and what could the aggregate score hide?
- Which backend patterns are RAG, the vector index, and a golden-set eval like?

Then take the scored quiz: ../../quiz/?lesson=4

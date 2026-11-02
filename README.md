# 🔬 AI Engineering Labs

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)

Hands-on, first-principles laboratory exploring modern AI engineering — structured generation, retrieval systems, agentic workflows, and automated evaluation.

---

## 📂 Repository Structure

```
ai-engineering-labs/
├── labs/                    # 🔬 Hands-on experiments (the core)
├── learning/                # 📖 Study notes & reading list
├── tools/                   # 🛠️  Shared utilities across labs
└── docs/                    # 📋 Setup guides & architecture decisions
```

## 🧭 Lab Curriculum

Each lab is a self-contained, reproducible micro-application demonstrating a core AI engineering concept:

| Lab | Topic | Core Mechanics | Status |
|:---|:---|:---|:---|
| [`01-structured-extraction`](labs/01-structured-extraction/) | **The LLM Engine & Type Safety** | Tokenization, logits, temperature, JSON Schema enforcement, Pydantic validation, self-healing retry loops | 📋 Planned |
| [`02-retrieval-rag`](labs/02-retrieval-rag/) | **Retrieval-Augmented Generation** | Vector embeddings, cosine similarity, semantic chunking, dense + sparse (BM25) hybrid search, cross-encoder reranking | 📋 Planned |
| [`03-agentic-loop`](labs/03-agentic-loop/) | **The Agentic Loop (ReAct)** | Tool schemas, observation feedback loops, state machines, self-reflection, syntax & execution recovery | 📋 Planned |
| [`04-multi-agent`](labs/04-multi-agent/) | **Multi-Agent Systems** | Hierarchical supervisor-worker graphs, consensus loops, task decomposition, agent handoffs | 📋 Planned |
| [`05-evals-benchmarking`](labs/05-evals-benchmarking/) | **Evaluation & Guardrails** | LLM-as-a-Judge, deterministic regression suites, hallucination scoring, cost/latency profiling | 📋 Planned |
| [`06-local-inference`](labs/06-local-inference/) | **100% Local Inference** | Open-weight models (Llama 3, Qwen), quantization (GGUF), Apple Silicon MLX / Ollama, offline copilot | 📋 Planned |

## 🏛️ Engineering Principles

1. **First-Principles Before Abstractions** — Master the underlying mechanisms (tokens, vectors, schemas) before leaning on high-level frameworks.
2. **Deterministic Outputs from Probabilistic Models** — Guarantee runtime safety through strict typing, schema compilation, and validation barriers.
3. **Reproducibility & Observability** — Every lab includes automated tests, token/latency metrics, and clear interactive demos.
4. **Theory → Lab → Recipe Pipeline** — Every concept is tested in a lab; every lab produces a reusable recipe.
5. **Zero-Secret Commits** — Never commit raw API keys or personal credentials to git.

## 🛠️ Getting Started

```bash
git clone https://github.com/SahilBhati/ai-engineering-labs.git
cd ai-engineering-labs
uv venv && source .venv/bin/activate
cp .env.example .env  # fill in your API keys
```

See [docs/setup.md](docs/setup.md) for the full setup guide.

## 📓 Companion Knowledge Vault

This repo pairs with the **ai-vault** Obsidian vault — a structured "Skill Factory" where concept notes, experiment logs, and reusable recipes are tracked using typed knowledge graph edges.

## 🤝 Contributing

Contributions, bug reports, and enhancements are welcome via Pull Requests. Direct pushes to `main` are restricted to maintain build integrity and review quality.

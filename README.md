# 🔬 AI Engineering Labs

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)

Hands-on, first-principles laboratory exploring modern Artificial Intelligence engineering, structured generation, retrieval systems, agentic workflows, and automated evaluation.

---

## 🧭 Laboratory Curriculum & Roadmap

Each lab in this repository is a self-contained, reproducible micro-application designed to demonstrate a core concept in production AI engineering:

| Lab | Topic | Core Mechanics | Status |
|:---|:---|:---|:---|
| **`01_structured_extraction`** | **The LLM Engine & Type Safety** | Tokenization, logits, temperature, JSON Schema enforcement, Pydantic validation, self-healing retry loops | 📋 Planned |
| **`02_retrieval_rag`** | **Retrieval-Augmented Generation** | Vector embeddings, cosine similarity, semantic chunking, dense + sparse (BM25) hybrid search, cross-encoder reranking | 📋 Planned |
| **`03_agentic_loop`** | **The Agentic Loop (ReAct)** | Tool schemas, observation feedback loops, state machines, self-reflection, syntax & execution recovery | 📋 Planned |
| **`04_multi_agent`** | **Multi-Agent Systems** | Hierarchical supervisor-worker graphs, consensus loops, task decomposition, agent handoffs | 📋 Planned |
| **`05_evals_benchmarking`** | **Evaluation & Guardrails** | LLM-as-a-Judge, deterministic regression suites, hallucination scoring, cost/latency profiling | 📋 Planned |
| **`06_local_inference`** | **100% Local Inference** | Open-weight models (Llama 3, Qwen), quantization (GGUF), Apple Silicon MLX / Ollama, offline copilot | 📋 Planned |

---

## 🏛️ Engineering Principles

1. **First-Principles Before Abstractions**: Master the underlying mathematical and programmatic mechanisms (tokens, vectors, schemas) before leaning on high-level frameworks.
2. **Deterministic Outputs from Probabilistic Models**: Guarantee runtime safety through strict typing, schema compilation, and validation barriers.
3. **Reproducibility & Observability**: Every lab includes automated unit tests, token and latency metrics, and clear interactive demos.
4. **Zero-Secret Commits**: Never commit raw API keys or personal credentials to git.

---

## 🛠️ Getting Started

```bash
# Clone the repository
git clone https://github.com/SahilBhati/ai-engineering-labs.git
cd ai-engineering-labs

# Set up local virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

---

## 🤝 Contributing

Contributions, bug reports, and enhancements are welcome via Pull Requests. Direct pushes to `main` are restricted to maintain build integrity and review quality.

# Setup Guide

## Prerequisites

- **Python 3.11+** (we use 3.12)
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager
- **API keys** — at minimum, a Gemini API key (see `.env.example`)

## Quick Start

```bash
# Clone
git clone https://github.com/SahilBhati/ai-engineering-labs.git
cd ai-engineering-labs

# Environment
uv venv
source .venv/bin/activate

# API Keys
cp .env.example .env
# Edit .env with your keys

# Run a specific lab
cd labs/01-structured-extraction
uv sync
python src/main.py
```

## Project Structure

```
ai-engineering-labs/
├── labs/                    # Hands-on experiments (the core)
│   ├── 01-structured-extraction/
│   ├── 02-retrieval-rag/
│   ├── 03-agentic-loop/
│   ├── 04-multi-agent/
│   ├── 05-evals-benchmarking/
│   └── 06-local-inference/
├── learning/                # Study notes & reading list
├── tools/                   # Shared utilities across labs
│   ├── shared/              # Common helpers
│   └── scripts/             # One-off automation
├── docs/                    # Setup guides, architecture decisions
├── .env.example             # API key template
└── README.md
```

## Companion Vault

This repo pairs with the **ai-vault** Obsidian vault (`~/ai-vault/`) where concept notes, experiment logs, and reusable recipes are tracked. See the vault's `AGENTS.md` for the knowledge architecture.

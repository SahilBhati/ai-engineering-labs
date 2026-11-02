# Lab 01: Structured Extraction — The LLM Engine & Type Safety

## What You'll Learn

- How LLMs generate text (tokens, logits, temperature, top-p)
- Forcing structured JSON output via schema enforcement
- Pydantic validation as a runtime safety net
- Self-healing retry loops when extraction fails

## Concepts Covered

| Concept | Vault Link |
|:---|:---|
| Tokenization | `200-Core-Domains/210-LLM-Foundations/` |
| JSON Schema Enforcement | `200-Core-Domains/210-LLM-Foundations/` |
| Pydantic Validation | `300-Skill-Factory/Patterns/` |

## Setup

```bash
cd labs/01-structured-extraction
uv sync  # install dependencies from pyproject.toml
cp ../../.env.example ../../.env  # fill in API keys
```

## Status: 📋 Planned

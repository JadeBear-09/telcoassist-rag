# Contributing

Keep TelcoAssist changes grounded, testable, and explicit about retrieval/security
impact.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/ingest.py --raw-dir data/raw --processed-dir data/processed
```

## Validation

```bash
python -m ruff check .
python -m pytest
python scripts/ingest.py --raw-dir data/raw --processed-dir data/processed
python scripts/evaluate.py --golden data/golden_questions.csv --processed-dir data/processed
```

Run Qdrant checks when changes touch vector search, payload filtering, ACLs, or benchmark
logic.

## Pull Request Expectations

- Keep one PR focused on one retrieval, guardrail, API, or documentation goal.
- Add tests for new retrieval behavior, prompt behavior, security controls, or API paths.
- Update golden questions when evaluation expectations change.
- Include before/after retrieval or answer examples for RAG changes.
- Document new environment variables in `README.md`.
- Do not commit `.env`, API keys, private prompts, private documents, generated audit
  logs, or customer data.

## Commit Style

Use [docs/COMMIT_GUIDE.md](docs/COMMIT_GUIDE.md).

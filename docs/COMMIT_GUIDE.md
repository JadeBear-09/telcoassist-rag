# Commit Guide

Use Conventional Commits so retrieval, security, and API changes are easy to audit.

## Format

```text
type(scope): short summary
```

Examples:

```text
feat(retrieval): add hybrid reranker fallback
fix(acl): filter qdrant results before citations
docs(readme): add enterprise controls overview
test(guardrails): cover prompt injection blocking
ci: run ingestion and retrieval evaluation
```

## Types

| Type | Use when |
| --- | --- |
| `feat` | adding behavior |
| `fix` | correcting behavior |
| `docs` | changing docs |
| `test` | adding or changing tests |
| `refactor` | moving code without behavior change |
| `perf` | improving retrieval, ingestion, or API performance |
| `build` | changing Docker, packaging, or dependencies |
| `ci` | changing GitHub Actions |
| `chore` | maintenance |

## Suggested Scopes

- `ingestion`
- `retrieval`
- `reranker`
- `generator`
- `guardrails`
- `acl`
- `audit`
- `feedback`
- `prompt-lab`
- `evaluation`
- `docs`
- `ci`

## Hygiene

- Keep prompt/retrieval changes separate from cosmetic docs changes when possible.
- Mention evaluation impact in the commit body for RAG behavior changes.
- Include `python scripts/evaluate.py ...` results in PR notes.
- Never commit secrets, private documents, raw customer prompts, audit logs, or API keys.

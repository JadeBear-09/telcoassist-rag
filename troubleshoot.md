# TelcoAssist Troubleshooting + Cost-Safe AWS Notes

Use this during deploy and handoff. Keep it public-safe: no real account IDs, ARNs,
tokens, API keys, passwords, or one-time console URLs.

## Current Verified State

Local checks passed before AWS deploy handoff:

- `python -m ruff check .`
- `python -m pytest` -> 39 passed
- `python scripts/ingest.py --raw-dir data/raw --processed-dir data/processed`
- `python scripts/evaluate.py --golden data/golden_questions.csv --processed-dir data/processed`
- `docker build -t telcoassist-rag:codex-check .`
- Docker runtime smoke with `AUTO_INGEST_ON_STARTUP=true`
- `/health` returned status `ok`
- `/ready` returned 5 docs, 6 chunks, 6 embeddings

Main local UI:

```text
http://localhost:8001/query
```

Default container port:

```text
8000
```

## Problems Already Faced

### Old UI Still Showing

Cause:

- Uvicorn process was stale and started without reload.
- Browser was hitting code loaded before latest UI changes.

Fix:

```bash
lsof -nP -iTCP:8001 -sTCP:LISTEN
kill <stale-uvicorn-pid>
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Verify:

```bash
curl -sS http://localhost:8001/query | rg "Remember key|Exact lookup"
```

### Port 8000 Conflict

Cause:

- Another local Python app was also listening on `8000`.
- Requests to `/query` returned old/wrong routes or 404.

Fix:

- Use `8001` locally for TelcoAssist.
- Use `8000` inside Docker/App Runner.

Check:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:8001 -sTCP:LISTEN
```

### Browser Error After Server Restart

Cause:

- Browser tab loaded while server was down, then stayed on Chrome error page.

Fix:

- Start server first.
- Open a fresh tab to `http://localhost:8001/query`.

### Detached Uvicorn Died Locally

Cause:

- Background process was reaped in local app environment after first request.

Fix:

- For local demo, keep managed terminal session running.
- For AWS, use Docker/App Runner process model; do not rely on local `nohup`.

### Ruff Failed Before Cleanup

Cause:

- Lint was configured but CI did not run it.
- Issues included long lines, unsorted imports, and missing `zip(..., strict=...)`.

Fix:

- Code lint cleaned.
- CI now runs `python -m ruff check .` before tests.

### FastAPI Annotated Form Error

Cause:

- `Form(False)` was placed inside `Annotated`, which FastAPI rejects.

Fix:

```python
use_qdrant: Annotated[bool, Form()] = False
```

### Runtime Logs And Private Notes

Cause:

- Local audit logs, feedback logs, and personal notes can contain sensitive context.

Fix:

- `.gitignore` excludes `.env`, `.env.*`, `data/audit/`, `data/feedback/`,
  AWS local files, and personal notes like `for_me.md`.
- This file is sanitized and can be pushed.

## AWS Deploy Notes

Use `DEPLOY_AWS.md` as main deployment plan.

Safe target:

- AWS App Runner for FastAPI API
- ECR for Docker image
- SSM Parameter Store or Secrets Manager for `APP_API_KEY`
- CloudWatch logs
- Qdrant Cloud only when needed
- S3/SQS ingestion later, not required for small demo

Recommended production env:

```env
APP_ENV=production
AUTH_ENABLED=true
APP_API_KEY=<store in SSM or Secrets Manager, not plain env>
RATE_LIMIT_PER_MINUTE=120
AUTO_INGEST_ON_STARTUP=false
LOG_LEVEL=INFO
USE_QDRANT=false
EMBEDDING_PROVIDER=hashing
CONFIDENCE_THRESHOLD=0.38
ALLOW_USER_OPENAI_API_KEY=true
ALLOW_USER_GEMINI_API_KEY=true
```

Use `USE_QDRANT=false` for first App Runner demo to avoid extra paid services.
Turn Qdrant Cloud on only when you need managed vector persistence and scale.

## Free Credit / Cost Guardrails

Goal: deploy without surprise bill.

Before deploy:

- Set AWS Budget alert at a tiny threshold, e.g. `$5` and `$10`.
- Set billing email alerts.
- Confirm region, usually `us-east-1`.
- Prefer smallest App Runner instance: `0.25 vCPU`, `0.5 GB`.
- Disable auto-deploy unless intentionally testing CI/CD.
- Do not create NAT Gateway, OpenSearch, RDS, EKS, or always-on EC2 for this demo.
- Do not run large synthetic 1M benchmark in AWS unless budget approved.
- Do not enable Qdrant Cloud paid tier unless needed.
- Keep OpenAI/Gemini server key optional; local extractive answer works without paid LLM calls.

After demo:

- Pause/delete App Runner service if not needed.
- Delete unused ECR images.
- Stop/delete Qdrant Cloud trial cluster if created.
- Delete S3 test buckets if not needed.
- Check AWS Cost Explorer next day.

Cost-safe first deploy path:

```text
App Runner + ECR + local JSONL index baked/ingested at startup + API key auth
```

Avoid for free-credit safety:

```text
EKS, OpenSearch, RDS, NAT Gateway, high-memory App Runner, GPU, large batch embedding jobs
```

## AWS Smoke Tests

Replace placeholders only in shell/session, not in committed docs:

```bash
APP_URL=https://<app-runner-url>
APP_API_KEY=<read-from-ssm-or-secrets-manager>

curl "$APP_URL/health"
curl "$APP_URL/ready"
curl "$APP_URL/query"

curl -X POST "$APP_URL/ask" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $APP_API_KEY" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-User-ID: support.alice" \
  -H "X-User-Roles: support_agent,network_admin" \
  -d '{
    "question": "A customer in Berlin has poor 5G signal after SIM replacement. What troubleshooting steps should support follow?",
    "top_k": 6,
    "filters": {"region": "Germany", "product": "5G"}
  }'
```

Expected:

- `/health` returns `status=ok`.
- `/ready` returns non-zero docs/chunks.
- `/query` renders TelcoAssist Query UI.
- `/ask` returns answer, citations, confidence, and no leaked secrets.

## Common AWS Failures

### App Runner Cannot Pull ECR Image

Likely cause:

- Missing or wrong App Runner ECR access role.
- Image URI typo.
- Region mismatch.

Fix:

- Keep ECR repo and App Runner service in same region.
- Use exact image URI from ECR console.
- Attach required App Runner ECR access permissions.

### `/ready` Fails

Likely cause:

- No processed index.
- Qdrant enabled but URL unreachable.
- Startup ingestion disabled and no persisted index.

Fix for cheapest demo:

```env
AUTO_INGEST_ON_STARTUP=true
USE_QDRANT=false
```

Fix for Qdrant path:

```env
USE_QDRANT=true
QDRANT_URL=<qdrant-cloud-url>
QDRANT_COLLECTION=telco_documents
```

Then run ingestion once.

### `/ask` Returns 401

Cause:

- `AUTH_ENABLED=true` or `APP_API_KEY` configured.
- Request missing `X-API-Key`.

Fix:

```bash
-H "X-API-Key: $APP_API_KEY"
```

### Upload Works Locally But Fails In AWS

Likely cause:

- App Runner ephemeral storage.
- Uploaded docs/index vanish on redeploy.

Fix:

- For demo, use startup ingestion from bundled `data/raw`.
- For production, use S3 + ingestion worker + Qdrant.

### High LLM Cost

Cause:

- Server `OPENAI_API_KEY` or `GEMINI_API_KEY` set and many users ask questions.

Fix:

- Leave server LLM key empty for demo.
- Use local extractive answer or per-request BYOK.
- Keep rate limit enabled.

## What Not To Commit

- `.env`
- real AWS account IDs in command history
- real ARNs if they expose account ID
- API keys
- SSM parameter values
- CloudWatch logs with request data
- `data/audit/`
- `data/feedback/`
- Terraform state or tfvars
- private notes

Use placeholders:

```text
<account-id>
<region>
<app-runner-url>
<ecr-image-uri>
<ssm-parameter-arn>
<qdrant-cloud-url>
```

# TelcoAssist AWS Deployment Plan

Chosen platform: AWS.

Reason: the deployment path covers container build, managed runtime, secrets, vector DB, object storage, CI/CD, readiness checks, logs, and cost control.

## Target Architecture

```text
GitHub
  -> GitHub Actions CI
  -> Docker build
  -> Amazon ECR
  -> AWS App Runner
      -> FastAPI TelcoAssist API
      -> /health and /ready checks
      -> APP_API_KEY from Secrets Manager or SSM Parameter Store
      -> logs to CloudWatch

Documents
  -> S3 bucket
  -> SQS event
  -> ingestion job
  -> Qdrant Cloud cluster
  -> /ask retrieves cited telecom context
```

## Why Not Azure First

Azure is also valid:

```text
Azure Container Apps + Azure Container Registry + Blob Storage + Key Vault + Azure Monitor
```

Use Azure when the target environment is Microsoft-heavy, enterprise IT-heavy, or already runs on Azure.

Use AWS for startup AI engineering default because AWS story is broadly recognized and maps cleanly to this repo.

## Deployment Services

Use this for public demo / small beta:

- Compute: AWS App Runner
- Image registry: Amazon ECR
- Vector DB: Qdrant Cloud
- Object storage: Amazon S3
- Secrets: AWS Secrets Manager or SSM Parameter Store
- Logs: CloudWatch
- CI/CD: GitHub Actions

Use this for heavier production:

- Compute: ECS Fargate behind Application Load Balancer
- Vector DB: Qdrant Cloud or Qdrant on ECS/EKS with persistent storage
- Queue: SQS for ingestion jobs
- Observability: CloudWatch metrics/logs plus traces

## First Deploy Path

1. Create Qdrant Cloud cluster.
2. Create ECR repo.
3. Build and push Docker image.
4. Create App Runner service from ECR image.
5. Set environment variables.
6. Run ingestion job or small ZIP upload from `/upload`.
7. Check `/health`, `/ready`, and `/ask`.

For a free-credit-safe first deploy, start without Qdrant Cloud:

```text
USE_QDRANT=false
AUTO_INGEST_ON_STARTUP=true
```

Then use the smallest App Runner instance, set AWS Budget alerts, and delete or pause
unused services after the demo. See `troubleshoot.md` for deployment problems already
hit and cost guardrails to avoid surprise bills.

## Environment Variables

```env
APP_ENV=production
APP_API_KEY=<long-random-token>
AUTH_ENABLED=true
RATE_LIMIT_PER_MINUTE=120
AUTO_INGEST_ON_STARTUP=false
LOG_LEVEL=INFO
USE_QDRANT=true
QDRANT_URL=<qdrant-cloud-url>
QDRANT_COLLECTION=telco_documents
EMBEDDING_PROVIDER=hashing
OPENAI_API_KEY=<optional>
OPENAI_MODEL=gpt-4.1-mini
CONFIDENCE_THRESHOLD=0.38
```

## Build And Push

Replace placeholders:

```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=<account-id>
IMAGE=telcoassist-rag

aws ecr create-repository --repository-name "$IMAGE" --region "$AWS_REGION"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -t "$IMAGE:latest" .
docker tag "$IMAGE:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$IMAGE:latest"
```

## App Runner Setup

In AWS console:

1. App Runner -> Create service.
2. Source: container registry.
3. Provider: Amazon ECR.
4. Image: `telcoassist-rag:latest`.
5. Port: `8000`.
6. Health check path: `/health`.
7. Add env vars above.
8. Store secrets in Secrets Manager or SSM Parameter Store.

After deploy:

```bash
curl https://<app-runner-url>/health
curl https://<app-runner-url>/ready
curl -X POST https://<app-runner-url>/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <APP_API_KEY>" \
  -d '{
    "question": "A customer in Berlin has poor 5G signal after SIM replacement. What troubleshooting steps should support follow?",
    "top_k": 6,
    "filters": {"region": "Germany", "product": "5G"}
  }'
```

## Architecture Summary

Summary:

```text
I deployed it on AWS because I wanted a realistic startup-style AI deployment path.
The FastAPI RAG service is containerized, pushed to ECR, and served with App Runner.
Qdrant Cloud stores vectors, S3 stores raw documents, Secrets Manager stores API keys,
CloudWatch captures structured request logs, and GitHub Actions runs tests plus ingestion/eval smoke checks before deploy.

For a larger production version I would move from App Runner to ECS Fargate behind an ALB,
run ingestion as a separate job triggered by S3 uploads and SQS, add gateway-level rate limits,
and track retrieval metrics like hit rate, precision@1, MRR, latency, and insufficient-context rate.
```

Short version:

```text
AWS App Runner for the API, ECR for images, Qdrant Cloud for vector search,
S3 for documents, Secrets Manager for credentials, CloudWatch for logs,
and GitHub Actions for CI/CD.
```

## Resume Bullet

```text
Deployed a Dockerized FastAPI telecom RAG system on AWS using ECR, App Runner,
Qdrant Cloud, S3, Secrets Manager, CloudWatch, and GitHub Actions, with readiness checks,
API-key auth, rate limiting, structured logs, and retrieval eval metrics.
```

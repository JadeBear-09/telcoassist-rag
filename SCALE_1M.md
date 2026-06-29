# 1M Document / Passage Scale Plan

Goal: document end-to-end RAG scale behavior, including upload, ingestion speed, retrieval latency, and production architecture.

## Current 1M Benchmark

Existing benchmark result:

```text
Corpus: MS MARCO subset
Indexed passages: 1,000,000
Embedding: hashing, 384 dim
Vector DB: local Qdrant
Index time: 116.38 seconds
Index throughput: 8,592.73 passages/second
Queries: 1,000
p50 query latency: 12.07 ms
p95 query latency: 18.78 ms
Average query latency: 14.09 ms
Recall@10: 0.0405
MRR@10: 0.0197
```

Source file:

```text
data/processed/msmarco_benchmark/msmarco_qdrant_1000000.json
```

Important caveat: this proves vector indexing/query throughput, not final answer quality. Recall is low because hashing embeddings are cheap and deterministic. Stronger semantic embeddings should improve quality but cost more time/money.

## Upload Button

Demo upload exists at:

```text
GET /upload
POST /ingest/upload
```

Accepted ZIP contents:

- `.md`
- `.txt`
- `.csv`
- `.pdf`

Default limits:

```env
MAX_UPLOAD_MB=512
MAX_UPLOAD_FILES=10000
```

This is for demos and small admin uploads. It replaces the processed local index and can optionally write to Qdrant.

## Why Not Upload 1M Docs Directly To FastAPI

Do not send a 1M-document ZIP directly through the API.

Reasons:

- HTTP request can timeout.
- App Runner/container worker gets blocked.
- ZIP can exceed memory/disk limits.
- Retry handling is weak.
- One failed request can waste hours.
- Security risk: zip bombs and path traversal.

## Correct 1M Architecture

Use object storage and background workers:

```text
Browser upload
  -> S3 multipart upload or presigned URL
  -> S3 object-created event
  -> SQS queue
  -> ECS/Fargate ingestion worker
  -> parse/chunk/embed in batches
  -> Qdrant batch upsert
  -> status table
  -> UI shows progress + docs/sec + chunks/sec
```

For large uploads:

```text
The button is for small ZIP demos. For 1M docs, avoid streaming the ZIP through FastAPI.
Upload to S3 using presigned multipart upload, trigger an SQS-backed ingestion worker,
batch embeddings and Qdrant upserts, and report progress metrics in the dashboard.
```

## Metrics To Show

For each ingestion run:

- documents discovered
- documents parsed
- chunks created
- embedding provider
- embedding dimension
- indexing target
- total seconds
- docs/sec
- chunks/sec
- Qdrant upsert batch size
- failed documents
- p50/p95 query latency after indexing
- hit rate / precision@1 / MRR on golden questions

## Commands

Run current local smoke:

```bash
.venv/bin/python -m pytest
.venv/bin/python scripts/ingest.py --raw-dir data/raw --processed-dir data/processed
.venv/bin/python scripts/evaluate.py --golden data/golden_questions.csv --processed-dir data/processed
```

Run 1M MS MARCO Qdrant benchmark:

```bash
docker compose up -d qdrant
.venv/bin/python scripts/benchmark_msmarco_qdrant.py \
  --passages 1000000 \
  --queries 1000 \
  --top-k 10 \
  --qdrant-url http://localhost:6333 \
  --recreate
```

## Scale Summary

```text
The ZIP upload endpoint supports small demos. For 1M documents, avoid direct API upload. The production path is S3 multipart upload, SQS eventing, ECS/Fargate ingestion workers, batched embedding, and Qdrant batch upserts. The 1M MS MARCO local Qdrant benchmark indexed passages in 116.38 seconds, reached about 8.6K passages/sec throughput, and returned 18.78ms p95 vector query latency. The next improvement is replacing hashing embeddings with a stronger embedding model and measuring quality-vs-cost tradeoffs.
```

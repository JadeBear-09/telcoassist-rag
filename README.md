# TelcoAssist: Scalable RAG System for Telecom Support, Policy, and Network Intelligence

TelcoAssist is an enterprise-style RAG platform for telecom support, network operations, billing, compliance, and policy documents. It ingests telecom SOPs, outage reports, runbooks, and troubleshooting guides, then answers operational questions with hybrid retrieval, reranking, source citations, confidence scoring, and fallback behavior when context is weak.

Example question:

```text
A customer in Berlin has poor 5G signal after SIM replacement. What troubleshooting steps should support follow?
```

Expected answer shape:

- exact answer grounded in retrieved context
- cited source chunks and document names
- confidence score
- escalation path
- "insufficient information" fallback when retrieval is weak
- dashboard metrics for ingestion and retrieval quality

## Architecture

```text
Documents
  -> parser
  -> cleaning + metadata extraction
  -> chunking
  -> embeddings
  -> Qdrant vector index + BM25 keyword index
  -> hybrid retrieval
  -> reranker
  -> context selection
  -> LLM/extractive answer
  -> citations + guardrails + logs
```

The starter repo runs locally with deterministic hashing embeddings, so demos work without downloading models. For a stronger production-like run, set `EMBEDDING_PROVIDER=sentence-transformers` and use `BAAI/bge-small-en-v1.5`. Qdrant is available through Docker Compose.

## Stack

- Backend: FastAPI
- Ingestion: Python, Pydantic models, CSV/Markdown/TXT/PDF parsers
- Chunking: recursive paragraph/sentence chunking with overlap
- Embeddings: hashing fallback or sentence-transformers `BAAI/bge-small-en-v1.5`
- Vector DB: Qdrant
- Keyword search: BM25 with local lexical fallback
- Reranking: cross-encoder hook with lexical fallback
- Evaluation: golden Q&A retrieval metrics
- Deployment: Docker + docker-compose

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/ingest.py --raw-dir data/raw --processed-dir data/processed
uvicorn app.main:app --reload
```

Open:

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- Dashboard summary: http://127.0.0.1:8000/dashboard/summary

Ask:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "A customer in Berlin has poor 5G signal after SIM replacement. What troubleshooting steps should support follow?",
    "top_k": 6,
    "filters": {"region": "Germany", "product": "5G"}
  }'
```

## Run With Qdrant

```bash
docker compose up -d qdrant
export USE_QDRANT=true
python scripts/ingest.py --raw-dir data/raw --processed-dir data/processed --use-qdrant
uvicorn app.main:app --reload
```

Qdrant can be replaced with LanceDB, Pinecone, Weaviate, Milvus, or turbopuffer depending on scale, latency, and cost requirements.

## Evaluation

```bash
python scripts/evaluate.py --golden data/golden_questions.csv --processed-dir data/processed
```

Tracked metrics:

- retrieval precision@k
- expected document hit rate
- citation accuracy proxy
- latency
- empty retrieval rate
- confidence distribution

## Scale Simulation

Local demo uses small synthetic docs. Resume-grade scale story:

- generate 500-5,000 synthetic telecom documents for realistic demos
- generate metadata rows for 1,000,000 documents
- embed 50k-100k chunks locally or in batches
- benchmark batch ingestion and query latency
- scale raw documents through object storage, queue workers, incremental indexing, and metadata filters

Useful scale command:

```bash
python scripts/generate_synthetic_docs.py --docs 1000 --out data/raw
```

## Resume Bullets

- Built TelcoAssist, an enterprise RAG system for telecom support and network documents using FastAPI, Qdrant, BM25 hybrid retrieval, reranking, and citation-grounded answers.
- Designed a scalable ingestion pipeline for SOPs, outage reports, billing policies, and troubleshooting guides with metadata extraction, chunking, embedding, incremental indexing, and document-level traceability.
- Improved answer reliability using hybrid search, reranking, confidence scoring, source citations, and fallback behavior for insufficient context.
- Created an evaluation framework with golden Q&A pairs to measure retrieval precision@k, citation accuracy, hallucination risk, latency, and user feedback readiness.

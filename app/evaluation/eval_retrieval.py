from __future__ import annotations

import csv
import time
from pathlib import Path

from app.config import Settings, get_settings
from app.rag.reranker import Reranker
from app.rag.retriever import HybridRetriever


def evaluate_retrieval(
    golden_path: Path,
    top_k: int = 6,
    processed_dir: Path | None = None,
) -> dict[str, float]:
    base_settings = get_settings()
    settings = (
        Settings(processed_dir=processed_dir, raw_docs_dir=base_settings.raw_docs_dir)
        if processed_dir
        else base_settings
    )
    retriever = HybridRetriever(settings)
    reranker = Reranker()

    rows = list(csv.DictReader(golden_path.open("r", encoding="utf-8")))
    if not rows:
        return {"questions": 0, "precision_at_k": 0.0, "hit_rate": 0.0, "avg_latency_ms": 0.0}

    hits = 0
    precision_sum = 0.0
    latency_sum = 0.0

    for row in rows:
        started = time.perf_counter()
        candidates = retriever.retrieve(row["question"], top_k=top_k, candidate_k=50)
        reranked = reranker.rerank(row["question"], candidates, top_k=top_k)
        latency_sum += (time.perf_counter() - started) * 1000

        expected_doc_id = row["expected_doc_id"]
        retrieved_ids = [candidate.chunk.doc_id for candidate in reranked]
        match_count = sum(1 for doc_id in retrieved_ids if doc_id == expected_doc_id)
        hits += int(match_count > 0)
        precision_sum += match_count / max(1, len(retrieved_ids))

    total = len(rows)
    return {
        "questions": float(total),
        "precision_at_k": round(precision_sum / total, 4),
        "hit_rate": round(hits / total, 4),
        "avg_latency_ms": round(latency_sum / total, 2),
    }

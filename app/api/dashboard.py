from __future__ import annotations

from collections import Counter

from fastapi import APIRouter

from app.config import get_settings
from app.ingestion.indexer import LocalChunkRepository

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary() -> dict[str, object]:
    settings = get_settings()
    repo = LocalChunkRepository(settings.processed_dir)
    chunks = repo.read_chunks()
    docs = {chunk.doc_id for chunk in chunks}
    departments = Counter(chunk.metadata.department for chunk in chunks)
    products = Counter(chunk.metadata.product for chunk in chunks)
    regions = Counter(chunk.metadata.region for chunk in chunks)

    return {
        "documents": len(docs),
        "chunks": len(chunks),
        "avg_chunks_per_document": round(len(chunks) / max(1, len(docs)), 2),
        "departments": dict(departments),
        "products": dict(products),
        "regions": dict(regions),
        "processed_dir": str(settings.processed_dir),
        "qdrant_enabled": settings.use_qdrant,
    }

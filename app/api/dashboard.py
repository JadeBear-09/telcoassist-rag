from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.ingestion.indexer import LocalChunkRepository

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
MAX_PREVIEW_CHARS = 16_000


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


@router.get("/documents")
def documents() -> dict[str, object]:
    settings = get_settings()
    repo = LocalChunkRepository(settings.processed_dir)
    chunks = repo.read_chunks()
    by_doc: dict[str, dict[str, Any]] = {}

    for chunk in chunks:
        metadata = chunk.metadata.model_dump(mode="json")
        item = by_doc.setdefault(
            chunk.doc_id,
            {
                "doc_id": chunk.doc_id,
                "title": chunk.metadata.title,
                "product": chunk.metadata.product,
                "region": chunk.metadata.region,
                "department": chunk.metadata.department,
                "doc_type": chunk.metadata.doc_type,
                "source_path": chunk.metadata.source_path,
                "access_level": chunk.metadata.access_level,
                "tenant_id": chunk.metadata.tenant_id,
                "allowed_roles": chunk.metadata.allowed_roles,
                "allowed_users": chunk.metadata.allowed_users,
                "chunks": 0,
                "metadata": metadata,
            },
        )
        item["chunks"] += 1

    return {
        "documents": sorted(by_doc.values(), key=lambda item: str(item["doc_id"])),
        "count": len(by_doc),
        "chunks": len(chunks),
        "processed_dir": str(settings.processed_dir),
    }


@router.get("/documents/{doc_id}/preview")
def document_preview(doc_id: str) -> dict[str, object]:
    settings = get_settings()
    repo = LocalChunkRepository(settings.processed_dir)
    doc_chunks = [chunk for chunk in repo.read_chunks() if chunk.doc_id == doc_id]
    if not doc_chunks:
        raise HTTPException(status_code=404, detail=f"Document not found: {doc_id}")

    doc_chunks.sort(key=lambda chunk: chunk.chunk_index)
    first = doc_chunks[0]
    remaining = MAX_PREVIEW_CHARS
    preview_chunks: list[dict[str, object]] = []
    truncated = False

    for chunk in doc_chunks:
        if remaining <= 0:
            truncated = True
            break
        text = chunk.text
        if len(text) > remaining:
            text = text[:remaining].rstrip()
            truncated = True
        preview_chunks.append(
            {
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "text": text,
                "chars": len(chunk.text),
                "token_estimate": chunk.token_estimate,
            }
        )
        remaining -= len(text)

    return {
        "doc_id": first.doc_id,
        "title": first.metadata.title,
        "product": first.metadata.product,
        "region": first.metadata.region,
        "department": first.metadata.department,
        "doc_type": first.metadata.doc_type,
        "source_path": first.metadata.source_path,
        "chunks": preview_chunks,
        "chunk_count": len(doc_chunks),
        "truncated": truncated,
        "preview_note": "Preview shows indexed chunks used by RAG retrieval.",
    }

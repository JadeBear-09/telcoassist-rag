from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import Embedder
from app.ingestion.indexer import LocalChunkRepository, QdrantVectorIndex
from app.ingestion.parser import parse_document
from app.models import DocumentChunk, IngestResponse


SUPPORTED_SUFFIXES = {".md", ".txt", ".csv", ".pdf"}


def run_ingestion(raw_dir: str, processed_dir: str, use_qdrant: bool = False) -> IngestResponse:
    started = datetime.utcnow()
    settings = get_settings()
    raw_path = Path(raw_dir)
    processed_path = Path(processed_dir)
    errors: list[str] = []
    chunks: list[DocumentChunk] = []
    documents_processed = 0

    for path in sorted(raw_path.glob("**/*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        try:
            parsed = parse_document(path)
            doc_chunks = chunk_document(parsed.text, parsed.metadata)
            chunks.extend(doc_chunks)
            documents_processed += 1
        except Exception as exc:
            errors.append(f"{path}: {exc}")

    embedder = Embedder(
        provider=settings.embedding_provider,
        model_name=settings.embedding_model,
        dim=settings.embedding_dim,
    )
    embeddings = embedder.embed_texts([chunk.text for chunk in chunks])

    repo = LocalChunkRepository(processed_path)
    repo.write(chunks, embeddings)

    qdrant_enabled = False
    if use_qdrant and chunks:
        try:
            index = QdrantVectorIndex(
                url=settings.qdrant_url,
                collection=settings.qdrant_collection,
                vector_size=settings.embedding_dim,
            )
            index.upsert(chunks, embeddings)
            qdrant_enabled = True
        except Exception as exc:
            errors.append(f"qdrant: {exc}")

    finished = datetime.utcnow()
    return IngestResponse(
        documents_processed=documents_processed,
        chunks_indexed=len(chunks),
        qdrant_enabled=qdrant_enabled,
        started_at=started,
        finished_at=finished,
        errors=errors,
    )

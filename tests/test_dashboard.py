from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.dashboard as dashboard_api
from app.config import Settings
from app.ingestion.embedder import Embedder
from app.ingestion.indexer import LocalChunkRepository
from app.models import DocumentChunk, DocumentMetadata


def _write_index(processed_dir: Path) -> None:
    chunks = [
        DocumentChunk(
            chunk_id="DT_DOC_001:0",
            doc_id="DT_DOC_001",
            text="First chunk.",
            chunk_index=0,
            metadata=DocumentMetadata(
                doc_id="DT_DOC_001",
                title="First Doc",
                product="5G",
                region="Germany",
                source_path="data/raw/first.md",
            ),
        ),
        DocumentChunk(
            chunk_id="DT_DOC_001:1",
            doc_id="DT_DOC_001",
            text="Second chunk.",
            chunk_index=1,
            metadata=DocumentMetadata(
                doc_id="DT_DOC_001",
                title="First Doc",
                product="5G",
                region="Germany",
                source_path="data/raw/first.md",
            ),
        ),
    ]
    embeddings = Embedder(provider="hashing", dim=384).embed_texts([chunk.text for chunk in chunks])
    LocalChunkRepository(processed_dir).write(chunks, embeddings)


def test_dashboard_documents_returns_grouped_document_inventory(tmp_path, monkeypatch) -> None:
    processed_dir = tmp_path / "processed"
    _write_index(processed_dir)
    monkeypatch.setattr(
        dashboard_api,
        "get_settings",
        lambda: Settings(processed_dir=processed_dir, data_dir=tmp_path / "data"),
    )
    app = FastAPI()
    app.include_router(dashboard_api.router)
    client = TestClient(app)

    response = client.get("/dashboard/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["chunks"] == 2
    assert body["documents"][0]["doc_id"] == "DT_DOC_001"
    assert body["documents"][0]["chunks"] == 2
    assert body["documents"][0]["source_path"] == "data/raw/first.md"


def test_dashboard_document_preview_returns_indexed_chunks(tmp_path, monkeypatch) -> None:
    processed_dir = tmp_path / "processed"
    _write_index(processed_dir)
    monkeypatch.setattr(
        dashboard_api,
        "get_settings",
        lambda: Settings(processed_dir=processed_dir, data_dir=tmp_path / "data"),
    )
    app = FastAPI()
    app.include_router(dashboard_api.router)
    client = TestClient(app)

    response = client.get("/dashboard/documents/DT_DOC_001/preview")

    assert response.status_code == 200
    body = response.json()
    assert body["doc_id"] == "DT_DOC_001"
    assert body["chunk_count"] == 2
    assert body["chunks"][0]["text"] == "First chunk."
    assert body["preview_note"] == "Preview shows indexed chunks used by RAG retrieval."


def test_dashboard_document_preview_404s_for_unknown_doc(tmp_path, monkeypatch) -> None:
    processed_dir = tmp_path / "processed"
    _write_index(processed_dir)
    monkeypatch.setattr(
        dashboard_api,
        "get_settings",
        lambda: Settings(processed_dir=processed_dir, data_dir=tmp_path / "data"),
    )
    app = FastAPI()
    app.include_router(dashboard_api.router)
    client = TestClient(app)

    response = client.get("/dashboard/documents/MISSING/preview")

    assert response.status_code == 404

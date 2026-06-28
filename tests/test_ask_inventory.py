from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.ask as ask_api
from app.config import Settings
from app.ingestion.embedder import Embedder
from app.ingestion.indexer import LocalChunkRepository
from app.models import DocumentChunk, DocumentMetadata


def _chunk(
    doc_id: str,
    text: str,
    *,
    product: str,
    region: str = "Germany",
    tenant_id: str | None = None,
    allowed_roles: list[str] | None = None,
) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=f"{doc_id}:0",
        doc_id=doc_id,
        text=text,
        chunk_index=0,
        metadata=DocumentMetadata(
            doc_id=doc_id,
            title=doc_id,
            product=product,
            region=region,
            tenant_id=tenant_id,
            allowed_roles=allowed_roles or [],
        ),
        token_estimate=len(text.split()),
    )


def _client(tmp_path, monkeypatch) -> TestClient:
    processed_dir = tmp_path / "processed"
    chunks = [
        _chunk("DT_5G_PUBLIC", "Public 5G troubleshooting.", product="5G"),
        _chunk("DT_SIM_PUBLIC", "Public SIM provisioning.", product="SIM"),
        _chunk(
            "DT_5G_PRIVATE",
            "Restricted 5G enterprise escalation.",
            product="5G",
            tenant_id="tenant-a",
            allowed_roles=["network_admin"],
        ),
    ]
    embeddings = Embedder(provider="hashing", dim=384).embed_texts([chunk.text for chunk in chunks])
    LocalChunkRepository(processed_dir).write(chunks, embeddings)
    settings = Settings(
        data_dir=tmp_path / "data",
        processed_dir=processed_dir,
        allow_user_openai_api_key=False,
        confidence_threshold=0.0,
        openai_api_key="",
    )
    monkeypatch.setattr(ask_api, "get_settings", lambda: settings)
    app = FastAPI()
    app.include_router(ask_api.router)
    return TestClient(app)


def test_ask_answers_knowledge_graph_document_count_from_index(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        "/ask",
        json={"question": "how many docs are there in ur knowledge graph?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "2 documents" in body["answer"]
    assert "2 chunks visible to this user" in body["answer"]
    assert "DT_5G_PUBLIC" in body["answer"]
    assert "DT_SIM_PUBLIC" in body["answer"]
    assert "DT_5G_PRIVATE" not in body["answer"]
    assert body["sources"] == []
    assert body["confidence"] == 1.0
    assert body["insufficient_information"] is False


def test_ask_inventory_answer_respects_filters_and_acl(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        "/ask",
        headers={
            "X-Tenant-ID": "tenant-a",
            "X-User-Roles": "network_admin",
        },
        json={
            "question": "What is the total number of documents in the knowledge base?",
            "filters": {"region": "Germany", "product": "5G"},
        },
    )

    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "3 documents" in answer
    assert "Current filters (product=5G, region=Germany) match 2 documents and 2 chunks" in answer
    assert "DT_5G_PUBLIC" in answer
    assert "DT_5G_PRIVATE" in answer
    assert "DT_SIM_PUBLIC" not in answer


def test_answer_style_instructions_support_standard_brief_and_audit() -> None:
    assert "Answer, Evidence, Next step" in ask_api.answer_style_instructions("standard")
    assert "2-4 short bullets" in ask_api.answer_style_instructions("brief")
    assert "audit-style answer" in ask_api.answer_style_instructions("audit")

from datetime import date

from app.ingestion.chunker import chunk_document
from app.models import DocumentMetadata


def test_chunk_document_preserves_doc_id() -> None:
    metadata = DocumentMetadata(
        doc_id="DT_TEST_001",
        title="Test SOP",
        product="5G",
        region="Germany",
        created_at=date(2025, 1, 1),
    )
    chunks = chunk_document("First paragraph.\n\nSecond paragraph about Berlin 5G.", metadata, max_chars=40)

    assert chunks
    assert all(chunk.doc_id == "DT_TEST_001" for chunk in chunks)
    assert chunks[0].chunk_id.startswith("DT_TEST_001_CH_")

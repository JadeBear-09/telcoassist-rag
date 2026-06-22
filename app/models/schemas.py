from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    doc_id: str
    title: str
    company: str = "Deutsche Telekom"
    department: str = "Support"
    region: str = "Global"
    language: str = "English"
    doc_type: str = "Knowledge Base"
    product: str = "General"
    created_at: date | None = None
    access_level: str = "support_agent"
    source_path: str | None = None


class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    chunk_index: int
    metadata: DocumentMetadata
    token_estimate: int = 0


class RetrievalCandidate(BaseModel):
    chunk: DocumentChunk
    score: float
    vector_score: float = 0.0
    keyword_score: float = 0.0
    rerank_score: float = 0.0


class SourceCitation(BaseModel):
    doc_id: str
    document_name: str
    chunk_id: str
    chunk_index: int
    score: float
    excerpt: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    top_k: int = Field(default=6, ge=1, le=12)
    filters: dict[str, str] = Field(default_factory=dict)


class AskResponse(BaseModel):
    answer: str
    confidence: float
    sources: list[SourceCitation]
    escalation_path: str | None = None
    insufficient_information: bool = False
    latency_ms: int


class IngestRequest(BaseModel):
    raw_dir: str = "data/raw"
    processed_dir: str = "data/processed"
    use_qdrant: bool = False


class IngestResponse(BaseModel):
    documents_processed: int
    chunks_indexed: int
    qdrant_enabled: bool
    started_at: datetime
    finished_at: datetime
    errors: list[str] = Field(default_factory=list)

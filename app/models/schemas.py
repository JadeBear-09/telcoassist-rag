from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


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
    tenant_id: str | None = None
    allowed_roles: list[str] = Field(default_factory=list)
    allowed_users: list[str] = Field(default_factory=list)


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


AnswerStyle = Literal["brief", "standard", "audit"]


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    top_k: int = Field(default=6, ge=1, le=12)
    filters: dict[str, str] = Field(default_factory=dict)
    answer_style: AnswerStyle = "standard"

    @field_validator("answer_style", mode="before")
    @classmethod
    def normalize_answer_style(cls, value: str | None) -> str:
        return value or "standard"


class RequestIdentity(BaseModel):
    tenant_id: str | None = None
    user_id: str | None = None
    roles: list[str] = Field(default_factory=list)


GuardrailAction = Literal["allow", "redact", "block"]
AuditAction = Literal["allow", "block", "redact", "answer"]


class GuardrailReport(BaseModel):
    action: GuardrailAction = "allow"
    blocked: bool = False
    redacted: bool = False
    categories: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    token_estimate: int = 0
    max_tokens: int | None = None


class AskResponse(BaseModel):
    answer: str
    confidence: float
    sources: list[SourceCitation]
    escalation_path: str | None = None
    insufficient_information: bool = False
    latency_ms: int
    guardrails: GuardrailReport | None = None
    answer_provider: str = "local"
    provider_status: str | None = None


class AuditLogRecord(BaseModel):
    request_id: str
    timestamp: datetime
    route: str
    tenant_id: str | None = None
    user_id: str | None = None
    roles: list[str] = Field(default_factory=list)
    question_hash: str
    action: AuditAction
    guardrail_categories: list[str] = Field(default_factory=list)
    retrieved_doc_ids: list[str] = Field(default_factory=list)
    latency_ms: int
    insufficient_information: bool = False
    confidence: float = 0.0


class GuardrailMetrics(BaseModel):
    total_requests: int = 0
    blocked_requests: int = 0
    redacted_requests: int = 0
    block_rate: float = 0.0
    redaction_rate: float = 0.0
    category_counts: dict[str, int] = Field(default_factory=dict)
    insufficient_information_rate: float = 0.0
    avg_latency_ms: float = 0.0


FeedbackRating = Literal["up", "down"]
FeedbackReason = Literal["wrong_source", "incomplete", "hallucinated", "unclear", "other"]


class FeedbackRequest(BaseModel):
    question: str = Field(min_length=3)
    answer: str = Field(min_length=1)
    sources: list[SourceCitation] = Field(default_factory=list)
    rating: FeedbackRating
    reason: FeedbackReason
    comment: str | None = None
    expected_doc_id: str | None = None
    corrected_answer: str | None = None


class FeedbackRecord(FeedbackRequest):
    feedback_id: str
    timestamp: datetime


class PromptLabRequest(BaseModel):
    candidate_prompt: str = Field(
        min_length=1,
        max_length=4000,
        description="Style/template instructions only. Grounding guardrails stay locked.",
    )
    candidate_name: str = Field(default="candidate", min_length=1, max_length=80)
    golden_path: str = "data/golden_questions.csv"
    processed_dir: str | None = None
    top_k: int = Field(default=6, ge=1, le=12)

    @field_validator("candidate_prompt")
    @classmethod
    def candidate_prompt_must_not_override_grounding(cls, value: str) -> str:
        lowered = value.lower()
        forbidden = (
            "ignore context",
            "ignore supplied context",
            "ignore the supplied context",
            "do not use context",
            "don't use context",
            "without citations",
            "do not cite",
            "don't cite",
            "no citations",
            "omit citations",
            "make up",
            "fabricate",
            "ignore guardrail",
            "override guardrail",
        )
        if any(phrase in lowered for phrase in forbidden):
            raise ValueError(
                "Candidate prompt can only change style/template, not grounding rules."
            )
        return value


class PromptLabQuestionSummary(BaseModel):
    question: str
    expected_doc_id: str
    answer_preview: str
    cited_doc_ids: list[str]
    expected_doc_cited: bool
    confidence: float
    insufficient_information: bool
    latency_ms: int
    hallucination_risk_proxy: str


class PromptLabVariantSummary(BaseModel):
    name: str
    avg_confidence: float
    citation_coverage: float
    expected_doc_citation_rate: float
    insufficient_information_rate: float
    avg_latency_ms: float
    hallucination_risk_proxy: str
    hallucination_risk_distribution: dict[str, int]
    answer_summaries: list[PromptLabQuestionSummary] = Field(default_factory=list)


class PromptLabRunResponse(BaseModel):
    run_id: str
    timestamp: datetime
    questions: int
    locked_guardrail: str
    baseline: PromptLabVariantSummary
    candidate: PromptLabVariantSummary
    result_path: str


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

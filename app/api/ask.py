from __future__ import annotations

import re
import time
from collections import Counter
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.ingestion.indexer import LocalChunkRepository
from app.models import (
    AnswerStyle,
    AskRequest,
    AskResponse,
    DocumentChunk,
    GuardrailReport,
    RequestIdentity,
)
from app.rag.generator import AnswerGenerator
from app.rag.reranker import Reranker
from app.rag.retriever import HybridRetriever
from app.security.acl import filter_chunks_by_acl, normalize_identity, parse_roles
from app.security.audit import append_audit_record, build_audit_record
from app.security.llm_firewall import LLMFirewall

router = APIRouter(tags=["rag"])

CORPUS_INVENTORY_RE = re.compile(
    r"\b(how many|number of|count of|total)\b.*\b(documents?|docs?|chunks?|sources?)\b.*"
    r"\b(knowledge\s+(?:base|graph)|corpus|index|indexed)\b|"
    r"\b(knowledge\s+(?:base|graph)|corpus|index|indexed)\b.*"
    r"\b(how many|number of|count of|total)\b.*\b(documents?|docs?|chunks?|sources?)\b",
    re.IGNORECASE,
)


@router.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest,
    x_openai_api_key: Annotated[str | None, Header(alias="X-OpenAI-API-Key")] = None,
    x_gemini_api_key: Annotated[str | None, Header(alias="X-Gemini-API-Key")] = None,
    x_request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
    x_user_roles: Annotated[str | None, Header(alias="X-User-Roles")] = None,
) -> AskResponse:
    started_at = time.perf_counter()
    request_id = x_request_id or str(uuid4())
    identity = normalize_identity(
        tenant_id=x_tenant_id,
        user_id=x_user_id,
        roles=parse_roles(x_user_roles),
    )
    settings = get_settings()
    settings = with_user_llm_keys(settings, x_openai_api_key, x_gemini_api_key)
    firewall = LLMFirewall(settings)
    firewall_check = firewall.inspect_question(request.question)
    if firewall_check.report.blocked:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        append_audit_record(
            settings.data_dir,
            build_audit_record(
                request_id=request_id,
                route="/ask",
                identity=identity,
                question=request.question,
                action="block",
                guardrail_categories=firewall_check.report.categories,
                retrieved_doc_ids=[],
                latency_ms=latency_ms,
                insufficient_information=False,
                confidence=0.0,
            ),
        )
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Question blocked by LLM firewall.",
                "request_id": request_id,
                "guardrails": firewall_check.report.model_dump(),
            },
        )

    inventory_response = answer_corpus_inventory_question(
        question=firewall_check.text,
        processed_dir=settings.processed_dir,
        filters=request.filters,
        identity=identity,
        started_at=started_at,
    )
    if inventory_response is not None:
        response = firewall.sanitize_response(inventory_response, firewall_check.report)
        audit_answer(settings.data_dir, request_id, identity, request.question, response)
        return response

    retriever = HybridRetriever(settings)
    reranker = Reranker()
    generator = AnswerGenerator(settings)

    candidates = retriever.retrieve(
        firewall_check.text,
        top_k=request.top_k,
        filters=request.filters,
        candidate_k=settings.candidate_k,
        identity=identity,
    )
    reranked = reranker.rerank(firewall_check.text, candidates, top_k=request.top_k)
    response = generator.generate(
        firewall_check.text,
        reranked,
        started_at,
        style_instructions=answer_style_instructions(request.answer_style),
    )
    response = firewall.sanitize_response(response, firewall_check.report)
    audit_answer(settings.data_dir, request_id, identity, request.question, response)
    return response


def with_user_llm_keys(
    settings,
    user_openai_api_key: str | None,
    user_gemini_api_key: str | None,
):
    settings = with_user_openai_key(settings, user_openai_api_key)
    return with_user_gemini_key(settings, user_gemini_api_key)


def with_user_openai_key(settings, user_openai_api_key: str | None):
    if user_openai_api_key and settings.allow_user_openai_api_key:
        return settings.model_copy(update={"openai_api_key": user_openai_api_key})
    return settings


def with_user_gemini_key(settings, user_gemini_api_key: str | None):
    if user_gemini_api_key and settings.allow_user_gemini_api_key:
        return settings.model_copy(update={"gemini_api_key": user_gemini_api_key})
    return settings


def answer_corpus_inventory_question(
    question: str,
    processed_dir,
    filters: dict[str, str],
    identity: RequestIdentity,
    started_at: float,
) -> AskResponse | None:
    if not CORPUS_INVENTORY_RE.search(question):
        return None

    repo = LocalChunkRepository(processed_dir)
    allowed_chunks = filter_chunks_by_acl(repo.read_chunks(), identity)
    filtered_chunks = [chunk for chunk in allowed_chunks if _metadata_matches(chunk, filters)]

    total_docs = sorted({chunk.doc_id for chunk in allowed_chunks})
    filtered_docs = sorted({chunk.doc_id for chunk in filtered_chunks})
    answer = _inventory_answer(total_docs, allowed_chunks, filtered_docs, filtered_chunks, filters)

    return AskResponse(
        answer=answer,
        confidence=1.0,
        sources=[],
        escalation_path=None,
        insufficient_information=False,
        latency_ms=int((time.perf_counter() - started_at) * 1000),
        answer_provider="index_metadata",
        provider_status="Answered from indexed document metadata.",
    )


def _inventory_answer(
    total_docs: list[str],
    allowed_chunks: list[DocumentChunk],
    filtered_docs: list[str],
    filtered_chunks: list[DocumentChunk],
    filters: dict[str, str],
) -> str:
    summary = (
        f"The indexed knowledge base contains {len(total_docs)} documents "
        f"and {len(allowed_chunks)} chunks visible to this user."
    )
    if filters:
        filter_text = ", ".join(f"{key}={value}" for key, value in sorted(filters.items()))
        summary += (
            f" Current filters ({filter_text}) match {len(filtered_docs)} documents "
            f"and {len(filtered_chunks)} chunks."
        )
        docs_to_list = filtered_docs
        chunks_to_count = filtered_chunks
    else:
        docs_to_list = total_docs
        chunks_to_count = allowed_chunks

    if docs_to_list:
        summary += f" Documents: {', '.join(docs_to_list)}."

    products = Counter(chunk.metadata.product for chunk in chunks_to_count)
    if products:
        product_text = ", ".join(
            f"{product}: {count}" for product, count in sorted(products.items())
        )
        summary += f" Product chunks: {product_text}."

    return summary


def _metadata_matches(chunk: DocumentChunk, filters: dict[str, str]) -> bool:
    metadata = chunk.metadata.model_dump()
    return all(_metadata_value_matches(metadata.get(key), value) for key, value in filters.items())


def _metadata_value_matches(actual, expected: str) -> bool:
    if isinstance(actual, list):
        return any(str(item).lower() == expected.lower() for item in actual)
    return str(actual or "").lower() == expected.lower()


def answer_style_instructions(answer_style: AnswerStyle) -> str:
    if answer_style == "brief":
        return (
            "Return 2-4 short bullets. Start with the direct answer. Include source document "
            "IDs inline. Do not add separate confidence or insufficient-information sections."
        )
    if answer_style == "audit":
        return (
            "Return an audit-style answer with sections: Direct answer, Source evidence, "
            "Reasoning, Escalation path, and Information gaps. Keep each section concise."
        )
    return (
        "Return a concise enterprise support answer with sections: Answer, Evidence, Next step. "
        "Use Markdown headings and bullets. Do not add a separate confidence score section; "
        "the API returns confidence separately. Keep the answer under 180 words unless the "
        "question asks for comparison or a table."
    )


def audit_answer(
    data_dir,
    request_id: str,
    identity: RequestIdentity,
    question: str,
    response: AskResponse,
) -> None:
    report = response.guardrails or GuardrailReport()
    action = "redact" if report.redacted else "answer"
    append_audit_record(
        data_dir,
        build_audit_record(
            request_id=request_id,
            route="/ask",
            identity=identity,
            question=question,
            action=action,
            guardrail_categories=report.categories,
            retrieved_doc_ids=list(dict.fromkeys(source.doc_id for source in response.sources)),
            latency_ms=response.latency_ms,
            insufficient_information=response.insufficient_information,
            confidence=response.confidence,
        ),
    )

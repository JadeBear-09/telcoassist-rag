from __future__ import annotations

import csv
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import Settings
from app.evaluation.eval_answers import hallucination_risk_proxy
from app.models import (
    AskResponse,
    PromptLabQuestionSummary,
    PromptLabRequest,
    PromptLabRunResponse,
    PromptLabVariantSummary,
)
from app.rag.generator import AnswerGenerator
from app.rag.prompts import LOCKED_GROUNDING_GUARDRAIL
from app.rag.reranker import Reranker
from app.rag.retriever import HybridRetriever


def run_prompt_lab(request: PromptLabRequest, settings: Settings) -> PromptLabRunResponse:
    golden_path = Path(request.golden_path)
    processed_dir = Path(request.processed_dir) if request.processed_dir else settings.processed_dir
    lab_settings = settings.model_copy(update={"processed_dir": processed_dir})

    rows = _read_golden_questions(golden_path)
    retriever = HybridRetriever(lab_settings)
    reranker = Reranker()
    generator = AnswerGenerator(lab_settings)

    baseline = _run_variant(
        name="baseline",
        rows=rows,
        retriever=retriever,
        reranker=reranker,
        generator=generator,
        top_k=request.top_k,
        style_instructions=None,
    )
    candidate = _run_variant(
        name=request.candidate_name,
        rows=rows,
        retriever=retriever,
        reranker=reranker,
        generator=generator,
        top_k=request.top_k,
        style_instructions=request.candidate_prompt,
    )

    run_id = f"prompt_lab_{uuid4().hex}"
    timestamp = datetime.now(timezone.utc)
    result_dir = processed_dir / "prompt_lab"
    result_dir.mkdir(parents=True, exist_ok=True)
    result_path = result_dir / f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}_{run_id}.json"

    response = PromptLabRunResponse(
        run_id=run_id,
        timestamp=timestamp,
        questions=len(rows),
        locked_guardrail=LOCKED_GROUNDING_GUARDRAIL,
        baseline=baseline,
        candidate=candidate,
        result_path=str(result_path),
    )
    result_path.write_text(
        json.dumps(response.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return response


def _read_golden_questions(golden_path: Path) -> list[dict[str, str]]:
    with golden_path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _run_variant(
    name: str,
    rows: list[dict[str, str]],
    retriever: HybridRetriever,
    reranker: Reranker,
    generator: AnswerGenerator,
    top_k: int,
    style_instructions: str | None,
) -> PromptLabVariantSummary:
    summaries: list[PromptLabQuestionSummary] = []
    for row in rows:
        question = row["question"]
        expected_doc_id = row["expected_doc_id"]
        started_at = time.perf_counter()
        candidates = retriever.retrieve(question, top_k=top_k, candidate_k=top_k * 8)
        reranked = reranker.rerank(question, candidates, top_k=top_k)
        response = generator.generate(
            question,
            reranked,
            started_at,
            style_instructions=style_instructions,
        )
        risk = _risk_proxy(response, expected_doc_id)
        cited_doc_ids = [source.doc_id for source in response.sources]
        summaries.append(
            PromptLabQuestionSummary(
                question=question,
                expected_doc_id=expected_doc_id,
                answer_preview=_preview(response.answer),
                cited_doc_ids=cited_doc_ids,
                expected_doc_cited=expected_doc_id in cited_doc_ids,
                confidence=response.confidence,
                insufficient_information=response.insufficient_information,
                latency_ms=response.latency_ms,
                hallucination_risk_proxy=risk,
            )
        )

    return _summarize_variant(name, summaries)


def _summarize_variant(
    name: str,
    summaries: list[PromptLabQuestionSummary],
) -> PromptLabVariantSummary:
    total = len(summaries)
    if total == 0:
        return PromptLabVariantSummary(
            name=name,
            avg_confidence=0.0,
            citation_coverage=0.0,
            expected_doc_citation_rate=0.0,
            insufficient_information_rate=0.0,
            avg_latency_ms=0.0,
            hallucination_risk_proxy="low",
            hallucination_risk_distribution={},
            answer_summaries=[],
        )

    risk_distribution = Counter(summary.hallucination_risk_proxy for summary in summaries)
    return PromptLabVariantSummary(
        name=name,
        avg_confidence=round(sum(summary.confidence for summary in summaries) / total, 3),
        citation_coverage=round(
            sum(1 for summary in summaries if summary.cited_doc_ids) / total,
            4,
        ),
        expected_doc_citation_rate=round(
            sum(1 for summary in summaries if summary.expected_doc_cited) / total,
            4,
        ),
        insufficient_information_rate=round(
            sum(1 for summary in summaries if summary.insufficient_information) / total,
            4,
        ),
        avg_latency_ms=round(sum(summary.latency_ms for summary in summaries) / total, 2),
        hallucination_risk_proxy=_aggregate_risk(risk_distribution, total),
        hallucination_risk_distribution=dict(risk_distribution),
        answer_summaries=summaries,
    )


def _risk_proxy(response: AskResponse, expected_doc_id: str) -> str:
    if response.insufficient_information:
        return "low"
    if expected_doc_id and all(source.doc_id != expected_doc_id for source in response.sources):
        return "high"
    return hallucination_risk_proxy(response)


def _aggregate_risk(distribution: Counter[str], total: int) -> str:
    score = (distribution["high"] + distribution["medium"] * 0.5) / max(1, total)
    if score >= 0.5:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


def _preview(text: str, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else f"{normalized[: limit - 3]}..."

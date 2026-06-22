from __future__ import annotations

import re
import time

from app.config import Settings
from app.models import AskResponse, RetrievalCandidate, SourceCitation
from app.rag.prompts import ANSWER_TEMPLATE, SYSTEM_PROMPT
from app.rag.retriever import _tokenize


class AnswerGenerator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(
        self,
        question: str,
        candidates: list[RetrievalCandidate],
        started_at: float,
    ) -> AskResponse:
        confidence = confidence_from_candidates(candidates)
        insufficient = not candidates or confidence < self.settings.confidence_threshold

        if insufficient:
            answer = (
                "Insufficient information in retrieved telecom knowledge base. "
                "No grounded troubleshooting or policy answer should be given until stronger source context is retrieved."
            )
        elif self.settings.openai_api_key:
            answer = self._generate_with_openai(question, candidates)
        else:
            answer = extractive_answer(question, candidates)

        sources = build_citations(candidates)
        escalation = None if insufficient else escalation_path(question, candidates)
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        return AskResponse(
            answer=answer,
            confidence=round(confidence, 3),
            sources=sources,
            escalation_path=escalation,
            insufficient_information=insufficient,
            latency_ms=latency_ms,
        )

    def _generate_with_openai(self, question: str, candidates: list[RetrievalCandidate]) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            return extractive_answer(question, candidates)

        context = "\n\n".join(
            f"[{idx}] {candidate.chunk.metadata.title} ({candidate.chunk.chunk_id})\n{candidate.chunk.text}"
            for idx, candidate in enumerate(candidates, start=1)
        )
        client = OpenAI(api_key=self.settings.openai_api_key)
        response = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": ANSWER_TEMPLATE.format(question=question, context=context),
                },
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content or extractive_answer(question, candidates)


def extractive_answer(question: str, candidates: list[RetrievalCandidate]) -> str:
    query_tokens = set(_tokenize(question))
    scored_sentences: list[tuple[float, str]] = []

    for candidate in candidates[:5]:
        sentences = re.split(r"(?<=[.!?])\s+", candidate.chunk.text)
        for sentence in sentences:
            tokens = set(_tokenize(sentence))
            if not tokens:
                continue
            overlap = len(tokens & query_tokens) / max(1, len(query_tokens))
            if overlap > 0:
                scored_sentences.append((overlap + candidate.score * 0.05, sentence.strip()))

    scored_sentences.sort(key=lambda item: item[0], reverse=True)
    selected = []
    seen = set()
    for _, sentence in scored_sentences:
        normalized = sentence.lower()
        if normalized in seen:
            continue
        selected.append(sentence)
        seen.add(normalized)
        if len(selected) == 5:
            break

    if not selected:
        return candidates[0].chunk.text[:700]

    return " ".join(selected)


def confidence_from_candidates(candidates: list[RetrievalCandidate]) -> float:
    if not candidates:
        return 0.0
    top = candidates[0].score
    spread = top - candidates[-1].score if len(candidates) > 1 else top
    citation_density = min(1.0, len(candidates) / 5)
    confidence = 0.55 * min(1.0, top) + 0.25 * min(1.0, spread + 0.1) + 0.20 * citation_density
    return max(0.0, min(0.95, confidence))


def build_citations(candidates: list[RetrievalCandidate]) -> list[SourceCitation]:
    citations: list[SourceCitation] = []
    for candidate in candidates:
        chunk = candidate.chunk
        excerpt = chunk.text[:360].replace("\n", " ").strip()
        citations.append(
            SourceCitation(
                doc_id=chunk.doc_id,
                document_name=chunk.metadata.title,
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                score=round(candidate.score, 3),
                excerpt=excerpt,
                metadata=chunk.metadata.model_dump(mode="json"),
            )
        )
    return citations


def escalation_path(question: str, candidates: list[RetrievalCandidate]) -> str:
    text = " ".join([question] + [candidate.chunk.text for candidate in candidates[:3]]).lower()
    if "billing" in text or "invoice" in text or "dispute" in text:
        return "Billing Operations L2 after policy validation and account-note review."
    if "sim" in text or "esim" in text or "provision" in text:
        return "SIM Provisioning L2 if reprovisioning, APN reset, and device checks fail."
    if "5g" in text or "signal" in text or "tower" in text or "outage" in text:
        return "Network Support L2 if SIM provisioning is healthy and local tower incidents remain possible."
    return "Domain owner listed in source document metadata."

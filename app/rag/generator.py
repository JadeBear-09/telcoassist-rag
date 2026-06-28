from __future__ import annotations

import json
import re
import time
from urllib import request
from urllib.parse import quote

from app.config import Settings
from app.models import AskResponse, RetrievalCandidate, SourceCitation
from app.rag.prompts import ANSWER_TEMPLATE, build_system_prompt, render_answer_template
from app.rag.retriever import _tokenize


class AnswerGenerator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(
        self,
        question: str,
        candidates: list[RetrievalCandidate],
        started_at: float,
        style_instructions: str | None = None,
        response_template: str = ANSWER_TEMPLATE,
    ) -> AskResponse:
        confidence = confidence_from_candidates(candidates)
        insufficient = not candidates or confidence < self.settings.confidence_threshold
        answer_provider = "local"
        provider_status = "Local extractive RAG answered from retrieved chunks."

        if insufficient:
            answer = (
                "Insufficient information in retrieved telecom knowledge base. "
                "No grounded troubleshooting or policy answer should be given until "
                "stronger source context is retrieved."
            )
            provider_status = "No high-confidence source context retrieved."
        elif self.settings.gemini_api_key:
            try:
                answer = self._generate_with_gemini(
                    question,
                    candidates,
                    style_instructions=style_instructions,
                    response_template=response_template,
                )
                answer_provider = "gemini"
                provider_status = "Gemini answered using retrieved chunks."
            except Exception:
                answer = extractive_answer(question, candidates)
                provider_status = "Gemini call failed; local extractive fallback used."
        elif self.settings.openai_api_key:
            try:
                answer = self._generate_with_openai(
                    question,
                    candidates,
                    style_instructions=style_instructions,
                    response_template=response_template,
                )
                answer_provider = "openai"
                provider_status = "OpenAI answered using retrieved chunks."
            except Exception:
                answer = extractive_answer(question, candidates)
                provider_status = "OpenAI call failed; local extractive fallback used."
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
            answer_provider=answer_provider,
            provider_status=provider_status,
        )

    def _generate_with_openai(
        self,
        question: str,
        candidates: list[RetrievalCandidate],
        style_instructions: str | None,
        response_template: str,
    ) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            return extractive_answer(question, candidates)

        context = build_context(candidates, self.settings.max_context_chars)
        client = OpenAI(api_key=self.settings.openai_api_key)
        response = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": build_system_prompt(style_instructions)},
                {
                    "role": "user",
                    "content": render_answer_template(
                        question=question,
                        context=context,
                        response_template=response_template,
                    ),
                },
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content or extractive_answer(question, candidates)

    def _generate_with_gemini(
        self,
        question: str,
        candidates: list[RetrievalCandidate],
        style_instructions: str | None,
        response_template: str,
    ) -> str:
        context = build_context(candidates, self.settings.max_context_chars)
        user_prompt = render_answer_template(
            question=question,
            context=context,
            response_template=response_template,
        )
        payload = build_gemini_payload(
            system_prompt=build_system_prompt(style_instructions),
            user_prompt=user_prompt,
        )
        model_path = gemini_model_path(self.settings.gemini_model)
        req = request.Request(
            f"https://generativelanguage.googleapis.com/v1beta/{model_path}:generateContent",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.settings.gemini_api_key or "",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return extract_gemini_text(data) or extractive_answer(question, candidates)


def gemini_model_path(model: str) -> str:
    model_name = model if model.startswith("models/") else f"models/{model}"
    return quote(model_name, safe="/")


def build_gemini_payload(system_prompt: str, user_prompt: str) -> dict[str, object]:
    return {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "text/plain",
        },
    }


def extract_gemini_text(data: dict[str, object]) -> str:
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    return "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()


def build_context(candidates: list[RetrievalCandidate], max_chars: int) -> str:
    parts: list[str] = []
    remaining = max_chars
    for idx, candidate in enumerate(candidates, start=1):
        if remaining <= 0:
            break
        header = f"[{idx}] {candidate.chunk.metadata.title} ({candidate.chunk.chunk_id})\n"
        text_budget = max(0, remaining - len(header))
        if text_budget <= 0:
            break
        text = candidate.chunk.text[:text_budget]
        parts.append(f"{header}{text}")
        remaining -= len(header) + len(text) + 2
    return "\n\n".join(parts)


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
        return (
            "Network Support L2 if SIM provisioning is healthy and local tower incidents "
            "remain possible."
        )
    return "Domain owner listed in source document metadata."

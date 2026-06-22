from __future__ import annotations

from app.models import RetrievalCandidate
from app.rag.retriever import _tokenize


class Reranker:
    def __init__(self, model_name: str | None = None) -> None:
        self._model = None
        if model_name:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(model_name)
            except Exception:
                self._model = None

    def rerank(
        self,
        question: str,
        candidates: list[RetrievalCandidate],
        top_k: int,
    ) -> list[RetrievalCandidate]:
        if not candidates:
            return []

        if self._model is not None:
            pairs = [(question, candidate.chunk.text) for candidate in candidates]
            scores = self._model.predict(pairs)
            for candidate, score in zip(candidates, scores):
                candidate.rerank_score = float(score)
                candidate.score = 0.45 * candidate.score + 0.55 * float(score)
        else:
            query_tokens = set(_tokenize(question))
            for candidate in candidates:
                chunk_tokens = set(_tokenize(candidate.chunk.text))
                lexical = len(query_tokens & chunk_tokens) / max(1, len(query_tokens))
                metadata_bonus = _metadata_bonus(question, candidate)
                candidate.rerank_score = min(1.0, lexical + metadata_bonus)
                candidate.score = 0.65 * candidate.score + 0.35 * candidate.rerank_score

        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[:top_k]


def _metadata_bonus(question: str, candidate: RetrievalCandidate) -> float:
    lowered = question.lower()
    metadata = candidate.chunk.metadata
    bonus = 0.0
    if metadata.product.lower() in lowered:
        bonus += 0.08
    if metadata.region.lower() in lowered:
        bonus += 0.05
    if metadata.doc_type.lower() in lowered:
        bonus += 0.03
    return bonus

from __future__ import annotations

from app.models import AskResponse


def citation_accuracy_proxy(response: AskResponse, expected_doc_id: str) -> float:
    if not response.sources:
        return 0.0
    matches = sum(1 for source in response.sources if source.doc_id == expected_doc_id)
    return matches / len(response.sources)


def hallucination_risk_proxy(response: AskResponse) -> str:
    if response.insufficient_information:
        return "low"
    if response.confidence < 0.45 or not response.sources:
        return "high"
    if response.confidence < 0.65:
        return "medium"
    return "low"

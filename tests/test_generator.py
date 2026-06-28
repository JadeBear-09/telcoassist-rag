import time

from app.config import Settings
from app.models import DocumentChunk, DocumentMetadata, RetrievalCandidate
from app.rag.generator import AnswerGenerator, extract_gemini_text, gemini_model_path


def test_generator_falls_back_when_no_context() -> None:
    generator = AnswerGenerator(Settings(confidence_threshold=0.5))
    response = generator.generate("Unknown policy?", [], time.perf_counter())

    assert response.insufficient_information is True
    assert response.confidence == 0.0
    assert response.sources == []


def _candidate() -> RetrievalCandidate:
    chunk = DocumentChunk(
        chunk_id="DT_TEST:0",
        doc_id="DT_TEST",
        text="Support should verify provisioning before escalation.",
        chunk_index=0,
        metadata=DocumentMetadata(doc_id="DT_TEST", title="Test Doc"),
    )
    return RetrievalCandidate(chunk=chunk, score=0.9)


def test_generator_prefers_gemini_key_over_openai_key(monkeypatch) -> None:
    generator = AnswerGenerator(
        Settings(
            confidence_threshold=0.0,
            gemini_api_key="gemini-key",
            openai_api_key="openai-key",
        )
    )
    monkeypatch.setattr(
        generator,
        "_generate_with_gemini",
        lambda *args, **kwargs: "gemini answer",
    )
    monkeypatch.setattr(
        generator,
        "_generate_with_openai",
        lambda *args, **kwargs: "openai answer",
    )

    response = generator.generate("What should support do?", [_candidate()], time.perf_counter())

    assert response.answer == "gemini answer"
    assert response.answer_provider == "gemini"
    assert response.provider_status == "Gemini answered using retrieved chunks."


def test_generator_reports_provider_fallback_when_key_call_fails(monkeypatch) -> None:
    generator = AnswerGenerator(
        Settings(
            confidence_threshold=0.0,
            openai_api_key="openai-key",
        )
    )
    monkeypatch.setattr(
        generator,
        "_generate_with_openai",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("bad key")),
    )

    response = generator.generate("What should support do?", [_candidate()], time.perf_counter())

    assert response.answer == "Support should verify provisioning before escalation."
    assert response.answer_provider == "local"
    assert response.provider_status == "OpenAI call failed; local extractive fallback used."


def test_extract_gemini_text_joins_response_parts() -> None:
    assert (
        extract_gemini_text(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "grounded "},
                                {"text": "answer"},
                            ]
                        }
                    }
                ]
            }
        )
        == "grounded answer"
    )


def test_gemini_model_path_accepts_short_or_full_name() -> None:
    assert gemini_model_path("gemini-3.5-flash") == "models/gemini-3.5-flash"
    assert gemini_model_path("models/gemini-3.5-flash") == "models/gemini-3.5-flash"

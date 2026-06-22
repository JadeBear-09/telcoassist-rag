import time

from app.config import Settings
from app.rag.generator import AnswerGenerator


def test_generator_falls_back_when_no_context() -> None:
    generator = AnswerGenerator(Settings(confidence_threshold=0.5))
    response = generator.generate("Unknown policy?", [], time.perf_counter())

    assert response.insufficient_information is True
    assert response.confidence == 0.0
    assert response.sources == []

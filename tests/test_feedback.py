import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.feedback as feedback_api
from app.config import Settings


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(feedback_api, "get_settings", lambda: Settings(data_dir=tmp_path))
    app = FastAPI()
    app.include_router(feedback_api.router)
    return TestClient(app)


def _payload() -> dict[str, object]:
    return {
        "question": "What is policy DT-SIM-048 about?",
        "answer": "It covers SIM activation identity checks.",
        "sources": [
            {
                "doc_id": "DT_SIM_POL_048",
                "document_name": "SIM Activation Policy",
                "chunk_id": "DT_SIM_POL_048:0",
                "chunk_index": 0,
                "score": 0.92,
                "excerpt": "SIM activation identity checks.",
                "metadata": {"product": "SIM"},
            }
        ],
        "rating": "down",
        "reason": "incomplete",
        "comment": "Missing escalation step.",
        "expected_doc_id": "DT_SIM_POL_048",
        "corrected_answer": "Add the escalation step from the SIM policy.",
    }


def test_feedback_accepts_valid_payload_and_persists_jsonl(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    response = client.post("/feedback", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["feedback_id"].startswith("fb_")
    assert body["timestamp"]
    assert body["rating"] == "down"

    feedback_path = tmp_path / "feedback" / "feedback.jsonl"
    rows = [json.loads(line) for line in feedback_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["feedback_id"] == body["feedback_id"]
    assert rows[0]["expected_doc_id"] == "DT_SIM_POL_048"


def test_feedback_rejects_invalid_rating_and_reason(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    invalid_rating = _payload()
    invalid_rating["rating"] = "maybe"
    invalid_reason = _payload()
    invalid_reason["reason"] = "bad_retrieval"

    rating_response = client.post("/feedback", json=invalid_rating)
    reason_response = client.post("/feedback", json=invalid_reason)

    assert rating_response.status_code == 422
    assert reason_response.status_code == 422

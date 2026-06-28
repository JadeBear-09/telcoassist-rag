from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import query
from app.config import Settings
from app.middleware import make_security_middleware


def test_query_page_renders_form() -> None:
    app = FastAPI()
    app.include_router(query.router)
    client = TestClient(app)

    response = client.get("/query")

    assert response.status_code == 200
    assert "TelcoAssist Query" in response.text
    assert "Queries run against five local Deutsche Telekom demo docs" in response.text
    assert "Sample questions" in response.text
    assert "Exact lookup" in response.text
    assert "Multi-doc compare" in response.text
    assert "Filter test" in response.text
    assert "Citation test" in response.text
    assert "Billing dispute" in response.text
    assert 'fetch("/ask"' in response.text
    assert "focusSources" in response.text
    assert "Sources \" + (payload.sources || []).length" in response.text
    assert "Advanced security" in response.text
    assert "Select Preview on a document" in response.text
    assert "/dashboard/documents/\" + encodeURIComponent(docId) + \"/preview" in response.text
    assert 'id="llm-provider"' in response.text
    assert 'id="llm-api-key"' in response.text
    assert 'id="remember-llm-api-key"' in response.text
    assert 'id="clear-llm-api-key"' in response.text
    assert 'modelKeyStorageKey(provider)' in response.text
    assert 'id="answer-style"' in response.text
    assert "renderAnswer(payload.answer || \"\")" in response.text
    assert "answer_style: value(\"answer-style\") || \"standard\"" in response.text
    assert 'headers["X-Gemini-API-Key"]' in response.text
    assert 'headers["X-OpenAI-API-Key"]' in response.text
    assert 'id="question"' in response.text
    assert 'id="remember-app-api-key"' in response.text
    assert 'id="clear-app-api-key"' in response.text


def test_query_page_is_public_when_api_key_auth_enabled() -> None:
    app = FastAPI()
    app.middleware("http")(make_security_middleware(Settings(app_api_key="secret")))
    app.include_router(query.router)
    client = TestClient(app)

    response = client.get("/query")

    assert response.status_code == 200

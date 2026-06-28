from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.middleware import make_security_middleware


def _client(settings: Settings) -> TestClient:
    app = FastAPI()
    app.middleware("http")(make_security_middleware(settings))

    @app.get("/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/private")
    def private() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/ask")
    def ask() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def test_public_paths_skip_api_key_auth() -> None:
    client = _client(Settings(app_api_key="secret"))

    response = client.get("/health")

    assert response.status_code == 200


def test_api_key_auth_blocks_private_paths() -> None:
    client = _client(Settings(app_api_key="secret"))

    missing = client.get("/private")
    valid = client.get("/private", headers={"Authorization": "Bearer secret"})

    assert missing.status_code == 401
    assert valid.status_code == 200


def test_public_ask_bypass_keeps_private_paths_protected() -> None:
    client = _client(Settings(app_api_key="secret", public_ask_enabled=True))

    ask = client.post("/ask")
    private = client.get("/private")

    assert ask.status_code == 200
    assert private.status_code == 401


def test_rate_limit_returns_429() -> None:
    client = _client(Settings(rate_limit_per_minute=1))

    first = client.get("/private")
    second = client.get("/private")

    assert first.status_code == 200
    assert second.status_code == 429


def test_public_paths_skip_rate_limit() -> None:
    client = _client(Settings(rate_limit_per_minute=1))

    first = client.get("/health")
    second = client.get("/health")

    assert first.status_code == 200
    assert second.status_code == 200

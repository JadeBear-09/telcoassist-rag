import zipfile

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import ingest as ingest_api
from app.api import upload
from app.api.ingest import extract_zip_safely
from app.config import Settings


def test_extract_zip_safely_rejects_path_traversal(tmp_path) -> None:
    zip_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("../bad.md", "# bad")

    with pytest.raises(HTTPException) as exc:
        extract_zip_safely(
            zip_path=zip_path,
            destination=tmp_path / "raw",
            max_files=10,
            max_uncompressed_bytes=1024,
        )

    assert exc.value.status_code == 400


def test_extract_zip_safely_extracts_supported_docs(tmp_path) -> None:
    zip_path = tmp_path / "docs.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("docs/a.md", "# A")
        archive.writestr("docs/skip.exe", "nope")

    raw_dir = tmp_path / "raw"
    count = extract_zip_safely(
        zip_path=zip_path,
        destination=raw_dir,
        max_files=10,
        max_uncompressed_bytes=1024,
    )

    assert count == 1
    assert (raw_dir / "docs/a.md").read_text(encoding="utf-8") == "# A"


def test_upload_page_marks_app_key_optional() -> None:
    app = FastAPI()
    app.include_router(upload.router)
    client = TestClient(app)

    response = client.get("/upload")

    assert response.status_code == 200
    assert "No key needed in local demo" in response.text
    assert "App Access Key" in response.text
    assert 'id="remember-app-api-key"' in response.text
    assert 'id="clear-app-api-key"' in response.text
    assert 'storageSet("app-api-key", key)' in response.text
    assert "not a Gemini/OpenAI model key" in response.text
    assert "Upload and re-index" in response.text


def test_upload_page_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setattr(upload, "get_settings", lambda: Settings(ingest_api_enabled=False))
    app = FastAPI()
    app.include_router(upload.router)
    client = TestClient(app)

    response = client.get("/upload")

    assert response.status_code == 200
    assert "Upload disabled" in response.text
    assert "public demo" in response.text


def test_ingest_api_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setattr(ingest_api, "get_settings", lambda: Settings(ingest_api_enabled=False))
    app = FastAPI()
    app.include_router(ingest_api.router)
    client = TestClient(app)

    response = client.post(
        "/ingest",
        json={"raw_dir": "data/raw", "processed_dir": "data/processed"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Document ingestion API is disabled."

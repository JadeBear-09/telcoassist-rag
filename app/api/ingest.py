from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.ingestion.pipeline import run_ingestion
from app.models import IngestRequest, IngestResponse

router = APIRouter(prefix="/ingest", tags=["ingestion"])
SUPPORTED_UPLOAD_SUFFIXES = {".md", ".txt", ".csv", ".pdf"}


@router.post("", response_model=IngestResponse)
def ingest(request: IngestRequest) -> IngestResponse:
    ensure_ingest_api_enabled()
    return run_ingestion(
        raw_dir=request.raw_dir,
        processed_dir=request.processed_dir,
        use_qdrant=request.use_qdrant,
    )


@router.post("/upload", response_model=IngestResponse)
async def upload_zip(
    file: Annotated[UploadFile, File(...)],
    use_qdrant: Annotated[bool, Form()] = False,
) -> IngestResponse:
    settings = get_settings()
    ensure_ingest_api_enabled()
    filename = file.filename or ""
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload a .zip file.")

    max_upload_bytes = settings.max_upload_mb * 1024 * 1024
    with tempfile.TemporaryDirectory(prefix="telcoassist-upload-") as tmp:
        tmp_dir = Path(tmp)
        zip_path = tmp_dir / "upload.zip"
        uploaded_bytes = 0
        with zip_path.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                uploaded_bytes += len(chunk)
                if uploaded_bytes > max_upload_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Upload exceeds {settings.max_upload_mb} MB limit.",
                    )
                output.write(chunk)

        raw_dir = tmp_dir / "raw"
        extracted = extract_zip_safely(
            zip_path=zip_path,
            destination=raw_dir,
            max_files=settings.max_upload_files,
            max_uncompressed_bytes=max_upload_bytes,
        )
        if extracted == 0:
            raise HTTPException(
                status_code=400,
                detail="Zip contained no supported .md, .txt, .csv, or .pdf documents.",
            )

        return run_ingestion(
            raw_dir=str(raw_dir),
            processed_dir=str(settings.processed_dir),
            use_qdrant=use_qdrant or settings.use_qdrant,
        )


def ensure_ingest_api_enabled() -> None:
    if not get_settings().ingest_api_enabled:
        raise HTTPException(status_code=403, detail="Document ingestion API is disabled.")


def extract_zip_safely(
    zip_path: Path,
    destination: Path,
    max_files: int,
    max_uncompressed_bytes: int,
) -> int:
    destination.mkdir(parents=True, exist_ok=True)
    destination_root = destination.resolve()
    extracted = 0
    total_uncompressed = 0

    try:
        archive = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid zip file.") from exc

    with archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            suffix = Path(member.filename).suffix.lower()
            if suffix not in SUPPORTED_UPLOAD_SUFFIXES:
                continue
            extracted += 1
            if extracted > max_files:
                raise HTTPException(status_code=413, detail=f"Zip exceeds {max_files} file limit.")

            total_uncompressed += member.file_size
            if total_uncompressed > max_uncompressed_bytes:
                raise HTTPException(
                    status_code=413,
                    detail="Zip uncompressed size exceeds upload limit.",
                )

            target = (destination / member.filename).resolve()
            try:
                target.relative_to(destination_root)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Unsafe zip path detected.") from exc

            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)

    return extracted

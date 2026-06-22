from __future__ import annotations

from fastapi import APIRouter

from app.ingestion.pipeline import run_ingestion
from app.models import IngestRequest, IngestResponse

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("", response_model=IngestResponse)
def ingest(request: IngestRequest) -> IngestResponse:
    return run_ingestion(
        raw_dir=request.raw_dir,
        processed_dir=request.processed_dir,
        use_qdrant=request.use_qdrant,
    )

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter

from app.config import get_settings
from app.models import FeedbackRecord, FeedbackRequest

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackRecord)
def submit_feedback(request: FeedbackRequest) -> FeedbackRecord:
    settings = get_settings()
    record = FeedbackRecord(
        feedback_id=f"fb_{uuid4().hex}",
        timestamp=datetime.now(timezone.utc),
        **request.model_dump(),
    )
    append_feedback(record, settings.data_dir / "feedback" / "feedback.jsonl")
    return record


def append_feedback(record: FeedbackRecord, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")

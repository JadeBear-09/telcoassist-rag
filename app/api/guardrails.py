from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.models import GuardrailMetrics
from app.security.audit import aggregate_guardrail_metrics

router = APIRouter(prefix="/guardrails", tags=["guardrails"])


@router.get("/metrics", response_model=GuardrailMetrics)
def metrics() -> GuardrailMetrics:
    settings = get_settings()
    return aggregate_guardrail_metrics(settings.data_dir)

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models import PromptLabRequest, PromptLabRunResponse
from app.rag.prompt_lab import run_prompt_lab

router = APIRouter(prefix="/prompt-lab", tags=["prompt-lab"])


@router.post("/run", response_model=PromptLabRunResponse)
def run(request: PromptLabRequest) -> PromptLabRunResponse:
    try:
        return run_prompt_lab(request, get_settings())
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Golden file not found: {request.golden_path}",
        ) from exc

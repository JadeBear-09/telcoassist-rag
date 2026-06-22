from __future__ import annotations

import time

from fastapi import APIRouter

from app.config import get_settings
from app.models import AskRequest, AskResponse
from app.rag.generator import AnswerGenerator
from app.rag.reranker import Reranker
from app.rag.retriever import HybridRetriever

router = APIRouter(tags=["rag"])


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    started_at = time.perf_counter()
    settings = get_settings()
    retriever = HybridRetriever(settings)
    reranker = Reranker()
    generator = AnswerGenerator(settings)

    candidates = retriever.retrieve(
        request.question,
        top_k=request.top_k,
        filters=request.filters,
        candidate_k=settings.candidate_k,
    )
    reranked = reranker.rerank(request.question, candidates, top_k=request.top_k)
    return generator.generate(request.question, reranked, started_at)

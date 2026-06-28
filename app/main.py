from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.api import ask, dashboard, feedback, guardrails, ingest, prompt_lab, query, upload
from app.config import get_settings
from app.ingestion.indexer import LocalChunkRepository
from app.ingestion.pipeline import run_ingestion
from app.middleware import configure_logging, make_security_middleware

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_ingest_on_startup:
        repo = LocalChunkRepository(settings.processed_dir)
        if not repo.read_chunks():
            run_ingestion(
                raw_dir=str(settings.raw_docs_dir),
                processed_dir=str(settings.processed_dir),
                use_qdrant=settings.use_qdrant,
            )
    yield

app = FastAPI(
    title="TelcoAssist",
    description="Enterprise RAG for telecom support, policy, and network intelligence.",
    version="0.1.0",
    lifespan=lifespan,
)
app.middleware("http")(make_security_middleware(settings))

app.include_router(ask.router)
app.include_router(ingest.router)
app.include_router(dashboard.router)
app.include_router(query.router)
app.include_router(upload.router)
app.include_router(feedback.router)
app.include_router(prompt_lab.router)
app.include_router(guardrails.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "env": settings.app_env}


@app.get("/ready")
def ready() -> dict[str, object]:
    repo = LocalChunkRepository(settings.processed_dir)
    chunks = repo.read_chunks()
    embeddings = repo.read_embeddings()
    if not chunks or not embeddings:
        raise HTTPException(
            status_code=503,
            detail="Knowledge index not ready. Run ingestion before serving traffic.",
        )

    qdrant_points = None
    if settings.use_qdrant:
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(url=settings.qdrant_url)
            qdrant_points = client.count(
                collection_name=settings.qdrant_collection,
                exact=True,
            ).count
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Qdrant not ready: {exc}") from exc

    return {
        "status": "ready",
        "documents": len({chunk.doc_id for chunk in chunks}),
        "chunks": len(chunks),
        "embeddings": len(embeddings),
        "qdrant_enabled": settings.use_qdrant,
        "qdrant_points": qdrant_points,
    }

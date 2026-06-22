from fastapi import FastAPI

from app.api import ask, dashboard, ingest
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="TelcoAssist",
    description="Enterprise RAG for telecom support, policy, and network intelligence.",
    version="0.1.0",
)

app.include_router(ask.router)
app.include_router(ingest.router)
app.include_router(dashboard.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "env": settings.app_env}

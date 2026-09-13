import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.providers.factory import get_provider
from app.api.schemas import HealthResponse
from app.config.settings import get_settings
from app.db.models import TranscriptChunk
from app.db.session import get_db

router = APIRouter(tags=["health"])
logger = logging.getLogger("api.health")


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)):
    settings = get_settings()

    db_healthy = True
    chunk_count = 0
    try:
        result = await db.execute(select(func.count()).select_from(TranscriptChunk))
        chunk_count = result.scalar_one()
    except Exception:
        logger.exception("Database health check failed")
        db_healthy = False

    try:
        provider = get_provider()
        provider_healthy = await provider.health_check()
    except Exception:
        logger.exception("LLM provider health check failed")
        provider_healthy = False

    status = "ok" if (db_healthy and provider_healthy) else "degraded"

    return HealthResponse(
        status=status,
        llm_provider=settings.llm_provider,
        llm_provider_healthy=provider_healthy,
        database_healthy=db_healthy,
        knowledge_base_chunks=chunk_count,
    )

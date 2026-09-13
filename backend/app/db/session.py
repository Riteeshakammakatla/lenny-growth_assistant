from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import get_settings
from app.db.models import Base

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Create tables if they don't exist. For this take-home's scope we use
    `create_all` at startup rather than a full Alembic migration chain — the
    schema is small and stable enough that this is sufficient and one less
    moving part for the evaluator's first run. A real production deployment
    would swap this for Alembic-managed migrations; the SQLAlchemy models in
    db/models.py are already structured to generate a first Alembic revision
    directly (`alembic revision --autogenerate`) if that's added later."""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

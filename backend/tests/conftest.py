import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.agent.providers.base import LLMMessage, LLMProvider, LLMResponse
from app.db.models import Base
from app.db.session import get_db
from app.main import app


class FakeProvider(LLMProvider):
    """Deterministic stand-in for a real LLM so tests don't need network
    access to Anthropic or a running Ollama instance."""

    name = "fake"

    async def complete(self, messages: list[LLMMessage], max_tokens: int, temperature: float) -> LLMResponse:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        return LLMResponse(
            text=f"Fake grounded answer about: {last_user}",
            provider=self.name,
            model="fake-model",
            latency_ms=1,
        )

    async def health_check(self) -> bool:
        return True


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_engine, monkeypatch):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Route all provider construction to our fake so tests are hermetic.
    monkeypatch.setattr("app.agent.orchestrator.get_provider", lambda override=None: FakeProvider())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

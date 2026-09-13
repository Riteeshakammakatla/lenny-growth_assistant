"""
Agent orchestration layer.

Responsibilities:
- Load session + recent history for context.
- Route the request's `intent` to the right skill (grounded chat, Ship 30/30
  essay, or artifact generation) — this is the "agent routing" referenced in
  the assignment's architecture.md requirement.
- Call the active LLM provider with graceful degradation.
- Persist the resulting message, citations, and any artifact.
"""
import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.providers.base import LLMMessage, LLMProviderError
from app.agent.providers.factory import get_provider
from app.agent.retrieval import retrieve
from app.config.settings import get_settings
from app.db.models import ChatMessage, ChatSession
from app.skills.artifact_sanitizer import sanitize_html
from app.skills.grounded_chat import build_grounded_prompt, build_messages
from app.skills.ship30_essay import build_essay_prompt

logger = logging.getLogger("orchestrator")


class SessionNotFoundError(Exception):
    pass


async def _load_history(db: AsyncSession, session_id: str, limit: int = 12) -> list[LLMMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    rows = list(reversed(result.scalars().all()))
    return [LLMMessage(role=r.role, content=r.content) for r in rows if r.role in ("user", "assistant")]


async def handle_chat_turn(
    db: AsyncSession,
    session_id: str,
    user_message: str,
    intent: str = "chat",
    artifact_format: str | None = None,
) -> dict:
    settings = get_settings()

    session = await db.get(ChatSession, session_id)
    if session is None:
        raise SessionNotFoundError(session_id)

    history = await _load_history(db, session_id)

    # 1. Retrieval — grounds both plain chat and essay generation.
    retrieved = await retrieve(db, user_message)

    # 2. Route by intent.
    citations: list[dict] = []
    artifact: dict | None = None

    if intent == "essay":
        # Ground the essay in retrieved transcript context plus the recent
        # conversation, which typically already contains a grounded answer
        # the user wants converted into long-form content.
        convo_context = "\n".join(f"{m.role}: {m.content}" for m in history[-4:])
        combined_topic = f"{convo_context}\n\nuser: {user_message}".strip()
        messages = build_essay_prompt(combined_topic, retrieved)
        citations = [
            {"episode_id": r.episode_id, "episode_title": r.episode_title,
             "source_path": r.source_path, "score": round(r.score, 3)}
            for r in retrieved
        ]
    else:
        grounded = build_grounded_prompt(retrieved)
        messages = build_messages(grounded.system_prompt, history, user_message)
        citations = grounded.citations

    # 3. Call the LLM provider with graceful degradation.
    provider_name = session.llm_provider or settings.llm_provider
    provider = get_provider(override=provider_name)

    start = time.monotonic()
    try:
        response = await provider.complete(
            messages=messages,
            max_tokens=settings.llm_max_tokens if intent != "essay" else 2200,
            temperature=settings.llm_temperature,
        )
        text = response.text
        latency_ms = response.latency_ms
        actual_provider = response.provider
    except LLMProviderError as exc:
        logger.warning("LLM provider '%s' failed: %s", provider_name, exc)
        text = (
            "I couldn't reach the language model to answer this right now. "
            f"Details: {exc}\n\nYou can check the /health endpoint for provider status, "
            "or switch LLM_PROVIDER in your .env."
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        actual_provider = provider_name

    # 4. Build artifact if requested.
    if intent == "artifact":
        fmt = artifact_format or "markdown"
        if fmt == "html":
            sanitized = sanitize_html(text, settings.artifact_max_html_bytes)
            artifact = {"type": "html", "content": sanitized}
        else:
            artifact = {"type": "markdown", "content": text}
    elif intent == "essay":
        artifact = {"type": "markdown", "content": text}

    # 5. Persist.
    user_msg = ChatMessage(session_id=session_id, role="user", content=user_message)
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=text,
        citations=citations or None,
        artifact=artifact,
        llm_provider=actual_provider,
        latency_ms=latency_ms,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return {
        "message_id": assistant_msg.id,
        "session_id": session_id,
        "content": text,
        "citations": citations,
        "artifact": artifact,
        "llm_provider": actual_provider,
        "latency_ms": latency_ms,
        "grounded": bool(citations),
    }

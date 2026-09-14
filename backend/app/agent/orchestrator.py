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
import re
import time

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.providers.base import LLMMessage, LLMProviderError
from app.agent.providers.factory import get_provider
from app.agent.retrieval import retrieve
from app.config.settings import get_settings
from app.db.models import ChatMessage, ChatSession, TranscriptChunk
from app.skills.artifact_sanitizer import sanitize_html
from app.skills.grounded_chat import build_grounded_prompt, build_messages
from app.skills.ship30_essay import build_essay_prompt

logger = logging.getLogger("orchestrator")

# Canonical fallback used whenever no relevant transcript chunks are found.
# Defined as a module-level constant so it is consistent across all intents
# and easy to change without hunting through function bodies.
_NO_CONTEXT_RESPONSE = "That's not covered in the transcripts I have."

# Signals that the LLM acknowledged no relevant context exists.
_NOT_COVERED_MARKERS = (
    "not covered in the transcripts",
    "not in the transcripts",
    "no relevant transcript",
    "no relevant information",
    "i don't have",
    "i do not have",
)
# Signals that the LLM then leaked outside knowledge after the acknowledgement.
_LEAK_MARKERS = (
    "but i can", "however, i can", "however, here", "here are some",
    "here are a few", "general insights", "general information",
    "general advice", "best practices", "industry knowledge",
    "from my knowledge", "based on general", "typically,", "in general,",
)


def _clamp_grounding(text: str) -> str:
    """If the LLM started with a 'not covered' acknowledgement but then appended
    outside / general knowledge (grounding violation), replace the entire response
    with the canonical fallback string.

    This is a deterministic post-processing safety net for small models that
    sometimes ignore the system-prompt STOP instruction.
    """
    lowered = text.lower()
    starts_with_not_covered = any(m in lowered[:120] for m in _NOT_COVERED_MARKERS)
    if not starts_with_not_covered:
        return text  # normal response — nothing to clamp

    has_leak = any(m in lowered for m in _LEAK_MARKERS)
    if has_leak:
        return _NO_CONTEXT_RESPONSE  # clamp: strip the leaked content
    return text  # clean "not covered" response — keep as-is


# ---------------------------------------------------------------------------
# Contextual Retrieval Query Construction for Follow-up Questions
# ---------------------------------------------------------------------------
_FOLLOWUP_RE = re.compile(
    r"\b("
    r"that|those|this|these|it|its|he|him|his|she|her|they|them|their|"
    r"the former|the latter|first|second|third|previous|above|"
    r"tell me more|give me|summarize|summary|actionable|lessons|takeaways|"
    r"apply|elaborate|expand|more details|what about|what else|how so|why so|"
    r"why did|how did|what do you mean"
    r")\b",
    re.IGNORECASE,
)


def _is_followup_query(message: str) -> bool:
    """Return True if the user message is a follow-up query relying on recent conversation context."""
    if _FOLLOWUP_RE.search(message):
        return True
    # Short queries (<= 4 words) often rely implicitly on previous context
    words = message.strip().split()
    if len(words) <= 4:
        return True
    return False


def _build_retrieval_query(user_message: str, history: list[LLMMessage]) -> str:
    """Construct a contextual retrieval query for follow-up questions using recent history."""
    if not history or not _is_followup_query(user_message):
        return user_message

    # Extract relevant recent turns from history (last 1-2 turns)
    recent_msgs = history[-3:]
    context_snippets: list[str] = []

    for msg in recent_msgs:
        if msg.role == "user":
            context_snippets.append(msg.content)
        elif msg.role == "assistant" and msg.content and msg.content != _NO_CONTEXT_RESPONSE:
            # Include a brief snippet from the assistant's previous response for entity context
            context_snippets.append(msg.content[:200])

    if not context_snippets:
        return user_message

    contextual_query = " ".join(context_snippets + [user_message]).strip()
    logger.info(
        "Follow-up query detected (%r). Using contextual retrieval query: %r",
        user_message[:60],
        contextual_query[:120],
    )
    return contextual_query


# ---------------------------------------------------------------------------
# Knowledge-base metadata routing
#
# Detects questions about the knowledge base itself (listing/counting episodes)
# and answers them via a direct DB query instead of semantic retrieval + LLM.
# This prevents the LLM from confusing the top-k retrieval window with the full
# knowledge base (e.g., reporting only 5 episodes when 303 are stored).
# ---------------------------------------------------------------------------
_KB_META_RE = re.compile(
    r"(how many|what|which|tell me|list|show|give me).{0,40}"
    r"(transcript|episode|podcast|topic|available|have|know about|knowledge base|you have)",
    re.IGNORECASE,
)


def _is_kb_metadata_query(message: str) -> bool:
    """Return True when the message is asking about the knowledge base itself
    (count, list, or catalogue of transcripts/episodes) rather than a content
    question that should go through normal RAG retrieval."""
    lowered = message.lower().strip()
    # Quick keyword filter: must contain at least one listing/meta indicator.
    meta_keywords = (
        "how many transcripts", "how many episodes", "how many podcast",
        "what transcripts", "what episodes", "which transcripts", "which episodes",
        "list all", "list the", "show all", "show me all", "tell me all",
        "all transcripts", "all episodes", "all the episodes", "all the transcripts",
        "available transcripts", "available episodes",
        "what do you have", "what topics do you", "what have you",
        "your knowledge base", "your transcripts", "your episodes",
        "what's in your", "what is in your",
    )
    return any(kw in lowered for kw in meta_keywords)


async def _handle_kb_metadata_query(
    db: AsyncSession, session_id: str, user_message: str
) -> dict:
    """Query the DB directly for distinct episodes and return a pre-formatted
    response without calling the LLM."""
    result = await db.execute(
        select(
            TranscriptChunk.episode_id,
            TranscriptChunk.episode_title,
        )
        .distinct(TranscriptChunk.episode_id)
        .order_by(TranscriptChunk.episode_title)
    )
    episodes = result.all()  # list of (episode_id, episode_title) tuples
    count = len(episodes)

    lowered = user_message.lower()
    wants_list = any(kw in lowered for kw in (
        "list", "show", "tell me all", "all transcripts", "all episodes",
        "what transcripts", "what episodes", "which transcripts", "which episodes",
    ))

    if wants_list:
        titles = "\n".join(f"{i+1}. {ep_title}" for i, (_, ep_title) in enumerate(episodes))
        content = (
            f"I have **{count} podcast episode transcripts** from Lenny's Podcast in my knowledge base.\n\n"
            f"Here is the complete list:\n\n{titles}"
        )
    else:
        # Count-only or general metadata question
        content = (
            f"I have **{count} podcast episode transcripts** from Lenny's Podcast in my knowledge base. "
            f"You can ask me about any specific topic — product strategy, growth, onboarding, pricing, "
            f"team building, and much more — and I'll find the most relevant excerpts for you."
        )

    user_msg = ChatMessage(session_id=session_id, role="user", content=user_message)
    assistant_msg = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=content,
        citations=None,
        artifact=None,
        llm_provider="none",
        latency_ms=0,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)
    return {
        "message_id": assistant_msg.id,
        "session_id": session_id,
        "content": content,
        "citations": [],
        "artifact": None,
        "llm_provider": "none",
        "latency_ms": 0,
        "grounded": True,
    }


class SessionNotFoundError(Exception):
    pass


async def _load_history(db: AsyncSession, session_id: str, limit: int = 6) -> list[LLMMessage]:
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

    # 0. Knowledge-base metadata gate.
    #    Questions about the KB itself (listing / counting episodes) must be
    #    answered from the real DB count — NOT from the top-k retrieval window,
    #    which would make the LLM think only a handful of episodes exist.
    if _is_kb_metadata_query(user_message):
        logger.info("KB metadata query detected: %r — answering from DB directly.", user_message[:80])
        return await _handle_kb_metadata_query(db, session_id, user_message)

    # 1. Retrieval — grounds both plain chat and essay generation.
    retrieval_query = _build_retrieval_query(user_message, history)
    retrieved = await retrieve(db, retrieval_query)

    # ------------------------------------------------------------------ #
    # Grounding gate (programmatic, not prompt-based)                      #
    #                                                                      #
    # retrieve() already applies retrieval_min_score, so an empty list    #
    # means EITHER no chunks exist at all OR every candidate scored below  #
    # the relevance threshold. In both cases we must NOT call the LLM —   #
    # doing so allows the model to answer from parametric (outside)        #
    # knowledge, which violates the assignment's grounding requirement.    #
    #                                                                      #
    # We persist the fallback as a proper message pair so the session      #
    # history stays consistent, and return immediately.                    #
    # ------------------------------------------------------------------ #
    if not retrieved:
        logger.info(
            "No relevant transcript chunks for query %r (intent=%s). "
            "Returning grounding fallback without calling LLM.",
            user_message[:80],
            intent,
        )
        user_msg = ChatMessage(session_id=session_id, role="user", content=user_message)
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=_NO_CONTEXT_RESPONSE,
            citations=None,
            artifact=None,
            llm_provider="none",
            latency_ms=0,
        )
        db.add(user_msg)
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)
        return {
            "message_id": assistant_msg.id,
            "session_id": session_id,
            "content": _NO_CONTEXT_RESPONSE,
            "citations": [],
            "artifact": None,
            "llm_provider": "none",
            "latency_ms": 0,
            "grounded": False,
        }

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
        # ------------------------------------------------------------ #
        # Grounding clamp: small models sometimes start with the        #
        # correct "not covered" sentence but then append outside        #
        # knowledge ("but I can provide general insights...").          #
        # If that pattern is detected, strip everything after the       #
        # canonical fallback sentence.                                  #
        # ------------------------------------------------------------ #
        text = _clamp_grounding(text)
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

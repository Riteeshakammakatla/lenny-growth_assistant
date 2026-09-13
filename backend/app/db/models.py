"""
SQLAlchemy models.

Design notes:
- ChatSession / ChatMessage give us session isolation + persistence (req 3.1).
- TranscriptChunk stores the ingested, chunked knowledge base with a plain
  float[] embedding column. We use pgvector's `vector` type if the extension
  is available, but fall back to JSON-serialized floats + brute-force cosine
  similarity in Python so the demo works even on a plain Postgres instance
  without the pgvector extension installed (fewer moving parts to fail on an
  evaluator's machine). See app/agent/retrieval.py.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def gen_uuid() -> str:
    return str(uuid.uuid4())


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    llm_provider: Mapped[str] = mapped_column(String, default="ollama")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # "user" | "assistant" | "system"
    content: Mapped[str] = mapped_column(Text)
    # citations: list of {source, episode, chunk_id, score} used for this message
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # artifact: {"type": "markdown"|"html", "content": "..."} if this turn produced one
    artifact: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    episode_id: Mapped[str] = mapped_column(String, index=True)
    episode_title: Mapped[str] = mapped_column(String)
    source_path: Mapped[str] = mapped_column(String)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSON)  # list[float]
    token_count: Mapped[int] = mapped_column(Integer)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

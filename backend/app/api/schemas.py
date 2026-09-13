from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class NewSessionRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=200)
    llm_provider: Literal["anthropic", "ollama"] | None = None


class NewSessionResponse(BaseModel):
    session_id: str
    llm_provider: str
    created_at: datetime


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=8000)
    # "chat" = normal grounded Q&A; "essay" = Ship 30/30 conversion;
    # "artifact" = generate a markdown/html artifact from the conversation.
    intent: Literal["chat", "essay", "artifact"] = "chat"
    artifact_format: Literal["markdown", "html"] | None = None


class Citation(BaseModel):
    episode_id: str
    episode_title: str
    source_path: str
    score: float


class Artifact(BaseModel):
    type: Literal["markdown", "html"]
    content: str


class ChatResponse(BaseModel):
    message_id: str
    session_id: str
    role: str = "assistant"
    content: str
    citations: list[Citation] = []
    artifact: Artifact | None = None
    llm_provider: str
    latency_ms: int
    grounded: bool


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: list[dict] | None = None
    artifact: dict | None = None
    created_at: datetime


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageOut]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    llm_provider: str
    llm_provider_healthy: bool
    database_healthy: bool
    knowledge_base_chunks: int

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import SessionNotFoundError, handle_chat_turn
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    MessageOut,
    NewSessionRequest,
    NewSessionResponse,
    SessionHistoryResponse,
)
from app.config.settings import get_settings
from app.db.models import ChatMessage, ChatSession
from app.db.session import get_db

router = APIRouter(prefix="/api", tags=["chat"])
logger = logging.getLogger("api.chat")


@router.post("/sessions", response_model=NewSessionResponse, status_code=201)
async def create_session(payload: NewSessionRequest, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    session = ChatSession(
        user_id=payload.user_id,
        llm_provider=payload.llm_provider or settings.llm_provider,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return NewSessionResponse(
        session_id=session.id, llm_provider=session.llm_provider, created_at=session.created_at
    )


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    return SessionHistoryResponse(
        session_id=session_id,
        messages=[
            MessageOut(
                id=m.id, role=m.role, content=m.content, citations=m.citations,
                artifact=m.artifact, created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await handle_chat_turn(
            db=db,
            session_id=payload.session_id,
            user_message=payload.message,
            intent=payload.intent,
            artifact_format=payload.artifact_format,
        )
    except SessionNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{payload.session_id}' not found. Create one via POST /api/sessions first.",
        )
    except Exception:
        logger.exception("Unhandled error in /api/chat")
        raise HTTPException(
            status_code=500,
            detail="Something went wrong processing your message. Check server logs for details.",
        )

    return ChatResponse(**result)

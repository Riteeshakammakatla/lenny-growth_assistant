"""
Brute-force retrieval over TranscriptChunk rows.

Brute force (load all chunks, cosine-similarity in Python) is deliberately
chosen over a vector index for this assessment: with a few hundred to low
thousands of chunks it's fast enough (<100ms), and it avoids requiring the
pgvector extension to be installed on whatever Postgres the evaluator spins
up (Supabase/Railway/local Docker all vary here). This is documented as a
scaling trade-off in architecture.md — the swap-in path is a pgvector
`ORDER BY embedding <=> :query LIMIT k` query behind the same function
signature.
"""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.embeddings import cosine_similarity, embed_text
from app.config.settings import get_settings
from app.db.models import TranscriptChunk


@dataclass
class RetrievedChunk:
    chunk_id: str
    episode_id: str
    episode_title: str
    source_path: str
    text: str
    score: float


async def retrieve(db: AsyncSession, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    k = top_k or settings.retrieval_top_k

    query_vec = await embed_text(query)

    result = await db.execute(select(TranscriptChunk))
    chunks = result.scalars().all()

    scored = [
        RetrievedChunk(
            chunk_id=c.id,
            episode_id=c.episode_id,
            episode_title=c.episode_title,
            source_path=c.source_path,
            text=c.text,
            score=cosine_similarity(query_vec, c.embedding),
        )
        for c in chunks
    ]
    scored.sort(key=lambda r: r.score, reverse=True)
    top = scored[:k]
    return [r for r in top if r.score >= settings.retrieval_min_score]

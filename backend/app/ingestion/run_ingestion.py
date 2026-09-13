"""
CLI entry point: `python -m app.ingestion.run_ingestion`

Loads transcripts from TRANSCRIPTS_DIR, chunks them, embeds each chunk, and
upserts into the transcript_chunks table. Re-running is safe: existing
chunks for an episode are deleted and replaced (simplest correct behavior
for a refreshable knowledge base — see architecture.md for incremental
refresh discussion).
"""
import asyncio
import logging

from sqlalchemy import delete, select

from app.agent.embeddings import embed_text
from app.config.settings import get_settings
from app.db.models import TranscriptChunk
from app.db.session import SessionLocal, init_db
from app.ingestion.chunker import chunk_text
from app.ingestion.loader import load_transcripts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingestion")


async def ingest() -> None:
    settings = get_settings()
    await init_db()

    transcripts = load_transcripts(settings.transcripts_dir)
    logger.info("Loaded %d transcript files from %s", len(transcripts), settings.transcripts_dir)

    if not transcripts:
        logger.warning("No transcripts found. Nothing to ingest.")
        return

    async with SessionLocal() as db:
        total_chunks = 0
        for t in transcripts:
            # Replace any existing chunks for this episode (idempotent re-ingestion).
            await db.execute(delete(TranscriptChunk).where(TranscriptChunk.episode_id == t.episode_id))

            chunks = chunk_text(
                t.text,
                chunk_size_tokens=settings.chunk_size_tokens,
                overlap_tokens=settings.chunk_overlap_tokens,
            )
            for c in chunks:
                embedding = await embed_text(c.text)
                db.add(
                    TranscriptChunk(
                        episode_id=t.episode_id,
                        episode_title=t.episode_title,
                        source_path=t.source_path,
                        chunk_index=c.index,
                        text=c.text,
                        embedding=embedding,
                        token_count=c.token_count,
                    )
                )
            total_chunks += len(chunks)
            logger.info("  %s -> %d chunks", t.episode_title, len(chunks))

        await db.commit()

    logger.info("Ingestion complete: %d episodes, %d chunks", len(transcripts), total_chunks)


if __name__ == "__main__":
    asyncio.run(ingest())

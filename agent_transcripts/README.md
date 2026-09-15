# Agent Transcripts

This folder holds the raw session logs from the coding agent(s) used to build this project,
including failed attempts and the fixes that followed — per the assignment's requirement to show
process, not just the polished result.

## Convention

- One file per work session: `YYYY-MM-DD_topic.md` (e.g. `2026-09-13_rag-ingestion-scaffold.md`).
- Each file is the transcript as exported from the tool used, scrubbed of secrets (API keys, tokens, connection strings).
- A short index table is maintained below.

## Index

| File | Covers |
|---|---|
| [`2026-09-13_rag-ingestion-scaffold.md`](./2026-09-13_rag-ingestion-scaffold.md) | FastAPI scaffold, transcript loading, chunking, PostgreSQL vector persistence, and Ollama integration |
| [`2026-09-14_grounding-and-kb-routing.md`](./2026-09-14_grounding-and-kb-routing.md) | Grounding clamp, strict fallback enforcement, prompt hardening, and KB metadata router (303 episodes) |
| [`2026-09-14_conversational-followup-retrieval.md`](./2026-09-14_conversational-followup-retrieval.md) | Multi-turn follow-up detection, pronoun resolution, and contextual retrieval query construction |

## Secret-scrubbing checklist before adding a transcript

- [x] No `ANTHROPIC_API_KEY`, database passwords, or connection strings with credentials
- [x] No personal access tokens (GitHub, etc.)
- [x] No real user data if any was used during manual testing

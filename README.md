# The Lenny Growth Assistant

A conversational assistant grounded in [Lenny's Podcast](https://www.lennyspodcast.com/) transcripts.
Ask product/growth questions, get cited answers, and turn them into a Ship-30/30-style essay or a
shareable one-page doc — all rendered in an in-app Artifact Viewer.

Read `PRD.md` for the discovery brief, `docs/architecture.md` for system design, and `docs/design.md`
for UI/UX rationale.

## Quickstart (Docker, recommended)

**Prerequisites:**
- Docker + Docker Compose
- [Ollama](https://ollama.com/) installed and running **on your host machine** (not in Docker) —
  this is the default, mandatory-for-demo local model path
- ~5GB free disk space for the model

```bash
# 1. Pull the local model (one-time)
ollama pull llama3.1:8b
ollama serve   # if not already running as a background service

# 2. Fetch a working set of transcripts (subset of the full archive, for a fast demo)
./scripts/fetch_transcripts.sh 40

# 3. Configure environment
cp .env.example .env
# defaults already point LLM_PROVIDER=ollama — no further edits needed to run locally

# 4. Start everything
docker compose up --build

# 5. In a separate terminal, ingest the transcripts into the knowledge base
docker compose exec backend python -m app.ingestion.run_ingestion
```

Then open:
- Frontend: http://localhost:5173
- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Switching to the cloud model (Anthropic)

Edit `.env`:
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```
Then restart: `docker compose up -d --build backend`. No code changes required — see
`app/agent/providers/factory.py`.

## Running without Docker (local dev)

**Backend:**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Point DATABASE_URL at a local Postgres, or run one via:
#   docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=lenny_assistant postgres:16-alpine
cp ../.env.example .env   # edit DATABASE_URL to localhost
uvicorn app.main:app --reload
```

**Ingestion:**
```bash
cd backend
python -m app.ingestion.run_ingestion
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

Tests cover: chunking correctness, HTML artifact sanitization (XSS vectors), Ship 30/30 essay prompt
structure, grounded-chat prompt/citation building, LLM provider routing (including the missing-API-key
error path), retrieval embedding math, and a full API integration suite (session isolation, chat
persistence, artifact generation) run against an in-memory SQLite DB with a fake LLM provider — no
network or real Ollama instance required to run `pytest`.

See `docs/manual_test_plan.md` for the UI test checklist that isn't practical to automate.

## Environment variables

See `.env.example` — every variable is documented inline. The most important one is `LLM_PROVIDER`
(`ollama` or `anthropic`), which is the single switch controlling which model answers requests.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/health` shows `llm_provider_healthy: false` with Ollama | `ollama serve` isn't running, or the model isn't pulled | `ollama serve` + `ollama pull llama3.1:8b` |
| Backend can't reach Ollama from inside Docker on Linux | `host.docker.internal` DNS not resolving | Confirm `extra_hosts: host-gateway` is present in `docker-compose.yml` (already included) |
| `/health` shows `knowledge_base_chunks: 0` | Ingestion hasn't run yet | `docker compose exec backend python -m app.ingestion.run_ingestion` |
| Ingestion fails with "Transcripts directory does not exist" | `fetch_transcripts.sh` wasn't run | `./scripts/fetch_transcripts.sh 40` |
| Chat responses are slow (10-20s) | Expected on CPU-only local Ollama inference | Switch to a smaller model or `LLM_PROVIDER=anthropic` for faster cloud responses |
| `422` on `/api/chat` | Missing/invalid `session_id` | Call `POST /api/sessions` first, use the returned `session_id` |
| CORS errors in browser console | Frontend origin not in `CORS_ALLOW_ORIGINS` | Add your origin to `.env`'s `CORS_ALLOW_ORIGINS` |

## Repo structure

```
backend/
  app/
    api/          FastAPI routes + Pydantic schemas
    agent/        LLM provider abstraction, retrieval, orchestration
    db/           SQLAlchemy models + session management
    ingestion/    Transcript loading, chunking, embedding, CLI
    skills/       Grounded chat, Ship 30/30 essay, artifact sanitizer
  tests/          Unit + integration tests
frontend/
  src/
    components/   Message, ArtifactViewer
    lib/          API client
docs/              architecture.md, design.md, manual_test_plan.md
agent_transcripts/ Coding-agent session logs (see its README)
scripts/           fetch_transcripts.sh
PRD.md             Discovery brief
docker-compose.yml One-command startup
.env.example       All configurable environment variables
```

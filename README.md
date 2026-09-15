# The Lenny Growth Assistant

A full-stack, AI-powered conversational assistant grounded strictly in [Lenny's Podcast](https://www.lennyspodcast.com/) transcripts.
Ask complex product/growth questions, get grounded answers with inline episode citations, generate Ship 30 for 30–style essays, and create Markdown or HTML/CSS artifacts rendered in an in-app side-by-side Artifact Viewer.

Read [`PRD.md`](./PRD.md) for the product brief & discovery scope, [`docs/architecture.md`](./docs/architecture.md) for system design, [`docs/design.md`](./docs/design.md) for UI/UX rationale, and [`docs/manual_test_plan.md`](./docs/manual_test_plan.md) for UI testing steps.

---

## 🚀 Quickstart (Docker, Recommended)

**Prerequisites:**
- Docker + Docker Compose
- [Ollama](https://ollama.com/) installed and running **on your host machine** (default local model provider)
- ~5GB free disk space for local model execution

```bash
# 1. Pull the local model (one-time setup)
ollama pull llama3.1:8b
ollama serve   # start host Ollama service if not already running

# 2. Configure environment
cp .env.example .env
# Default setting points LLM_PROVIDER=ollama — no further edits required for local demo

# 3. Start PostgreSQL database, FastAPI backend, and React frontend
docker compose up -d --build

# 4. Ingest podcast transcripts into PostgreSQL knowledge base (303 episodes / 11,012 chunks)
docker compose exec backend python -m app.ingestion.run_ingestion
```

Then open:
- **Frontend UI:** http://localhost:5173
- **API Documentation (Swagger):** http://localhost:8000/docs
- **Health Check Endpoint:** http://localhost:8000/health

---

## 🔄 Switching to Cloud Provider (Anthropic)

Edit `.env`:
```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```
Then restart the backend container: `docker compose up -d --build backend`.  
No code changes are required — provider switching is handled via configuration (`app/agent/providers/factory.py`).

---

## 💻 Running Without Docker (Local Dev)

**1. Backend:**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Start a local Postgres container or instance:
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=lenny_assistant postgres:16-alpine

cp ../.env.example .env   # ensure DATABASE_URL points to localhost:5432
uvicorn app.main:app --reload
```

**2. Ingestion:**
```bash
cd backend
python -m app.ingestion.run_ingestion
```

**3. Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Running Automated Tests

Run the full automated test suite using `pytest`:

```bash
# Running tests inside Docker container:
docker compose exec backend pytest -v

# Or running locally inside backend virtual environment:
cd backend
pytest -v
```

The **33 automated unit and integration tests** cover:
- Token chunking logic and overlap guarantees
- HTML artifact sanitization against XSS vectors (`bleach`)
- Ship 30 for 30 essay prompt generation & constraints
- Grounded chat prompt construction & citation formatting
- LLM provider factory routing & graceful failure paths
- Hashed term-frequency embedding math & cosine similarity
- API integration tests (session creation, history isolation, message persistence, health reporting) against an in-memory test database with a deterministic fake provider.

---

## ⚙️ Environment Variables

See [`.env.example`](./.env.example) for inline documentation. Primary controls:
- `LLM_PROVIDER`: `ollama` (local) or `anthropic` (cloud).
- `OLLAMA_BASE_URL`: Defaults to `http://host.docker.internal:11434` for Docker-to-host connectivity.
- `RETRIEVAL_TOP_K`: Default `6` candidate chunks per retrieval turn.
- `RETRIEVAL_MIN_SCORE`: Relevance threshold `0.20` below which queries return the canonical non-grounded fallback.

---

## 🔍 Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| `/health` shows `llm_provider_healthy: false` with Ollama | `ollama serve` isn't running on host, or model isn't pulled | Run `ollama serve` and `ollama pull llama3.1:8b` |
| Backend can't reach Ollama from inside Docker on Linux | `host.docker.internal` DNS not resolving | Confirm `extra_hosts: host-gateway` is present in `docker-compose.yml` (included by default) |
| `/health` shows `knowledge_base_chunks: 0` | Transcript ingestion hasn't run yet | Run `docker compose exec backend python -m app.ingestion.run_ingestion` |
| "Tell me all transcripts" lists only a few episodes | Direct semantic search window limitation | Resolved by KB Metadata Router in `orchestrator.py` which queries distinct episodes directly from DB |
| `422 Unprocessable Entity` on `/api/chat` | Missing or invalid `session_id` | Call `POST /api/sessions` first to get a valid `session_id` |

---

## 📂 Repository Structure

```
backend/
  app/
    api/          FastAPI endpoints, Pydantic schemas, exception handlers
    agent/        LLM provider factory, retrieval engine, orchestrator
    db/           SQLAlchemy models (ChatSession, ChatMessage, TranscriptChunk)
    ingestion/    Recursive transcript loader, tiktoken chunker, CLI runner
    skills/       Grounded chat prompt, Ship 30/30 essay skill, artifact sanitizer
  tests/          Automated unit & integration test suite (33 tests)
frontend/
  src/
    components/   Message, CitationBadge, ArtifactViewer
    lib/          API client hooks
docs/             architecture.md, design.md, manual_test_plan.md
agent_transcripts/ Coding-agent session logs (see index README)
scripts/          fetch_transcripts.sh
PRD.md            Discovery brief & product requirements
docker-compose.yml Reproducible one-command multi-container setup
.env.example      Environment variable template
```

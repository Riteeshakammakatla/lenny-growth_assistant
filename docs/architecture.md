# Architecture & System Design

## 1. System Overview

```
┌─────────────┐      HTTP/JSON       ┌───────────────────────────────────────────┐      SQL       ┌────────────┐
│  Frontend   │ ───────────────────▶ │             FastAPI Backend               │ ─────────────▶ │ PostgreSQL │
│ (Vite/React)│ ◀─────────────────── │                                           │ ◀───────────── │ (asyncpg)  │
└─────────────┘                      │  ┌─────────────────────────────────────┐  │                └────────────┘
                                     │  │        Agent Orchestrator           │  │
                                     │  │  - KB Metadata Router (Priority 0)  │  │
                                     │  │  - Contextual Retrieval Query Builder│  │
                                     │  │  - Grounding Gate & Post-LLM Clamp  │  │
                                     │  └──────────────────┬──────────────────┘  │
                                     │                     │                     │
                                     │  ┌──────────────────┴──────────────────┐  │
                                     │  │ Retrieval Engine (Hash Embedding)   │  │
                                     │  │ Skills: Grounded Chat, Ship 30/30,  │  │
                                     │  │         Artifact Sanitizer (Bleach) │  │
                                     │  └──────────────────┬──────────────────┘  │
                                     └─────────────────────┼─────────────────────┘
                                                           │
                                             ┌─────────────┴─────────────┐
                                             │   LLM Provider Factory    │
                                             │  ┌─────────┐   ┌───────┐  │
                                             │  │ Anthropic│   │Ollama │  │
                                             │  │ (cloud) │   │(local)│  │
                                             │  └─────────┘   └───────┘  │
                                             └───────────────────────────┘
```

---

## 2. Database Schema (PostgreSQL)

### `chat_sessions`
| Column | Type | Description |
|---|---|---|
| `id` | String (UUID, PK) | Session identifier |
| `user_id` | String | Client-generated user identifier |
| `title` | String, Nullable | Session title |
| `llm_provider` | String | Provider snapshot at creation (`ollama` or `anthropic`) |
| `created_at` / `updated_at` | DateTime | Timestamps |

### `chat_messages`
| Column | Type | Description |
|---|---|---|
| `id` | String (UUID, PK) | Message identifier |
| `session_id` | String (FK) | References `chat_sessions.id` |
| `role` | String | `user` or `assistant` |
| `content` | Text | Message body or generated essay text |
| `citations` | JSON, Nullable | List of `{episode_id, episode_title, source_path, score}` |
| `artifact` | JSON, Nullable | `{format: "markdown"|"html", content: "...", download_filename: "..."}` |
| `llm_provider` | String, Nullable | Provider used for this turn |
| `latency_ms` | Integer, Nullable | Response latency in milliseconds |
| `created_at` | DateTime | Creation timestamp |

### `transcript_chunks`
| Column | Type | Description |
|---|---|---|
| `id` | String (UUID, PK) | Chunk identifier |
| `episode_id` | String (Indexed) | Derived from episode folder/filename |
| `episode_title` | String | Extracted episode title |
| `source_path` | String | Relative filepath for citation traceability |
| `chunk_index` | Integer | Order within episode |
| `text` | Text | Chunk text body |
| `token_count` | Integer | Token count computed by `tiktoken` |
| `embedding` | JSON (List[Float]) | 128-dimensional term-frequency vector embedding |
| `ingested_at` | DateTime | Ingestion timestamp |

---

## 3. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/sessions` | Create a new chat session |
| `GET` | `/api/sessions/{session_id}` | Retrieve session details & full message history |
| `POST` | `/api/chat` | Send a chat message (`intent`: `chat` \| `essay` \| `artifact`) |
| `GET` | `/health` | System health check (DB status, provider status, episode & chunk counts) |

---

## 4. Ingestion & Retrieval Pipeline

### Ingestion (`app/ingestion/`)
- **Loader:** [`loader.py`](file:///c:/Users/ritee/Downloads/lenny-growth-assistant/lenny-growth-assistant/backend/app/ingestion/loader.py) recursively scans `/app/data/transcripts/episodes/` to ingest all **303 podcast episode transcripts**.
- **Chunker:** [`chunker.py`](file:///c:/Users/ritee/Downloads/lenny-growth-assistant/lenny-growth-assistant/backend/app/ingestion/chunker.py) uses `tiktoken` to split text into 500-token chunks with 75-token overlap.
- **Persistence:** Ingestion populates **11,012 TranscriptChunk records** in PostgreSQL. Re-ingestion for an episode is idempotent (`DELETE WHERE episode_id = ...` before insert).

### Vector Embedding (`app/agent/embeddings.py`)
- Uses a deterministic, lightweight 128-dimensional term-frequency hash vectorizer (`_hash_embed()`) with stopword filtering and sublinear term-frequency weighting (`1 + log(tf)`).
- Provides fast, offline similarity search without requiring heavy external embedding server dependencies.

### Retrieval & Gatekeeper (`app/agent/orchestrator.py` & `retrieval.py`)
1. **Priority-0 KB Metadata Router:** `_is_kb_metadata_query()` intercepts queries asking about transcript catalogs or episode counts, querying PostgreSQL directly (`SELECT DISTINCT episode_id, episode_title`) to return all **303 episodes** instantly without an LLM call.
2. **Contextual Retrieval Query Builder:** `_build_retrieval_query()` detects follow-up triggers (pronouns *"that"*, *"those"*, *"they"*, *"actionable lessons"*) and combines recent conversation context with the current query to ensure vector search retrieves relevant topic chunks.
3. **Relevance Thresholding:** `retrieve()` computes cosine similarity score across stored chunks. Results below `RETRIEVAL_MIN_SCORE=0.20` are filtered out.
4. **Grounding Gate:** If zero chunks pass the relevance threshold, the orchestrator immediately returns `"That's not covered in the transcripts I have."` without calling the LLM.
5. **Post-LLM Grounding Clamp:** `_clamp_grounding()` inspects LLM responses to strip any outside knowledge leaked after a non-grounded acknowledgement.

---

## 5. LLM Provider Architecture

- Abstract base class [`LLMProvider`](file:///c:/Users/ritee/Downloads/lenny-growth-assistant/lenny-growth-assistant/backend/app/agent/providers/base.py) defines `complete()` and `health_check()`.
- Provider factory [`factory.py`](file:///c:/Users/ritee/Downloads/lenny-growth-assistant/lenny-growth-assistant/backend/app/agent/providers/factory.py) inspects `LLM_PROVIDER` environment variable (`ollama` or `anthropic`).
- [`OllamaProvider`](file:///c:/Users/ritee/Downloads/lenny-growth-assistant/lenny-growth-assistant/backend/app/agent/providers/ollama_provider.py) connects to host Ollama service (`http://host.docker.internal:11434`) with a 120-second timeout.
- [`AnthropicProvider`](file:///c:/Users/ritee/Downloads/lenny-growth-assistant/lenny-growth-assistant/backend/app/agent/providers/anthropic_provider.py) connects to Anthropic Messages API with exponential retry logic.

---

## 6. Artifact Security Strategy

- **Server-Side Sanitization:** [`artifact_sanitizer.py`](file:///c:/Users/ritee/Downloads/lenny-growth-assistant/lenny-growth-assistant/backend/app/skills/artifact_sanitizer.py) uses `bleach` with a strict allowlist to strip `<script>`, `<iframe>`, `<object>`, `<embed>`, `<form>`, inline event handlers (`onload`, `onerror`), and `javascript:` URIs.
- **Client-Side Isolation:** [`ArtifactViewer.jsx`](file:///c:/Users/ritee/Downloads/lenny-growth-assistant/lenny-growth-assistant/frontend/src/components/ArtifactViewer.jsx) renders HTML inside an `<iframe sandbox="allow-same-origin">` explicitly **without** `allow-scripts`.
- **Markdown Security:** Markdown artifacts render via `react-markdown` without raw HTML injection support.

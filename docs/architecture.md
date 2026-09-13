# Architecture

## System overview

```
┌─────────────┐      HTTP/JSON       ┌──────────────────┐      SQL       ┌────────────┐
│  Frontend   │ ───────────────────▶ │   FastAPI backend │ ─────────────▶ │ PostgreSQL │
│  (Vite/React)│ ◀─────────────────── │                  │ ◀───────────── │            │
└─────────────┘                      │  ┌────────────┐  │                └────────────┘
                                      │  │ Orchestrator│  │
                                      │  └─────┬──────┘  │
                                      │        │         │
                              ┌───────┴────────┴────────┴───────┐
                              │  Retrieval   │  Skills           │
                              │  (embeddings │  - Grounded chat  │
                              │   + cosine   │  - Ship 30/30     │
                              │   similarity)│  - Artifact       │
                              │              │    sanitizer      │
                              └───────┬──────┴───────────────────┘
                                      │
                          ┌───────────┴────────────┐
                          │   LLM Provider (choice) │
                          │  ┌────────┐ ┌─────────┐ │
                          │  │Anthropic│ │ Ollama  │ │
                          │  │ (cloud) │ │ (local) │ │
                          │  └────────┘ └─────────┘ │
                          └─────────────────────────┘
```

## Database schema

**`chat_sessions`**
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| user_id | string | client-generated, no auth in v1 |
| title | string, nullable | reserved for future auto-titling |
| llm_provider | string | snapshot of provider at session creation; can differ from global default |
| created_at / updated_at | datetime | |

**`chat_messages`**
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| session_id | string | FK -> chat_sessions.id |
| role | string | `user` \| `assistant` |
| content | text | raw message or generated answer/essay text |
| citations | JSON, nullable | list of `{episode_id, episode_title, source_path, score}` |
| artifact | JSON, nullable | `{type: "markdown"|"html", content: "..."}` |
| llm_provider | string, nullable | actual provider that answered this turn |
| latency_ms | int, nullable | |
| created_at | datetime | |

**`transcript_chunks`**
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| episode_id | string | derived from filename, indexed |
| episode_title | string | derived from H1 or filename |
| source_path | string | relative path, used for citation traceability |
| chunk_index | int | position within episode |
| text | text | chunk content |
| embedding | JSON (list[float]) | see "Embeddings" below |
| token_count | int | |
| ingested_at | datetime | |

Re-running ingestion for an episode deletes and replaces its chunks (`DELETE WHERE episode_id = ...`
then re-insert), making ingestion idempotent and safe to re-run as transcripts are added.

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/sessions` | Create a new chat session; returns `session_id` |
| GET | `/api/sessions/{id}` | Full message history for a session |
| POST | `/api/chat` | Send a message; `intent` = `chat` \| `essay` \| `artifact` |
| GET | `/health` | Provider health, DB health, knowledge base chunk count |

`POST /api/chat` request:
```json
{
  "session_id": "uuid",
  "message": "How did Superhuman think about activation?",
  "intent": "chat",
  "artifact_format": null
}
```
Response includes `content`, `citations`, `artifact` (if applicable), `llm_provider`, `latency_ms`,
and `grounded` (whether any citation was found).

## Agent routing

The orchestrator (`app/agent/orchestrator.py`) is the single place that decides what happens for a
turn:

1. Load session + last N messages of history.
2. Retrieve top-k transcript chunks for the user's latest message (retrieval always runs, even for
   `essay`/`artifact` intents, so generated content stays grounded).
3. Branch on `intent`:
   - `chat` → grounded-chat skill builds a system prompt constrained to retrieved context, with an
     explicit "not covered" fallback instruction.
   - `essay` → Ship 30/30 skill builds a longer-form prompt encoding specific structural rules
     (hook, one-idea focus, headers, takeaway) using both retrieved context and recent conversation.
   - `artifact` → same as `chat`, but the raw model output is passed through the HTML sanitizer
     before being stored/returned as an artifact.
4. Call the active `LLMProvider` (chosen per-session, falling back to the global `LLM_PROVIDER`
   env var). On failure, degrade gracefully: return an explanatory message instead of a stack trace,
   and still persist the turn so the conversation isn't lost.
5. Persist both the user and assistant `ChatMessage` rows, including citations/artifact/latency.

## LLM provider abstraction

`app/agent/providers/base.py` defines `LLMProvider` with `complete()` and `health_check()`.
`AnthropicProvider` and `OllamaProvider` implement it independently; `factory.get_provider()` is the
only place that reads `LLM_PROVIDER` from config. This means:
- Swapping providers is a `.env` edit, not a code change.
- Adding a third provider (e.g. a different local runtime) means implementing the interface once —
  nothing else in the codebase needs to know it exists.
- A session can pin its own provider (`ChatSession.llm_provider`) independent of the current global
  default, so provider choice is visible and auditable per-conversation.

## Retrieval / RAG design

- **Chunking**: word-count-based with overlap (default 500 tokens, 75 overlap) — see
  `app/ingestion/chunker.py`. Chosen over sentence/paragraph chunking because transcripts are
  unstructured speech without reliable segmentation markers.
- **Embeddings**: default is a dependency-free deterministic hashed bag-of-words embedding
  (`app/agent/embeddings.py`). This keeps the mandatory local demo path fully offline with zero
  extra services. `EMBEDDING_PROVIDER=anthropic` (misnomer kept for config-simplicity) attempts
  Ollama's `nomic-embed-text` model for materially better retrieval quality, falling back silently
  to the hashed embedding if that model isn't pulled. This trade-off is explicit in the PRD's Risks
  section — retrieval quality with the default embedding is topical/keyword-ish rather than
  semantic, but is transparent, debuggable, and requires no additional infrastructure.
- **Similarity search**: brute-force cosine similarity over all chunks in Python
  (`app/agent/retrieval.py`). Deliberately not using pgvector's ANN index for this assessment: it
  avoids a hard dependency on the pgvector Postgres extension being installed on whatever Postgres
  instance the evaluator provisions (Supabase, Railway, plain Docker image all vary). At the scale
  of a few hundred to low thousands of chunks this is well under 100ms. **Scaling path**: swap the
  body of `retrieve()` for an `ORDER BY embedding <=> :query_vec LIMIT k` pgvector query behind the
  same function signature — no caller changes needed.
- **Groundedness**: results below `RETRIEVAL_MIN_SCORE` are dropped; if no chunks clear the
  threshold, the system prompt explicitly tells the model no context was found, and instructs it to
  say so rather than answer from parametric knowledge.

## Artifact generation & security

Generated artifacts are either:
- **Markdown** — rendered client-side via `react-markdown`, which never uses
  `dangerouslySetInnerHTML`; Markdown is parsed into React elements, so there's no HTML injection
  surface here at all.
- **HTML** — treated as fully untrusted, LLM-influenced content, same threat model as user-submitted
  HTML:
  1. **Server-side sanitization** (`app/skills/artifact_sanitizer.py`): `bleach` allowlist strips
     `<script>`, `<iframe>`, `<object>`, `<embed>`, `<form>`, all `on*` event handler attributes, and
     `javascript:` URLs, before the HTML is ever persisted or returned to the client.
  2. **Client-side isolation** (`ArtifactViewer.jsx`): sanitized HTML is rendered inside an
     `<iframe sandbox="allow-same-origin">` — critically, **without** `allow-scripts`. Even if a
     sanitizer bypass were discovered, the sandboxed frame cannot execute JavaScript.
  3. A strict `Content-Security-Policy` (`script-src 'none'`) is injected into the iframe's document
     as defense-in-depth.

**Explicitly not allowed** in artifacts: any `<script>`, inline event handlers, iframes/objects/embeds
(preventing artifact-in-artifact escapes), forms (preventing hidden exfiltration submissions), and
non-image `data:`/`javascript:` URLs. Allowed: headings, paragraphs, lists, tables, basic inline
formatting, images (http/https/data-image only), and `style`/`class` attributes for layout.

## Resilience & error handling

- **Missing API key** (`LLM_PROVIDER=anthropic` with no key): `AnthropicProvider.__init__` raises a
  clear `LLMProviderError` immediately, surfaced to the user as a chat message rather than a 500.
- **Ollama down**: `httpx.ConnectError` is caught and turned into an actionable message telling the
  user to run `ollama serve` and pull the model.
- **Model timeout**: `httpx.TimeoutException` caught with a message suggesting a smaller model.
- **Empty retrieval**: handled at the prompt level (see Groundedness above), not an error path.
- **DB connection issues**: `/health` reports `database_healthy: false` independently of provider
  health, so the two failure modes are distinguishable at a glance.
- All unhandled exceptions are caught by a global FastAPI exception handler and logged as structured
  JSON, returning a generic 500 rather than leaking a stack trace to the client.

## Deployment topology

`docker-compose.yml` runs three services: `db` (Postgres), `backend` (FastAPI), `frontend` (Vite dev
server). **Ollama runs on the host**, not in a container — this matches how most evaluators will
already have it installed, and avoids bundling a multi-gigabyte model image. The backend reaches it
via `host.docker.internal` (mapped explicitly via `extra_hosts` for Linux compatibility, since
`host.docker.internal` is Docker-Desktop-only by default).

## Known limitations / explicit trade-offs

- Embeddings are a simple hashed bag-of-words by default, not a trained semantic model (documented
  above and in PRD Risks).
- Brute-force retrieval doesn't scale past roughly tens of thousands of chunks without moving to a
  real vector index.
- No auth; `user_id` is a client-generated identifier, not a verified identity.
- Ingestion loads the full transcript set into memory at once; fine for the demo-scale subset, would
  need batching/streaming for the full historical archive.

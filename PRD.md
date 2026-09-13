# PRD — The Lenny Growth Assistant

## 1. Problem & User

**Primary user:** Product managers, growth PMs, and founders who follow Lenny's Podcast/Newsletter
but don't have time to re-listen to hours of interviews to find a specific answer (e.g., "how did
Superhuman think about activation?").

**Job to be done:** "When I have a product/growth question, let me ask it in plain language and get
a grounded answer sourced from specific episodes — plus let me turn that answer into something I can
publish (an essay) or hand to a teammate (a formatted doc) without doing extra writing work."

**Pain removed:** Manual transcript search, re-listening to podcasts, and blank-page essay writing.
The assistant compresses "search + synthesize + draft" into one conversational flow.

## 2. Success Metrics

Primary (product): **% of chat sessions that end in an accepted artifact** (essay or doc generated
and not immediately regenerated/discarded) — target ≥ 40% of multi-turn sessions in the evaluation
demo.

Secondary (operational): **Groundedness rate** — % of assistant answers that include at least one
valid transcript citation, measured over a fixed eval set of 20 test questions. Target ≥ 90%
(remaining 10% should be explicit "not covered in the transcripts" responses, not unsupported claims).

Guardrail: **p50 response latency** under 6s for cloud model, under 15s for local Ollama model on
a standard laptop (CPU-only, 8B-class model).

## 3. Assumptions (brief was underspecified)

- "Evaluator" = a technical reviewer who will clone the repo, run `docker compose up`, and test
  locally — not an end customer. Optimize docs/DX for that reader.
- Local Ollama model target: `llama3.1:8b` or `qwen2.5:7b` — small enough to run on a laptop CPU,
  good enough instruction-following for RAG QA.
- We do not need multi-user auth for v1 — "user metadata" means a lightweight client-generated
  user_id (e.g., stored in browser localStorage / cookie), not a full account system.
- Transcript repo is the single source of truth; we do not need to re-scrape Lenny's website.
- "Artifacts" render read-only in v1 — no live-editing of generated HTML by the user (out of scope,
  noted below).
- Given assessment time constraints, we ingest a representative subset of transcripts (see Scope)
  rather than the entire historical archive, and design ingestion to be re-run incrementally.

## 4. Scope

**In scope**
- FastAPI backend, session-scoped chat, Postgres persistence
- RAG over a subset (~30–50 episodes to start, extensible) of Lenny's transcripts
- Cloud (Anthropic) + local (Ollama) model toggle via config, no code changes
- Ship 30/30 essay-generation skill as a distinct tool, not an ad-hoc prompt
- Markdown/HTML artifact generation + sanitized in-app viewer
- Docker Compose one-command startup
- Structured logging, basic resilience (timeouts, retries, graceful degradation)
- Automated tests for API, retrieval, routing, persistence + manual UI test plan

**Out of scope (v1)**
- Full user auth/accounts (session-id based only)
- Multi-tenant deployment / horizontal scaling
- Live collaborative editing of artifacts
- Fine-tuning or training custom models
- Ingesting the full transcript archive (hundreds of episodes) — architecture supports it, initial
  load does a representative subset for demo speed
- Streaming token-by-token UI (nice-to-have, not required for grading criteria)

## 5. Key Flows

1. **New chat** → user asks a product/growth question → backend retrieves relevant transcript
   chunks → agent answers with inline citations → session persisted.
2. **Follow-up** → same session_id → prior turns + new question sent to agent with retrieved
   context → coherent multi-turn answer.
3. **"Turn this into an essay"** → user requests Ship 30/30 conversion → skill takes the grounded
   answer + retrieved sources → produces ~1,250-word structured essay → rendered as Markdown
   artifact in the viewer.
4. **"Make this a one-pager"** → user requests HTML artifact → agent generates sanitized HTML/CSS →
   rendered in isolated iframe in the Artifact Viewer.
5. **No answer available** → retrieval returns low-relevance results → assistant explicitly states
   the transcripts don't cover this, no fabrication.
6. **Model toggle** → evaluator sets `LLM_PROVIDER=ollama|anthropic` in `.env` → visible in UI
   badge → app behaves identically save for latency/quality.

## 6. Acceptance Criteria

- [ ] Can start a new session and get an independent conversation thread
- [ ] Answers cite at least one transcript source when transcripts support the claim
- [ ] Assistant explicitly declines to answer (no hallucination) when retrieval is empty/low-confidence
- [ ] Essay skill produces ~1,250-word Ship-30-style output with headings/bullets/bold and a takeaway
- [ ] Artifact viewer renders Markdown and HTML safely, side-by-side with chat
- [ ] App runs via `docker compose up` with only `.env` edits, using Ollama as the default local model
- [ ] Switching `LLM_PROVIDER` env var changes the active model with no code change
- [ ] Conversations, sessions, and metadata persist in Postgres across restarts
- [ ] Basic tests pass: retrieval returns expected chunks, session isolation holds, provider routing
      selects correct backend, artifact sanitizer strips scripts

## 7. Risks & Trade-offs

| Risk | Mitigation |
|---|---|
| Hallucination when transcripts don't cover a topic | Retrieval confidence threshold + explicit "not covered" fallback; system prompt constrains answers to retrieved context |
| Local model (Ollama) quality much lower than cloud | Document this trade-off explicitly in demo video; keep prompts simple/structured to help smaller models; allow cloud fallback |
| Latency on CPU-only local inference | Cap context size sent to local model; smaller model choice (7–8B); show loading state in UI |
| Unsafe HTML artifact rendering (XSS) | Sanitize with allowlist (e.g., DOMPurify) + render inside sandboxed iframe with restricted `sandbox` attribute, no script execution by default |
| Data leakage (secrets in transcripts/logs) | `.env.example` only, secrets excluded via `.gitignore`, logs redact API keys |
| Cost of cloud calls during grading | Default demo path uses Ollama; cloud path documented but optional |
| Incomplete transcript ingestion (subset only) | Architecture supports incremental re-ingestion; documented as an explicit scope choice, not a hidden gap |

## 8. Implementation Plan (high-level)

1. Backend skeleton: FastAPI app, health check, config layer, DB models/migrations
2. LLM provider abstraction (Anthropic + Ollama) behind a common interface
3. Ingestion pipeline: clone/read transcript repo → chunk → embed → store in pgvector (or local
   vector store) → source metadata retained
4. RAG chat endpoint + session persistence
5. Ship 30/30 skill (structured prompt/tool with encoded writing principles)
6. Artifact generation endpoint + sanitization layer
7. Frontend: chat UI + Artifact Viewer (iframe-sandboxed) + provider badge
8. Dockerize everything, write docs, write tests, record demo

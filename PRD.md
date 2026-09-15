# PRD — The Lenny Growth Assistant

## 1. Problem & User

**Primary user:** Product managers, growth PMs, and founders who follow Lenny's Podcast/Newsletter but don't have time to re-listen to hours of interviews to find specific actionable insights (e.g., *"How did Superhuman approach manual onboarding?"*).

**Job to be done:** *"When I have a product or growth question, let me ask it in plain language and get a grounded answer sourced from specific podcast episodes — plus let me turn that answer into something I can publish (an essay) or hand to a teammate (a formatted doc) without starting from a blank page."*

**Pain removed:** Manual transcript search, re-listening to podcasts, and blank-page writing block. The assistant compresses "search + synthesize + draft" into one conversational workflow.

---

## 2. Success Metrics

- **Primary (Product):** **% of chat sessions that end in an accepted artifact** (essay or doc generated and displayed in viewer) — target ≥ 40% of multi-turn sessions.
- **Secondary (Operational):** **Groundedness rate** — % of assistant answers that include at least one valid transcript citation. Target ≥ 90% (remaining 10% should be explicit *"That's not covered in the transcripts I have."* responses, not unsupported claims).
- **Guardrail:** **p50 response latency** under 6s for cloud model, under 15s for local Ollama model on a laptop CPU.

---

## 3. Assumptions

- Evaluator will clone the repository, run `docker compose up -d`, and test locally using Ollama (`llama3.1:8b`).
- Local Ollama model target: `llama3.1:8b` or `qwen2.5:7b` — small enough to run on CPU with good instruction-following capability.
- Lightweight client-generated `user_id` stored in browser state (no complex multi-tenant auth required for v1).
- Transcripts repository is the single source of truth (**303 episode transcripts** producing **11,012 chunks**).
- Artifacts render in an in-app split-pane Artifact Viewer side-by-side with chat.

---

## 4. Scope

### In Scope
- FastAPI backend, session-scoped chat persistence in PostgreSQL.
- RAG over **303 podcast episode transcripts** (~11,012 chunks).
- Cloud (Anthropic) + local (Ollama) model toggle via configuration with zero code changes.
- Priority-0 KB Metadata Router that queries DB directly for distinct episode counts/titles.
- Ship 30 for 30 essay-generation skill (~1,250 words target, strong hook, narrative flow, headings/bullets, takeaways).
- Markdown & HTML/CSS artifact generation with `bleach` server-side sanitization and sandboxed iframe isolation.
- Contextual retrieval query builder for multi-turn follow-ups resolving pronouns (*"that"*, *"those"*, *"they"*).
- Deterministic post-LLM grounding clamp (`_clamp_grounding()`) enforcing canonical fallback.
- Docker Compose one-command startup.
- 33 automated unit and integration tests.

### Out of Scope (v1)
- Full multi-tenant authentication system (session-ID based isolation used).
- Live collaborative multi-user editing of rendered artifacts.
- Token-by-token streaming UI (complete turn responses returned).

---

## 5. Key Flows

1. **New Chat Turn:** User asks a growth question → backend retrieves top-k matching transcript chunks → agent answers with inline citations → session persisted in PostgreSQL.
2. **Follow-Up Turn:** Contextual retrieval query builder resolves pronouns (*"that"*, *"those"*) by combining recent conversation context → retrieves relevant transcript chunks → answers in context.
3. **KB Catalog Query:** User asks *"Tell me all the transcripts you have"* → intercepted by KB Metadata Router → returns direct DB list of all **303 episode titles** instantly.
4. **"Turn this into an essay":** User clicks "Write Essay" → Ship 30/30 skill formats grounded answer into structured essay → rendered as Markdown in Artifact Viewer.
5. **"Make a doc":** User requests document artifact → agent generates HTML/CSS snippet → server sanitizes via `bleach` → rendered in sandboxed iframe.
6. **Out-of-Domain Query:** Retrieval score below relevance threshold (`RETRIEVAL_MIN_SCORE=0.20`) → returns explicit fallback *"That's not covered in the transcripts I have."* without calling LLM.

---

## 6. Acceptance Criteria

- [x] Independent chat session creation and PostgreSQL persistence across restarts.
- [x] Answers cite real episode sources inline when material supports the claim.
- [x] Assistant declines unsupported queries with explicit fallback string.
- [x] KB Metadata queries answer with accurate DB counts (**303 episodes**).
- [x] Ship 30 for 30 skill generates structured long-form essays grounded in transcripts.
- [x] Artifact viewer displays Markdown & HTML safely beside chat.
- [x] Docker Compose starts full stack cleanly with default local Ollama model.
- [x] `LLM_PROVIDER` toggle switches between Ollama and Anthropic seamlessly.
- [x] All 33 automated tests pass.

---

## 7. Risks & Trade-offs

| Risk | Mitigation |
|---|---|
| Hallucination on unsupported topics | Retrieval confidence threshold (`RETRIEVAL_MIN_SCORE=0.20`) + programmatic grounding gate + post-LLM clamp |
| CPU latency on local Ollama inference | Cap context length, use lightweight prompt structure, and show UI loading state |
| Unsafe HTML artifact rendering (XSS) | Server-side `bleach` allowlist sanitization + client-side sandboxed `<iframe sandbox="allow-same-origin">` |

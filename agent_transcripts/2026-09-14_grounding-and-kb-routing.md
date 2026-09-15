# Coding Agent Session Log: Grounding Enforcement & KB Metadata Router

**Date:** 2026-09-14  
**Topic:** Grounding Gate, Post-LLM Grounding Clamp, System Prompt Hardening, and Knowledge Base Metadata Routing

---

## 1. Initial Goal & Bug Resolution
Resolve two critical issues reported during manual testing:
1. **Grounding Violation:** When retrieval found no chunks or low relevance, small models like `llama3.2:3b` occasionally responded with:
   *"That's not covered in the transcripts I have. However, I can provide some general insights..."*
   which violates the strict no-outside-knowledge constraint.
2. **Metadata Listing Bug:** When asked *"Tell me all the transcripts you have"*, the LLM only cited the top-k retrieved chunks (5-6 episodes) instead of the full 303 episodes in the database.

---

## 2. Technical Solution & Process

### Step 1: Priority-0 KB Metadata Router (`orchestrator.py`)
- Added `_is_kb_metadata_query()` in `orchestrator.py` to detect queries asking about the catalog of transcripts (e.g., *"how many transcripts do you have?"*, *"list all episodes"*).
- Intercepted these queries *before* retrieval and answered directly via PostgreSQL `SELECT DISTINCT episode_id, episode_title`, returning the full list / count (**303 episodes**) instantly without an LLM call.

### Step 2: Post-LLM Grounding Clamp & System Prompt Hardening
- Updated `SYSTEM_TEMPLATE` in `app/skills/grounded_chat.py` with an explicit `STOP` directive and concrete prohibited-vs-allowed examples.
- Implemented `_clamp_grounding(text)` in `orchestrator.py`. If the model output starts with a `"not covered"` statement but appends general knowledge (`"but I can"`, `"however"`), it is clamped to `"That's not covered in the transcripts I have."` deterministically.

---

## 3. Verification & Outcome
- Evaluated against test cases:
  - *"How many transcripts do you have?"* → Returns 303 episodes instantly.
  - *"What is the capital of France?"* → Clamped to exact non-grounded fallback.

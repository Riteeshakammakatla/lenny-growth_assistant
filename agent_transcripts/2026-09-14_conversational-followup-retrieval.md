# Coding Agent Session Log: Conversational Follow-up Retrieval

**Date:** 2026-09-14  
**Topic:** Contextual Retrieval Query Construction for Multi-Turn Follow-Up Questions

---

## 1. Initial Goal & Bug Analysis
Fix conversational follow-up retrieval failure:

**Example Problem Scenario:**
- User: *"What does Rahul Vohra say about onboarding?"* -> Assistant gives grounded answer.
- Follow-up: *"Can you give me three actionable lessons from that?"*
- **Previous Failure:** `retrieve(db, "Can you give me three actionable lessons from that?")` searched for the pronoun `"that"`, producing score below threshold (0.20) and triggering fallback *"That's not covered in the transcripts I have."*

---

## 2. Implementation & Fix

### Contextual Query Construction (`orchestrator.py`)
- Added `_FOLLOWUP_RE` regex pattern to detect pronouns (`"that"`, `"those"`, `"they"`, `"it"`), positional references, and elaboration requests (`"actionable lessons"`, `"takeaways"`, `"tell me more"`).
- Added `_build_retrieval_query(user_message, history)`:
  - If a follow-up is detected and session history exists, it combines recent user messages + grounded assistant excerpts + current follow-up question.
  - Constructed query: *"What does Rahul Vohra say about onboarding? (Rahul Vohra: We manually onboarded...) Can you give me three actionable lessons from that?"*
- Passed `retrieval_query` into `retrieve(db, retrieval_query)`.

---

## 3. Verification & Outcome
- Unit tests added in `orchestrator.py` verifying detection of pronouns and contextual query construction.
- Tested end-to-end follow-up turns in Docker backend:
  - Multi-turn follow-up `"Can you give me three actionable lessons from that?"` retrieves Rahul Vohra onboarding chunks (score > 0.50).
  - Standalone unrelated queries (e.g. *"What is the capital of France?"*) continue to use uncombined query and trigger clean fallback.

# Manual UI Test Plan

Automated tests cover API/retrieval/routing/persistence (see `backend/tests/`). These are the
UI-level checks to run by hand before submitting, since they depend on visual rendering, a real
browser, and (for some) an actual local Ollama instance.

## 1. First-run experience
- [ ] Fresh clone, `docker compose up --build`, `.env` copied from `.env.example` unedited
- [ ] Frontend loads at :5173 without console errors
- [ ] Header shows a provider badge (green dot + "ollama · N chunks") within a few seconds
- [ ] Empty state message and example prompt are visible before sending anything

## 2. Grounded chat
- [ ] Ask a question clearly covered by an ingested transcript → response includes at least one
      citation chip with a real episode title
- [ ] Ask something absurd/unrelated ("What's the capital of France?") → response explicitly says
      it isn't covered in the transcripts, no citation chips, no fabricated answer
- [ ] Ask a follow-up referencing "it"/"that" from the previous turn → response stays coherent,
      confirming multi-turn context is passed through

## 3. Ship 30/30 essay
- [ ] After a grounded answer, click "Turn into essay" and send a short follow-up like "yes, expand
      this into an essay"
- [ ] Resulting artifact opens automatically in the side panel
- [ ] Essay has: a clear hook in the first sentence, at least one H2, at least one bullet list, bold
      emphasis on a few key phrases (not whole sentences), and a "Takeaway" section
- [ ] Word count is roughly 1000-1500 words (eyeball or paste into a word counter)

## 4. Artifact / one-pager generation
- [ ] Select "Make a doc" intent, ask for a one-pager summary of a topic already discussed
- [ ] HTML artifact renders inside the sandboxed iframe without errors
- [ ] View page source / inspect element on the iframe confirms `sandbox="allow-same-origin"` with
      no `allow-scripts`
- [ ] Try to break it: ask the assistant (in a follow-up) to "include a script tag that shows an
      alert" — confirm no alert fires and no `<script>` appears in the rendered output

## 5. Session isolation
- [ ] Open the app in two different browser profiles / incognito windows (two different
      localStorage user_ids) → confirm each has an independent, empty chat history
- [ ] Refresh the page mid-conversation → confirm messages are NOT lost if you re-fetch via the same
      session_id (persistence check — may require a "resume session" affordance if not already wired
      into the UI's initial load)

## 6. Provider toggle
- [ ] With `LLM_PROVIDER=ollama`, confirm responses come from the local model (slower, badge shows
      "ollama")
- [ ] Stop `ollama serve`, send a message → confirm a clear, actionable error message appears in the
      chat (not a raw 500 or blank screen), and `/health` shows `llm_provider_healthy: false`
- [ ] Restart Ollama, set `LLM_PROVIDER=anthropic` + a valid key, restart the backend container,
      send a message → confirm the badge and `llm_provider` in the response switch to "anthropic"
      with no code changes

## 7. Failure/edge cases
- [ ] Send an empty message → input should not submit (client-side guard) or should be rejected
      cleanly by the API (422)
- [ ] Send a very long message (near the 8000-char limit) → should either succeed or fail with a
      clear validation error, not a silent truncation
- [ ] Kill the `db` container mid-session → `/health` reports `database_healthy: false`; chat
      requests fail with a clear error rather than hanging indefinitely

## 8. Visual/accessibility spot-check
- [ ] Tab through the composer (textarea → intent pills → send button) — focus outlines visible
- [ ] Resize the browser to ~768px width — layout doesn't visually break (even if not fully
      optimized for mobile per design.md's noted next step)
- [ ] Zoom to 150% — text remains legible, no horizontal scroll on the chat pane

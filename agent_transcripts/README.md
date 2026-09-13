# Agent Transcripts

This folder holds the raw session logs from the coding agent(s) used to build this project,
including failed attempts and the fixes that followed — per the assignment's requirement to show
process, not just the polished result.

## Convention

- One file per work session: `YYYY-MM-DD_topic.md` (e.g. `2026-09-13_backend-scaffold.md`).
- Each file is the transcript as exported from the tool used (Claude, Claude Code, etc.), lightly
  reviewed only to **scrub secrets** (API keys, tokens, connection strings) — content and structure
  otherwise left intact, including mistakes and corrections.
- A short one-line index is kept in this README as sessions are added, so a reviewer can find the
  session that covers a specific area (e.g. "ingestion pipeline debugging," "artifact sanitizer
  XSS fix") without opening every file.

## Index

| File | Covers |
|---|---|
| _(add entries here as sessions are exported)_ | |

## Secret-scrubbing checklist before adding a transcript

- [ ] No `ANTHROPIC_API_KEY`, database passwords, or connection strings with credentials
- [ ] No personal access tokens (GitHub, etc.)
- [ ] No real user data if any was used during manual testing

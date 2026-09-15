# Design Rationale & UI/UX Principles

## 1. Design Philosophy

**Target Audience:** Product Managers, Growth Leads, and Founders who follow Lenny's Podcast and need grounded research, actionable frameworks, or structured writing assets without re-listening to hours of audio.

**Core Concept:** A dark, focused studio interface. The assistant acts as a reliable growth research partner. Chrome is minimal; warmth comes from curated typography and subtle accent colors rather than generic SaaS dashboards.

---

## 2. Color System

| Token | Hex Value | Purpose |
|---|---|---|
| `--ink-950` | `#12141c` | App background |
| `--ink-900` / `--ink-800` | `#191c28` / `#232636` | Container surfaces & panel borders |
| `--paper` | `#eee9de` | Primary body text (warm off-white) |
| `--paper-dim` | `#b8b3a6` | Secondary metadata & timestamps |
| `--amber` | `#e3a23a` | Primary accent — active state & assistant markers |
| `--moss` | `#7ea888` | Grounded indicator — verified citation signal |
| `--danger` | `#c96a5a` | Error banners |

---

## 3. Typography

- **Display Header:** *Fraunces* (serif) — Used exclusively for the main header title and section headers within the Artifact Viewer.
- **Body & UI Controls:** *Inter* (sans-serif) — Clean, highly readable for conversational text, code blocks, and action buttons.

---

## 4. UI Layout & Component Hierarchy

```
┌──────────────────────────────────────────────────────────────────────────┐
│  The Lenny Growth Assistant                 ● ollama · 11,012 chunks     │  <- Header Bar
├────────────────────────────────────────┬─────────────────────────────────┤
│                                        │                                 │
│   Chat Stream                          │   Artifact Viewer               │
│   - User message bubble                │   (Appears when an essay        │
│   - Assistant grounded response        │    or doc artifact is active)   │
│   - Moss citation chips                │   - Tab bar (Markdown / HTML)   │
│                                        │   - Sandboxed render area       │
│                                        │                                 │
├────────────────────────────────────────┤                                 │
│  [Ask] [Turn into essay] [Make a doc]  │                                 │
│  [ Input textarea............... Send ]│                                 │
└────────────────────────────────────────┴─────────────────────────────────┘
```

---

## 5. Interaction States & Controls

1. **Intent Actions:**
   - **Ask:** Standard grounded chat query (`intent="chat"`).
   - **Turn into essay:** Triggers Ship 30 for 30 skill (`intent="essay"`), generating a structured essay rendered in the Artifact Viewer.
   - **Make a doc:** Generates structured document artifact (`intent="artifact"`) sanitized via `bleach` and rendered in the viewer.
2. **Citation Chips:** Sourced episode citations render as moss-colored chips inline below assistant messages.
3. **Grounding Fallback:** When retrieval returns scores below threshold (`0.20`), an explicit amber fallback message displays (*"That's not covered in the transcripts I have."*).
4. **Artifact Split-Pane:** The Artifact Viewer opens automatically on the right when an essay or doc artifact is created, providing side-by-side view with chat.

# Design

## Design plan

**Subject & audience:** a research/writing tool for product people who listen to long-form podcast
interviews and want to extract and repackage insight quickly. The audience is comfortable with
technical tools (PMs, growth leads) but wants the tone of a good editor, not a generic SaaS dashboard.

**Concept:** a "late-night studio" feel — the assistant is like a producer sitting with you at the
mixing desk, pulling up the right clip from hours of tape. Dark, focused, unfussy chrome; warmth comes
from one accent color rather than a bright UI.

### Color
| Token | Hex | Role |
|---|---|---|
| `--ink-950` | `#12141c` | App background |
| `--ink-900` / `--ink-800` / `--ink-700` / `--ink-600` | `#191c28` / `#232636` / `#2f3346` / `#3d4258` | Surface layering, borders |
| `--paper` | `#eee9de` | Primary text (warm off-white, not pure white) |
| `--paper-dim` | `#b8b3a6` | Secondary text |
| `--amber` | `#e3a23a` | Primary accent — "on air" warmth, assistant voice marker |
| `--moss` | `#7ea888` | Grounded/citation indicator — a "safe, verified" signal distinct from the amber accent |
| `--danger` | `#c96a5a` | Errors only |

Deliberately avoided the near-cream (`#F4F1EA`) + terracotta (`#D97757`) combination flagged as an
AI-generated default — chose a cooler ink background and a more saturated amber instead, with moss
green doing double duty as both an accent and a semantic "verified" signal.

### Type
- **Display**: Fraunces (serif) — used only for the app title and section headers in the artifact
  viewer. Its slight quirkiness (variable optical size) gives warmth without looking corporate.
- **Body/UI**: Inter — neutral, highly legible at small sizes for chat text and controls.
Two families, clearly distinct roles: Fraunces never appears in body copy; Inter never appears in
headings.

### Layout
```
┌───────────────────────────────────────────────────────────┐
│  The Lenny Growth Assistant             ● ollama · 412 chunks │  <- header, thin border, no shadow
├───────────────────────────────┬─────────────────────────────┤
│                                │                              │
│   chat messages (scrolling)   │   artifact viewer            │
│   assistant replies use a     │   (only appears once an      │
│   left border rule, not a     │    artifact is generated;    │
│   bubble — distinguishes      │    otherwise chat takes the  │
│   "voice" from "note"         │    full width)                │
│                                │                              │
├───────────────────────────────┤                              │
│  [Ask] [Essay] [Doc]  intent  │                              │
│  [ textarea............ Send ]│                              │
└───────────────────────────────┴─────────────────────────────┘
```
Left-aligned throughout; chat bubbles/rows never center. The artifact pane only claims screen space
when there's something to show — it doesn't reserve a permanent empty panel.

### Principles
1. **The transcript is the hero, not the chrome.** Citations render as small moss-colored chips, not
   footnote numbers or hover tooltips — visible at a glance without interrupting reading.
2. **Assistant replies read as annotations, not chat-bubble chatter.** A left border rule (borrowed
   from margin notes / manuscript markup) instead of a rounded bubble, reinforcing that this is
   sourced, edited content rather than casual back-and-forth.
3. **One accent, one job.** Amber = "the model is speaking / active." Moss = "this claim is grounded."
   They're never used interchangeably.
4. **No decorative motion.** The only animated moment is the scroll-to-latest-message behavior — no
   hover-lift cards, no fade-ins on load.

## Interaction states

- **Empty state**: centered prompt suggesting an example question and the essay/doc follow-up, so a
  first-time user immediately understands the two-step workflow (ask → transform).
- **Loading**: a plain "Thinking…" row in the same visual language as an assistant message — avoids
  a spinner that implies indeterminate work when latency is often just "the local model is slow."
- **Grounded vs. not grounded**: grounded replies show citation chips; ungrounded replies show an
  explicit amber note ("Not covered in the transcripts I have") rather than silently answering.
- **Error**: a dedicated banner above the message list, in the danger color, with the actual error
  detail from the backend (e.g. "Could not reach Ollama...") rather than a generic "Something went
  wrong."
- **Artifact generated**: an inline "Open generated document/one-pager →" link appears under the
  message; clicking opens the side panel. The panel can be closed without losing the artifact — it
  stays attached to its message.

## Responsiveness & accessibility

- Layout uses CSS grid with `minmax()` columns; below a certain width the artifact pane should stack
  below chat rather than side-by-side (documented here as the next responsive breakpoint to implement
  if extending past desktop-first demo scope).
- All interactive elements (`textarea`, buttons, intent pills) use real form elements with visible
  `:focus` outlines (amber outline, not just color change) — no `div onClick` buttons.
- Color choices maintain sufficient contrast: `--paper` (#eee9de) on `--ink-950` (#12141c) exceeds
  WCAG AA for body text; `--paper-dim` is used only for secondary/metadata text, never primary
  content.
- The sandboxed HTML artifact iframe includes its own `<meta charset>` and system font stack so it
  renders legibly even though it's isolated from the app's own styles.
- No motion is triggered automatically beyond the necessary scroll-into-view, respecting users
  sensitive to animation.

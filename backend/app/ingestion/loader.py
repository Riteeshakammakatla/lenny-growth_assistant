"""
Loads transcript files from disk into (episode_id, episode_title, source_path, text) records.

Only loads actual episode transcripts located at:
    <transcripts_dir>/episodes/<episode-slug>/transcript.md

This deliberately excludes:
- CLAUDE.md, README.md (root documentation)
- index/*.md (topic index files)
- Any other non-episode markdown files

See scripts/fetch_transcripts.sh for the one-time clone step.
"""
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RawTranscript:
    episode_id: str
    episode_title: str
    source_path: str
    text: str


_FRONTMATTER_TITLE_RE = re.compile(r"^title:\s*['\"]?(.*?)['\"]?\s*$", re.MULTILINE)
_H1_RE = re.compile(r"^#\s+(.*)", re.MULTILINE)


def _extract_title(text: str, episode_slug: str) -> str:
    """Extract a meaningful title using three strategies in priority order:

    1. YAML frontmatter ``title:`` field (transcripts have ``---`` frontmatter).
    2. First markdown H1 heading found anywhere in the text.
    3. Humanise the episode directory slug as a final fallback.
    """
    # 1. YAML frontmatter: look for `title:` between the opening `---` fences.
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            frontmatter = text[3:end]
            # Handle multi-line YAML scalars: grab only the first continuation
            # that starts with 'title:' and collapse the inline value.
            fm_match = _FRONTMATTER_TITLE_RE.search(frontmatter)
            if fm_match:
                title = fm_match.group(1).strip().strip("\"'")
                if title:
                    return title

    # 2. First H1 heading anywhere in the document.
    h1_match = _H1_RE.search(text)
    if h1_match:
        return h1_match.group(1).strip()

    # 3. Humanise the directory slug: "ami-vora" → "Ami Vora".
    return episode_slug.replace("-", " ").replace("_", " ").title()


def load_transcripts(transcripts_dir: str) -> list[RawTranscript]:
    """Load only actual podcast episode transcripts.

    Targets the pattern:
        <transcripts_dir>/episodes/<slug>/transcript.md

    All other files (CLAUDE.md, README.md, index/*.md, etc.) are ignored.
    """
    root = Path(transcripts_dir)
    if not root.exists():
        raise FileNotFoundError(
            f"Transcripts directory '{transcripts_dir}' does not exist. Run "
            f"scripts/fetch_transcripts.sh first, or set TRANSCRIPTS_DIR to a directory "
            f"you've populated manually."
        )

    episodes_dir = root / "episodes"
    if not episodes_dir.exists():
        raise FileNotFoundError(
            f"Expected an 'episodes' subdirectory at '{episodes_dir}'. "
            f"Make sure TRANSCRIPTS_DIR points to the root of the transcript repo "
            f"(which should contain episodes/, index/, etc.)."
        )

    # Only match the canonical transcript file inside each episode directory.
    # This deliberately excludes README.md, CLAUDE.md, index/*.md, scripts/*, etc.
    transcript_files = sorted(episodes_dir.glob("*/transcript.md"))

    transcripts: list[RawTranscript] = []
    for path in transcript_files:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            continue

        # episode_id = the episode's directory name (e.g. "ami-vora"), NOT path.stem
        # which would always be "transcript" for every file.
        episode_id = path.parent.name

        title = _extract_title(text, episode_id)

        transcripts.append(
            RawTranscript(
                episode_id=episode_id,
                episode_title=title,
                source_path=str(path.relative_to(root)),
                text=text,
            )
        )
    return transcripts

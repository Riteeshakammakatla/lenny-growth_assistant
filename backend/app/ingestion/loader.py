"""
Loads transcript files from disk into (episode_id, episode_title, source_path, text) records.

Expects `transcripts_dir` (see settings) to contain one file per episode —
`.md` or `.txt` — such as a checkout of
https://github.com/ChatPRD/lennys-podcast-transcripts. We deliberately read
from a local directory rather than shelling out to `git` at ingestion time,
so ingestion works offline and the evaluator controls exactly which
transcripts are present (see scripts/fetch_transcripts.sh for the one-time
clone step).
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


def _derive_title(filename: str, first_line: str) -> str:
    # Prefer a markdown H1 if present, else fall back to a cleaned filename.
    h1_match = re.match(r"^#\s+(.*)", first_line.strip())
    if h1_match:
        return h1_match.group(1).strip()
    return filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").strip()


def load_transcripts(transcripts_dir: str) -> list[RawTranscript]:
    root = Path(transcripts_dir)
    if not root.exists():
        raise FileNotFoundError(
            f"Transcripts directory '{transcripts_dir}' does not exist. Run "
            f"scripts/fetch_transcripts.sh first, or set TRANSCRIPTS_DIR to a directory "
            f"you've populated manually."
        )

    files = sorted([*root.rglob("*.md"), *root.rglob("*.txt")])
    transcripts: list[RawTranscript] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            continue
        first_line = text.splitlines()[0] if text.splitlines() else ""
        title = _derive_title(path.name, first_line)
        episode_id = path.stem
        transcripts.append(
            RawTranscript(
                episode_id=episode_id,
                episode_title=title,
                source_path=str(path.relative_to(root)),
                text=text,
            )
        )
    return transcripts

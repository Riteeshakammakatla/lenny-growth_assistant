#!/usr/bin/env bash
# Clones (or updates) Lenny's Podcast transcript repo into ./data/transcripts.
# Run this once before `python -m app.ingestion.run_ingestion`.
#
# Usage: ./scripts/fetch_transcripts.sh [max_files]
#   max_files (optional): if set, keep only the first N transcript files —
#   useful for a fast demo ingestion instead of the full archive (see PRD
#   Scope: "representative subset").

set -euo pipefail

REPO_URL="https://github.com/ChatPRD/lennys-podcast-transcripts.git"
DEST="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/data/transcripts"
MAX_FILES="${1:-}"

if [ -d "$DEST/.git" ]; then
  echo "Updating existing checkout at $DEST"
  git -C "$DEST" pull --ff-only
else
  echo "Cloning $REPO_URL into $DEST"
  rm -rf "$DEST"
  git clone --depth 1 "$REPO_URL" "$DEST"
fi

if [ -n "$MAX_FILES" ]; then
  echo "Trimming to first $MAX_FILES transcript files for a faster demo ingestion..."
  mapfile -t files < <(find "$DEST" -type f \( -name "*.md" -o -name "*.txt" \) | sort)
  keep=("${files[@]:0:$MAX_FILES}")
  keep_set=$(printf '%s\n' "${keep[@]}")
  for f in "${files[@]}"; do
    if ! grep -qxF "$f" <<< "$keep_set"; then
      rm -f "$f"
    fi
  done
fi

count=$(find "$DEST" -type f \( -name "*.md" -o -name "*.txt" \) | wc -l)
echo "Done. $count transcript files ready in $DEST"

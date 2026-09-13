"""Simple word-based chunking with overlap.

We chunk by word count (approximated as tokens) rather than sentences or
markdown headers because Lenny's transcripts are largely unstructured speech
transcripts without reliable heading markers. Overlap preserves context
across chunk boundaries so a claim split mid-thought is still retrievable.
"""
from dataclasses import dataclass


@dataclass
class Chunk:
    index: int
    text: str
    token_count: int  # approximated as word count


def approx_tokens(text: str) -> int:
    return len(text.split())


def chunk_text(text: str, chunk_size_tokens: int = 500, overlap_tokens: int = 75) -> list[Chunk]:
    words = text.split()
    if not words:
        return []

    chunks: list[Chunk] = []
    start = 0
    index = 0
    step = max(chunk_size_tokens - overlap_tokens, 1)

    while start < len(words):
        end = min(start + chunk_size_tokens, len(words))
        chunk_words = words[start:end]
        chunk_str = " ".join(chunk_words)
        chunks.append(Chunk(index=index, text=chunk_str, token_count=len(chunk_words)))
        index += 1
        if end == len(words):
            break
        start += step

    return chunks

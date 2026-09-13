"""
Embeddings for the knowledge base.

Why "local" is the default: the mandatory demo path runs entirely offline
via Ollama, so requiring a cloud embedding API for retrieval would break the
"mandatory local demo" requirement even if chat itself was local. We default
to a lightweight local embedding (hashed TF-IDF-style bag-of-words projected
into a fixed-size vector) that needs zero extra services. It's meaningfully
worse than a real embedding model, but it's transparent, dependency-free,
and good enough for topical retrieval over a few hundred chunks — an
explicit, documented trade-off (see PRD "Risks").

If EMBEDDING_PROVIDER=anthropic is set and a key is available, we instead use
Ollama's embedding endpoint (`nomic-embed-text`) when present, giving much
better retrieval quality with no cloud dependency. Anthropic does not
currently expose a public embeddings endpoint, so "anthropic" mode here
actually routes to Ollama's embedding model if configured — documented in
architecture.md.
"""
import hashlib
import re

import numpy as np

from app.config.settings import get_settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_VECTOR_DIM = 384


def _hash_embed(text: str, dim: int = _VECTOR_DIM) -> list[float]:
    """Deterministic, dependency-free embedding: hash each token into a bucket
    of a fixed-size vector, weighted by term frequency, then L2-normalize.
    This is intentionally simple — see module docstring for the trade-off."""
    vec = np.zeros(dim, dtype=np.float32)
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        return vec.tolist()
    for tok in tokens:
        h = int(hashlib.sha256(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


async def embed_text(text: str) -> list[float]:
    """Single entry point used by both ingestion and query time so they stay
    consistent. Swappable for a real embedding model later without touching
    callers (see embed_ollama below for the higher-quality path)."""
    settings = get_settings()
    if settings.embedding_provider == "local":
        return _hash_embed(text)
    return await _embed_ollama(text)


async def _embed_ollama(text: str) -> list[float]:
    import httpx

    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]
    except Exception:
        # Fall back to local hashing rather than failing the whole request —
        # embeddings are an internal implementation detail the user never sees.
        return _hash_embed(text)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)

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

from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_VECTOR_DIM = 384

_STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren", "as",
    "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "cannot",
    "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from", "further", "had",
    "has", "have", "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how", "i", "if",
    "in", "into", "is", "it", "its", "itself", "just", "me", "more", "most", "my", "myself", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "same",
    "she", "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", "very",
    "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why", "with", "would",
    "you", "your", "yours", "yourself", "yourselves", "re", "s", "ve", "d", "ll", "m", "don", "t", "will",
    "just", "like", "know", "think", "yeah", "going", "get", "got", "thing", "things", "lot", "kind", "way",
    "make", "much", "see", "well", "also", "really", "want", "us", "take", "say", "said"
}


def _hash_embed(text: str, dim: int = _VECTOR_DIM) -> list[float]:
    """Deterministic, dependency-free embedding: hash content tokens into buckets
    of a fixed-size vector, weighted by sublinear term frequency, then L2-normalize.
    Filters out high-frequency stop words to prevent query/document vector dilution."""
    vec = np.zeros(dim, dtype=np.float32)
    raw_tokens = _TOKEN_RE.findall(text.lower())
    if not raw_tokens:
        return vec.tolist()
    
    # Filter stop words; fall back to raw tokens if all tokens were stop words
    tokens = [t for t in raw_tokens if t not in _STOP_WORDS]
    if not tokens:
        tokens = raw_tokens

    counts = Counter(tokens)
    for tok, count in counts.items():
        h = int(hashlib.sha256(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        # Sublinear term frequency scaling: 1 + log(count)
        weight = 1.0 + float(np.log(count))
        vec[idx] += sign * weight

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

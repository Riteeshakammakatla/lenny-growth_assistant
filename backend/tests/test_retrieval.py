import asyncio

from app.agent.embeddings import cosine_similarity, embed_text


def test_hash_embedding_is_deterministic():
    a = asyncio.run(embed_text("growth loops and activation"))
    b = asyncio.run(embed_text("growth loops and activation"))
    assert a == b


def test_identical_text_has_similarity_one():
    vec = asyncio.run(embed_text("pricing strategy for B2B SaaS"))
    assert abs(cosine_similarity(vec, vec) - 1.0) < 1e-6


def test_similar_topics_score_higher_than_unrelated():
    a = asyncio.run(embed_text("activation metrics onboarding retention product"))
    b = asyncio.run(embed_text("onboarding activation product retention metrics"))
    c = asyncio.run(embed_text("banana bread recipe oven temperature flour"))

    sim_related = cosine_similarity(a, b)
    sim_unrelated = cosine_similarity(a, c)
    assert sim_related > sim_unrelated


def test_cosine_similarity_handles_zero_vector():
    zero = [0.0] * 10
    other = [1.0] * 10
    assert cosine_similarity(zero, other) == 0.0

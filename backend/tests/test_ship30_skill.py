from app.agent.retrieval import RetrievedChunk
from app.skills.ship30_essay import build_essay_prompt, word_count_in_range


def test_word_count_in_range_accepts_target():
    text = " ".join(["word"] * 1250)
    assert word_count_in_range(text) is True


def test_word_count_in_range_rejects_too_short():
    text = " ".join(["word"] * 300)
    assert word_count_in_range(text) is False


def test_word_count_in_range_rejects_too_long():
    text = " ".join(["word"] * 3000)
    assert word_count_in_range(text) is False


def test_build_essay_prompt_includes_retrieved_context():
    retrieved = [
        RetrievedChunk(
            chunk_id="1",
            episode_id="ep1",
            episode_title="Growth Loops 101",
            source_path="ep1.md",
            text="Growth loops compound because output feeds back into input.",
            score=0.8,
        )
    ]
    messages = build_essay_prompt("How do growth loops work?", retrieved)
    system_msg = next(m for m in messages if m.role == "system")
    assert "Growth Loops 101" in system_msg.content
    assert "compound because output feeds back" in system_msg.content
    assert "atomic essay" in system_msg.content.lower()


def test_build_essay_prompt_handles_no_context():
    messages = build_essay_prompt("A topic with no retrieval hits", [])
    system_msg = next(m for m in messages if m.role == "system")
    assert "no additional transcript excerpts" in system_msg.content.lower()

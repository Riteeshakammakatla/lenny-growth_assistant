from app.agent.retrieval import RetrievedChunk
from app.skills.grounded_chat import NOT_COVERED_PHRASE, build_grounded_prompt


def test_no_retrieval_produces_not_covered_instruction():
    result = build_grounded_prompt([])
    assert result.has_context is False
    assert result.citations == []
    assert NOT_COVERED_PHRASE in result.system_prompt


def test_retrieval_populates_citations_and_context():
    retrieved = [
        RetrievedChunk(
            chunk_id="c1",
            episode_id="ep42",
            episode_title="Pricing Strategy Deep Dive",
            source_path="ep42.md",
            text="Anchoring the price against a competitor changes perceived value.",
            score=0.62,
        )
    ]
    result = build_grounded_prompt(retrieved)
    assert result.has_context is True
    assert result.citations == [
        {
            "episode_id": "ep42",
            "episode_title": "Pricing Strategy Deep Dive",
            "source_path": "ep42.md",
            "score": 0.62,
        }
    ]
    assert "Pricing Strategy Deep Dive" in result.system_prompt
    assert "Anchoring the price" in result.system_prompt

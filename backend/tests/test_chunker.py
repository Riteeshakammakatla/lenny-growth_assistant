from app.ingestion.chunker import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []


def test_short_text_returns_single_chunk():
    text = "This is a short transcript excerpt about activation metrics."
    chunks = chunk_text(text, chunk_size_tokens=500, overlap_tokens=75)
    assert len(chunks) == 1
    assert chunks[0].text == text


def test_long_text_is_split_with_overlap():
    words = [f"word{i}" for i in range(1200)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size_tokens=500, overlap_tokens=75)

    assert len(chunks) >= 3
    # Every chunk except possibly the last should be full-sized.
    for c in chunks[:-1]:
        assert c.token_count == 500

    # Overlap: the tail of chunk N should reappear at the head of chunk N+1.
    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert first_words[-75:] == second_words[:75]


def test_chunk_indices_are_sequential():
    text = " ".join(f"w{i}" for i in range(1000))
    chunks = chunk_text(text, chunk_size_tokens=300, overlap_tokens=50)
    assert [c.index for c in chunks] == list(range(len(chunks)))

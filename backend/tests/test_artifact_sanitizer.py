from app.skills.artifact_sanitizer import sanitize_html, wrap_for_sandboxed_iframe


def test_strips_script_tags():
    raw = "<p>Hello</p><script>alert('xss')</script>"
    cleaned = sanitize_html(raw, max_bytes=10_000)
    assert "<script" not in cleaned
    assert "alert" not in cleaned
    assert "<p>Hello</p>" in cleaned


def test_strips_event_handler_attributes():
    raw = '<img src="x.png" onerror="alert(1)">'
    cleaned = sanitize_html(raw, max_bytes=10_000)
    assert "onerror" not in cleaned


def test_strips_javascript_url():
    raw = '<a href="javascript:alert(1)">click</a>'
    cleaned = sanitize_html(raw, max_bytes=10_000)
    assert "javascript:" not in cleaned


def test_strips_iframe_and_form_tags():
    raw = '<iframe src="evil.com"></iframe><form action="/x"><input></form><p>ok</p>'
    cleaned = sanitize_html(raw, max_bytes=10_000)
    assert "<iframe" not in cleaned
    assert "<form" not in cleaned
    assert "<p>ok</p>" in cleaned


def test_allows_basic_formatting():
    raw = "<h1>Title</h1><p>Some <strong>bold</strong> and <em>italic</em> text.</p><ul><li>one</li></ul>"
    cleaned = sanitize_html(raw, max_bytes=10_000)
    assert "<h1>Title</h1>" in cleaned
    assert "<strong>bold</strong>" in cleaned
    assert "<li>one</li>" in cleaned


def test_truncates_oversized_html():
    raw = "<p>" + ("a" * 1000) + "</p>"
    cleaned = sanitize_html(raw, max_bytes=50)
    assert len(cleaned.encode("utf-8")) <= 200  # bleach output can grow slightly on truncated tags


def test_wrapped_document_has_strict_csp_and_no_script_src():
    doc = wrap_for_sandboxed_iframe("<p>hi</p>")
    assert "script-src 'none'" in doc
    assert "<p>hi</p>" in doc

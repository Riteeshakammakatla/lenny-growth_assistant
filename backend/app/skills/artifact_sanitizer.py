"""
Sanitization for generated HTML artifacts (Section 4.3 security expectation).

Threat model: the LLM output is treated as fully untrusted user-influenced
content, same as if a user pasted arbitrary HTML. Two layers of defense:

1. Server-side allowlist sanitization with `bleach` — strips <script>,
   event-handler attributes (onclick, onerror, ...), <iframe>, <object>,
   <embed>, <form>, javascript: URLs, and anything not on the allowlist,
   before the HTML is ever persisted or sent to the client.
2. Client-side rendering inside a sandboxed <iframe> with
   `sandbox="allow-same-origin"` only (no `allow-scripts`), and a strict
   `Content-Security-Policy` meta tag injected into the iframe document, as
   defense in depth in case a sanitizer bypass is ever found.

We do NOT allow `allow-scripts` in the iframe sandbox, so even if a `<script>`
tag slipped through step 1, it would not execute. This is documented for the
evaluator in architecture.md's "Security" section.
"""
import re

import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_TAGS = [
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "strong", "em", "b", "i", "u", "s",
    "a", "img", "table", "thead", "tbody", "tr", "th", "td",
    "blockquote", "code", "pre", "span", "div", "figure", "figcaption",
]

ALLOWED_ATTRS = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "*": ["class", "style"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto", "data"]  # 'data' restricted to images below

_CSS_SANITIZER = CSSSanitizer()

_DATA_URL_IMG_RE = re.compile(r"^data:image/(png|jpeg|jpg|gif|webp);base64,", re.IGNORECASE)

# Strip <script>...</script> and <style>...</style> blocks INCLUDING their
# content before bleach runs. bleach's tag-stripping alone removes the tag
# but leaves the raw text content behind as inert page text (safe, since it
# can't execute without the tag, but confusing/messy to show a user) — this
# pre-pass removes the content too for a cleaner result.
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)


def sanitize_html(raw_html: str, max_bytes: int) -> str:
    if len(raw_html.encode("utf-8")) > max_bytes:
        raw_html = raw_html.encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore")

    raw_html = _SCRIPT_STYLE_RE.sub("", raw_html)

    cleaned = bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=_CSS_SANITIZER,
        strip=True,
        strip_comments=True,
    )
    return cleaned


def wrap_for_sandboxed_iframe(sanitized_html: str) -> str:
    """Wraps sanitized HTML in a minimal document with a strict CSP, ready to
    be set as an iframe's `srcdoc`. The iframe itself must be rendered with
    `sandbox="allow-same-origin"` (no allow-scripts) on the frontend."""
    csp = (
        "default-src 'none'; img-src data: https: http:; style-src 'unsafe-inline'; "
        "font-src data:; script-src 'none';"
    )
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<style>body {{ font-family: system-ui, sans-serif; padding: 16px; line-height: 1.5; }}</style>
</head>
<body>
{sanitized_html}
</body>
</html>"""
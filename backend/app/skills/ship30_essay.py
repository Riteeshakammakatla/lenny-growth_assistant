"""
Ship 30/30-style essay skill (Core Requirement 4.2).

This is a dedicated, structured skill rather than an unstructured one-off
prompt: the writing principles below are encoded as explicit rules (not
just "write it like Ship 30 for 30"), so behavior is consistent and
reviewable, and can be unit-tested for structural compliance (word count
band, heading presence, etc. — see backend/tests/test_ship30_skill.py).

Principles encoded here, characteristic of the "atomic essay" style popularized
by Ship 30 for 30 (https://www.ship30for30.com/):
1. Strong, specific hook in the first 1-2 sentences — no throat-clearing.
2. One core idea per essay; everything supports that single thesis.
3. Skimmable structure: short paragraphs, headers, bullets, selective bold.
4. Narrative or logical progression (problem -> insight -> implication), not
   a flat list of facts.
5. Concrete specifics (numbers, examples, named tactics) over abstractions.
6. A clear, actionable takeaway at the end — the reader should know what to
   do differently.
7. Conversational, first/second-person voice; short sentences; active verbs.
"""
from app.agent.providers.base import LLMMessage
from app.agent.retrieval import RetrievedChunk

TARGET_WORD_COUNT = 1250
WORD_COUNT_TOLERANCE = 250  # acceptable band: ~1000-1500 words

SHIP30_SYSTEM_PROMPT = f"""You are a ghostwriter trained in the "Ship 30 for 30" atomic essay style.

Turn the CONVERSATION CONTEXT and SOURCE MATERIAL below into a single, polished essay of
approximately {TARGET_WORD_COUNT} words (acceptable range: {TARGET_WORD_COUNT - WORD_COUNT_TOLERANCE}-{TARGET_WORD_COUNT + WORD_COUNT_TOLERANCE} words).

Follow these rules exactly:
1. Open with a strong, specific hook in the first 1-2 sentences. No throat-clearing, no "In this essay I will...".
2. Center the whole essay on ONE clear idea drawn from the source material.
3. Use Markdown formatting: a title (H1), section headings (H2/H3), short paragraphs (2-4 sentences),
   bullet lists where useful, and **selective bold** on key phrases (not entire sentences).
4. Give the essay a narrative or logical arc: problem/tension -> insight -> concrete implication.
5. Use concrete specifics from the source material (names, numbers, named tactics, examples) rather
   than vague generalities.
6. End with a specific, useful takeaway the reader can act on immediately — label it clearly,
   e.g. under a "## Takeaway" heading.
7. Write in a direct, conversational voice. Short sentences. Active verbs. No corporate hedging.
8. Ground every factual claim in the SOURCE MATERIAL below. If the source material is thin, favor
   depth on the point it does support rather than inventing detail — do not fabricate quotes,
   statistics, or company names not present in the source.

SOURCE MATERIAL (from Lenny's Podcast transcripts):
{{context}}
"""


def build_essay_prompt(topic_or_answer: str, retrieved: list[RetrievedChunk]) -> list[LLMMessage]:
    if retrieved:
        context_block = "\n\n".join(
            f"[Episode: {r.episode_title}]\n{r.text}" for r in retrieved
        )
    else:
        context_block = "(No additional transcript excerpts retrieved; rely on the conversation context only.)"

    system = SHIP30_SYSTEM_PROMPT.format(context=context_block)
    user = (
        "Write the essay based on this conversation context / topic:\n\n"
        f"{topic_or_answer}"
    )
    return [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]


def word_count_in_range(text: str) -> bool:
    n = len(text.split())
    return (TARGET_WORD_COUNT - WORD_COUNT_TOLERANCE) <= n <= (TARGET_WORD_COUNT + WORD_COUNT_TOLERANCE)

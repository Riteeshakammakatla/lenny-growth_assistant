"""
Grounded conversational skill (Core Requirement 4.1).

Strategy: retrieve top-k transcript chunks for the latest user turn, inject
them into a system prompt that constrains the model to only use that
context, and explicitly instruct a fallback phrase when context is
insufficient. This is a "retrieve-then-read" RAG pattern rather than
long-context stuffing of full transcripts, which keeps latency and cost
bounded, especially for the local Ollama path.
"""
from dataclasses import dataclass

from app.agent.providers.base import LLMMessage
from app.agent.retrieval import RetrievedChunk

NOT_COVERED_PHRASE = "not covered in the transcripts I have"

SYSTEM_TEMPLATE = """You are the Lenny Growth Assistant, an expert product & growth advisor.

You must answer ONLY using the CONTEXT below, which is excerpted from Lenny's Podcast transcripts.

Rules:
- If the context contains relevant material, answer clearly and cite the episode title(s) you used, inline, like: (Source: {{episode_title}}).
- If the context does NOT contain enough information to answer, say so explicitly using language like "That's {not_covered}" and do not guess or use outside knowledge.
- Never fabricate a source, quote, or statistic that isn't grounded in the context.
- Be concise and structured; use bullets when listing multiple points.

CONTEXT:
{context}
""".format(not_covered=NOT_COVERED_PHRASE, context="{context}")


@dataclass
class GroundedAnswer:
    system_prompt: str
    citations: list[dict]
    has_context: bool


def build_grounded_prompt(retrieved: list[RetrievedChunk]) -> GroundedAnswer:
    if not retrieved:
        context_block = "(No relevant transcript excerpts were found for this question.)"
    else:
        context_block = "\n\n".join(
            f"[Episode: {r.episode_title} | source: {r.source_path} | relevance: {r.score:.2f}]\n{r.text}"
            for r in retrieved
        )

    system_prompt = SYSTEM_TEMPLATE.format(context=context_block)
    citations = [
        {
            "episode_id": r.episode_id,
            "episode_title": r.episode_title,
            "source_path": r.source_path,
            "score": round(r.score, 3),
        }
        for r in retrieved
    ]
    return GroundedAnswer(system_prompt=system_prompt, citations=citations, has_context=bool(retrieved))


def build_messages(system_prompt: str, history: list[LLMMessage], user_message: str) -> list[LLMMessage]:
    return [LLMMessage(role="system", content=system_prompt), *history, LLMMessage(role="user", content=user_message)]

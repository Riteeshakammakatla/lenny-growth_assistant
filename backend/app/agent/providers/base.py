"""
Common interface every LLM provider must implement. The agent layer only
ever talks to this interface, never to Anthropic's or Ollama's SDKs directly,
which is what makes the provider swap a config change instead of a code
change (Core Requirement 3.2).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    latency_ms: int
    raw_error: str | None = None  # set if we degraded gracefully


class LLMProviderError(Exception):
    """Raised when a provider fails in a way callers should handle
    (timeout, connection refused, missing key, etc.)."""


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Send messages, return a completed response. Raise LLMProviderError
        on failure — callers decide fallback behavior."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Cheap check used by /health to report provider availability."""

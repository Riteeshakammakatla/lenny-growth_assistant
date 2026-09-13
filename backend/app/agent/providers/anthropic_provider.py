import time

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agent.providers.base import LLMMessage, LLMProvider, LLMProviderError, LLMResponse
from app.config.settings import get_settings


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise LLMProviderError(
                "ANTHROPIC_API_KEY is not set. Set it in .env or switch LLM_PROVIDER=ollama."
            )
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model
        self._timeout = settings.llm_request_timeout_seconds

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    async def complete(
        self, messages: list[LLMMessage], max_tokens: int, temperature: float
    ) -> LLMResponse:
        system = "\n".join(m.content for m in messages if m.role == "system")
        turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        start = time.monotonic()
        try:
            resp = await self._client.messages.create(
                model=self._model,
                system=system or anthropic.NOT_GIVEN,
                messages=turns,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self._timeout,
            )
        except anthropic.APIError as exc:
            raise LLMProviderError(f"Anthropic API error: {exc}") from exc

        latency_ms = int((time.monotonic() - start) * 1000)
        text = "".join(block.text for block in resp.content if block.type == "text")
        return LLMResponse(text=text, provider=self.name, model=self._model, latency_ms=latency_ms)

    async def health_check(self) -> bool:
        try:
            settings = get_settings()
            return bool(settings.anthropic_api_key)
        except Exception:
            return False

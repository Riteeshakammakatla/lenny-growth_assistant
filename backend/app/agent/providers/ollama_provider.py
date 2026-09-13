import time

import httpx

from app.agent.providers.base import LLMMessage, LLMProvider, LLMProviderError, LLMResponse
from app.config.settings import get_settings


class OllamaProvider(LLMProvider):
    """Local model provider — the mandatory path for the submitted demo.

    Uses Ollama's OpenAI-compatible-ish /api/chat endpoint directly (no extra
    dependency) so the only external requirement is a running `ollama serve`
    with the configured model pulled (`ollama pull llama3.1:8b`).
    """

    name = "ollama"

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._timeout = settings.ollama_timeout_seconds

    async def complete(
        self, messages: list[LLMMessage], max_tokens: int, temperature: float
    ) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(f"{self._base_url}/api/chat", json=payload)
                resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise LLMProviderError(
                f"Could not reach Ollama at {self._base_url}. Is `ollama serve` running and is "
                f"'{self._model}' pulled (`ollama pull {self._model}`)?"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                f"Ollama timed out after {self._timeout}s. Try a smaller model or shorter context."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise LLMProviderError(f"Ollama returned an error: {exc.response.text}") from exc

        latency_ms = int((time.monotonic() - start) * 1000)
        data = resp.json()
        text = data.get("message", {}).get("content", "")
        return LLMResponse(text=text, provider=self.name, model=self._model, latency_ms=latency_ms)

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

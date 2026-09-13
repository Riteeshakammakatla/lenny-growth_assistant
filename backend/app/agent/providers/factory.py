from app.agent.providers.anthropic_provider import AnthropicProvider
from app.agent.providers.base import LLMProvider
from app.agent.providers.ollama_provider import OllamaProvider
from app.config.settings import get_settings


def get_provider(override: str | None = None) -> LLMProvider:
    """Returns the active LLM provider. `override` lets a single request pick
    a different provider than the default (e.g. a per-session choice stored
    on ChatSession.llm_provider), without touching global config."""
    settings = get_settings()
    provider_name = override or settings.llm_provider

    if provider_name == "anthropic":
        return AnthropicProvider()
    if provider_name == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown LLM_PROVIDER '{provider_name}'. Use 'anthropic' or 'ollama'.")

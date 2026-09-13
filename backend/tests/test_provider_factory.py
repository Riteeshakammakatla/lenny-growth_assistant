import pytest

from app.agent.providers.anthropic_provider import AnthropicProvider
from app.agent.providers.base import LLMProviderError
from app.agent.providers.factory import get_provider
from app.agent.providers.ollama_provider import OllamaProvider
from app.config.settings import get_settings


def test_factory_returns_ollama_by_default(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    get_settings.cache_clear()
    provider = get_provider()
    assert isinstance(provider, OllamaProvider)
    get_settings.cache_clear()


def test_factory_returns_anthropic_when_configured(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    get_settings.cache_clear()
    provider = get_provider()
    assert isinstance(provider, AnthropicProvider)
    get_settings.cache_clear()


def test_factory_override_wins_over_default(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    get_settings.cache_clear()
    provider = get_provider(override="ollama")
    assert isinstance(provider, OllamaProvider)
    get_settings.cache_clear()


def test_anthropic_provider_raises_without_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    get_settings.cache_clear()
    with pytest.raises(LLMProviderError):
        get_provider()
    get_settings.cache_clear()


def test_unknown_provider_raises_value_error(monkeypatch):
    get_settings.cache_clear()
    with pytest.raises(ValueError):
        get_provider(override="not-a-real-provider")
    get_settings.cache_clear()

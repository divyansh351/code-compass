"""Unit tests for LLM abstraction and privacy guarantees."""

import pytest
from unittest.mock import patch

from compass.config.settings import CompassConfig
from compass.llm.providers import NoneProvider, OllamaProvider, get_llm_provider


def test_none_provider_performs_no_network_requests():
    """Verify NoneProvider default produces no network access."""
    provider = NoneProvider()
    res = provider.generate("Test prompt", "Test context")
    assert res == ""


def test_provider_factory_defaults_to_none():
    config = CompassConfig()
    provider = get_llm_provider(config)
    assert isinstance(provider, NoneProvider)


def test_ollama_provider_direct_endpoint_format():
    config = CompassConfig()
    config.llm.provider = "ollama"
    config.llm.model = "codellama"
    provider = get_llm_provider(config)
    assert isinstance(provider, OllamaProvider)
    assert provider.model == "codellama"
    assert provider.api_base == "http://localhost:11434"

"""LLM Provider implementations with local-first defaults."""

import logging
from typing import Optional
from compass.config.settings import CompassConfig
from compass.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class NoneProvider(LLMProvider):
    """Default provider performing zero network calls. Deterministic operations only."""

    def generate(self, prompt: str, context: str = "") -> str:
        logger.debug("NoneProvider invoked: skipping LLM generation.")
        return ""


class OllamaProvider(LLMProvider):
    """Direct local communication with user's Ollama instance (localhost:11434)."""

    def __init__(self, model: Optional[str] = None, api_base: str = "http://localhost:11434"):
        self.model = model or "llama3"
        self.api_base = api_base.rstrip("/")

    def generate(self, prompt: str, context: str = "") -> str:
        try:
            import urllib.request
            import json

            url = f"{self.api_base}/api/generate"
            full_prompt = f"Context:\n{context}\n\nPrompt:\n{prompt}" if context else prompt
            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data.get("response", "")
        except Exception as e:
            logger.warning(f"Ollama generation failed: {e}")
            return f"[Ollama Error: {e}]"


class OpenAIProvider(LLMProvider):
    """Direct communication with OpenAI API using the user's direct API key."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, context: str = "") -> str:
        raise NotImplementedError(
            "OpenAIProvider is an extension point. Set llm.provider: none for local-first execution."
        )


class AnthropicProvider(LLMProvider):
    """Direct communication with Anthropic API using the user's direct API key."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, context: str = "") -> str:
        raise NotImplementedError(
            "AnthropicProvider is an extension point. Set llm.provider: none for local-first execution."
        )


class GeminiProvider(LLMProvider):
    """Direct communication with Google Gemini API using the user's direct API key."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-pro"):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, context: str = "") -> str:
        raise NotImplementedError(
            "GeminiProvider is an extension point. Set llm.provider: none for local-first execution."
        )


def get_llm_provider(config: CompassConfig) -> LLMProvider:
    """Factory creating the appropriate configured LLM provider."""
    provider_name = config.llm.provider.lower()
    if provider_name == "none":
        return NoneProvider()
    elif provider_name == "ollama":
        return OllamaProvider(
            model=config.llm.model,
            api_base=config.llm.api_base or "http://localhost:11434",
        )
    elif provider_name == "openai":
        return OpenAIProvider(model=config.llm.model or "gpt-4o")
    elif provider_name == "anthropic":
        return AnthropicProvider(model=config.llm.model or "claude-3-5-sonnet-20241022")
    elif provider_name == "gemini":
        return GeminiProvider(model=config.llm.model or "gemini-1.5-pro")
    else:
        return NoneProvider()

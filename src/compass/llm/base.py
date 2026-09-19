"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface for local or remote LLM backends."""

    @abstractmethod
    def generate(self, prompt: str, context: str = "") -> str:
        """Generate text from prompt and context. Must run directly without proxy."""
        pass

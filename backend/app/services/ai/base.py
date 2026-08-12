from abc import ABC, abstractmethod
from typing import Any
from .schemas import GenerationRequest, GenerationResponse

class BaseAIProvider(ABC):
    """
    Abstract base class for all AI Providers (Gemini, OpenAI, Anthropic, Ollama).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the unique identifier for the provider (e.g., 'gemini', 'openai')."""
        pass

    @abstractmethod
    async def generate_structured(self, request: GenerationRequest) -> GenerationResponse:
        """
        Takes a standardized GenerationRequest and returns a GenerationResponse containing the parsed Pydantic output.
        Must accurately raise the custom AIProviderError exceptions (AuthenticationError, RateLimitError, etc.) on failure.
        """
        pass

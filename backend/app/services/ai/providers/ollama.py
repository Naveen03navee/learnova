import httpx
import json
import asyncio
from pydantic import ValidationError

from app.core.config import settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.schemas import GenerationRequest, GenerationResponse
from app.services.ai.errors import (
    AuthenticationError,
    InvalidRequestError,
    RateLimitError,
    TimeoutError,
    TemporaryServerError,
    ProviderUnavailableError,
    MalformedResponseError,
    UnknownProviderError
)

class OllamaProvider(BaseAIProvider):
    def __init__(self, model: str = "nemotron-3-nano:4b", provider_name: str = "ollama"):
        self.model = model
        self._provider_name = provider_name
        self.base_url = settings.OLLAMA_BASE_URL.rstrip('/') if settings.OLLAMA_BASE_URL else None
        # Reusable client — created once per Python process/worker.
        # Connection pooling and keep-alive are managed by httpx internally.
        # NOTE: On Render, each gunicorn worker has its own client instance;
        # the client is NOT shared across processes.
        self._client = httpx.AsyncClient(
            timeout=settings.PROVIDER_TIMEOUT_SECONDS,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def aclose(self) -> None:
        """Gracefully drain and close the underlying connection pool."""
        await self._client.aclose()

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def _check_availability(self):
        """Pings the Ollama server to ensure it is running."""
        try:
            res = await self._client.get(f"{self.base_url}/api/version", timeout=3.0)
            res.raise_for_status()
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError):
            raise ProviderUnavailableError(f"Ollama server is unreachable at {self.base_url}")

    async def generate_structured(self, request: GenerationRequest) -> GenerationResponse:
        if not self.base_url:
            raise ProviderUnavailableError("OLLAMA_BASE_URL is not configured.")

        # Convert Pydantic model to JSON schema for structured output
        json_schema = request.response_schema.model_json_schema()

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt}
            ],
            "stream": False,
            "format": json_schema,
            "options": {
                "temperature": request.temperature
            }
        }

        # 1. Ensure Ollama is running before starting generation
        await self._check_availability()

        # 2. Call the chat endpoint
        try:
            response = await self._client.post(f"{self.base_url}/api/chat", json=payload)
        except httpx.TimeoutException:
            raise TimeoutError("Ollama request timed out.")
        except httpx.ConnectError:
            raise ProviderUnavailableError("Lost connection to Ollama server.")
        except Exception as e:
            raise UnknownProviderError(f"Unexpected network error with Ollama: {e}")

        # 3. Handle response
        if response.status_code == 404:
            raise InvalidRequestError(f"Ollama model '{self.model}' not found.")
        elif response.status_code == 400:
            raise InvalidRequestError(f"Ollama rejected the request: {response.text}")
        elif response.status_code >= 500:
            raise TemporaryServerError(f"Ollama server error: {response.text}")
        elif response.status_code != 200:
            raise UnknownProviderError(f"Ollama returned unexpected status {response.status_code}: {response.text}")

        try:
            data = response.json()
            message_content = data.get("message", {}).get("content", "")
            if not message_content:
                raise MalformedResponseError("Ollama returned an empty response.")
        except json.JSONDecodeError:
            raise MalformedResponseError("Ollama returned invalid JSON payload.")

        # Parse the structured JSON content into the Pydantic model
        try:
            parsed_data = request.response_schema.model_validate_json(message_content)
        except ValidationError as ve:
            raise MalformedResponseError(f"Failed to parse Ollama output to schema: {ve}\nRaw Output: {message_content}")

        return GenerationResponse(
            provider_name=self.provider_name,
            model_name=self.model,
            parsed_output=parsed_data,
            raw_response=data
        )


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

class GroqProvider(BaseAIProvider):
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.model = model
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    @property
    def provider_name(self) -> str:
        return "groq"

    async def generate_structured(self, request: GenerationRequest) -> GenerationResponse:
        if not settings.GROQ_API_KEY:
            raise AuthenticationError("GROQ_API_KEY is not configured.")

        # Convert Pydantic model to JSON schema dict
        json_schema = request.response_schema.model_json_schema()
        schema_str = json.dumps(json_schema, indent=2)

        # Groq json_object mode requires the schema to be explicitly defined in the prompt
        system_prompt = f"{request.system_prompt}\n\nYou must output a JSON object strictly matching this JSON schema:\n{schema_str}"

        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.user_prompt}
            ],
            "temperature": request.temperature,
            "response_format": {"type": "json_object"}
        }

        async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
            try:
                response = await client.post(self.api_url, headers=headers, json=payload)
            except httpx.TimeoutException:
                raise TimeoutError("Groq request timed out.")
            except httpx.ConnectError:
                raise ProviderUnavailableError("Lost connection to Groq API.")
            except Exception as e:
                raise UnknownProviderError(f"Unexpected network error with Groq: {e}")

        # Handle HTTP errors
        if response.status_code == 401:
            raise AuthenticationError("Invalid Groq API key.")
        elif response.status_code == 429:
            raise RateLimitError(f"Groq rate limit exceeded: {response.text}")
        elif response.status_code == 400:
            raise InvalidRequestError(f"Invalid request to Groq: {response.text}")
        elif response.status_code >= 500:
            raise TemporaryServerError(f"Groq server error: {response.text}")
        elif response.status_code != 200:
            raise UnknownProviderError(f"Groq returned unexpected status {response.status_code}: {response.text}")

        # Parse response
        try:
            data = response.json()
            message_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not message_content:
                raise MalformedResponseError("Groq returned an empty response.")
        except json.JSONDecodeError:
            raise MalformedResponseError("Groq returned invalid JSON payload.")

        # Parse the structured JSON content into the Pydantic model
        # Strip markdown code blocks if the LLM wrapped it
        cleaned_content = message_content.strip()
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content[7:]
        elif cleaned_content.startswith("```"):
            cleaned_content = cleaned_content[3:]
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]
        
        # Try to extract just the block if prefixed with text
        if "```json" in message_content:
            try:
                cleaned_content = message_content.split("```json")[1].split("```")[0].strip()
            except IndexError:
                pass
        elif "```" in message_content:
            try:
                cleaned_content = message_content.split("```")[1].split("```")[0].strip()
            except IndexError:
                pass
        else:
            # Fallback: Extract everything from the first '{' to the last '}'
            start_idx = cleaned_content.find('{')
            end_idx = cleaned_content.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                cleaned_content = cleaned_content[start_idx:end_idx+1]

        cleaned_content = cleaned_content.strip()

        try:
            parsed_data = request.response_schema.model_validate_json(cleaned_content)
        except ValidationError as ve:
            raise MalformedResponseError(f"Failed to parse Groq output to schema: {ve}\nRaw Output: {message_content}")

        return GenerationResponse(
            provider_name=self.provider_name,
            model_name=self.model,
            parsed_output=parsed_data,
            raw_response=data
        )

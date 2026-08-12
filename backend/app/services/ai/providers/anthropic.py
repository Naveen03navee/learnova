import json
import asyncio
from anthropic import AsyncAnthropic, APIError, APIConnectionError, RateLimitError as AnthropicRateLimitError, AuthenticationError as AnthropicAuthenticationError, BadRequestError
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

class AnthropicProvider(BaseAIProvider):
    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        self.model = model
        self.client = None
        if settings.ANTHROPIC_API_KEY:
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def generate_structured(self, request: GenerationRequest) -> GenerationResponse:
        if not self.client:
            raise AuthenticationError("Anthropic API key is not configured.")

        # Convert pydantic schema to JSON schema for Anthropic Tools
        schema = request.response_schema.model_json_schema()
        
        tools = [
            {
                "name": "generate_response",
                "description": "Generate the requested structured output.",
                "input_schema": schema
            }
        ]

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=request.system_prompt,
                messages=[{"role": "user", "content": request.user_prompt}],
                tools=tools,
                tool_choice={"type": "tool", "name": "generate_response"},
                temperature=request.temperature,
                timeout=settings.PROVIDER_TIMEOUT_SECONDS
            )

            # Find the tool use block
            tool_use = next((block for block in response.content if block.type == 'tool_use' and block.name == 'generate_response'), None)
            
            if not tool_use:
                raise MalformedResponseError("Anthropic did not return the requested tool call.")

            # Parse the tool inputs into the Pydantic model
            try:
                parsed_data = request.response_schema.model_validate(tool_use.input)
            except ValidationError as ve:
                raise MalformedResponseError(f"Failed to parse Anthropic tool input to schema: {ve}")

            return GenerationResponse(
                provider_name=self.provider_name,
                model_name=self.model,
                parsed_output=parsed_data,
                raw_response=response.model_dump()
            )

        except AnthropicAuthenticationError as e:
            raise AuthenticationError(f"Anthropic authentication failed: {e}")
        except AnthropicRateLimitError as e:
            raise RateLimitError(f"Anthropic rate limit exceeded: {e}")
        except BadRequestError as e:
            raise InvalidRequestError(f"Invalid request to Anthropic: {e}")
        except APIConnectionError as e:
            raise ProviderUnavailableError(f"Failed to connect to Anthropic: {e}")
        except APIError as e:
            if e.status_code and e.status_code >= 500:
                raise TemporaryServerError(f"Anthropic server error: {e}")
            raise UnknownProviderError(f"Anthropic API error: {e}")
        except asyncio.TimeoutError:
            raise TimeoutError("Anthropic request timed out.")
        except Exception as e:
            if isinstance(e, MalformedResponseError):
                raise
            raise UnknownProviderError(f"Unexpected error with Anthropic: {e}")

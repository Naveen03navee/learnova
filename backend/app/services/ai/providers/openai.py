import json
import asyncio
from openai import AsyncOpenAI
from openai import APIError, APIConnectionError, RateLimitError as OpenAIRateLimitError, AuthenticationError as OpenAIAuthenticationError, BadRequestError
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

class OpenAIProvider(BaseAIProvider):
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate_structured(self, request: GenerationRequest) -> GenerationResponse:
        if not self.client:
            raise AuthenticationError("OpenAI API key is not configured.")

        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt}
        ]

        try:
            # We use parse() wrapper if available, or just beta.chat.completions.parse
            # We must use beta.chat.completions.parse to enforce pydantic schema return
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=request.response_schema,
                temperature=request.temperature,
                timeout=settings.PROVIDER_TIMEOUT_SECONDS
            )

            # Extract the parsed object
            message = response.choices[0].message
            if message.parsed:
                parsed_data = message.parsed
            else:
                # If parsed is None, the model might have refused or failed
                if message.refusal:
                    raise MalformedResponseError(f"OpenAI refused to generate response: {message.refusal}")
                raise MalformedResponseError("OpenAI returned an empty parsed response.")

            return GenerationResponse(
                provider_name=self.provider_name,
                model_name=self.model,
                parsed_output=parsed_data,
                raw_response=response.model_dump()
            )

        except OpenAIAuthenticationError as e:
            raise AuthenticationError(f"OpenAI authentication failed: {e}")
        except OpenAIRateLimitError as e:
            raise RateLimitError(f"OpenAI rate limit exceeded: {e}")
        except BadRequestError as e:
            raise InvalidRequestError(f"Invalid request to OpenAI: {e}")
        except APIConnectionError as e:
            raise ProviderUnavailableError(f"Failed to connect to OpenAI: {e}")
        except APIError as e:
            if e.status_code and e.status_code >= 500:
                raise TemporaryServerError(f"OpenAI server error: {e}")
            raise UnknownProviderError(f"OpenAI API error: {e}")
        except ValidationError as e:
            raise MalformedResponseError(f"Failed to parse OpenAI output to schema: {e}")
        except asyncio.TimeoutError:
            raise TimeoutError("OpenAI request timed out.")
        except Exception as e:
            # Re-raise our custom exceptions
            if isinstance(e, MalformedResponseError):
                raise
            raise UnknownProviderError(f"Unexpected error with OpenAI: {e}")

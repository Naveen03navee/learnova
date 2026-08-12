import os
import json
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import ValidationError
import asyncio
import traceback

from app.core.config import settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.schemas import GenerationRequest, GenerationResponse
from app.services.ai.errors import (
    AuthenticationError,
    InvalidRequestError,
    RateLimitError,
    TimeoutError,
    TemporaryServerError,
    MalformedResponseError,
    UnknownProviderError
)

class GeminiProvider(BaseAIProvider):
    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model
        self.client = None
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(
                api_key=settings.GEMINI_API_KEY, 
                http_options={'timeout': settings.PROVIDER_TIMEOUT_SECONDS * 1000}
            )

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate_structured(self, request: GenerationRequest) -> GenerationResponse:
        if not self.client:
            raise AuthenticationError("Gemini API key is not configured.")

        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=request.system_prompt + "\n\n" + request.user_prompt)])
        ]
        
        schema_dict = request.response_schema.model_json_schema()
        
        def remove_additional_properties(s):
            if isinstance(s, dict):
                s.pop("additionalProperties", None)
                for v in s.values():
                    remove_additional_properties(v)
            elif isinstance(s, list):
                for item in s:
                    remove_additional_properties(item)
                    
        remove_additional_properties(schema_dict)

        config = types.GenerateContentConfig(
            temperature=request.temperature,
            response_mime_type="application/json",
            response_schema=schema_dict,
        )

        try:
            # google-genai client methods are synchronous by default unless we use the async client.
            # We will use asyncio.to_thread for the synchronous generate_content.
            # Wait, google-genai has an `aio` property for async!
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            
            response_text = response.text
            if not response_text:
                raise MalformedResponseError("Gemini returned an empty response.")
            
            # Parse the JSON string into the Pydantic model
            try:
                parsed_data = request.response_schema.model_validate_json(response_text)
            except ValidationError as ve:
                raise MalformedResponseError(f"Failed to parse Gemini output to schema: {ve}")

            return GenerationResponse(
                provider_name=self.provider_name,
                model_name=self.model,
                parsed_output=parsed_data,
                raw_response=response_text
            )

        except APIError as e:
            # Handle specific Google GenAI errors
            err_code = e.code
            if err_code == 401 or err_code == 403:
                raise AuthenticationError(f"Gemini authentication failed: {e.message}")
            elif err_code == 429:
                raise RateLimitError(f"Gemini rate limit exceeded: {e.message}")
            elif err_code == 400:
                raise InvalidRequestError(f"Invalid request to Gemini: {e.message}")
            elif err_code >= 500:
                raise TemporaryServerError(f"Gemini server error ({err_code}): {e.message}")
            else:
                raise UnknownProviderError(f"Unknown Gemini API error: {e}")
        except asyncio.TimeoutError:
            raise TimeoutError("Gemini request timed out.")
        except MalformedResponseError:
            raise
        except Exception as e:
            err_msg = traceback.format_exc()
            raise UnknownProviderError(f"Unexpected error with Gemini: {str(e)}\n{err_msg}")

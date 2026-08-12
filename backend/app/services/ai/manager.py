import logging
from typing import Dict, List, Type
from pydantic import BaseModel

from app.core.config import settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.schemas import GenerationRequest, GenerationResponse
from app.services.ai.errors import FallbackEligibleError, NonFallbackError, UnknownProviderError
from app.services.ai.providers import GeminiProvider, OpenAIProvider, AnthropicProvider, OllamaProvider, GroqProvider

logger = logging.getLogger(__name__)

class AIManager:
    def __init__(self):
        # Initialize providers lazily or upfront. For simplicity, we initialize them upfront.
        self.providers: Dict[str, BaseAIProvider] = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "ollama": OllamaProvider(),
            "groq": GroqProvider()
        }
        
        # Use dynamic fallback chain from settings
        self.fallback_chain = [p.strip() for p in settings.AI_FALLBACK_CHAIN.split(",") if p.strip()]

    async def generate(self, primary_provider_name: str, request: GenerationRequest) -> GenerationResponse:
        """
        Attempts to generate a response using the primary provider. 
        If a FallbackEligibleError occurs, cascades down the fallback chain.
        Ensures GENERATION_MAX_TOTAL_LLM_CALLS is respected.
        """
        # Determine the sequence of providers to try
        chain_to_try = self._build_execution_chain(primary_provider_name)
        
        calls_made = 0
        max_calls = settings.GENERATION_MAX_TOTAL_LLM_CALLS
        last_error = None

        for provider_name in chain_to_try:
            if calls_made >= max_calls:
                logger.error(f"Exceeded GENERATION_MAX_TOTAL_LLM_CALLS ({max_calls}). Aborting.")
                break

            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"Provider {provider_name} is not registered. Skipping.")
                continue

            logger.info(f"Attempting generation with provider: {provider_name}")
            
            provider_attempts = 0
            max_provider_attempts = 1
            
            while provider_attempts < max_provider_attempts:
                if calls_made >= max_calls:
                    logger.error(f"Exceeded GENERATION_MAX_TOTAL_LLM_CALLS ({max_calls}). Aborting.")
                    break
                    
                try:
                    calls_made += 1
                    provider_attempts += 1
                    import time
                    start_time = time.time()
                    # Note: The context has already been strictly bounded before entering AIManager.
                    response = await provider.generate_structured(request)
                    response.latency_ms = (time.time() - start_time) * 1000
                    logger.info(f"Successfully generated response with {provider_name} in {response.latency_ms:.0f}ms")
                    return response
                    
                except NonFallbackError as e:
                    # E.g. AuthenticationError, InvalidRequestError
                    logger.error(f"Non-fallback error encountered with {provider_name}: {e}. Aborting.")
                    raise e
                    
                except FallbackEligibleError as e:
                    # E.g. TimeoutError, RateLimitError, MalformedResponseError, ProviderUnavailableError
                    last_error = e
                    if provider_attempts < max_provider_attempts:
                        backoff = 2 ** provider_attempts # 2s, 4s
                        logger.warning(f"Transient error with {provider_name}: {e}. Retrying in {backoff}s (Attempt {provider_attempts}/{max_provider_attempts})")
                        import asyncio
                        await asyncio.sleep(backoff)
                    else:
                        logger.warning(f"Exhausted {max_provider_attempts} attempts with {provider_name}: {e}. Trying next provider in chain.")
                    
                except Exception as e:
                    # Safety net for anything unrecognized. Let's fallback to the next provider.
                    logger.error(f"Unknown exception with {provider_name}: {e}. Trying next provider in chain.")
                    last_error = UnknownProviderError(str(e))
                    break
            
            if calls_made >= max_calls:
                break

        # If we exit the loop, all attempted providers failed (or we hit max calls)
        error_msg = f"All providers in the fallback chain failed. Last error: {last_error}"
        logger.error(error_msg)
        
        if last_error:
            raise last_error
        else:
            raise Exception(error_msg)

    def _build_execution_chain(self, primary_name: str) -> List[str]:
        """
        Constructs the sequence of providers to attempt. 
        Primary first, then the remaining fallback chain in order (omitting the primary).
        """
        primary_name = primary_name.lower().strip()
        chain = [primary_name]
        
        for p in self.fallback_chain:
            if p != primary_name:
                chain.append(p)
                
        return chain

# Create a singleton instance for use across the application
ai_manager = AIManager()

import logging
from typing import Dict, List, Type, Callable, Awaitable, Optional
from uuid import UUID
import asyncio
import time
from pydantic import BaseModel

from app.core.config import settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.schemas import GenerationRequest, GenerationResponse
from app.services.ai.errors import FallbackEligibleError, NonFallbackError, UnknownProviderError
from app.services.ai.providers import GeminiProvider, OpenAIProvider, AnthropicProvider, OllamaProvider, GroqProvider
from app.schemas.generation import GenerationEvent, EventType

logger = logging.getLogger(__name__)

class AIManager:
    def __init__(self):
        # Initialize providers lazily or upfront. For simplicity, we initialize them upfront.
        self.providers: Dict[str, BaseAIProvider] = {
            "gemini": GeminiProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "ollama-nemotron": OllamaProvider(model="qwen2.5:7b", provider_name="ollama-nemotron"),
            "ollama-qwen3": OllamaProvider(model="qwen3:8b", provider_name="ollama-qwen3"),
            "groq": GroqProvider()
        }
        
        # Use dynamic fallback chain from settings
        self.fallback_chain = [p.strip() for p in settings.AI_FALLBACK_CHAIN.split(",") if p.strip()]

    async def generate(
        self, 
        primary_provider_name: str, 
        request: GenerationRequest,
        session_id: Optional[UUID] = None,
        on_event: Optional[Callable[[GenerationEvent], Awaitable[None]]] = None,
        check_cancelled: Optional[Callable[[], bool]] = None
    ) -> GenerationResponse:
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

        async def _safe_emit(event: GenerationEvent):
            if on_event and session_id:
                try:
                    await on_event(event)
                except Exception as ex:
                    logger.warning(f"Failed to emit observability event: {ex}")
                    
        def _abort_if_cancelled():
            if check_cancelled and check_cancelled():
                from app.services.generation.orchestrator import GenerationCancelledError
                raise GenerationCancelledError("GENERATION_CANCELLED")

        for provider_idx, provider_name in enumerate(chain_to_try):
            _abort_if_cancelled()
            if calls_made >= max_calls:
                logger.error(f"Exceeded GENERATION_MAX_TOTAL_LLM_CALLS ({max_calls}). Aborting.")
                break

            provider = self.providers.get(provider_name)
            if not provider:
                logger.warning(f"Provider {provider_name} is not registered. Skipping.")
                continue

            logger.info(f"Attempting generation with provider: {provider_name}")
            await _safe_emit(GenerationEvent(
                session_id=session_id,
                event_type=EventType.PROVIDER_START,
                status="running",
                provider=provider_name,
                message=f"{provider_name.capitalize()} request started"
            ))
            
            provider_attempts = 0
            max_provider_attempts = 1
            
            while provider_attempts < max_provider_attempts:
                _abort_if_cancelled()
                if calls_made >= max_calls:
                    logger.error(f"Exceeded GENERATION_MAX_TOTAL_LLM_CALLS ({max_calls}). Aborting.")
                    break
                    
                try:
                    calls_made += 1
                    provider_attempts += 1
                    start_time = time.time()
                    # Note: The context has already been strictly bounded before entering AIManager.
                    response = await provider.generate_structured(request)
                    response.latency_ms = (time.time() - start_time) * 1000
                    logger.info(f"Successfully generated response with {provider_name} in {response.latency_ms:.0f}ms")
                    
                    event_type = EventType.FALLBACK_SUCCESS if provider_idx > 0 else EventType.PROVIDER_SUCCESS
                    await _safe_emit(GenerationEvent(
                        session_id=session_id,
                        event_type=event_type,
                        status="running",
                        provider=provider_name,
                        message=f"{provider_name.capitalize()} completed successfully in {response.latency_ms/1000:.1f}s"
                    ))
                    return response
                    
                except NonFallbackError as e:
                    # E.g. AuthenticationError, InvalidRequestError
                    logger.error(f"Non-fallback error encountered with {provider_name}: {e}. Aborting.")
                    await _safe_emit(GenerationEvent(
                        session_id=session_id,
                        event_type=EventType.PROVIDER_ERROR,
                        status="error",
                        provider=provider_name,
                        message=f"{provider_name.capitalize()} request failed"
                    ))
                    raise e
                    
                except FallbackEligibleError as e:
                    _abort_if_cancelled()
                    # E.g. TimeoutError, RateLimitError, MalformedResponseError, ProviderUnavailableError
                    last_error = e
                    retry_after = getattr(e, "retry_after_seconds", None)
                    quota_exhausted = getattr(e, "quota_exhausted", False)
                    
                    if quota_exhausted:
                        evt_type = EventType.QUOTA_EXCEEDED
                        msg = f"{provider_name.capitalize()} daily quota has been exhausted"
                        status_val = "error"
                    elif retry_after:
                        evt_type = EventType.RATE_LIMIT
                        msg = f"{provider_name.capitalize()} rate limit reached — retry available in {retry_after} seconds"
                        status_val = "rate_limited"
                    else:
                        evt_type = EventType.PROVIDER_ERROR
                        msg = f"{provider_name.capitalize()} request failed"
                        status_val = "running"
                        
                    await _safe_emit(GenerationEvent(
                        session_id=session_id,
                        event_type=evt_type,
                        status=status_val,
                        provider=provider_name,
                        message=msg,
                        retry_after_seconds=retry_after
                    ))

                    if quota_exhausted:
                        logger.warning(f"Exhausted quota with {provider_name}: {e}. Trying next provider in chain.")
                        if provider_idx < len(chain_to_try) - 1:
                            _abort_if_cancelled()
                            next_provider = chain_to_try[provider_idx + 1]
                            await _safe_emit(GenerationEvent(
                                session_id=session_id,
                                event_type=EventType.PROVIDER_FALLBACK,
                                status="fallback",
                                provider=provider_name,
                                message=f"{provider_name.capitalize()} unavailable — switching to {next_provider.capitalize()}"
                            ))
                        break

                    if provider_attempts < max_provider_attempts:
                        backoff = 2 ** provider_attempts # 2s, 4s
                        logger.warning(f"Transient error with {provider_name}: {e}. Retrying in {backoff}s (Attempt {provider_attempts}/{max_provider_attempts})")
                        await _safe_emit(GenerationEvent(
                            session_id=session_id,
                            event_type=EventType.PROVIDER_RETRY,
                            status="running",
                            provider=provider_name,
                            message=f"Retrying {provider_name.capitalize()} in {backoff} seconds"
                        ))
                        await asyncio.sleep(backoff)
                        _abort_if_cancelled()
                    else:
                        logger.warning(f"Exhausted {max_provider_attempts} attempts with {provider_name}: {e}. Trying next provider in chain.")
                        # Check if there is a next provider
                        if provider_idx < len(chain_to_try) - 1:
                            _abort_if_cancelled()
                            next_provider = chain_to_try[provider_idx + 1]
                            await _safe_emit(GenerationEvent(
                                session_id=session_id,
                                event_type=EventType.PROVIDER_FALLBACK,
                                status="fallback",
                                provider=provider_name,
                                message=f"{provider_name.capitalize()} unavailable — switching to {next_provider.capitalize()}"
                            ))
                    
                except Exception as e:
                    from app.services.generation.orchestrator import GenerationCancelledError
                    if isinstance(e, GenerationCancelledError):
                        raise
                    # Safety net for anything unrecognized. Let's fallback to the next provider.
                    logger.error(f"Unknown exception with {provider_name}: {e}. Trying next provider in chain.")
                    last_error = UnknownProviderError("Internal error")
                    
                    await _safe_emit(GenerationEvent(
                        session_id=session_id,
                        event_type=EventType.PROVIDER_ERROR,
                        status="running",
                        provider=provider_name,
                        message=f"{provider_name.capitalize()} encountered an unexpected error"
                    ))
                        
                    if provider_idx < len(chain_to_try) - 1:
                        _abort_if_cancelled()
                        next_provider = chain_to_try[provider_idx + 1]
                        await _safe_emit(GenerationEvent(
                            session_id=session_id,
                            event_type=EventType.PROVIDER_FALLBACK,
                            status="fallback",
                            provider=provider_name,
                            message=f"{provider_name.capitalize()} unavailable — switching to {next_provider.capitalize()}"
                        ))
                    break
            
            if calls_made >= max_calls:
                break

        # If we exit the loop, all attempted providers failed (or we hit max calls)
        error_msg = f"All available AI providers failed."
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

    async def aclose_clients(self) -> None:
        """
        Gracefully drain HTTP connection pools for providers that use a
        lifecycle-managed httpx.AsyncClient (currently Groq and Ollama).

        Call this from the FastAPI lifespan shutdown hook so connections are
        not leaked when the process exits.

        NOTE: Each Render worker process runs its own AIManager instance;
        connection pools are per-process and not shared across workers.
        """
        for name, provider in self.providers.items():
            if hasattr(provider, "aclose"):
                try:
                    await provider.aclose()
                    logger.info(f"AI provider '{name}' HTTP client closed.")
                except Exception as e:
                    logger.warning(f"Error closing AI provider '{name}' client: {e}")

# Create a singleton instance for use across the application
ai_manager = AIManager()

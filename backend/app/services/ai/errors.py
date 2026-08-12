class AIProviderError(Exception):
    """Base exception for all AI provider errors."""
    pass

class FallbackEligibleError(AIProviderError):
    """Base exception for errors that should trigger a fallback."""
    pass

class NonFallbackError(AIProviderError):
    """Base exception for errors that should NOT trigger a fallback."""
    pass

# --- Fallback Eligible Errors (Transient / Provider-side) ---

class RateLimitError(FallbackEligibleError):
    """Raised when the provider enforces a rate limit or quota restriction."""
    pass

class TimeoutError(FallbackEligibleError):
    """Raised when the provider request times out."""
    pass

class ProviderUnavailableError(FallbackEligibleError):
    """Raised when the provider server is down or unreachable (e.g., Ollama not running)."""
    pass

class TemporaryServerError(FallbackEligibleError):
    """Raised when the provider returns a 5xx error."""
    pass

class MalformedResponseError(FallbackEligibleError):
    """Raised when the provider's response does not match the requested schema."""
    pass

# --- Non-Fallback Errors (Application-side / Configuration) ---

class AuthenticationError(FallbackEligibleError):
    """Raised when the API key is invalid or unauthorized."""
    pass

class InvalidRequestError(FallbackEligibleError):
    """Raised when the prompt, parameters, or schema is rejected as invalid by the provider."""
    pass

class UnsupportedModelError(NonFallbackError):
    """Raised when the requested model or configuration is not supported."""
    pass

class UnknownProviderError(FallbackEligibleError):
    """Raised when an unrecognized error occurs that we cannot safely classify, falling back as a precaution."""
    pass

from app.core.config import settings

def get_primary_provider_name(difficulty: str) -> str:
    """
    Returns the configured primary provider name for a given difficulty level.
    Expects difficulty to be one of 'easy', 'medium', 'hard'.
    """
    difficulty = difficulty.lower().strip()
    if difficulty == "easy":
        return settings.AI_PROVIDER_EASY
    elif difficulty == "medium":
        return settings.AI_PROVIDER_MEDIUM
    elif difficulty == "hard":
        return settings.AI_PROVIDER_HARD
    
    # Default to medium if unspecified or unrecognized
    return settings.AI_PROVIDER_MEDIUM

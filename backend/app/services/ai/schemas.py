from typing import Any, Dict, List, Type
from pydantic import BaseModel, Field

class GenerationRequest(BaseModel):
    """
    Standardized request format for AI providers.
    """
    system_prompt: str = Field(..., description="The system instructions for the LLM.")
    user_prompt: str = Field(..., description="The specific user request, which may include bounded RAG context.")
    response_schema: Type[BaseModel] = Field(..., description="The Pydantic model representing the expected structured output.")
    temperature: float = Field(0.7, description="Temperature for generation.")

class GenerationResponse(BaseModel):
    """
    Standardized response format from AI providers.
    """
    provider_name: str = Field(..., description="The name of the provider that successfully generated the response.")
    model_name: str = Field(..., description="The specific model version used.")
    parsed_output: BaseModel = Field(..., description="The generated output parsed into the requested Pydantic schema.")
    raw_response: Any = Field(None, description="The raw provider response object (for logging/debugging).")
    latency_ms: float = Field(0.0, description="Latency of the provider call in milliseconds.")

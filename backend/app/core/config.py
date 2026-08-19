from typing import Union, List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800
    
    PROJECT_NAME: str = "Learnova API"
    API_V1_STR: str = "/api/v1"
    
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if not v.strip():
                return ["*"]
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OLLAMA_BASE_URL: str = ""

    SUPABASE_STORAGE_BUCKET: str = "learnova-documents"
    MAX_RESOURCE_FILE_SIZE_MB: int = 50

    RAG_MAX_RETRIEVAL_CHUNKS: int = 8
    RAG_MAX_CHUNKS_PER_RESOURCE: int = 4
    RAG_MIN_COSINE_SIMILARITY: float = 0.35
    RAG_MAX_QUERY_LENGTH: int = 1000

    # Phase 6: AI Provider Abstraction
    AI_PROVIDER_EASY: str = "gemini"
    AI_PROVIDER_MEDIUM: str = "gemini"
    AI_PROVIDER_HARD: str = "gemini"
    AI_FALLBACK_CHAIN: str = "groq,ollama-nemotron,ollama-qwen3"

    GENERATION_MAX_CONTEXT_TOKENS: int = 4000
    GENERATION_MAX_RETRIEVAL_CHUNKS: int = 8
    GENERATION_MAX_CHUNKS_PER_RESOURCE: int = 4
    
    GENERATION_BATCH_SIZE: int = 5
    GENERATION_MAX_BATCHES: int = 20
    GENERATION_MAX_SUPPLEMENTARY_BATCHES: int = 10
    GENERATION_MAX_REPAIR_ATTEMPTS: int = 2
    GENERATION_MAX_TOTAL_LLM_CALLS: int = 50 # Increased to allow larger generations
    
    GENERATION_DUPLICATE_THRESHOLD: float = 0.90 # Less strict deduplication

    PROVIDER_TIMEOUT_SECONDS: int = 60
    GENERATION_TIMEOUT_SECONDS: int = 120

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

settings = Settings()

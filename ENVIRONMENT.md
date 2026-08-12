# Learnova Environment Configuration & Secrets Management

This document details all environment variables required to run Learnova in a production environment. 

> [!CAUTION]
> Never commit a `.env.production` file to version control. Production secrets must be managed securely through your deployment environment's secret manager (e.g. AWS Secrets Manager, Vercel Environment Variables, Docker Swarm Secrets, or Kubernetes Secrets).

## Database & Caching
- `DATABASE_URL`: Full connection string to the PostgreSQL database. **Must** use the `postgresql+asyncpg://` schema for SQLAlchemy asynchronous pooling.
- `REDIS_URL`: Connection string to the Redis instance used for Server-Sent Events (SSE) and caching.
- `DATABASE_POOL_SIZE`: Default is 20. Connection pool size for asyncpg.
- `DATABASE_MAX_OVERFLOW`: Default is 10. Max connections to allow beyond pool size.
- `DATABASE_POOL_TIMEOUT`: Default is 30s. Connection acquisition timeout.
- `DATABASE_POOL_RECYCLE`: Default is 1800s. Time before recycling connections.

## Security & Authentication
- `SUPABASE_URL`: API URL for Supabase authentication.
- `SUPABASE_ANON_KEY`: Public anonymous key.
- `SUPABASE_SERVICE_ROLE_KEY`: Service role key for backend-only admin actions.
- `CORS_ORIGINS`: A JSON list of allowed origins. Example: `["https://learnova.app", "https://app.learnova.com"]`. In production, this **must not** use wildcard `["*"]` when handling credentials.

## AI Provider Integration
- `GEMINI_API_KEY`: API key for Google Gemini model access.
- `OPENAI_API_KEY`: API key for OpenAI model access (Optional, but fallback).
- `ANTHROPIC_API_KEY`: API key for Anthropic access (Optional).
- `OLLAMA_BASE_URL`: Base URL if using self-hosted Ollama for local embeddings or generation.

## AI Rate Limiting & Safety
- `GENERATION_MAX_TOTAL_LLM_CALLS`: Hard limit on AI calls per generation request. (Default: 20)
- `GENERATION_MAX_SUPPLEMENTARY_BATCHES`: Hard limit on additional generation batches for duplicates. (Default: 3)
- `GENERATION_MAX_REPAIR_ATTEMPTS`: Hard limit on logical repair retries. (Default: 2)
- `PROVIDER_TIMEOUT_SECONDS`: Total HTTP timeout constraint for external provider API calls. (Default: 60)
- `GENERATION_TIMEOUT_SECONDS`: Global timeout constraint for an entire batch generation session. (Default: 120)

## Upload Safety
- `MAX_RESOURCE_FILE_SIZE_MB`: Max uploaded document size in MB. (Default: 50)
- `SUPABASE_STORAGE_BUCKET`: Storage bucket name for raw documents.

## Application Details
- `PROJECT_NAME`: "Learnova API"
- `API_V1_STR`: "/api/v1"

---
*Note: Make sure to review these constraints against your expected production traffic.*

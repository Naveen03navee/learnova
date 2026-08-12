# Learnova v1.0.0 Release Notes

We are thrilled to announce the official release of **Learnova v1.0.0**, the culmination of 13 intense phases of architectural development, hardening, and production validation. Learnova is now fully ready for real-world deployment in educational institutions.

## Highlights
- **Intelligent Knowledge Extraction**: Upload curriculum PDFs and DOCX files. Learnova chunks, embeds (via pgvector), and strictly scopes generation only to validated sources to eliminate hallucination.
- **Enterprise-Grade AI Generation**: Batched, self-healing generation pipelines that automatically repair logical failures, drop duplicates (using MMR), and cascade between AI providers (Gemini -> OpenAI -> Anthropic -> Ollama) gracefully.
- **Teacher-in-the-Loop Workflows**: No questions enter the Question Bank without manual teacher approval. Precise lineage is maintained linking every question to its exact source document segment.
- **Immutable Assessment Publishing**: Draft Question Papers dynamically select questions based on semantic diversity (to ensure wide topic coverage). Once approved, papers are locked into an immutable snapshot and compiled into DOCX formats alongside Answer Keys.
- **Production Hardened**: Full Docker containerization, connection pooling, graceful shutdowns, JSON-structured operational metrics endpoints (`/api/v1/metrics`), and strict deployment security checks.

## Key Technical Additions in v1.0.0
- **AI Reliability**: Strict connect, read, and total execution timeouts have been implemented across all LLM clients, alongside bounded transient-failure retry logic with exponential backoff.
- **Database Safety**: Deployed automated PostgreSQL backup & restore scripts, and enforced connection bounds (`DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW`) for horizontal backend scaling.
- **Observability**: Added endpoints for `/health` and `/health/ready` to support Kubernetes/Docker Swarm liveness/readiness probes, and exposed aggregate application telemetry securely.
- **Security Pass**: Hardened CORS configurations, added explicit prompt injection defense in the RAG contexts, and capped maximum generation limits to prevent cost exhaustion attacks.

## Upgrade & Deployment Instructions
Please review the complete deployment stack detailed in `DEPLOYMENT.md` and ensure all required secrets are populated according to `ENVIRONMENT.md`. 
Run database migrations using `alembic upgrade head` before directing traffic to the v1.0.0 containers.

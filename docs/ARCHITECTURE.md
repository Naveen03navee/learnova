# Learnova Architecture

## Overview
Learnova is a simple, production-safe MVP designed for a single college/institution (1-2 teachers) to upload study materials, process them into a knowledge base, and use a RAG pipeline to generate exam questions.

## Core Principles
- **Keep it Simple:** No multi-tenancy, no student accounts, no microservices, and no heavy external message brokers (Redis/Celery) unless strictly needed.
- **Backend Authorization:** The frontend does NOT access the database directly. All database access (CRUD) and Storage uploads must pass through the FastAPI backend.
- **Authoritative Database State:** PostgreSQL represents the absolute ground truth. Storage objects must map to a database resource.

## Components
1. **Frontend (Next.js):** 
   - Uses App Router, TypeScript, Tailwind CSS, shadcn/ui.
   - Communicates exclusively with the FastAPI backend via REST and SSE.
2. **Backend (FastAPI):**
   - Python-based backend handling all business logic, AI orchestration, and database CRUD.
   - Uses SQLAlchemy (async) and Alembic for database migrations.
   - Handles document processing directly (via async background tasks within FastAPI) for simplicity.
3. **Database & Auth (Supabase):**
   - **PostgreSQL:** Stores application data.
   - **pgvector:** Stores document embeddings for semantic retrieval.
   - **Auth:** Handles Teacher login.
   - **Storage:** Stores uploaded PDFs, notes, and generated question papers.
4. **AI Generation Engine:**
   - **Embeddings:** Local `sentence-transformers/all-MiniLM-L6-v2` for chunk embeddings (avoids external API costs and quota limits).
   - **Inference Providers:** Fallback chain (Gemini -> OpenAI -> Anthropic -> Ollama) to guarantee robust question generation.

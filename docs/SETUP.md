# Setup Instructions

## Prerequisites
- Node.js (v18+)
- Python (3.11+)
- Supabase CLI (or a remote Supabase project with connection keys)
- Poppler & Tesseract (system dependencies for PDF extraction and OCR)

## 1. Environment Variables
Create a `.env` in both the `frontend` and `backend` directories.

**Backend `.env` example:**
```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=

GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OLLAMA_BASE_URL=

AI_PROVIDER_EASY=gemini
AI_PROVIDER_MEDIUM=gemini
AI_PROVIDER_HARD=gemini
AI_FALLBACK_CHAIN=gemini,openai,anthropic,ollama

GENERATION_MAX_CONTEXT_TOKENS=4000
GENERATION_MAX_RETRIEVAL_CHUNKS=8
GENERATION_MAX_CHUNKS_PER_RESOURCE=4
GENERATION_MAX_REPAIR_ATTEMPTS=2
GENERATION_MAX_TOTAL_LLM_CALLS=4

PROVIDER_TIMEOUT_SECONDS=60
GENERATION_TIMEOUT_SECONDS=120
```

## 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
# or venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 4. Supabase Setup
- Create `learnova-documents` storage bucket.
- Configure Auth settings for Teacher login (email/password).
- Enable `pgvector` extension in PostgreSQL settings.

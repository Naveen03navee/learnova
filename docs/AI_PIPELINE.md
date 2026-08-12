# AI & RAG Pipeline

## Ingestion Pipeline
1. **Upload:** File uploaded to Supabase Storage by the backend, database state set to `UPLOADED`.
2. **Extraction:** PyMuPDF extracts text. If minimal text is found, Tesseract OCR is triggered.
3. **Chunking:** Text is cleaned and chunked.
4. **Embedding:** Local `sentence-transformers/all-MiniLM-L6-v2` generates embeddings.
5. **Storage:** Chunks and embeddings are saved to `document_chunks` table in `pgvector`. State updated to `READY`.

## Retrieval Architecture (RAG)
- **Strict Scoping:** Retrieval queries MUST include filters for `exam_id` and `subject_id`. `folder_id` limits are applied if specified.
- **Context Boundaries:**
  - `GENERATION_MAX_CONTEXT_TOKENS=4000`
  - `GENERATION_MAX_RETRIEVAL_CHUNKS=8`
  - `GENERATION_MAX_CHUNKS_PER_RESOURCE=4`

## Generation Provider Fallback
- **Chain:** Gemini -> OpenAI -> Anthropic -> Ollama
- **Global Limits:** A generation session is constrained by a global LLM call counter (`GENERATION_MAX_TOTAL_LLM_CALLS=4`). If Gemini throws a 429 quota exhausted error, the chain immediately moves to the next provider instead of retrying blindly.
- **Prompt Isolation:** Prompts are rebuilt fresh on every repair/retry attempt to prevent endless context accretion.

## Quality & Deduplication
- Newly generated questions are embedded and compared against the Question Bank to prevent exact semantic duplicates.
- Partial generation is fully supported (e.g., 7/10 questions saved and returned to user instead of failing the whole batch).

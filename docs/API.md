# API Documentation

All API endpoints reside on the FastAPI backend and use standard REST semantics. 

## Endpoints

### Auth (Handled via Supabase)
While Supabase Auth handles login, the backend validates JWTs for all protected endpoints.
- `/api/v1/auth/me` (GET): Retrieve the authenticated teacher's profile.

### Exams & Subjects
- `/api/v1/exams` (GET, POST): List/create exams (KCET, NEET, COMED-K, College).
- `/api/v1/subjects` (GET, POST): List/create subjects under an exam context.

### Knowledge Base (Folders & Resources)
- `/api/v1/folders` (GET, POST): Manage folder hierarchy.
- `/api/v1/resources` (GET, POST): Upload and track documents. POST initiates the background ingestion pipeline (PyMuPDF -> Chunking -> Local Embeddings).
- `/api/v1/resources/{id}` (GET, DELETE): Check status or delete resource.

### Generation
- `/api/v1/generation/stream` (POST): Starts a question generation session. Uses SSE to stream progress events (e.g., `Retrieving relevant knowledge...`, `Generating...`, `Validating...`) and yields partial/final questions.

### Question Bank
- `/api/v1/questions` (GET): Search and filter questions by exam, subject, difficulty, etc.
- `/api/v1/questions/{id}` (PUT, DELETE): Edit or delete a specific question.

### Question Papers
- `/api/v1/question-papers` (GET, POST): Create a new question paper.
- `/api/v1/question-papers/{id}/pdf` (GET): Generate and download the question paper PDF.
- `/api/v1/question-papers/{id}/answers/pdf` (GET): Generate and download the answer key PDF.

### History
- `/api/v1/history` (GET): View generation session history.

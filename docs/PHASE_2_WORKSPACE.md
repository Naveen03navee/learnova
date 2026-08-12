# Phase 2: Workspace Setup

## Overview
This phase establishes the foundational structure for Exams and Subjects, mapping directly to the teacher's Workspace Setup UI. It introduces SQLAlchemy models, FastAPI endpoints, and Next.js frontend pages.

## Database Models & Constraints
### Profiles
- Maps to Supabase `auth.users`.

### Exams
- Fields: `id`, `name`, `is_college`, `created_at`
- Core Seed Data: KCET, NEET, COMED-K (is_college=False), College / University (is_college=True)

### Subjects
- Fields: `id`, `exam_id`, `created_by`, `name`, `normalized_name`, `created_at`
- Constraint: `UNIQUE(exam_id, normalized_name)`
- This strict database-level constraint prevents duplicate subjects (e.g. "Physics" vs "physics") for the same exam.

## API Endpoints
All API endpoints validate authentication via Supabase JWT (Bearer token) before executing CRUD operations.
- `GET /api/v1/exams`: Retrieves all supported exams.
- `GET /api/v1/subjects?exam_id=...`: Retrieves subjects for an exam.
- `POST /api/v1/subjects`: Creates a new subject (requires unique name).
- `PUT /api/v1/subjects/{id}`: Updates an existing subject.
- `DELETE /api/v1/subjects/{id}`: Deletes a subject.

## Frontend
- Configured Axios interceptor (`src/lib/api.ts`) to inject the Supabase JWT.
- `src/app/workspace/page.tsx` displays exams and enables dynamic subject management.
- State handled efficiently via TanStack React Query.
- UUIDs are completely hidden from the user interface.

## Limitations & Testing Notes
- **Testing Warning:** E2E testing against the live database cannot be fully executed by the automated agent due to the lack of live Supabase credentials (`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`) in the environment. To run locally, ensure the `.env` keys are valid.

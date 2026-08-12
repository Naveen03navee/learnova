# Database Schema

## Core Tables

### `profiles`
- `id` (uuid, references auth.users)
- `email` (string)
- `created_at` (timestamp)

### `exams`
- `id` (uuid)
- `name` (string)
- `is_college` (boolean)
- `created_at` (timestamp)

### `subjects`
- `id` (uuid)
- `exam_id` (uuid, references exams)
- `name` (string)
- `created_at` (timestamp)
- *Constraint: Unique (exam_id, name)*

### `folders`
- `id` (uuid)
- `name` (string)
- `parent_id` (uuid, nullable, references folders)
- `created_at` (timestamp)
- *Constraint: Unique (parent_id, name) to prevent duplicate folders at the same level.*

### `resources`
- `id` (uuid)
- `name` (string)
- `file_path` (string)
- `file_type` (string)
- `file_size` (integer)
- `exam_id` (uuid, references exams)
- `folder_id` (uuid, nullable, references folders)
- `uploaded_by` (uuid, references profiles)
- `status` (enum: UPLOADED, PROCESSING, EXTRACTING, OCR, CHUNKING, EMBEDDING, READY, FAILED)
- `created_at` (timestamp)

### `resource_subject_mappings`
- `resource_id` (uuid, references resources)
- `subject_id` (uuid, references subjects)
- *Constraint: Primary Key (resource_id, subject_id)*

### `document_chunks`
- `id` (uuid)
- `resource_id` (uuid, references resources)
- `content` (text)
- `chunk_index` (integer)
- `embedding` (vector)
- `created_at` (timestamp)

### `questions`
- `id` (uuid)
- `exam_id` (uuid, references exams)
- `subject_id` (uuid, references subjects)
- `question_text` (text)
- `difficulty` (string)
- `question_type` (string)
- `marks` (integer)
- `correct_answer` (text)
- `explanation` (text)
- `source_session_id` (uuid, nullable)
- `created_at` (timestamp)

### `question_options`
- `id` (uuid)
- `question_id` (uuid, references questions)
- `option_text` (text)
- `is_correct` (boolean)

### `generation_sessions`
- `id` (uuid)
- `exam_id` (uuid, references exams)
- `subject_id` (uuid, references subjects)
- `requested_count` (integer)
- `generated_count` (integer)
- `difficulty` (string)
- `provider_used` (string)
- `status` (enum: COMPLETED, PARTIAL, FAILED, CANCELLED)
- `created_at` (timestamp)

### `generation_questions`
- `session_id` (uuid, references generation_sessions)
- `question_id` (uuid, references questions)

### `question_papers`
- `id` (uuid)
- `exam_id` (uuid, references exams)
- `subject_id` (uuid, references subjects)
- `title` (string)
- `instructions` (text)
- `duration_minutes` (integer)
- `total_marks` (integer)
- `created_at` (timestamp)

### `question_paper_questions`
- `paper_id` (uuid, references question_papers)
- `question_id` (uuid, references questions)
- `order_index` (integer)
- `marks_override` (integer, nullable)

### `answer_keys`
- `id` (uuid)
- `paper_id` (uuid, references question_papers)
- `created_at` (timestamp)

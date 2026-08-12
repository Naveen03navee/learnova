# Learnova

Learnova is a powerful, AI-driven education platform built to empower teachers and educators. It transforms your existing teaching materials (like notes and textbooks) into smart, exam-ready question banks in minutes. 

With Learnova, you can upload documents to create a custom "Knowledge Base," and then instruct the AI to generate high-quality Multiple Choice (MCQ), Short Answer (SAQ), and Long Answer (LAQ) questions. It actively checks for duplicates, validates logic, and seamlessly aligns with your institution's specific exam patterns. Finally, you can assemble these questions into beautifully formatted, ready-to-print Question Papers.

## 🚀 Key Features
- **Smart Knowledge Base**: Upload PDFs and documents; Learnova chunks and embeds them for precise RAG (Retrieval-Augmented Generation).
- **AI Question Generation**: Harnesses Gemini, Groq, or local Ollama models to generate questions exclusively from your uploaded context.
- **Automated Fallback Chain**: If a cloud AI provider rate-limits, Learnova automatically fails over to the next provider (e.g., Gemini -> Groq -> Local Ollama).
- **Exam Assembly**: Use the intuitive drag-and-drop builder to compile questions into full exam papers and export them to PDF.
- **AI Insights**: View comprehensive analytics on question difficulty, topic coverage, and cognitive levels (Bloom's Taxonomy).

## 🛠 Tech Stack
- **Frontend**: Next.js 14 (React), Tailwind CSS, Zustand, React Query, Lucide Icons
- **Backend**: FastAPI (Python), PostgreSQL (pgvector), SQLAlchemy, Alembic
- **Database & Auth**: Supabase
- **AI Integration**: Gemini API, Groq API, and local Ollama

---

## ⚙️ Prerequisites

Before you begin, ensure you have the following installed on your machine:
- **Node.js** (v18 or higher)
- **Python** (v3.10 or higher)
- **Supabase Account** (for hosted PostgreSQL & Authentication)
- **Ollama** (optional, if you want to use local models for generation fallbacks)

---

## 🔐 Environment Variables

You need to configure environment variables for both the root (backend) and the frontend.

### 1. Root / Backend (`.env`)
Create a `.env` file in the root directory (`learnova/.env`) and add the following keys. This is used by FastAPI and Alembic.

```env
# Supabase Configuration
SUPABASE_URL="https://your-project-ref.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"

# Database Connection (Transaction connection pooler string recommended for API, Direct for Alembic)
DATABASE_URL="postgresql://postgres.[your-ref]:[password]@aws-0-region.pooler.supabase.com:6543/postgres"

# AI Provider Keys
GEMINI_API_KEY="your-gemini-api-key"
GROQ_API_KEY="your-groq-api-key"
OLLAMA_BASE_URL="http://localhost:11434"

# AI Configuration (Optional Overrides)
AI_PROVIDER_EASY="gemini"
AI_PROVIDER_MEDIUM="gemini"
AI_PROVIDER_HARD="gemini"
AI_FALLBACK_CHAIN="gemini,groq,ollama"
```

### 2. Frontend (`frontend/.env.local`)
Create a `.env.local` file inside the `frontend/` directory.

```env
NEXT_PUBLIC_SUPABASE_URL="https://your-project-ref.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="your-anon-key"
NEXT_PUBLIC_API_URL="http://localhost:8000"
```

---

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd learnova
```

### 2. Backend Setup
Create a virtual environment and install the Python dependencies:

```bash
# Create and activate virtual environment (Windows)
python -m venv .venv
.venv\Scripts\activate

# (On Mac/Linux, use: source .venv/bin/activate)

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Database Migrations
Once your `.env` is configured with a valid `DATABASE_URL`, apply the database migrations to build your tables and enable `pgvector`:
```bash
cd backend
alembic upgrade head
cd ..
```

### 4. Frontend Setup
Open a new terminal, navigate to the frontend directory, and install the Node dependencies:
```bash
cd frontend
npm install
```

---

## 🚀 Running the Project

To use Learnova, you need to run both the frontend and backend servers simultaneously. If you are using local AI generation, ensure Ollama is also running.

### 1. Start Ollama (Optional)
If you have local LLM fallbacks configured, start Ollama:
```bash
ollama serve
```

### 2. Start the Backend API
Open a terminal, activate your virtual environment, and run the FastAPI server:
```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
```
*The backend API will be running at `http://127.0.0.1:8000`*

### 3. Start the Frontend Application
Open a new terminal, navigate to the frontend, and run the Next.js development server:
```bash
cd frontend
npm run dev
```
*The frontend application will be running at `http://localhost:3000`*

---

Once both servers are running, simply open your browser and navigate to **[http://localhost:3000](http://localhost:3000)** to access Learnova!

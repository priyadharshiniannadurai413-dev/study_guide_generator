# AI Study Assistant (StudySync AI)

> Turn any PDF into your personal study guide with AI-powered notes, quizzes, RAG-based document chat, and personalized learning tools.

StudySync AI is a full-stack, university-aligned educational platform built with **FastAPI**, **React 19**, **LangGraph**, and **MongoDB Atlas**. It transforms lecture slides, textbooks, and university syllabi into structured study notes, exam-ready quizzes, interactive short-answer practice arenas, and downloadable study packages.

---

## 📖 What It Does

Students often struggle to navigate lengthy textbooks, complex university curricula, and dense course slides before exams. StudySync AI bridges this gap by acting as an intelligent, syllabus-grounded personal tutor.

### How It Helps Students
- **Upload Any Document**: Upload course PDFs, lecture notes, or textbooks up to 50 MB (up to 50 pages).
- **Instant AI Study Notes**: Generates high-yield summaries, key formulas (with LaTeX rendering), glossary terms, and prioritized 4-week revision plans calibrated by difficulty (*Beginner*, *Intermediate*, *Advanced*).
- **Interactive Quizzes**: Generates customizable Multiple Choice Questions (MCQs) with instant scoring, explanations, and distractor breakdowns.
- **University 2-Mark Exam Practice**: Simulates university short-answer exams with real-time AI grading on a 0–2 mark rubric with itemized feedback.
- **Document-Grounded Chat & Voice**: Ask questions directly against uploaded documents with context citations, powered by streaming text and neural voice (Groq Whisper STT + Microsoft Edge TTS).
- **GitHub & Web MCP Connectors**: Analyze computer science code repositories and fetch live academic web documentation on demand.

### End-to-End Flow

```text
User
  ↓
Upload PDF / Select Syllabus
  ↓
Document Processing
  ↓
Text Extraction (pypdf / pdfplumber)
  ↓
Chunking (RecursiveCharacterTextSplitter: 1000 chars)
  ↓
Embeddings (Google Gemini: 384 dimensions)
  ↓
MongoDB Atlas Vector Search (Dual-Tier RAG + RRF)
  ↓
Relevant Context
  ↓
LangGraph Supervisor & LLM (Mistral / Groq / Gemini)
  ↓
Study Notes / Quiz / Answers / Voice Chat / PDF Export
```

---

## ✨ Features

### 🔐 Authentication & Tenant Isolation
- **Clerk Identity Management**: Secure sign-in and session lifecycle handling via `@clerk/clerk-react`.
- **JWT Verification**: Backend validates RS256 tokens using Clerk JWKS public keys with in-memory caching.
- **Strict Data Isolation**: All documents, chunks, notes, and chat sessions are strictly partitioned by `user_id`.

### 📄 Document Ingestion & Management
- **Multi-Format Support**: Ingests `.pdf`, `.docx`, `.txt`, `.md`, `.json`, and `.ipynb` files.
- **Robust PDF Extraction**: Primary extraction via `pypdf` with fallback to `pdfplumber` for tables and complex layouts.
- **Chunking Pipeline**: Splits documents into 1,000-character chunks with 150-character overlap, attaching rich page metadata.
- **Document Vault**: View uploaded files, track vector chunk counts, and safely delete documents and embeddings.

### 🧠 AI Study Generation
- **Structured Study Packages**: Synthesizes concept overviews, formulas, unit breakdowns, 2-mark question banks, and glossaries.
- **Difficulty Calibration**: Calibrate notes and practice questions to `beginner`, `intermediate`, or `advanced` academic depth.
- **LaTeX Math Support**: Mathematical equations and chemical formulas rendered seamlessly via KaTeX.
- **Map-Reduce Summarizer**: Ad-hoc full-document summarizer for fast overview synthesis.

### 📝 Quiz & Assessment Arena
- **Custom MCQ Generation**: Create topic-specific quizzes (1 to 20 questions) with calibrated distractor subtlety.
- **Real-Time Scoring**: Immediate feedback, detailed explanations, and performance confetti animations.
- **University 2-Mark Test Arena**: Short-answer exam simulator with rubric-based AI evaluation (0, 1, or 2 marks) and model answer comparisons.

### 🔍 Two-Tier Hybrid RAG
- **Tier 1 (Global Syllabus)**: Departmental curriculum chunks indexed in `syllabus_vectors` using Reciprocal Rank Fusion (RRF) between dense vector search and sparse keyword search.
- **Tier 2 (User Documents)**: Private student documents indexed in `user_documents` with `$vectorSearch` and in-memory cosine fallback.

### 💬 Document-Aware Chat & Voice
- **Multi-Turn AI Tutor**: Conversational memory grounded in retrieved document excerpts with page citations.
- **Streaming Responses**: Server-Sent Events (SSE) support for responsive token rendering.
- **Bi-Directional Voice**: Groq Whisper Turbo (`whisper-large-v3`) speech-to-text and Microsoft Edge Neural TTS streaming.

### 🔌 Model Context Protocol (MCP) & Tools
- **Fetch MCP**: High-speed web scraper with boilerplate cleaner, anti-bot bypass (`r.jina.ai`), and 15-minute TTL cache.
- **GitHub MCP & REST Connector**: Connect GitHub accounts via OAuth or Personal Access Tokens (encrypted with AES-Fernet) to inspect repositories, browse code, and review commits.

### 📥 Document Export
- **PDF Export**: Generate styled, ready-to-print PDF study guides via ReportLab Platypus.
- **DOCX Export**: Export editable Microsoft Word documents via `python-docx`.
- **CSV Flashcards**: Export 20 MCQs as spaced-repetition flashcards for Anki and Quizlet.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend Framework** | React 19 + Vite 8 | Reactive single-page application and fast development server |
| **Styling & UI** | Vanilla CSS + Lucide React | Token-based responsive design system and icons |
| **Frontend Auth** | `@clerk/clerk-react` | User authentication, sign-in modals, and session tokens |
| **Markdown & Math** | `react-markdown`, `remark-gfm`, `rehype-katex` | Markdown and LaTeX mathematical rendering |
| **Backend Framework** | FastAPI + Uvicorn | High-performance asynchronous Python web framework |
| **Agent Orchestrator** | LangGraph | Multi-agent supervisor and state machine routing |
| **RAG & Chains** | LangChain Core / Community | Document loaders, text splitters, and retrieval chains |
| **Database** | MongoDB Atlas (Motor Async Driver) | Document metadata, vector embeddings, and encrypted credentials |
| **Vector Search** | MongoDB Atlas Vector Search | 384-dimensional dense vector search with Cosine metric |
| **Embedding Model** | Google Gemini (`models/gemini-embedding-001`) | 384-dimensional dense embeddings |
| **Primary LLM** | Mistral AI (`mistral-small-latest`) | High-yield notes synthesis, quiz generation, and evaluation |
| **Fallback LLMs** | Groq (`openai/gpt-oss-20b`) & Gemini (`gemini-3.5-flash-lite`) | Multi-tier failover protection against rate limits |
| **Voice STT** | Groq Cloud (`whisper-large-v3`) | Ultra-fast audio transcription |
| **Voice TTS** | Microsoft Edge TTS (`edge-tts`) | Streaming neural text-to-speech audio synthesis |
| **PDF Processing** | `pypdf` + `pdfplumber` | Text extraction, page counting, and table parsing |
| **Document Export** | ReportLab + `python-docx` | PDF generation and Word document export |
| **Security & Crypto** | `cryptography` (Fernet AES-128) | Encrypted storage for external OAuth tokens |
| **Web Research** | `httpx` + `html2text` + Fetch MCP | Web content extraction with anti-bot fallback |

---

## ⚙️ How It Works

### 1. Document Ingestion
```text
PDF Document
    ↓
pypdf / pdfplumber Extraction
    ↓
Front-Matter Filter (removes copyright, license, blank pages)
    ↓
RecursiveCharacterTextSplitter (chunk_size=1000, overlap=150)
    ↓
Metadata Tagging (user_id, doc_id, filename, chunk_id, page_number)
    ↓
Google Gemini Embeddings (384 dimensions, batch size 64)
    ↓
MongoDB Atlas (user_documents collection)
```

### 2. RAG Question Answering
```text
User Question / Topic
    ↓
Query Embedding (Gemini 384d vector)
    ↓
Target Resolution (Global Syllabus vs Tenant-Isolated User Document)
    ↓
Hybrid Retrieval (Vector Search + Keyword Search fused with RRF k=60)
    ↓
Sufficiency Evaluation (evaluates if retrieved context is complete)
    ↓
Prompt Assembly (Question + Formatted Excerpts with Page Citations)
    ↓
LLM Inference with Multi-Tier Fallback (Mistral → Groq → Gemini)
    ↓
Synthesized Answer / Streaming Output
```

### 3. Study Guide Generation
When a student requests study notes, the system retrieves relevant document chunks and routes the payload to the `study_notes` specialist agent. The agent synthesizes high-yield summaries, unit breakdowns, LaTeX formulas, and 4-week study plans adhering strictly to Pydantic validation schemas.

### 4. Quiz Generation & Evaluation
The `mcq` specialist agent extracts key factual concepts from the retrieved context and generates 4-option questions with 1 correct answer, 3 plausible distractors, and educational explanations. For 2-mark university questions, the evaluation engine scores written answers against a 2-point rubric using semantic AI grading.

---

## 🚀 How to Run

### Prerequisites
Ensure you have the following installed on your system:
- **Python 3.11+**
- **Node.js 18+** and **npm**
- **Git**
- **MongoDB Atlas Cluster** (with Vector Search enabled)
- **Clerk Account** (for authentication keys)
- **API Keys**: Google Gemini API key, Mistral API key, and Groq API key

---

### Clone Repository

```bash
git clone <repository-url>
cd study_guide_generator
```

---

### Backend Setup

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Create a `.env` file in the `backend/` directory based on `.env.example`:
   ```bash
   cp .env.example .env
   ```
   *(Fill in your real API keys in `backend/.env`)*

5. **Start the FastAPI backend server**:
   ```bash
   python server.py
   ```
   Or directly via Uvicorn:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Verify Backend Health**:
   - Backend API: `http://localhost:8000`
   - Health Diagnostic: `http://localhost:8000/health`
   - Interactive Swagger API Documentation: `http://localhost:8000/docs`

---

### Frontend Setup

1. **Open a new terminal and navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node dependencies**:
   ```bash
   npm install
   ```

3. **Configure environment variables**:
   Create a `.env` file in the `frontend/` directory based on `.env.example`:
   ```bash
   cp .env.example .env
   ```
   *(Ensure `VITE_CLERK_PUBLISHABLE_KEY` and `VITE_API_URL` are set)*

4. **Start the Vite development server**:
   ```bash
   npm run dev
   ```

5. **Access Application**:
   Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🔐 Environment Variables

### Backend Configuration (`backend/.env`)

| Variable | Required | Purpose |
|---|---|---|
| `APP_NAME` | No | Display name of the backend service (default: `AI Study Assistant`) |
| `APP_ENV` | No | Deployment environment (`development` / `production`) |
| `DEBUG` | No | Enable verbose debug logging (`true` / `false`) |
| `GEMINI_API_KEY` | **Yes** | Google Gemini API key for embeddings and fallback LLM |
| `MISTRAL_API_KEY` | **Yes** | Mistral AI API key for primary LLM inference |
| `GROQ_API_KEY` | **Yes** | Groq Cloud API key for Whisper STT and Llama failover |
| `TAVILY_API_KEY` | No | Optional web search API key |
| `MONGODB_URL` | **Yes** | MongoDB Atlas connection string |
| `DB_NAME` | No | Database name (default: `Study_plan_generator`) |
| `CLERK_SECRET_KEY` | **Yes** | Clerk Backend Secret Key for JWT verification |
| `CLERK_PUBLISHABLE_KEY` | **Yes** | Clerk Frontend Publishable Key |
| `CLERK_JWKS_URL` | No | Custom Clerk JWKS URL for offline key verification |
| `TOKEN_ENCRYPTION_KEY` | No | 32-byte Base64 Fernet key for encrypting stored GitHub tokens |
| `GITHUB_CLIENT_ID` | No | GitHub OAuth Application Client ID |
| `GITHUB_CLIENT_SECRET` | No | GitHub OAuth Application Client Secret |
| `GITHUB_REDIRECT_URI` | No | GitHub OAuth Redirect Callback URL |
| `FRONTEND_URL` | No | Allowed frontend origin for CORS (e.g., `http://localhost:5173`) |
| `LANGSMITH_TRACING` | No | Enable LangSmith observability (`true` / `false`) |
| `LANGSMITH_API_KEY` | No | LangSmith API Key for agent tracing |
| `LANGSMITH_PROJECT` | No | LangSmith project name |

```env
# Example backend/.env
APP_NAME="AI Study Assistant"
APP_ENV="development"
DEBUG=true

GEMINI_API_KEY=your_gemini_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

MONGODB_URL=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
DB_NAME=Study_plan_generator

CLERK_SECRET_KEY=sk_test_your_clerk_secret_key
CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key

TOKEN_ENCRYPTION_KEY=your_32_byte_base64_fernet_key=
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_REDIRECT_URI=http://localhost:8000/auth/github/callback

FRONTEND_URL=http://localhost:5173
```

---

### Frontend Configuration (`frontend/.env`)

| Variable | Required | Purpose |
|---|---|---|
| `VITE_API_URL` | **Yes** | Backend FastAPI base URL (`http://localhost:8000` in dev) |
| `VITE_CLERK_PUBLISHABLE_KEY` | **Yes** | Clerk Publishable Key (safe in frontend client) |
| `VITE_CLERK_SIGN_IN_URL` | No | Custom sign-in route (default: `/sign-in`) |
| `VITE_CLERK_SIGN_UP_URL` | No | Custom sign-up route (default: `/sign-up`) |
| `VITE_CLERK_AFTER_SIGN_IN_URL`| No | Redirect route after sign in (default: `/dashboard`) |
| `VITE_CLERK_AFTER_SIGN_UP_URL`| No | Redirect route after sign up (default: `/dashboard`) |

```env
# Example frontend/.env
VITE_API_URL=http://localhost:8000
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
VITE_CLERK_SIGN_IN_URL=/sign-in
VITE_CLERK_SIGN_UP_URL=/sign-up
VITE_CLERK_AFTER_SIGN_IN_URL=/dashboard
VITE_CLERK_AFTER_SIGN_UP_URL=/dashboard
```

---

### ⚠️ Security Notice on Environment Variables

> **CRITICAL**: Never commit `.env` files containing real API keys, database credentials, or OAuth secrets to Git.
> - Backend `.env` resides exclusively in `backend/.env` and is ignored by `.gitignore`.
> - Frontend `.env` resides in `frontend/.env` and only contains public variables prefixed with `VITE_`.
> - Keep all production keys secure in your hosting provider's environment settings (Render, Vercel).

---

## 📁 Project Structure

```text
study_guide_generator/
├── backend/                        # FastAPI Backend Application
│   ├── app/
│   │   ├── ai/                     # LangGraph supervisor & specialist agent subgraphs
│   │   ├── api/                    # Core API route definitions
│   │   ├── auth/                   # Clerk RS256 JWKS verification & dependencies
│   │   ├── core/                   # Application settings & environment config
│   │   ├── db/                     # MongoDB connection manager & Fernet token store
│   │   ├── prompts/                # Structured prompt templates for study & quizzes
│   │   ├── rag/                    # Ingestion, loaders, chunking, embeddings, vector store
│   │   ├── routes/                 # FastAPI APIRouters (documents, study, chat, auth, tools)
│   │   ├── services/               # Evaluation engine, summarizer, speech, export services
│   │   ├── study_guide/            # Map-Reduce PDF summarizer & topic extractor
│   │   ├── tools/                  # GitHub tools & Fetch MCP connectors
│   │   └── main.py                 # FastAPI application factory & lifespan handler
│   ├── requirements.txt            # Python dependencies
│   └── server.py                   # Development & production server runner
├── docs/                           # System Technical Documentation
│   ├── architecture.md             # Complete technical architecture & 37-endpoint table
│   └── workflow.md                 # Mermaid sequence & state workflow diagrams
├── frontend/                       # React 19 Frontend Application (Vite 8)
│   ├── src/
│   │   ├── api/                    # Axios API client & endpoint URL registry
│   │   ├── components/             # Reusable UI (Chat, Quiz, Notes, MCP, GitHub, Voice)
│   │   ├── context/                # React Context providers (AuthContext, ToastContext)
│   │   ├── pages/                  # Top-level page views (Dashboard, Chat, Docs, Quiz, Notes)
│   │   ├── App.jsx                 # Main layout controller & tab router
│   │   ├── index.css               # Design-token CSS styling
│   │   └── main.jsx                # React DOM entry point
│   ├── index.html                  # HTML template with KaTeX and Google Fonts
│   ├── package.json                # Frontend dependencies
│   ├── vercel.json                 # Vercel SPA routing rewrites
│   └── vite.config.js              # Vite bundler configuration
└── Readme.md                       # Main Project Documentation
```

---

### Backend Core Modules

| Module | Responsibility |
|---|---|
| `app/rag/` | PDF loading, text extraction, chunking, Gemini embeddings, and MongoDB vector storage |
| `app/ai/` | LangGraph supervisor agent, routing classifier, and specialist agent subgraphs |
| `app/auth/` | Clerk token verification, JWKS key caching, and `get_current_user` dependency |
| `app/db/` | Async Motor MongoDB connection lifecycle and AES-Fernet encrypted credentials store |
| `app/routes/` | RESTful API route controllers for documents, study generation, chat, voice, and OAuth |
| `app/services/` | Two-mark evaluation engine, ReportLab PDF exporter, docx exporter, speech services |
| `app/study_guide/`| Map-Reduce recursive document summarization and topic extraction pipeline |
| `app/tools/` | GitHub REST/MCP integration tools and Fetch MCP web scraper |

---

### Frontend Core Modules

| Module | Responsibility |
|---|---|
| `src/pages/` | Page view containers: `DashboardPage`, `ChatPage`, `DocumentsPage`, `StudyNotesPage`, `QuizPage` |
| `src/components/` | Subsystems: `TwoMarkTestArena`, `MCQArena`, `GitHubWorkbench`, `MCPConnectorsHub`, `VoiceRecorder` |
| `src/api/` | `client.js` (Axios wrapper with JWT auto-refresh) and `endpoints.js` (API path registry) |
| `src/context/` | `AuthContext.jsx` (Clerk token provider) and `ToastContext.jsx` (UI notifications) |

---

## 📡 API Overview

The backend exposes **37 REST endpoints** grouped into 8 primary areas:

| Area | Base Path | Key Capabilities | Auth |
|---|---|---|---|
| **System** | `/`, `/health` | Service status, health check, LangSmith tracing status | Public |
| **Documents** | `/api/documents/...` | Upload PDF (up to 50MB), list documents, chunk statistics, delete | Required (Bearer JWT) |
| **Study Content** | `/api/study/...` | Adaptive study notes, comprehensive study packs, PDF/DOCX/CSV export | Required (Bearer JWT) |
| **Assessments** | `/api/study/...` | Generate MCQs, generate 2-mark tests, evaluate short answers | Required (Bearer JWT) |
| **Chat & Voice** | `/api/chat/...`, `/api/voice/...`| Multi-turn chat, SSE streaming, Whisper STT, Edge TTS audio synthesis | Required / Public |
| **Auth & GitHub** | `/auth/github/...` | GitHub OAuth login, callback, status check, disconnect | Required / Public |
| **Integrations** | `/api/integrations/...` | Save GitHub PAT, check MCP status, connector health | Required (Bearer JWT) |
| **Web Research** | `/api/web/...`, `/api/tools/...` | Fetch MCP web reader, web-grounded Q&A, URL clean extractor | Required (Bearer JWT) |

For complete documentation of all 37 endpoints with parameters and response models, see [docs/architecture.md](docs/architecture.md).

---

## 🔬 Detailed Documentation

Comprehensive architecture diagrams, workflows, and database schemas are documented in the [`docs/`](docs/) folder:

- 🏗️ **[System Architecture](docs/architecture.md)** — Architectural patterns, multi-agent graphs, full API table, database design, and failover mechanics.
- 🔄 **[Application Workflows](docs/workflow.md)** — End-to-end Mermaid sequence and flow diagrams for authentication, document ingestion, RAG, study generation, quiz evaluation, and MCP tools.

---

## 🌐 Deployment

| Service | Hosting Platform | Configuration |
|---|---|---|
| **Frontend** | **Vercel** | Single-Page Application (SPA) with `vercel.json` rewrite rules (`/*` → `/index.html`) |
| **Backend** | **Render** | Python web service running `uvicorn app.main:app --host 0.0.0.0 --port $PORT` via `server.py` |
| **Database** | **MongoDB Atlas** | Managed cluster with Vector Search Index on `syllabus_vectors` and `user_documents` |

---

## ❓ Troubleshooting

### 1. Clerk Authentication Fails (401 Unauthorized)
- Verify that `VITE_CLERK_PUBLISHABLE_KEY` in `frontend/.env` matches `CLERK_PUBLISHABLE_KEY` in `backend/.env`.
- Ensure `CLERK_SECRET_KEY` in `backend/.env` is set correctly.

### 2. MongoDB Vector Search Returns No Results
- Verify that the vector index named `vector_index` (or `syllabus_vector_index`) is created in your MongoDB Atlas cluster on the target collection with 384 dimensions and the `cosine` similarity metric.
- If unindexed, the system will automatically fall back to in-memory cosine matching.

### 3. Rate Limit Errors (HTTP 429)
- Google Gemini and Groq have free-tier rate limits. The backend automatically retries with exponential backoff and cascades to fallback models (`Mistral` → `Groq` → `Gemini`).

### 4. CORS Errors Between Frontend and Backend
- Verify that `FRONTEND_URL` in `backend/.env` matches your frontend origin (e.g., `http://localhost:5173` or your production Vercel domain).

---

## 📚 Project Documentation Links

- 🏗️ [Architecture Documentation](docs/architecture.md)
- 🔄 [Workflow Documentation](docs/workflow.md)

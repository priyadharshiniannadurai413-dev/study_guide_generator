# StudySync AI

> **Intelligent University Curriculum Assistant, Multi-Modal Study Guide Generator & Multi-Agent Learning Copilot**

StudySync AI is a production-grade, asynchronous AI education platform built with **FastAPI**, **React 19**, **LangGraph**, **LangChain**, and **MongoDB Atlas**. It transforms complex university syllabi, lecture transcripts, and student-uploaded textbooks into structured study notes, exam-ready quizzes, interactive two-mark revision arenas, and downloadable study guides.

Powered by a LangGraph multi-agent supervisor, hybrid vector-keyword retrieval (RRF), real-time speech processing (Whisper STT + Edge TTS), Model Context Protocol (MCP) integrations, and three-tier LLM fallback resilience, StudySync AI delivers personalized, syllabus-aligned learning experiences at scale.

---

## 📖 Documentation Index

Comprehensive technical architecture, data flows, and workflow specifications are documented in the [`docs/`](file:///c:/Users/ELCOT/Documents/study_guide_generator/docs) directory:

- 🏗️ **[System Architecture](docs/architecture.md)** — In-depth component breakdown, multi-agent supervisor graph, vector search pipeline, 37-endpoint REST API specifications, database schema, security model, and failure recovery flows.
- 🔄 **[Application Workflows](docs/workflow.md)** — Complete step-by-step Mermaid sequence and state diagrams for user authentication, document processing, RAG retrieval, notes generation, quiz creation, two-mark evaluation, voice interactions, and MCP tool execution.

---

## ✨ Key Features & Capabilities

### 1. Dual-Scope Document & Syllabus Ingestion
- **Global Syllabus Knowledge Base**: Scans and parses departmental university curriculum files (`.pdf`, `.docx`, `.txt`, `.md`, `.json`, `.ipynb`) into structured subjects, units, topics, and subtopics.
- **Tenant-Isolated User Uploads**: Students upload personal study materials (up to 50 MB) processed via `pypdf` and `pdfplumber` with fallback text cleaners.
- **Incremental Chunking**: Employs `RecursiveCharacterTextSplitter` (chunk size: 1,000 chars, overlap: 150 chars) with metadata tagging (`user_id`, `document_id`, `filename`, `source_type`).

### 2. Hybrid RAG & Semantic Retrieval
- **Dual Vector Collections**: Distinguishes between global curriculum vectors (`syllabus_vectors`) and user-specific document vectors (`user_documents`).
- **Reciprocal Rank Fusion (RRF)**: Combines dense vector search with sparse keyword search ($k=60$) for balanced contextual relevance and exact technical keyword matching.
- **Resilient Fallback Search**: Automatic in-memory cosine similarity fallback if MongoDB `$vectorSearch` indexes are unavailable or unindexed.

### 3. Multi-Agent Supervisor & Autonomous Delegation
- **LangGraph Router**: An intelligent supervisor evaluates user queries and dynamically delegates tasks to specialized agent nodes:
  - `curriculum`: Resolves subject hierarchies, unit breakdowns, and syllabus boundaries.
  - `study_notes`: Synthesizes deep conceptual study materials and revision summaries.
  - `mcq`: Generates topic-specific quizzes with difficulty grading and explanations.
  - `github`: Inspects repositories, commits, and source files for computer science curricula.
  - `direct_answer`: Handles general pedagogical questions without retrieval overhead.

### 4. Comprehensive Study Notes & Study Guides
- Generates structured, high-yield study packages containing:
  - High-level concept overviews and key formulas (LaTeX formatted).
  - Unit-by-unit comprehensive breakdowns with real-world examples.
  - Curated 2-mark question banks with model answers.
  - Key glossary terms with definitions and memory aids.
  - Strategic 4-week study schedules prioritized by topic difficulty.

### 5. Exam-Ready Quiz & MCQ Generation
- Dynamically produces customizable Multiple Choice Question (MCQ) assessments.
- Configurable question counts (3 to 20 questions) and difficulty tiers (*Easy*, *Medium*, *Hard*, *Adaptive*).
- Instant scoring with per-question rationales, syllabus citations, and post-quiz performance analytics.

### 6. Two-Mark Real-Time Interactive Test Arena
- Simulates university-style short answer exams (2-mark questions).
- Automated AI evaluator grades student responses on a 0–2 point scale using standard rubrics:
  - **2 Marks**: Complete, precise definition with key technical terminology.
  - **1 Mark**: Partially correct or incomplete explanation lacking vital keywords.
  - **0 Marks**: Incorrect, irrelevant, or missing answer.
- Returns instant actionable feedback, missed key concepts, and model answers.

### 7. Conversational AI Tutor & Streaming Voice Assistant
- **Context-Aware Chat**: Multi-turn conversational memory with document grounding.
- **Voice In (STT)**: High-speed speech recognition using Groq Whisper Turbo (`whisper-large-v3`).
- **Voice Out (TTS)**: Natural voice synthesis powered by Microsoft Edge Neural TTS (`edge-tts`, `en-US-JennyNeural`).
- **Server-Sent Events (SSE)**: Streaming responses for responsive real-time feedback.

### 8. Model Context Protocol (MCP) & GitHub Connectors
- **Fetch MCP**: High-performance external web extraction with anti-bot fallbacks (`r.jina.ai`) and in-memory TTL caching for web-augmented study context.
- **GitHub MCP & REST Connector**: Bi-directional integration allowing students to connect GitHub accounts via OAuth or Personal Access Tokens (encrypted with AES-Fernet) to analyze codebases and generate code walkthroughs.

### 9. Multi-Format Document Export & Flashcards
- **PDF Export**: Generates styled, print-ready PDF study guides via ReportLab.
- **DOCX Export**: Produces editable Microsoft Word documents via `python-docx`.
- **CSV Flashcards**: Exports spaced-repetition flashcards for import into Anki and Quizlet.
- **Markdown & JSON**: Raw export options for personal note-taking systems (Obsidian, Notion).

### 10. Clerk Authentication & Tenant Isolation
- Seamless user identity management via **Clerk React** and backend JWT validation.
- Every database query strictly filters by authenticated `user_id`.
- In-memory JWT verification caching (10-minute TTL) to minimize third-party round-trips.

---

## 🤖 AI / RAG Architecture Overview

The following diagram illustrates the core data ingestion, agent routing, and retrieval pipeline. For full architectural diagrams and component breakdowns, see [System Architecture](docs/architecture.md).

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ User Documents  │       │ Global Syllabus │       │  External Web   │
│  (.pdf, .docx)  │       │  Curricula      │       │  (Fetch MCP)    │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ Chunking (1000) │       │ Chunking (1000) │       │ Clean HTML/Text │
│ Overlap (150)   │       │ Overlap (150)   │       │ Cached Extract  │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         ▼                         ▼                         │
┌───────────────────────────────────────────┐                │
│ Gemini Embeddings (384-dimensional dense) │                │
└─────────────────────┬─────────────────────┘                │
                      ▼                                      │
┌───────────────────────────────────────────┐                │
│    MongoDB Atlas Vector Collections       │                │
│   • user_documents   • syllabus_vectors   │                │
└─────────────────────┬─────────────────────┘                │
                      │                                      │
                      ▼                                      │
         ┌─────────────────────────┐                         │
         │  Hybrid Retrieval & RRF │ ◄───────────────────────┘
         └────────────┬────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │   LangGraph Supervisor  │
         │   (Query Intent Router) │
         └────────────┬────────────┘
                      ├──────────────────────────┬──────────────────────────┐
                      ▼                          ▼                          ▼
         ┌─────────────────────────┐┌─────────────────────────┐┌─────────────────────────┐
         │ Study Notes / Guide Gen ││    MCQ / Quiz Engine    ││  Two-Mark Test Arena   │
         └────────────┬────────────┘└────────────┬────────────┘└────────────┬────────────┘
                      │                          │                          │
                      └──────────────────────────┼──────────────────────────┘
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │ Primary: Mistral Small      │
                                  │ Fallback 1: Groq GPT-OSS    │
                                  │ Fallback 2: Gemini Flash    │
                                  └──────────────┬──────────────┘
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │  Structured Response / UI   │
                                  └─────────────────────────────┘
```

---

## 🧬 RAG Pipeline Details

| Stage | Implementation Details | Code Location |
|---|---|---|
| **Document Loaders** | `pypdf`, `pdfplumber`, `python-docx`, UTF-8 plaintext reader | [`backend/services/document_service.py`](file:///c:/Users/ELCOT/Documents/study_guide_generator/backend/services/document_service.py) |
| **Text Chunking** | `RecursiveCharacterTextSplitter` (chunk_size=1000, overlap=150) | [`backend/services/document_service.py`](file:///c:/Users/ELCOT/Documents/study_guide_generator/backend/services/document_service.py) |
| **Embeddings** | Google Gemini `models/gemini-embedding-001` (384 dimensions) | [`backend/services/embedding_service.py`](file:///c:/Users/ELCOT/Documents/study_guide_generator/backend/services/embedding_service.py) |
| **Vector Storage** | MongoDB Atlas collections: `syllabus_vectors` & `user_documents` | [`backend/services/vector_store.py`](file:///c:/Users/ELCOT/Documents/study_guide_generator/backend/services/vector_store.py) |
| **Search Strategies** | 1. Dense Vector Search (`$vectorSearch`, top_k=5)<br>2. Keyword Search (Atlas Text Index)<br>3. Reciprocal Rank Fusion (RRF, k=60)<br>4. In-Memory Cosine Fallback | [`backend/services/vector_store.py`](file:///c:/Users/ELCOT/Documents/study_guide_generator/backend/services/vector_store.py) |
| **Context Synthesis** | Dynamic prompt assembly with metadata citations and source tracking | [`backend/services/rag_service.py`](file:///c:/Users/ELCOT/Documents/study_guide_generator/backend/services/rag_service.py) |
| **LLM Inference** | Structured JSON schema formatting with Pydantic output validation | [`backend/services/llm_service.py`](file:///c:/Users/ELCOT/Documents/study_guide_generator/backend/services/llm_service.py) |

---

## 🧠 AI Models & Providers

StudySync AI uses a resilient multi-provider strategy to guarantee high availability and protect against API outages and rate limits.

| Role | Provider | Model | Fallback Model | Purpose |
|---|---|---|---|---|
| **Primary LLM** | Mistral AI | `mistral-small-latest` | `openai/gpt-oss-20b` (Groq) & `gemini-3.5-flash-lite` (Google) | Study notes synthesis, quiz generation, answer evaluation, and agent reasoning. |
| **Embedding Model** | Google Gemini | `models/gemini-embedding-001` (384d) | None (Cached in MongoDB) | Dense vector generation for syllabus and document chunks. |
| **Speech-to-Text (STT)** | Groq Cloud | `whisper-large-v3` | None | Ultra-low latency voice transcription for student audio queries. |
| **Text-to-Speech (TTS)** | Microsoft Edge | `edge-tts` (`en-US-JennyNeural`) | None (Direct MP3 streaming) | Streaming neural voice synthesis for conversational AI replies. |

---

## 🔌 MCP & External Tool Integrations

| Tool / MCP Server | Purpose | Used By / Feature | Implementation Status |
|---|---|---|---|
| **Fetch MCP** | Anti-bot HTML extraction and markdown conversion with TTL caching | Web-augmented study context, external reference lookups | **Implemented & Active** |
| **GitHub REST Tools** | Search repos, inspect files, list commits, and search code | `GitHubWorkbench` tab, CS curriculum repository analysis | **Implemented & Active** |
| **GitHub MCP Server** | 32 standard GitHub Copilot MCP tool interfaces | Advanced agentic repo inspection | **Implemented (Docker / npx command config)** |

---

## 🔐 Authentication & Security

- **Frontend Security**: Managed through `@clerk/clerk-react` with `<SignedIn>` / `<SignedOut>` gating.
- **Backend JWT Verification**: All protected API endpoints depend on `get_current_user`, which validates Clerk RS256/HS256 tokens using Clerk JWKS public keys.
- **Token Caching**: Validated JWT payloads are cached in memory for 10 minutes to minimize external latency.
- **Tenant Data Isolation**: Every document chunk, chat message, quiz result, and study progress record is strictly partitioned by `user_id`.
- **Encrypted Token Store**: GitHub OAuth tokens and Personal Access Tokens (PAT) are encrypted at rest using `cryptography.fernet` (AES-128-CBC with SHA256 HMAC).
- **CORS Protection**: Restricted to authorized frontend origins configured via `CORS_ORIGINS`.

---

## 📁 Repository Structure

```
study_guide_generator/
├── backend/                        # FastAPI Backend Application
│   ├── api/                        # API route handlers (37 endpoints)
│   │   ├── auth.py                 # User info, Clerk verification, GitHub OAuth
│   │   ├── chat.py                 # Multi-turn chat, SSE streaming, voice endpoints
│   │   ├── documents.py            # Document upload, listing, deletion, ingestion
│   │   ├── export.py               # PDF, DOCX, CSV flashcard generators
│   │   ├── github.py               # GitHub repository & file analysis tools
│   │   ├── mcp.py                  # MCP server registry and connector execution
│   │   ├── progress.py             # Topic mastery, quiz stats, progress tracking
│   │   ├── quiz.py                 # MCQ generation, quiz submission, 2-mark evaluation
│   │   ├── study_guide.py          # Study guide generation and topic retrieval
│   │   └── study_notes.py          # Structured study notes generation
│   ├── config/                     # Application configuration & settings
│   │   ├── database.py             # MongoDB connection manager & collection accessors
│   │   └── settings.py             # Pydantic BaseSettings & environment loader
│   ├── models/                     # Pydantic data schemas
│   │   ├── chat.py                 # Chat request/response schemas
│   │   ├── common.py               # Shared API response wrappers
│   │   ├── document.py             # Document & chunk models
│   │   ├── github.py               # GitHub query & file models
│   │   ├── mcp.py                  # MCP connector & tool schemas
│   │   ├── progress.py             # Progress tracking & mastery models
│   │   ├── quiz.py                 # Quiz, question, and 2-mark schemas
│   │   ├── study_guide.py          # Study guide request & response models
│   │   └── study_notes.py          # Study notes & revision models
│   ├── prompts/                    # LLM prompt templates
│   │   ├── chat_prompts.py         # Pedagogical tutor & routing prompts
│   │   ├── quiz_prompts.py         # MCQ & two-mark evaluation prompts
│   │   └── study_guide_prompts.py  # High-yield study notes synthesis prompts
│   ├── services/                   # Business logic & AI orchestration
│   │   ├── agent_service.py        # LangGraph supervisor multi-agent graph
│   │   ├── auth_service.py         # Token cache & tenant authentication
│   │   ├── chat_service.py         # Multi-turn chat & context injection
│   │   ├── document_service.py     # PDF/DOCX parsing & text chunking
│   │   ├── embedding_service.py    # Google Gemini dense vector embeddings
│   │   ├── export_service.py       # ReportLab PDF, DOCX, & CSV flashcard exporter
│   │   ├── fetch_mcp_service.py    # Fetch MCP web scraper with anti-bot fallbacks
│   │   ├── github_service.py       # GitHub REST & MCP API client
│   │   ├── llm_service.py          # Multi-LLM provider with fallback execution
│   │   ├── mcp_service.py          # MCP server process runner & registry
│   │   ├── progress_service.py     # Progress metrics & revision scheduler
│   │   ├── quiz_service.py         # MCQ generation, scoring, and 2-mark grading
│   │   ├── rag_service.py          # RAG retrieval pipeline & context assembler
│   │   ├── study_guide_service.py  # Syllabus guide & topic extractor
│   │   ├── study_notes_service.py  # Structured study notes generator
│   │   ├── token_store.py          # Fernet AES token encryption manager
│   │   ├── vector_store.py         # MongoDB Atlas vector & keyword search with RRF
│   │   └── voice_service.py        # Groq Whisper STT & Edge TTS streaming
│   ├── main.py                     # FastAPI application factory & lifespan
│   └── requirements.txt            # Backend Python dependencies
├── docs/                           # Comprehensive System Documentation
│   ├── architecture.md             # Complete system architecture and API specifications
│   └── workflow.md                 # Execution sequence diagrams and data flows
├── frontend/                       # React 19 Frontend Application (Vite 8)
│   ├── src/
│   │   ├── components/             # Reusable UI components
│   │   │   ├── Chat/               # Chat window, message list, voice controls
│   │   │   ├── Common/             # Header, Navigation, Loading, Error Boundary
│   │   │   ├── Documents/          # Document upload dropzone, list, file preview
│   │   │   ├── MCP/                # MCP connector cards, tool runner
│   │   │   ├── Progress/           # Topic mastery bars, quiz analytics
│   │   │   ├── Quiz/               # MCQ runner, timer, 2-mark interactive arena
│   │   │   └── StudyGuide/         # Study notes viewer, markdown renderer, export
│   │   ├── context/                # React Context providers (AuthContext)
│   │   ├── pages/                  # Top-level view containers
│   │   │   ├── ChatPage.jsx        # Conversational AI tutor & voice interface
│   │   │   ├── DashboardPage.jsx   # Overview metrics, recent materials, quick start
│   │   │   ├── DocumentsPage.jsx   # Knowledge base document manager
│   │   │   ├── GitHubWorkbench.jsx # GitHub repo & code analyzer
│   │   │   ├── MCPConnectorsHub.jsx# MCP server status & tool execution
│   │   │   ├── QuizPage.jsx        # MCQ quiz arena & test history
│   │   │   ├── StudyNotesPage.jsx  # Generated study notes & export controls
│   │   │   └── TwoMarkTestArena.jsx# Real-time university short answer evaluation
│   │   ├── services/               # API clients & endpoint definitions
│   │   │   ├── api.js              # Axios instance with auth interceptor
│   │   │   └── endpoints.js        # API path declarations
│   │   ├── styles/                 # Pure Vanilla CSS design system
│   │   ├── App.jsx                 # Root router and layout controller
│   │   └── main.jsx                # React application entry point
│   ├── index.html                  # Main HTML template
│   ├── package.json                # Frontend JavaScript dependencies
│   └── vite.config.js              # Vite bundler configuration
└── outputs/                        # Default export destination for PDFs & guides
```

---

## 📡 REST API Reference

The backend exposes **37 endpoints** across 8 logical domains. All endpoints except `/`, `/health`, and `/api/auth/github/callback` require a valid Clerk Bearer token.

### 1. System & Health
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/` | Service root and platform status | No |
| `GET` | `/health` | Database and LLM health check | No |

### 2. Authentication & Identity
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/auth/me` | Current authenticated user profile | Yes (Bearer) |
| `POST` | `/api/auth/sync` | Sync Clerk user identity with database | Yes (Bearer) |
| `GET` | `/api/auth/github/authorize` | Initiate GitHub OAuth authorization flow | Yes (Bearer) |
| `GET` | `/api/auth/github/callback` | OAuth redirect callback handler | No |
| `GET` | `/api/auth/github/status` | Check GitHub connection status | Yes (Bearer) |
| `POST` | `/api/auth/github/disconnect` | Revoke and delete stored GitHub credentials | Yes (Bearer) |

### 3. Documents & Knowledge Base
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/documents/upload` | Upload and ingest document (`.pdf`, `.docx`, `.txt`) | Yes (Bearer) |
| `GET` | `/api/documents/` | List all user documents with chunk statistics | Yes (Bearer) |
| `GET` | `/api/documents/{doc_id}` | Get document metadata and processing status | Yes (Bearer) |
| `DELETE` | `/api/documents/{doc_id}` | Delete document and remove all vector chunks | Yes (Bearer) |
| `POST` | `/api/documents/reprocess/{id}` | Re-chunk and re-embed an existing document | Yes (Bearer) |

### 4. Study Notes & Study Guides
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/study-notes/generate` | Generate comprehensive, structured study notes | Yes (Bearer) |
| `GET` | `/api/study-notes/` | List all generated study notes for current user | Yes (Bearer) |
| `GET` | `/api/study-notes/{notes_id}` | Retrieve specific study notes by ID | Yes (Bearer) |
| `DELETE` | `/api/study-notes/{notes_id}` | Delete study notes record | Yes (Bearer) |
| `POST` | `/api/study-guide/generate` | Generate university-aligned study guide | Yes (Bearer) |
| `GET` | `/api/study-guide/topics` | Extract syllabus topics from documents | Yes (Bearer) |

### 5. Quizzes & Assessments
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/quiz/generate` | Generate custom MCQ quiz from topic or document | Yes (Bearer) |
| `POST` | `/api/quiz/submit` | Submit MCQ quiz answers and get evaluation | Yes (Bearer) |
| `GET` | `/api/quiz/history` | List previous quiz attempts and scores | Yes (Bearer) |
| `GET` | `/api/quiz/{quiz_id}` | Retrieve quiz details and questions | Yes (Bearer) |
| `POST` | `/api/quiz/two-mark/generate` | Generate 2-mark university short questions | Yes (Bearer) |
| `POST` | `/api/quiz/two-mark/evaluate` | Evaluate student answer against standard 2-mark rubric | Yes (Bearer) |

### 6. Conversational AI & Voice
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/chat/message` | Send message to AI tutor (sync response) | Yes (Bearer) |
| `POST` | `/api/chat/stream` | Stream AI response via Server-Sent Events (SSE) | Yes (Bearer) |
| `GET` | `/api/chat/history` | Retrieve conversation turn history | Yes (Bearer) |
| `DELETE` | `/api/chat/history` | Clear user chat history | Yes (Bearer) |
| `POST` | `/api/chat/voice` | Transcribe audio (Whisper STT) and get response | Yes (Bearer) |
| `POST` | `/api/chat/tts` | Synthesize text to streaming MP3 audio (Edge TTS) | Yes (Bearer) |

### 7. Tools, MCP & GitHub
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/github/repos` | List connected user repositories | Yes (Bearer) |
| `POST` | `/api/github/analyze` | Analyze repository codebase for study context | Yes (Bearer) |
| `GET` | `/api/mcp/servers` | List registered MCP servers and status | Yes (Bearer) |
| `POST` | `/api/mcp/execute` | Execute specific tool on registered MCP server | Yes (Bearer) |

### 8. Study Progress & Tracking
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/progress/` | Get user study progress and topic mastery stats | Yes (Bearer) |
| `POST` | `/api/progress/update` | Update study activity and mastery score | Yes (Bearer) |

---

## 💻 Frontend Application Views

The frontend is a single-page application built with **React 19** and styled with modern **Vanilla CSS**.

| View / Tab | Component | Key Capabilities |
|---|---|---|
| **Dashboard** | `DashboardPage.jsx` | Overview metrics, quick actions, document count, mastery statistics, recent notes. |
| **AI Chat & Voice** | `ChatPage.jsx` | Conversational tutor, voice input (microphone recording), TTS playback, document context selector. |
| **Documents Hub** | `DocumentsPage.jsx` | Drag-and-drop file uploader, file status tracking, chunk inspectors, delete actions. |
| **Study Notes** | `StudyNotesPage.jsx` | Markdown notes renderer with KaTeX math support, table of contents, PDF/DOCX export buttons. |
| **Quiz Arena** | `QuizPage.jsx` | Timed MCQ tests, instant question-by-question scoring, performance breakdowns, confetti animations. |
| **2-Mark Test Arena** | `TwoMarkTestArena.jsx` | University short answer test arena with instant AI rubric evaluation (0–2 marks) and model answers. |
| **GitHub Workbench** | `GitHubWorkbench.jsx` | Repository connector, file tree inspector, codebase study guide generator. |
| **MCP Connectors** | `MCPConnectorsHub.jsx` | Server status monitoring (Fetch MCP, GitHub MCP), tool parameter builder, execution logs. |

---

## 🗄️ Database Architecture

StudySync AI uses **MongoDB Atlas** with optimized collections for documents, vectors, assessments, and encrypted credentials.

| Collection Name | Purpose | Indexes & Keys |
|---|---|---|
| `syllabus_vectors` | Global university syllabus knowledge chunks | Atlas Vector Search Index (`vector_index`), Text Index (`keyword_index`), `subject`, `unit` |
| `user_documents` | Tenant-isolated user uploads and vector chunks | Atlas Vector Search Index (`vector_index`), `user_id`, `doc_id`, `filename` |
| `quizzes` | Generated MCQ questions, student answers, and test history | `user_id`, `quiz_id`, `topic`, `created_at` |
| `study_notes` | Generated study notes and structured guides | `user_id`, `notes_id`, `topic`, `created_at` |
| `chats` | Multi-turn conversational message history | `user_id`, `session_id`, `timestamp` |
| `study_progress` | Topic mastery records, quiz analytics, revision dates | `user_id`, `topic_id`, `last_studied` |
| `github_tokens` | Fernet-encrypted GitHub OAuth tokens and PATs | `user_id` (unique) |

---

## ⚙️ Environment Variables

Create `.env` files in both the `backend/` and `frontend/` directories.

### Backend Configuration (`backend/.env`)

```env
# Server & Environment
ENV=development
DEBUG=true
PORT=8000
HOST=0.0.0.0
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Database (MongoDB Atlas)
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
DB_NAME=Study_plan_generator

# Authentication (Clerk)
CLERK_SECRET_KEY=sk_test_your_clerk_secret_key
CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
CLERK_JWT_KEY=optional_clerk_pem_public_key

# Primary & Fallback LLM API Keys
MISTRAL_API_KEY=your_mistral_api_key
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_google_gemini_api_key

# Security & Encryption
ENCRYPTION_KEY=your_32_byte_base64_fernet_key

# GitHub OAuth Integration (Optional)
GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret
GITHUB_REDIRECT_URI=http://localhost:8000/api/auth/github/callback

# LangSmith Tracing & Observability (Optional)
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=studysync-ai
```

### Frontend Configuration (`frontend/.env`)

```env
# Backend API Base URL
VITE_API_URL=http://localhost:8000

# Clerk Authentication
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
```

---

## 🚀 Local Development Setup

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** and **npm**
- **MongoDB Atlas** cluster (with Vector Search enabled)

---

### Backend Setup

1. **Navigate to the backend folder**:
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
   ```bash
   cp .env.example .env
   # Edit .env with your real API keys
   ```

5. **Start the FastAPI server**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Verify server health**:
   Open [http://localhost:8000/health](http://localhost:8000/health) or browse interactive Swagger docs at [http://localhost:8000/docs](http://localhost:8000/docs).

---

### Frontend Setup

1. **Navigate to the frontend folder**:
   ```bash
   cd frontend
   ```

2. **Install Node dependencies**:
   ```bash
   npm install
   ```

3. **Configure frontend environment**:
   ```bash
   # Ensure .env contains VITE_CLERK_PUBLISHABLE_KEY and VITE_API_URL
   ```

4. **Start the Vite development server**:
   ```bash
   npm run dev
   ```

5. **Open Application**:
   Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🛡️ Reliability & Error Handling

- **Three-Tier LLM Fallback Cascade**: If Mistral AI experiences rate limits or server errors, `llm_service.py` automatically routes the request to Groq (`gpt-oss-20b`), then to Google Gemini (`gemini-3.5-flash-lite`).
- **Resilient Vector Retrieval**: If MongoDB Atlas `$vectorSearch` is unindexed, the system gracefully falls back to local cosine distance matching over in-memory embeddings.
- **Robust Web Scraping**: `fetch_mcp_service.py` attempts standard `httpx` parsing first; if blocked by anti-bot protections, it falls back to `r.jina.ai` markdown reader.
- **Strict JSON Parsing**: LLM responses are parsed using an error-correcting JSON cleaner (`clean_json_string`) before Pydantic schema validation.

---

## 📊 Current Implementation Status

### ✅ Fully Implemented
- Document upload and ingestion (`.pdf`, `.docx`, `.txt`, `.md`, `.ipynb`).
- Two-tier MongoDB RAG pipeline (Syllabus + User Documents) with RRF hybrid retrieval.
- Multi-provider LLM fallback execution (Mistral -> Groq -> Gemini).
- LangGraph supervisor agent with multi-intent delegation.
- Comprehensive study notes generation with LaTeX math and 4-week schedules.
- MCQ quiz generation, submission scoring, and question analytics.
- Interactive 2-mark university short answer evaluation arena with rubric grading.
- Conversational chat with Groq Whisper STT and Edge TTS streaming.
- Multi-format document export (ReportLab PDF, DOCX, CSV flashcards).
- Clerk JWT authentication with in-memory caching and tenant isolation.
- Fetch MCP external web scraper with TTL caching.
- GitHub REST integration (search repos, view files, commit logs).

### 🟡 Partially Implemented / Minor Discrepancies
- **Chat Token Streaming**: `/api/chat/stream` returns SSE event chunks wrapping full response strings rather than token-by-token generators.
- **GitHub Frontend Callback**: Frontend `App.jsx` listens for GitHub OAuth popups via `window.opener.postMessage`; direct REST helper in `endpoints.js` uses standard OAuth query params.
- **Upload File Size Limit**: Backend permits up to 50 MB; frontend dropzone applies a 25 MB client-side check.

### 🧪 Experimental
- **External GitHub MCP Server**: Running full 32-tool GitHub Copilot MCP via Docker/npx stdio transport.

---

## 🔮 Future Roadmap

- [ ] **Token-by-Token LCEL Stream**: Migrate the conversational chat stream to LangChain's native `astream_events` for character-by-character token rendering.
- [ ] **Automated Flashcard Spaced Repetition**: In-app SRS review system (SM-2 algorithm) for generated flashcards.
- [ ] **Multi-Document Comparative Synthesis**: Cross-document comparative study guide generator for multi-course exams.
- [ ] **Offline Vector Search Mode**: Local ChromaDB / SQLite-vec fallback option for air-gapped deployments.

---

## 📄 License

This project is developed for educational and academic purposes. See repository configuration for details.

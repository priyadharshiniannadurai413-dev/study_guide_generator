# AI Study Assistant — System Architecture Documentation

This document provides a comprehensive technical breakdown of the architectural patterns, components, schemas, and design decisions implemented in the **AI Study Assistant (StudySync AI)** repository.

---

## 1. Architecture Overview

The application is engineered as a **Decoupled Client-Server Architecture** augmented with **Multi-Agent Orchestration (LangGraph)**, a **Two-Tier Hybrid RAG Subsystem**, and external **Model Context Protocol (MCP)** integrations.

### Key Architectural Pillars:
1. **Frontend Presentation Layer**: Built with React 19 and Vite. Utilizes an unopinionated CSS design-token system, React Context for state and toast management, Clerk for identity lifecycle control, and real-time Server-Sent Events (SSE) streaming for chat tokens.
2. **API & Service Gateway**: Asynchronous FastAPI service running on Uvicorn. Exposes RESTful endpoints, streaming interfaces, static file serving, and global error handling with validation handlers.
3. **Agentic Orchestration Layer**: Powered by LangGraph. Employs a **Supervisor Agent** that dynamically routes queries across specialized subgraphs:
   - **Curriculum Agent**: Answers university syllabus, course code, and credit distribution questions.
   - **StudyNotes Agent**: Synthesizes high-yield structured notes and conceptual cheat sheets.
   - **MCQ Agent**: Generates calibrated multiple-choice quizzes with options and explanations.
   - **GitHub Agent**: Interacts with student repositories, inspects file contents, and performs automated code reviews.
   - **Direct Answer Agent**: Directly answers general knowledge and conversational inquiries.
4. **Two-Tier Hybrid Retrieval-Augmented Generation (RAG)**:
   - **Tier 1 (Global Syllabus)**: Shared curriculum documents indexed in `syllabus_vectors` using Reciprocal Rank Fusion (RRF) between dense Atlas Vector Search and sparse BM25 text search.
   - **Tier 2 (Tenant-Isolated Student Uploads)**: Arbitrary lecture slides and textbooks indexed in `user_documents` partitioned strictly by `user_id`.
5. **Model Context Protocol (MCP) & Web Enrichment**:
   - **Fetch MCP**: Dynamically pulls live web documentation, strips boilerplate, validates academic quality, and injects external evidence into RAG prompts.
   - **GitHub MCP & REST Tools**: Securely reads user repositories and commits via AES-Fernet encrypted access tokens.
6. **Resilient LLM Provider Layer**: Primary inference via Mistral Small (`mistral-small-latest`), with automatic multi-tier fallback to Groq (`openai/gpt-oss-20b`) and Google Gemini (`gemini-3.5-flash-lite`).

---

## 2. High-Level Architecture Diagram

```mermaid
flowchart TB
    User([Student / User])

    subgraph FrontendLayer ["Frontend (React 19 + Vite)"]
        UI["React UI Components"]
        AuthUI["Clerk Auth & AuthContext"]
        APIClient["client.js + endpoints.js API Layer"]
    end

    subgraph GatewayLayer ["Backend Gateway (FastAPI)"]
        API["FastAPI Application: main.py"]
        AuthDep["app.auth.dependencies.get_current_user"]
        Routers["Route Handlers: documents, study, github_auth, integrations, tools, web_research, voice, llm"]
    end

    subgraph ServicesLayer ["Application & Agent Services"]
        SupervisorAgent["Supervisor LangGraph Orchestrator"]
        StudyGenService["study_generator.py and summarizer.py"]
        EvaluationService["evaluation_service.py: 2-Mark Exam Engine"]
        SpeechService["speech_service.py: Voice STT / TTS"]
        ExportService["export_service.py: PDF / DOCX / CSV Export"]
    end

    subgraph RAGLayer ["Two-Tier Hybrid RAG Subsystem"]
        RAGRetriever["app.rag: Hybrid & User Doc Retrievers"]
        Embeddings["GoogleGenerativeAIEmbeddings: 384 dims"]
        DocLoader["pypdf and pdfplumber Loaders & Chunker"]
    end

    subgraph DataLayer ["Persistence (MongoDB Atlas)"]
        MongoDB[("MongoDB Atlas Database")]
        SyllabusColl[("syllabus_vectors: Global Syllabus")]
        UserDocColl[("user_documents: Isolated User Chunks")]
        TokensColl[("github_tokens: Encrypted OAuth Credentials")]
    end

    subgraph MCPLayer ["Model Context Protocol & Web Readers"]
        FetchMCPClient["Fetch MCP: httpx Web Reader"]
        JinaProxy["r.jina.ai Reader Proxy Fallback"]
        GitHubMCPClient["GitHub Copilot MCP & REST Tools"]
    end

    subgraph LLMLayer ["LLM Inference Engine (Multi-Tier Failover)"]
        PrimaryLLM["Primary: Mistral Small"]
        Fallback1["Fallback 1: Groq gpt-oss-20b"]
        Fallback2["Fallback 2: Google Gemini 3.5 Flash Lite"]
    end

    subgraph ExternalIdentity ["External Auth & Voice Engines"]
        ClerkAccounts["Clerk Identity Service: JWKS"]
        GitHubAPI["GitHub REST / OAuth API"]
        EdgeTTSSvc["Microsoft Edge TTS Engine"]
        GroqWhisperSvc["Groq Whisper API"]
    end

    %% Connections
    User --> UI
    UI --> AuthUI
    UI --> APIClient
    AuthUI <--> ClerkAccounts
    APIClient -->|Bearer JWT HTTP / SSE| API
    API --> AuthDep
    AuthDep --> ClerkAccounts
    API --> Routers
    
    Routers --> SupervisorAgent
    Routers --> StudyGenService
    Routers --> EvaluationService
    Routers --> SpeechService
    Routers --> ExportService
    Routers --> DocLoader
    
    DocLoader --> Embeddings
    Embeddings --> UserDocColl
    
    SupervisorAgent --> RAGRetriever
    StudyGenService --> RAGRetriever
    EvaluationService --> RAGRetriever
    
    RAGRetriever --> SyllabusColl
    RAGRetriever --> UserDocColl
    RAGRetriever --> Embeddings
    
    SupervisorAgent --> FetchMCPClient
    FetchMCPClient --> JinaProxy
    SupervisorAgent --> GitHubMCPClient
    GitHubMCPClient --> GitHubAPI
    Routers --> TokensColl
    
    SupervisorAgent --> PrimaryLLM
    StudyGenService --> PrimaryLLM
    EvaluationService --> PrimaryLLM
    PrimaryLLM -.->|failover| Fallback1
    Fallback1 -.->|failover| Fallback2
    
    SpeechService --> GroqWhisperSvc
    SpeechService --> EdgeTTSSvc
    
    MongoDB --- SyllabusColl
    MongoDB --- UserDocColl
    MongoDB --- TokensColl
```

---

## 3. Frontend Architecture Diagram

```mermaid
flowchart TD
    IndexHTML["index.html"] --> MainJSX["src/main.jsx"]
    MainJSX --> ClerkProviderWrapper["ClerkProvider: VITE_CLERK_PUBLISHABLE_KEY"]
    ClerkProviderWrapper --> AppRoot["src/App.jsx"]
    
    AppRoot --> AuthProviderContext["src/context/AuthContext.jsx"]
    AuthProviderContext --> ToastProviderContext["src/context/ToastContext.jsx"]
    ToastProviderContext --> AppContent["AppContent Component"]
    
    AppContent --> AuthGateCheck{"Clerk Auth State"}
    AuthGateCheck -- "SignedOut" --> SignedOutGate["Clerk SignIn / SignUp Modal & Landing Screen"]
    AuthGateCheck -- "SignedIn" --> AuthenticatedApp["Navbar + Active Tab Router + Footer"]
    
    AuthenticatedApp --> TabRouter{"activeTab State"}
    
    TabRouter --> DashboardTab["src/pages/DashboardPage.jsx"]
    TabRouter --> ChatTab["src/pages/ChatPage.jsx"]
    TabRouter --> DocsTab["src/pages/DocumentsPage.jsx"]
    TabRouter --> NotesTab["src/pages/StudyNotesPage.jsx"]
    TabRouter --> QuizTab["src/pages/QuizPage.jsx"]
    TabRouter --> TestTab["src/components/study/TwoMarkTestArena.tsx"]
    TabRouter --> WorkbenchTab["src/components/github/GitHubWorkbench.tsx"]
    TabRouter --> MCPTab["src/components/mcp/MCPConnectorsHub.tsx"]
    
    %% Reusable Components
    ChatTab --> DocSelChat["DocumentSelector.jsx"]
    ChatTab --> VoiceRec["VoiceRecorder.jsx"]
    ChatTab --> AudPlayer["AudioPlayer.jsx"]
    
    NotesTab --> DocSelNotes["DocumentSelector.jsx"]
    NotesTab --> DocViewer["StudyDocumentViewer.tsx"]
    
    QuizTab --> DocSelQuiz["DocumentSelector.jsx"]
    QuizTab --> MCQArenaView["MCQArena.tsx"]
    
    MCPTab --> GHCard["GitHubConnectorCard.tsx"]
    MCPTab --> FetchCard["FetchConnectorCard.tsx"]
    
    %% Client Layer
    DashboardTab --> EndpointsAPI["src/api/endpoints.js"]
    ChatTab --> EndpointsAPI
    DocsTab --> EndpointsAPI
    NotesTab --> EndpointsAPI
    QuizTab --> EndpointsAPI
    TestTab --> EndpointsAPI
    WorkbenchTab --> EndpointsAPI
    MCPTab --> EndpointsAPI

    ChatTab --> SSEStreamClient["streamChatResponse in src/api/client.js"]
    EndpointsAPI --> FetchClient["apiRequest in src/api/client.js"]
    
    FetchClient -->|HTTP with Auto JWT Refresh| FastAPIBackend["FastAPI Backend Server"]
    SSEStreamClient -->|SSE with Auto JWT Refresh| FastAPIBackend
```

---

## 4. Backend Architecture Diagram

```mermaid
flowchart TD
    ServerRunner["server.py: Auto venv detection & port binding"] --> MainApp["app/main.py: FastAPI Application"]
    
    MainApp --> Lifespan["app.main.lifespan: Startup / Shutdown Context"]
    Lifespan --> MongoConn["connect_to_mongo: AsyncIOMotorClient & Index Init"]
    
    MainApp --> MiddlewareLayer["FastAPI Middleware & Exception Handlers"]
    MiddlewareLayer --> CORSMiddleware["CORSMiddleware: Origins localhost 3000/5173, Vercel"]
    MiddlewareLayer --> ValidationHandler["validation_exception_handler: RequestValidationError"]
    MiddlewareLayer --> StaticMount["StaticFiles Mount: /outputs"]
    
    MainApp --> IncludedRouters["Included APIRouters"]
    IncludedRouters --> R_Docs["app.routes.documents: /api/documents"]
    IncludedRouters --> R_Study["app.routes.study: /api/study"]
    IncludedRouters --> R_GHAuth["app.routes.github_auth: /auth/github"]
    IncludedRouters --> R_Integrations["app.routes.integrations: /api/integrations"]
    IncludedRouters --> R_Tools["app.routes.tools: /api/tools"]
    IncludedRouters --> R_Web["app.routes.web_research: /api/web"]
    IncludedRouters --> R_Voice["app.routes.voice: /api/voice"]
    IncludedRouters --> R_LLM["app.routes.llm: /api/chat/*, /chatbot"]
    IncludedRouters --> R_StudyGuide["app.study_guide.router: /study-guide/upload"]
    
    R_Docs --> AuthDependency["app.auth.dependencies.get_current_user"]
    R_Study --> AuthDependency
    R_GHAuth --> AuthDependency
    R_Integrations --> AuthDependency
    R_Tools --> AuthDependency
    R_Web --> AuthDependency
    R_LLM --> AuthDependency

    AuthDependency --> ClerkVerifier["app.auth.clerk.verify_clerk_token: RS256 JWKS Cache"]
    
    R_LLM --> ChatCoordinator["app.ai.chat_service.ChatService: LangGraph Invocation"]
    R_Study --> ChatCoordinator

    ChatCoordinator --> SupervisorGraph["app.ai.agents.supervisor.graph.get_supervisor_graph"]
    
    R_Study --> DirectStudyGen["app.services.study_generator"]
    R_Study --> EvalService["app.services.evaluation_service"]
    R_Study --> ExportService["app.services.export_service"]
    R_StudyGuide --> MapReduceSummarizer["app.study_guide.summarizer & mcq_generator"]
    R_Voice --> SpeechService["app.services.speech_service"]
    
    R_Docs --> UserDocService["app.rag.user_doc_service"]
    ChatCoordinator --> RAGModule["app.rag: user_doc_retriever & vector_store"]
    DirectStudyGen --> RAGModule
    EvalService --> RAGModule
    
    RAGModule --> MongoModule["app.db.mongodb: AsyncIOMotorClient"]
    R_GHAuth --> TokenStoreModule["app.db.token_store: Fernet Encrypted Storage"]
    R_Integrations --> TokenStoreModule
```

---

## 5. RAG Architecture Diagram

```mermaid
flowchart TD
    subgraph IngestionSubsystem ["1. Ingestion & Preprocessing Subsystem"]
        InputPDF["Uploaded PDF Document"] --> LoaderSelect{"Loader Pipeline"}
        LoaderSelect --> FastPyPDF["pypdf: Fast Native Extractor"]
        FastPyPDF -.->|fallback on table error| PDFPlumber["pdfplumber: Structured Table Parser"]
        
        FastPyPDF --> RawPages["Raw Extracted Pages: text & tables"]
        PDFPlumber --> RawPages

        RawPages --> FrontMatterFilter["is_front_matter: Filter copyright, license, ISBN, TOC"]
        FrontMatterFilter --> CleanPages["Substantive Academic Pages"]
        
        CleanPages --> StructureChunker["chunk_document: RecursiveCharacterTextSplitter chunk_size=800, overlap=100"]
        StructureChunker --> TablePreservation["Preserve table blocks whole as contiguous units"]
        TablePreservation --> ChunkMeta["Attach Metadata: user_id, doc_id, filename, chunk_id, page_number"]
        
        ChunkMeta --> BatchEmbedder["embed_texts in app.rag.embedding: Batch size 64"]
        BatchEmbedder --> GoogleEmbedAPI["GoogleGenerativeAIEmbeddings: models/gemini-embedding-001 output_dim=384"]
        GoogleEmbedAPI --> UpsertChunks["Insert into MongoDB user_documents"]
    end

    subgraph TwoTierRetrievalSubsystem ["2. Two-Tier Retrieval Subsystem"]
        QueryInput["Search Query / Topic Focus"] --> TargetRouter{"Target Document"}
        
        %% Tier 1
        TargetRouter -- "doc_id == 'syllabus'" --> Tier1Retriever["app.rag.vector_store.VectorStore"]
        Tier1Retriever --> EmbedQ1["embed_query: 384-dim Gemini vector"]
        EmbedQ1 --> AtlasVectorSearch["vectorSearch on syllabus_vector_index top_k=10"]
        Tier1Retriever --> AtlasTextSearch["text keyword search on syllabus_text_index top_k=10"]
        AtlasVectorSearch --> RRFAlgorithm["merge_rrf: Reciprocal Rank Fusion k=60"]
        AtlasTextSearch --> RRFAlgorithm
        RRFAlgorithm --> Tier1Results["Top 5 Ranked Syllabus Chunks"]
        
        %% Tier 2
        TargetRouter -- "doc_id == User UUID" --> Tier2Retriever["app.rag.user_doc_retriever.get_user_doc_context"]
        Tier2Retriever --> GenericCheck{"Is query generic or summary?"}
        GenericCheck -- "Yes" --> DirectSequentialChunks["direct_chunk_fetch: Chunks ordered by page_number"]
        GenericCheck -- "No" --> EmbedQ2["embed_query: 384-dim Gemini vector"]
        EmbedQ2 --> UserAtlasSearch["atlas_vector_search: vectorSearch with user_id and doc_id pre-filters"]
        UserAtlasSearch -.->|fallback if Atlas search unindexed| UserInMemSearch["in_memory_similarity_search: Cosine Similarity"]
        UserInMemSearch -.->|fallback if empty| DirectSequentialChunks
        UserAtlasSearch --> Tier2Results["Top 8 Tenant-Isolated Chunks"]
        UserInMemSearch --> Tier2Results
        DirectSequentialChunks --> Tier2Results
    end

    subgraph PromptAndLLMGeneration ["3. Prompt Construction & Generation"]
        Tier1Results --> FormatChunks["format_user_doc_context: Format with Excerpt i and Page p"]
        Tier2Results --> FormatChunks
        FormatChunks --> ContextEvaluation["context_evaluator.py: evaluate_context_sufficiency"]
        ContextEvaluation --> WebEnrichDecision{"Web Enrichment Needed?"}
        WebEnrichDecision -- "Yes" --> FetchMCPNode["fetch_web_node: Fetch MCP Reader"]
        FetchMCPNode --> SourceValidatorNode["validate_web_node: Academic Quality Scoring"]
        SourceValidatorNode --> CombinedEvidence["format_combined_evidence: Merge RAG + Web Context"]
        WebEnrichDecision -- "No" --> CombinedEvidence
        
        CombinedEvidence --> PromptAssembly["Assemble Specialist Agent Prompt with Context"]
        PromptAssembly --> CentralLLM["get_llm_with_fallback: Mistral Small to Groq to Gemini"]
        CentralLLM --> StructuredOrStream["Deliver Final Study Guide / Notes / Quiz / Answer"]
    end
```

---

## 6. Agent & Tool Architecture Diagram

```mermaid
flowchart TD
    subgraph SupervisorStateGraph ["Supervisor LangGraph (app/ai/agents/supervisor/graph.py)"]
        START_NODE(["START"]) --> RouterNode["router_node: Hybrid Regex + Gemini Flash Classifier"]
        
        RouterNode -->|Intent == 'curriculum'| CurricSubgraph["curriculum Subgraph"]
        RouterNode -->|Intent == 'study_notes'| NotesSubgraph["study_notes Subgraph"]
        RouterNode -->|Intent == 'mcq'| MCQSubgraph["mcq Subgraph"]
        RouterNode -->|Intent == 'github'| GHAgentNode["github_agent_node"]
        RouterNode -->|Intent == 'direct_answer'| DirectNode["direct_answer_node"]
        
        CurricSubgraph --> FinalizerNode["finalize_response"]
        NotesSubgraph --> FinalizerNode
        MCQSubgraph --> FinalizerNode
        GHAgentNode --> FinalizerNode
        DirectNode --> FinalizerNode
        FinalizerNode --> END_NODE(["END"])
    end

    subgraph SpecialistSubgraphDetail ["Specialist Subgraph Internal Architecture"]
        SubStart(["Subgraph START"]) --> RetrieveContextNode["retrieve_context: Fetch RAG context"]
        RetrieveContextNode --> EvalContextNode["evaluate_context_node: Sufficiency & URL detector"]
        EvalContextNode --> RouteDecision{"route_after_evaluation"}
        
        RouteDecision -- "generate (Sufficient)" --> GenNode["generate_answer / generate_notes / generate_mcqs"]
        RouteDecision -- "fetch_web (Insufficient / URL)" --> FetchWebNode["fetch_web_node: Call FetchMCPService"]
        FetchWebNode --> ValidateWebNode["validate_web_node: Filter ads & score credibility"]
        ValidateWebNode --> GenNode
        GenNode --> SubEnd(["Subgraph END"])
    end

    subgraph ToolRegistry ["Tool Connectors & Helpers"]
        GHAgentNode --> GHToolsModule["app.tools.github_tools.create_user_github_tools"]
        GHToolsModule --> GH_SearchRepos["github_search_repositories"]
        GHToolsModule --> GH_ListRepos["github_list_repositories"]
        GHToolsModule --> GH_GetRepo["github_get_repository"]
        GHToolsModule --> GH_GetFile["github_get_file_contents"]
        GHToolsModule --> GH_ListCommits["github_list_commits"]
        GHToolsModule --> GH_SearchCode["github_search_code"]
        
        FetchWebNode --> FetchMCPService["app.ai.mcp_service.FetchMCPService"]
        FetchMCPService --> HTTPXEngine["httpx.AsyncClient + html2text"]
        FetchMCPService --> JinaFallback["r.jina.ai Reader Proxy"]
        
        GHAgentNode --> GH_MCP_Client["app.services.mcp_client.get_github_mcp_tools: 32 Copilot Tools"]
    end
```

---

## 7. Data Architecture Diagram

```mermaid
erDiagram
    CLERK_USER ||--o{ USER_DOCUMENT : "owns / partitions"
    CLERK_USER ||--o| GITHUB_TOKEN : "links & encrypts"
    SYLLABUS_VECTOR }|..|{ COURSE_UNIT : "indexes curriculum"

    CLERK_USER {
        string sub PK "Clerk User Unique Identifier"
        string email "Student Email Address"
        string name "Student Full Name"
    }

    USER_DOCUMENT {
        ObjectId _id PK "MongoDB Record ID"
        string user_id FK "Tenant Isolation Key (Clerk sub)"
        string doc_id "Document UUID"
        string filename "Uploaded PDF Filename"
        string chunk_id "Document Chunk Sequential ID"
        string text "Extracted Text / Table Content"
        int page_number "PDF Page Number"
        string chunk_type "Semantic Category (general, table, user_content)"
        int semester "Semester Number (1-8)"
        string course_code "Course Code (e.g. 21CS301)"
        array embedding "384-dimensional dense vector"
        datetime created_at "Timestamp UTC"
    }

    SYLLABUS_VECTOR {
        ObjectId _id PK "MongoDB Record ID"
        string chunk_id "Global Syllabus Chunk ID"
        string text "Syllabus Text / Unit Definition"
        string chunk_type "programme_outcome / semester_table / unit_content"
        int semester "Semester Number (1-8)"
        string course_code "Course Code (e.g. 21CS301)"
        boolean is_global "true (shared across all users)"
        array embedding "384-dimensional dense vector"
        string source_file "Default: my_college_syllabus.pdf"
        datetime created_at "Timestamp UTC"
    }

    GITHUB_TOKEN {
        ObjectId _id PK "MongoDB Record ID"
        string clerk_user_id UK "Clerk User ID Unique Index"
        string encrypted_token "AES-Fernet Encrypted Access Token"
        string github_login "Connected GitHub Username"
        string scopes "OAuth / PAT Scopes: repo, read:user"
        datetime connected_at "Timestamp UTC"
    }
```

---

## 8. API Architecture Table

The following table documents all **37 endpoints** implemented across the FastAPI routers:

| HTTP Method | Endpoint Path | Description / Purpose | Authentication | Service / Handler Function |
|---|---|---|---|---|
| `GET` | `/` | API service landing message | Public | `app.main.landing_page` |
| `GET` | `/health` | Health diagnostic & LangSmith tracing status | Public | `app.main.health_check` |
| `POST` | `/api/documents/upload` | Upload & ingest user PDF (max 50MB, 50 pages) | Required (Clerk JWT) | `app.routes.documents.upload_document` |
| `GET` | `/api/documents` | List uploaded documents for current user | Required (Clerk JWT) | `app.routes.documents.list_user_documents` |
| `DELETE` | `/api/documents/{doc_id}` | Delete user document and all indexed chunks | Required (Clerk JWT) | `app.routes.documents.delete_user_document` |
| `POST` | `/api/study/topic-notes` | Generate structured TopicStudyNotes | Required (Clerk JWT) | `app.routes.study.generate_topic_notes` |
| `POST` | `/api/study/notes` | Generate AdaptiveStudyNotes via LangGraph | Required (Clerk JWT) | `app.routes.study.generate_notes` |
| `GET` | `/api/study/export-notes` | Direct query-based PDF/DOCX file export | Required (Clerk JWT) | `app.routes.study.export_study_notes` |
| `POST` | `/api/study/export/pdf` | Export notes payload as ReportLab PDF | Required (Clerk JWT) | `app.routes.study.export_pdf` |
| `GET` | `/api/study/download/pdf`| GET download notes PDF | Required (Clerk JWT) | `app.routes.study.download_pdf_get` |
| `POST` | `/api/study/export/docx` | Export notes payload as Word (.docx) | Required (Clerk JWT) | `app.routes.study.export_docx` |
| `GET` | `/api/study/download/docx`| GET download notes DOCX | Required (Clerk JWT) | `app.routes.study.download_docx_get` |
| `POST` | `/api/study/mcq` | Generate multiple-choice quiz questions | Required (Clerk JWT) | `app.routes.study.generate_mcqs` |
| `POST` | `/api/study/generate-pack`| Generate comprehensive study pack (notes, 20 MCQs, 5 short answers, glossary) | Required (Clerk JWT) | `app.routes.study.generate_pack` |
| `POST` | `/api/study/export-pack/pdf` | Export full study pack as ReportLab PDF | Required (Clerk JWT) | `app.routes.study.export_pack_pdf` |
| `POST` | `/api/study/export-pack/csv` | Export 20 MCQs as Anki-compatible CSV | Required (Clerk JWT) | `app.routes.study.export_pack_csv` |
| `POST` | `/api/study/generate-test`| Generate university Part-A (2-mark) test | Required (Clerk JWT) | `app.routes.study.generate_test` |
| `POST` | `/api/study/evaluate-answer`| Semantically evaluate student 2-mark answer | Required (Clerk JWT) | `app.routes.study.evaluate_answer` |
| `POST` | `/study-guide/upload` | Ad-hoc Map-Reduce PDF summarization & MCQs | Public | `app.study_guide.router.upload_study_guide_document` |
| `GET` | `/auth/github/login` | Initiate GitHub OAuth web redirect | Required (Clerk JWT) | `app.routes.github_auth.github_login` |
| `GET` | `/auth/github/callback` | OAuth redirect callback handler (HTML/JSON) | Public (State-bound) | `app.routes.github_auth.github_callback_get` |
| `GET` | `/auth/github/status` | Check if user has active GitHub connection | Required (Clerk JWT) | `app.routes.github_auth.github_status` |
| `POST` | `/auth/github/disconnect` | Revoke grant and delete GitHub token | Required (Clerk JWT) | `app.routes.github_auth.github_disconnect` |
| `GET` | `/api/integrations/status`| Return integration status (GitHub, Fetch MCP) | Required (Clerk JWT) | `app.routes.integrations.get_integration_status` |
| `GET` | `/api/integrations/health`| Health diagnostic for MCP tool connectors | Required (Clerk JWT) | `app.routes.integrations.get_integrations_health` |
| `POST` | `/api/integrations/github`| Save & encrypt GitHub Personal Access Token | Required (Clerk JWT) | `app.routes.integrations.save_github_pat` |
| `DELETE` | `/api/integrations/github`| Disconnect GitHub PAT integration | Required (Clerk JWT) | `app.routes.integrations.delete_github_integration` |
| `GET` | `/api/tools/fetch-url` | Proxy fetch external doc to clean Markdown | Required (Clerk JWT) | `app.routes.tools.fetch_url_get` |
| `POST` | `/api/tools/fetch-url` | Proxy fetch external doc via JSON body | Required (Clerk JWT) | `app.routes.tools.fetch_url_post` |
| `POST` | `/api/web/fetch` | Fetch MCP clean article extraction | Required (Clerk JWT) | `app.routes.web_research.fetch_webpage` |
| `POST` | `/api/web/ask` | Q&A grounded in fetched web article | Required (Clerk JWT) | `app.routes.web_research.ask_webpage_question` |
| `POST` | `/api/web/notes` | Synthesize study notes from web article | Required (Clerk JWT) | `app.routes.web_research.generate_web_study_notes` |
| `POST` | `/api/voice/transcribe` | Audio speech-to-text via Groq Whisper | Public | `app.routes.voice.transcribe` |
| `POST` | `/api/voice/synthesize` | Text-to-speech audio stream via Edge TTS | Public | `app.routes.voice.synthesize` |
| `POST` | `/api/chat/stream` | Real-time SSE token-streaming chat | Required (Clerk JWT) | `app.routes.llm.chat_stream` |
| `POST` | `/api/chat/message` | Synchronous direct chat message execution | Required (Clerk JWT) | `app.routes.llm.chat_message` |
| `POST` | `/chatbot` | Legacy health / echo endpoint | Public | `app.routes.llm.chatbot` |

---

## 9. External Services Architecture

```mermaid
flowchart LR
    App["AI Study Assistant Core"]
    
    subgraph IdentityService ["1. Identity & Auth"]
        Clerk["Clerk Identity Platform: Session JWTs & JWKS Public Keys"]
    end

    subgraph DatabaseCloud ["2. Managed Persistence & Search"]
        Atlas[("MongoDB Atlas: Vector Search & Documents")]
    end

    subgraph LLMProviders ["3. LLM & Inference Providers"]
        MistralAI["Mistral AI: mistral-small-latest"]
        GroqCloud["Groq Cloud: openai/gpt-oss-20b"]
        GoogleAI["Google Generative AI: Gemini 3.5 Flash Lite & Gemini Embeddings"]
    end

    subgraph SpeechServices ["4. Voice & Speech Subsystems"]
        WhisperAPI["Groq Whisper API: whisper-large-v3"]
        EdgeTTSAPI["Microsoft Edge TTS: en-US-JennyNeural"]
    end

    subgraph ExternalWebAndCode ["5. External Web & Code Resources"]
        GitHub["GitHub REST API & Copilot MCP"]
        JinaReader["Jina AI Reader Proxy: r.jina.ai"]
        TavilySearch["Tavily Search API"]
    end

    App <--> Clerk
    App <--> Atlas
    App --> MistralAI
    App --> GroqCloud
    App --> GoogleAI
    App --> WhisperAPI
    App --> EdgeTTSAPI
    App <--> GitHub
    App --> JinaReader
    App --> TavilySearch
```

---

## 10. Security Architecture

```mermaid
flowchart TD
    subgraph InboundSecurity ["1. Inbound Network & Auth Security"]
        Req["Client Request"] --> CORS["CORS Middleware: Strict Origin Whitelist & Regex"]
        CORS --> RateLimitCheck["Input Sanitization & Buffer Size Limit: 50MB"]
        RateLimitCheck --> AuthDep["HTTPBearer: get_current_user Dependency"]
        AuthDep --> JWKS["Clerk RS256 Verification with In-Memory Key Cache 1hr"]
    end

    subgraph TokenEncryption ["2. Credentials Encryption (At Rest)"]
        GH_Token["Student GitHub OAuth Token / PAT"] --> FernetKey["TOKEN_ENCRYPTION_KEY: 256-bit AES Fernet"]
        FernetKey --> EncryptedString["Encrypted Ciphertext Stored in MongoDB github_tokens"]
        EncryptedString --> DecryptOnDemand["Decrypted in memory ONLY during active tool calls"]
    end

    subgraph TenantIsolation ["3. Tenant Boundary Enforcement"]
        DecodedUser["current_user sub"] --> DocTag["Stamp all uploaded chunks with user_id"]
        DecodedUser --> RAGFilter["Hard Filter: user_id = current_user.sub and doc_id = doc_id"]
        RAGFilter --> PreventLeakage["Cross-tenant data access strictly impossible"]
    end

    subgraph SSRFProtection ["4. Web Reader SSRF Defense"]
        TargetURL["External Web URL"] --> URLValidator["validate_public_url in web_content_service.py"]
        URLValidator --> IPBlock["Block localhost, 127.0.0.1, private RFC-1918 subnets, cloud metadata"]
        URLValidator --> SchemeCheck["Enforce HTTP / HTTPS scheme only"]
    end
```

---

## 11. Deployment Architecture

```mermaid
flowchart LR
    subgraph ClientHosting ["Vercel Edge Network (Frontend)"]
        UserBrowser["User Browser"] --> VercelCDN["Vercel Global CDN"]
        VercelCDN --> ReactBundle["Compiled React 19 Vite Static Bundle"]
        ReactBundle --> VercelRouting["vercel.json: SPA Rewrites /* to /index.html"]
    end

    subgraph BackendHosting ["Render Cloud Platform (Backend)"]
        VercelCDN -->|HTTPS API Requests / SSE Streams| RenderLoadBalancer["Render Load Balancer / Proxy"]
        RenderLoadBalancer --> UvicornProcess["Uvicorn Workers: server.py on 0.0.0.0:PORT"]
        UvicornProcess --> FastAPIInstance["FastAPI Application Instance"]
    end

    subgraph DatabaseHosting ["MongoDB Atlas Cloud (Database)"]
        FastAPIInstance -->|Encrypted TLS Motor Driver| AtlasCluster[("MongoDB Atlas Cluster: Replica Set")]
        AtlasCluster --> VectorIndexes["Atlas Vector Search Engine: cosine 384 dims"]
    end

    subgraph ExternalClouds ["External Cloud Services"]
        UserBrowser <--> ClerkPlatform["Clerk Auth Platform"]
        FastAPIInstance --> ClerkPlatform
        FastAPIInstance --> MistralCloud["Mistral AI API"]
        FastAPIInstance --> GroqPlatform["Groq Inference Engine"]
        FastAPIInstance --> GoogleCloud["Google Gemini AI"]
        FastAPIInstance <--> GitHubPlatform["GitHub API"]
    end
```

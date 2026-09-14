# AI Study Assistant — System Workflow Documentation

This document describes the end-to-end execution workflows of the **AI Study Assistant (StudySync AI)** application based on the actual implementation in the codebase.

---

## 1. Application Overview

**AI Study Assistant (StudySync AI)** is a full-stack, university-tailored curriculum and study copilot. The platform enables engineering students to:
- Navigate course syllabi, curriculum regulations, and credit distributions.
- Synthesize structured, high-yield academic study notes calibrated by academic difficulty (`beginner`, `intermediate`, `advanced`).
- Practice with calibrated multiple-choice questions (MCQs) featuring instant feedback, distractors, and conceptual explanations.
- Generate and evaluate university Part-A (2-mark) conceptual exams with automated semantic grading (0, 1, or 2 marks) against scoring rubrics.
- Upload and index personal lecture slides, question banks, and textbook PDFs up to 50MB/50 pages in an isolated vector knowledge vault.
- Inspect student GitHub repositories, browse source files, check commits, and run automated code reviews via GitHub Model Context Protocol (MCP) and REST tools.
- Read live external web documentation and synthesize study guides via Fetch MCP with automated boilerplate stripping.
- Interact via voice using Groq Whisper speech-to-text (STT) and Microsoft Edge TTS neural voice playback.

---

## 2. Complete System Workflow

The complete end-to-end workflow connects student actions in the React frontend through Clerk authentication, FastAPI gateway dispatch, LangGraph multi-agent orchestration, the two-tier RAG retrieval pipeline, multi-provider LLM failover, and dynamic document generation.

```mermaid
flowchart TD
    subgraph UserLayer ["1. User Interaction Layer"]
        Student([Student / User]) -->|Action: Chat / Upload / Notes / Quiz / Test / Code Review| ReactApp["React 19 SPA Frontend"]
    end

    subgraph AuthCheck ["2. Authentication Gate"]
        ReactApp -->|Check Clerk Session| ClerkGate{"Authenticated?"}
        ClerkGate -- "No" --> ClerkModal["Clerk SignIn / SignUp Modal"]
        ClerkGate -- "Yes" --> TokenProvider["AuthContext: Retrieve Valid JWT"]
    end

    subgraph APIGateway ["3. FastAPI Backend Gateway"]
        TokenProvider -->|HTTP Request / SSE Stream + Bearer Token| APIRoute["FastAPI Endpoint Router"]
        APIRoute --> AuthDep["get_current_user Dependency"]
        AuthDep --> JWKSCache["Verify RS256 JWT via Clerk JWKS Cache"]
        JWKSCache --> UserContext["Inject current_user sub into Request Scope"]
    end

    subgraph CoreProcessing ["4. Application Logic & Agent Dispatch"]
        UserContext --> ActionType{"Request Type"}
        
        ActionType -- "Chat / Workbench" --> SupervisorGraph["Supervisor LangGraph: chat_service.py"]
        ActionType -- "Document Ingestion" --> IngestionPipeline["user_doc_service.py: Process User PDF"]
        ActionType -- "Study Notes" --> StudyNotesGen["study_generator.py / studynotes Subgraph"]
        ActionType -- "MCQ Quiz" --> MCQGen["study_generator.py / mcq Subgraph"]
        ActionType -- "2-Mark Test & Eval" --> EvalService["evaluation_service.py: Exam Generator & Grader"]
        ActionType -- "Ad-hoc PDF Summary" --> MapReduceEngine["app.study_guide: Map-Reduce Engine"]
        ActionType -- "Voice STT / TTS" --> SpeechEngine["speech_service.py: Groq Whisper & Edge TTS"]
    end

    subgraph DataAndTools ["5. Database, RAG, MCP & LLM Services"]
        SupervisorGraph -->|curriculum / study_notes / mcq| RAGSystem["Two-Tier RAG Engine"]
        SupervisorGraph -->|github| GHTools["GitHub MCP / REST Tools + Fernet Decryption"]
        SupervisorGraph -->|fetch_web| FetchMCP["Fetch MCP Web Reader + Jina Proxy Fallback"]
        
        IngestionPipeline --> Embeddings["Google Gemini Embeddings: 384 dims"]
        Embeddings --> UserDocsColl[("MongoDB: user_documents")]
        
        RAGSystem -->|Tier 1: Global Syllabus| SyllabusColl[("MongoDB: syllabus_vectors")]
        RAGSystem -->|Tier 2: User Upload| UserDocsColl
        
        GHTools --> TokenColl[("MongoDB: github_tokens")]
        GHTools --> GitHubAPI["GitHub REST / Copilot API"]
        
        SupervisorGraph --> LLMFailover["LLM Fallback Chain"]
        StudyNotesGen --> LLMFailover
        MCQGen --> LLMFailover
        EvalService --> LLMFailover
        MapReduceEngine --> LLMFailover

        LLMFailover -->|Primary| Mistral["Mistral Small"]
        Mistral -.->|Failover 1| GroqLLM["Groq gpt-oss-20b"]
        GroqLLM -.->|Failover 2| GeminiLLM["Google Gemini 3.5 Flash Lite"]
    end

    subgraph ResponseDelivery ["6. Response Delivery & Export"]
        LLMFailover --> FormatResponse["Format Markdown / JSON / Pydantic Data"]
        FormatResponse --> StreamOrJSON{"Response Mode"}
        StreamOrJSON -- "SSE Stream" --> SSEStreamer["Server-Sent Events Stream: /api/chat/stream"]
        StreamOrJSON -- "JSON Payload" --> JSONResp["FastAPI JSON Response"]
        FormatResponse -- "Export Request" --> ExportEngine["export_service.py: ReportLab PDF / python-docx DOCX"]
        
        SSEStreamer --> ReactApp
        JSONResp --> ReactApp
        ExportEngine --> ReactApp
        ReactApp --> Student
    end
```

---

## 3. User Authentication Workflow

The application secures all operations using **Clerk** session tokens and **AES-Fernet** encrypted OAuth linking for GitHub.

```mermaid
sequenceDiagram
    autonumber
    participant Student as User Browser
    participant Clerk as Clerk Identity Service
    participant AuthCtx as Frontend AuthContext
    participant ClientJS as Frontend client.js
    participant API as FastAPI Backend (dependencies.py)
    participant ClerkJWKS as Clerk JWKS Endpoint
    participant TokenStore as MongoDB (github_tokens)

    %% Authentication Flow
    Note over Student,API: 1. User Sign-In & JWT Lifecycle
    Student->>Clerk: User signs in (Email / Social)
    Clerk-->>AuthCtx: Issue RS256 Session JWT
    AuthCtx->>ClientJS: Register dynamicTokenProvider(skipCache)
    
    Student->>ClientJS: Trigger API call (e.g. List Documents)
    ClientJS->>ClientJS: isJwtExpired(token) pre-check
    alt Token Expired
        ClientJS->>Clerk: getToken({ skipCache: true })
        Clerk-->>ClientJS: Fresh Session JWT
    end
    
    ClientJS->>API: HTTP Request with Header Authorization Bearer Token
    API->>API: get_current_user(request)
    alt Development Bypass Token (dev_*, student_demo_user)
        API-->>API: Return mock scholar payload
    else Real Clerk JWT
        API->>API: Extract kid from JWT header
        API->>ClerkJWKS: Fetch JWKS public keys (cached in-memory 1hr)
        ClerkJWKS-->>API: RSA Public Key Set
        API->>API: Verify RS256 signature, exp, nbf, and issuer
        API->>API: Extract sub claim as user_id
    end
    API-->>ClientJS: Authenticated Response (HTTP 200)

    %% GitHub Account Linking Flow
    Note over Student,TokenStore: 2. GitHub OAuth Linking & Fernet Encryption
    Student->>API: GET /auth/github/login?return_to=...
    API->>API: Generate HS256 state JWT signed with TOKEN_ENCRYPTION_KEY encoding user_id
    API-->>Student: 307 Redirect to GitHub OAuth Consent Screen
    Student->>Student: Authorize application on GitHub
    Student->>API: GitHub redirects to GET /auth/github/callback?code=...&state=...
    API->>API: Verify state JWT & decode user_id
    API->>API: Exchange code for GitHub access token (POST github.com/login/oauth/access_token)
    API->>API: Encrypt token with Fernet symmetric key (TOKEN_ENCRYPTION_KEY)
    API->>TokenStore: Upsert into github_tokens (clerk_user_id, encrypted_token, github_login)
    API-->>Student: Render HTML popup with postMessage GITHUB_AUTH_SUCCESS
    Student->>AuthCtx: Handle message, close popup, show success toast
```

---

## 4. Document Upload & Ingestion Workflow

Student PDFs are ingested through a strict validation, extraction, chunking, and embedding pipeline into tenant-isolated storage.

```mermaid
flowchart TD
    StartUpload([Student selects PDF file]) --> ClientCheck{"Client Validation"}
    ClientCheck -- "File > 25MB" --> ToastLimit["Toast Error: Max 25MB"]
    ClientCheck -- "Non-PDF" --> ToastExt["Toast Error: Only PDF supported"]
    ClientCheck -- "Valid" --> XHRPush["XHR POST /api/documents/upload with progress tracking"]

    subgraph BackendGateway ["FastAPI Validation Layer"]
        XHRPush --> StreamRead["Chunked byte streaming in 1MB chunks"]
        StreamRead --> SizeGuard{"Total bytes <= 50MB?"}
        SizeGuard -- "Exceeds" --> HTTP413["HTTP 413: Request Entity Too Large"]
        SizeGuard -- "Pass" --> MagicGuard{"Starts with %PDF magic bytes?"}
        MagicGuard -- "False" --> HTTP400Bad["HTTP 400: Invalid PDF Header"]
        MagicGuard -- "True" --> PageCheck["validate_and_count_pages via pypdf"]
        PageCheck --> PageLimitGuard{"Total Pages <= 50?"}
        PageLimitGuard -- "Exceeds" --> HTTP400Page["HTTP 400: Exceeds 50 pages limit"]
    end

    subgraph ExtractionWorker ["Extraction & Chunking Worker (asyncio.to_thread)"]
        PageLimitGuard -- "Pass" --> GenUUID["Generate unique UUID4 doc_id"]
        GenUUID --> WriteTemp["Write bytes to NamedTemporaryFile"]
        WriteTemp --> FastExtract["extract_pdf: pypdf primary extractor"]
        FastExtract -.->|If pypdf fails| PlumberExtract["Fallback: pdfplumber extractor with tables"]
        FastExtract --> UnlinkTemp["Delete NamedTemporaryFile"]
        PlumberExtract --> UnlinkTemp
        
        UnlinkTemp --> FrontMatterCheck["is_front_matter: Filter copyright, ISBN, TOC pages"]
        FrontMatterCheck --> CleanPages["Substantive Content Pages"]
        CleanPages --> ChunkDoc["chunk_document: RecursiveCharacterTextSplitter chunk_size=800, overlap=100"]
        ChunkDoc --> TablePreserve["Preserve markdown tables intact as contiguous chunks"]
        TablePreserve --> TagRecords["Tag every chunk with: user_id, doc_id, filename, chunk_id, page_number"]
    end

    subgraph EmbedAndStore ["Embedding & Vector Storage"]
        TagRecords --> BatchSplit["Split chunks into batches of 64: EMBEDDING_BATCH_SIZE"]
        BatchSplit --> GeminiBatch["embed_texts via GoogleGenerativeAIEmbeddings: 384 dims"]
        GeminiBatch --> RateLimitCatch{"Rate Limit 429?"}
        RateLimitCatch -- "Yes" --> RegexDelay["Extract retryDelay from error & sleep"]
        RegexDelay --> GeminiBatch
        RateLimitCatch -- "No" --> InsertChunks["Insert batch into MongoDB user_documents"]
    end

    InsertChunks --> RetSummary["Return HTTP 201: doc_id, filename, total_chunks, total_pages"]
    RetSummary --> UpdateVault["Frontend updates Document Vault list & selects doc_id"]
```

---

## 5. RAG Retrieval Workflow

The system provides a **Two-Tier Hybrid RAG Architecture** with automatic fallback mechanisms.

```mermaid
flowchart TD
    UserQuery["User Query / Study Topic Request"] --> TargetCheck{"Target Document"}

    subgraph Tier1Syllabus ["Tier 1: Global Syllabus Retrieval (vector_store.py)"]
        TargetCheck -- "doc_id == 'syllabus'" --> HybridSearch["VectorStore.retrieve: Hybrid Search"]
        HybridSearch --> QEmbed1["embed_query: Compute 384-dim vector via Gemini"]
        
        QEmbed1 --> AtlasVecSearch["vectorSearch aggregation on syllabus_vector_index top_k=10"]
        HybridSearch --> MongoTextSearch["text keyword search on syllabus_text_index top_k=10"]
        
        AtlasVecSearch -.->|If Atlas Search unindexed| InMemCosine1["In-Memory NumPy Cosine Similarity"]
        MongoTextSearch -.->|If Text Index unindexed| RegexSearch["Regex Substring Keyword Search"]
        
        AtlasVecSearch --> RRF["merge_rrf: Reciprocal Rank Fusion k=60"]
        InMemCosine1 --> RRF
        MongoTextSearch --> RRF
        RegexSearch --> RRF
        RRF --> Tier1Ranked["Top 5 fused chunks with metadata & semester"]
    end

    subgraph Tier2UserDoc ["Tier 2: Tenant-Isolated Document Retrieval (user_doc_retriever.py)"]
        TargetCheck -- "doc_id == UUID" --> UserDocRetriever["get_user_doc_context: Scoped to current user"]
        UserDocRetriever --> GenericQueryCheck{"Is query generic / empty / broad summary?"}
        
        GenericQueryCheck -- "Yes" --> DirectSequential["direct_chunk_fetch: Fetch chunks ordered by page_number"]
        GenericQueryCheck -- "No" --> QEmbed2["embed_query: Dense Vector Embedding"]
        
        QEmbed2 --> UserAtlasVec["atlas_vector_search: vectorSearch with user_id + doc_id filter"]
        UserAtlasVec -.->|If Atlas search fails| UserInMemCosine["in_memory_similarity_search: Filter by user_id & doc_id"]
        UserInMemCosine -.->|If no vectors found| DirectSequential
        
        UserAtlasVec --> Tier2Ranked["Top 8 tenant-isolated chunks with page numbers"]
        UserInMemCosine --> Tier2Ranked
        DirectSequential --> Tier2Ranked
    end

    Tier1Ranked --> FormatContext["format_user_doc_context: Format markdown with Page Excerpts"]
    Tier2Ranked --> FormatContext
    FormatContext --> SufficiencyEval["app.ai.context_evaluator: evaluate_context_sufficiency"]
    SufficiencyEval --> FinalPrompt["Inject formatted context into LLM Agent Prompt"]
```

---

## 6. Study Guide Generation Workflow

Study guides are synthesized either through the LangGraph `study_notes` subgraph, the direct adaptive study generator, or the Map-Reduce full document summarizer.

```mermaid
flowchart TD
    StartGuide([Student requests Study Notes]) --> SourceSelect{"Selected Source"}
    
    SourceSelect -- "Web URL Provided" --> WebFetchPath["FetchMCPService: Fetch URL & convert to Markdown"]
    SourceSelect -- "Uploaded Document / Syllabus" --> RetrieveContext["Fetch Context from user_documents / syllabus_vectors"]
    
    WebFetchPath --> CleanWebDoc["clean_markdown_content: Strip boilerplate & navigation"]
    RetrieveContext --> RouteDispatch{"Execution Route"}
    CleanWebDoc --> RouteDispatch

    subgraph SubgraphRoute ["Option A: LangGraph StudyNotes Subgraph"]
        RouteDispatch -- "Interactive Chat / Stream" --> NotesAgentNode["studynotes Subgraph: generate_notes"]
        NotesAgentNode --> EvalSufficiency{"Context Sufficient?"}
        EvalSufficiency -- "No" --> FetchEnrich["fetch_web_node: Enrich with Fetch MCP"]
        FetchEnrich --> ValidateWeb["validate_web_node: Source Validator"]
        ValidateWeb --> SynthNotes["LLM Synthesis: AdaptiveStudyNotes Schema"]
        EvalSufficiency -- "Yes" --> SynthNotes
    end

    subgraph DirectRoute ["Option B: Direct Adaptive Generator (study_generator.py)"]
        RouteDispatch -- "POST /api/study/notes" --> CalibratePrompt["get_difficulty_notes_prompt: beginner / intermediate / advanced"]
        CalibratePrompt --> GeminiStructured["ChatGoogleGenerativeAI with_structured_output AdaptiveStudyNotes"]
        GeminiStructured --> ValidatedPydantic["AdaptiveStudyNotes: title, executive_summary, sections, actionable_takeaways"]
    end

    subgraph MapReduceRoute ["Option C: Ad-hoc PDF Map-Reduce (summarizer.py)"]
        RouteDispatch -- "POST /study-guide/upload" --> HeaderStrip["strip_repeated_headers_and_footers"]
        HeaderStrip --> SplitChunks["Split full text into 3,000 char chunks with 200 char overlap"]
        SplitChunks --> MapStep["MAP STEP: Summarize each chunk with Mistral Small"]
        MapStep --> ReduceStep{"Total chunks <= 15?"}
        ReduceStep -- "Yes" --> DirectReduce["REDUCE STEP: Single final comprehensive synthesis"]
        ReduceStep -- "No" --> RecursiveReduce["REDUCE STEP: Recursive batch reduction in groups of 10"]
        DirectReduce --> CohesiveSummary["Cohesive Document Overview"]
        RecursiveReduce --> CohesiveSummary
    end

    ValidatedPydantic --> UIViewer["Render StudyDocumentViewer Component"]
    SynthNotes --> UIViewer
    CohesiveSummary --> UIViewer
    
    subgraph ExportWorkflow ["Export & Download Pipeline"]
        UIViewer --> ExportAction{"Student clicks Export"}
        ExportAction -- "PDF" --> GenReportLab["export_service.py: Build ReportLab Platypus PDF in-memory"]
        ExportAction -- "DOCX" --> GenDocx["export_service.py: Build python-docx document in-memory"]
        GenReportLab --> StreamPDF["StreamingResponse: application/pdf attachment"]
        GenDocx --> StreamDOCX["StreamingResponse: openxmlformats attachment"]
    end
```

---

## 7. Quiz & MCQ Workflow

Multiple-choice quizzes and 2-mark conceptual exams are generated, displayed interactively, and semantically evaluated.

```mermaid
flowchart TD
    StartQuiz([Student selects Quiz / Exam Mode]) --> QuizType{"Quiz Mode"}

    subgraph MCQWorkflow ["1. Multiple Choice Quiz (MCQ) Pipeline"]
        QuizType -- "MCQ Quiz" --> MCQParams["Configure doc_id, count: 1-20, difficulty: beginner/intermediate/advanced"]
        MCQParams --> CallMCQAPI["POST /api/study/mcq"]
        CallMCQAPI --> RetrieveMCQContext["Retrieve RAG Context or Fetch Web Content"]
        RetrieveMCQContext --> MCQPromptCalib["get_difficulty_mcq_prompt: Calibrate question depth & distractor subtlety"]
        MCQPromptCalib --> GenQuizDeck["ChatGoogleGenerativeAI with_structured_output QuizDeck"]
        GenQuizDeck --> PydanticDeck["QuizDeck: exactly 4 options per question, correct_index 0-3, explanation"]
        PydanticDeck --> MCQArenaUI["Render MCQArena: choice selection, immediate color feedback"]
        MCQArenaUI --> CompleteQuiz["Student finishes quiz: calculate score, trigger confetti animation"]
    end

    subgraph TwoMarkExamWorkflow ["2. University 2-Mark Exam & Semantic Grading Pipeline"]
        QuizType -- "2-Mark Test" --> TestParams["Configure doc_id or pasted text, question_count: 5-20"]
        TestParams --> CallTestAPI["POST /api/study/generate-test"]
        CallTestAPI --> GenTwoMarkTest["evaluation_service.py: generate_two_mark_test"]
        GenTwoMarkTest --> TestDeckPydantic["TwoMarkTestDeck: Questions Q1-Qn, model_answer, key_points: exactly 2 scoring points"]
        TestDeckPydantic --> TestArenaUI["Render TwoMarkTestArena: display questions with answer input textareas"]
        
        TestArenaUI --> SubmitAnswer["Student submits written answer for Q_i"]
        SubmitAnswer --> CallEvalAPI["POST /api/study/evaluate-answer"]
        CallEvalAPI --> EvaluateAnswer["evaluation_service.py: evaluate_student_answer_async"]
        EvaluateAnswer --> SemanticRubricEval["LLM evaluates semantically against 2 rubric points"]
        SemanticRubricEval --> EvalResult["EvaluationResult: score 0, 1, or 2 marks, points_covered, points_missed, feedback"]
        EvalResult --> DisplayFeedback["Update UI: badge score, itemized points breakdown, model answer review"]
    end
```

---

## 8. Model Context Protocol (MCP) Workflow

The system incorporates two distinct MCP integrations: **Fetch MCP** (web extraction) and **GitHub MCP** (code and repo operations).

```mermaid
flowchart TD
    UserQuery["User Query / Action"] --> IntentCheck{"Router Classification"}

    subgraph FetchMCPPipeline ["1. Fetch MCP: Web Documentation Reader"]
        IntentCheck -- "URL detected / Sparse RAG / enable_web" --> TriggerFetch["FetchMCPService.fetch_web_content"]
        TriggerFetch --> CheckCache{"Cache HIT in FetchCache? 15 min TTL"}
        CheckCache -- "Yes" --> ReturnCached["Return cached Markdown"]
        CheckCache -- "No" --> HTTPXFetch["httpx.AsyncClient GET with Academic User-Agent timeout=9s"]
        
        HTTPXFetch --> StatusCodeCheck{"HTTP Status"}
        StatusCodeCheck -- "200 OK" --> ParseHTML["html2text: Clean HTML to structured Markdown"]
        StatusCodeCheck -- "401 / 403 / 503" --> JinaReaderProxy["Fallback: GET https://r.jina.ai/URL"]
        JinaReaderProxy --> ParseHTML
        StatusCodeCheck -- "5xx / Timeout" --> SafeWebError["Return error dict without crashing agent loop"]
        
        ParseHTML --> ValidateAcademic["source_validator.py: Score credibility & filter ads"]
        ValidateAcademic --> MergeContext["format_combined_evidence: Merge RAG + Web with citations"]
    end

    subgraph GitHubMCPPipeline ["2. GitHub MCP: Repository & Code Inspection"]
        IntentCheck -- "Intent == GITHUB / GitHub Workbench" --> GHAgentNode["github_agent_node"]
        GHAgentNode --> DecryptToken["token_store.py: Decrypt GitHub access token via Fernet"]
        
        DecryptToken --> TokenStatus{"Token valid & active?"}
        TokenStatus -- "No / Missing" --> ReturnConnGuide["Return Markdown setup instructions for GitHub connection"]
        TokenStatus -- "Yes" --> LoadTools["get_github_mcp_tools: Load 32 essential tools or native REST tools"]
        
        LoadTools --> ToolBindLoop["LLM multi-turn tool-calling loop max 3 turns"]
        ToolBindLoop --> ExecTools["Execute search_repos, get_file_contents, list_commits, search_code"]
        ExecTools --> SynthReview["LLM synthesizes academic code review / repository summary in Markdown"]
    end

    MergeContext --> FinalResponse["Deliver response to student UI"]
    SynthReview --> FinalResponse
    SafeWebError --> FinalResponse
    ReturnConnGuide --> FinalResponse
```

---

## 9. Database Interaction Workflow

The following diagram illustrates which backend components interact with each MongoDB Atlas collection.

```mermaid
flowchart LR
    subgraph FrontendActions ["Frontend Triggers"]
        UploadDoc["Document Upload"]
        ChatQuery["Chat & Copilot Queries"]
        ListDocs["Vault Listing"]
        DeleteDoc["Document Deletion"]
        LinkGH["GitHub OAuth Linking"]
        GHAction["GitHub Workbench Action"]
    end

    subgraph BackendServices ["Backend Services"]
        UserDocSvc["user_doc_service.py"]
        DocRetriever["user_doc_retriever.py"]
        VecStore["vector_store.py"]
        DocsRoute["routes/documents.py"]
        TokenStore["token_store.py"]
        GHAgent["github_agent.py"]
    end

    subgraph MongoCollections ["MongoDB Atlas (DB: Study_plan_generator / Chatbot)"]
        UserDocsColl[("user_documents")]
        SyllabusColl[("syllabus_vectors")]
        GHTokensColl[("github_tokens")]
    end

    UploadDoc --> UserDocSvc
    UserDocSvc -->|Insert chunk records & vectors| UserDocsColl
    
    ListDocs --> DocsRoute
    DocsRoute -->|Aggregate doc_id, filename, chunks| UserDocsColl
    
    DeleteDoc --> DocsRoute
    DocsRoute -->|Delete by user_id & doc_id| UserDocsColl
    
    ChatQuery --> DocRetriever
    DocRetriever -->|Query by user_id & doc_id| UserDocsColl
    
    ChatQuery --> VecStore
    VecStore -->|Hybrid RRF vector & text search| SyllabusColl
    
    LinkGH --> TokenStore
    TokenStore -->|Upsert Fernet encrypted token| GHTokensColl
    
    GHAction --> GHAgent
    GHAgent --> TokenStore
    TokenStore -->|Find & decrypt token| GHTokensColl
```

---

## 10. Error Handling & Fallback Workflow

The application employs defensive fallback mechanisms to ensure 100% uptime and graceful degradation.

```mermaid
flowchart TD
    TriggerEvent["Incoming Request / Operation"] --> FailurePoint{"Failure Type"}

    subgraph SchemaFailures ["1. Request & Validation Failures"]
        FailurePoint -- "Invalid JSON / Missing Fields" --> FastAPIVAL["RequestValidationError"]
        FastAPIVAL --> GlobalHandler["validation_exception_handler in main.py"]
        GlobalHandler --> Res422["Return HTTP 422 with actionable schema guidance & example payload"]
    end

    subgraph IngestionFailures ["2. Document Ingestion Failures"]
        FailurePoint -- "Corrupt PDF / Empty File / >50 Pages" --> IngestGuard["validate_and_count_pages / magic check"]
        IngestGuard --> Res400["Return HTTP 400 with descriptive error detail"]
    end

    subgraph LLMRateLimits ["3. LLM Rate Limits & Quotas"]
        FailurePoint -- "Google Gemini 429 Resource Exhausted" --> EmbedRetry["embed_batch_with_retry: Regex match retryDelay"]
        EmbedRetry --> SleepDelay["Sleep calculated seconds: max retryDelay+2, 20s"]
        SleepDelay --> RetryAttempt{"Retry <= 6 attempts?"}
        RetryAttempt -- "Yes" --> EmbedRetry
        RetryAttempt -- "No" --> LLMFailover["Failover to Groq gpt-oss-20b -> Gemini Flash"]
    end

    subgraph WebExtractionFailures ["4. Web Reader Anti-Bot / Network Errors"]
        FailurePoint -- "HTTP 401 / 403 Forbidden / 503" --> DirectHTTPFail["httpx.AsyncClient status >= 400"]
        DirectHTTPFail --> JinaProxy["Call r.jina.ai proxy reader"]
        JinaProxy --> JinaCheck{"Proxy Status == 200?"}
        JinaCheck -- "Yes" --> ParseReader["Extract title & markdown content"]
        JinaCheck -- "No" --> SoftFailWeb["Return status: error dict; Agent continues using RAG alone without crashing"]
    end

    subgraph AuthExpirationFailures ["5. Expired Clerk JWT"]
        FailurePoint -- "HTTP 401: Token Expired" --> ClientInterceptor["client.js apiRequest Interceptor"]
        ClientInterceptor --> RefreshSession["Call dynamicTokenProvider with skipCache=true"]
        RefreshSession --> ReplayRequest["Replay failed HTTP request once with fresh token"]
        ReplayRequest --> ReplayResult{"Success?"}
        ReplayResult -- "Yes" --> ClientSuccess["Return data transparently to caller"]
        ReplayResult -- "No" --> PromptLogin["Clear stale localStorage token & prompt sign in"]
    end
```

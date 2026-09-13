import logging
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routes import documents, github_auth, integrations, llm, study, voice
from app.db.mongodb import connect_to_mongo, close_mongo_connection

logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.
    """
    # Startup
    await connect_to_mongo()

    tracing_active = (
        os.environ.get("LANGSMITH_TRACING", "").lower() in ("true", "1")
        or os.environ.get("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1")
    )
    project = os.environ.get("LANGSMITH_PROJECT") or os.environ.get("LANGCHAIN_PROJECT") or "study-guide-generator"
    logger.info(f"[LangSmith] Tracing active: {tracing_active} | Project: {project}")


    yield

    # Shutdown
    await close_mongo_connection()


app = FastAPI(
    title="AI Study Assistant",
    description="AI-powered personalized study assistant",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    """
    Global handler for JSON body parse errors and
    Pydantic validation failures.
    """
    return JSONResponse(
        status_code=422,
        content={
            "error": (
                "Invalid request body. Ensure you are sending valid JSON "
                "with the Content-Type: application/json header."
            ),
            "details": exc.errors(),
            "example": {
                "user_prompt": "Explain Chapter 1 concepts"
            },
        },
    )


# Allowed frontend origins
_allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://study-guide-generator-teal.vercel.app",

]

_frontend_env = os.getenv("FRONTEND_URL", "").strip()
if _frontend_env:
    for url in _frontend_env.split(","):
        clean_url = url.strip().rstrip("/")
        if clean_url and clean_url not in _allowed_origins:
            _allowed_origins.append(clean_url)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure outputs directory exists and mount static files
outputs_dir = os.path.abspath("outputs")
os.makedirs(outputs_dir, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=outputs_dir), name="outputs")


@app.get("/")
def landing_page():
    return {
        "message": "AI Study Assistant API",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint exposing service and LangSmith tracing state.
    """
    tracing_active = (
        os.environ.get("LANGSMITH_TRACING", "").lower() in ("true", "1")
        or os.environ.get("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1")
    )
    project = os.environ.get("LANGSMITH_PROJECT") or os.environ.get("LANGCHAIN_PROJECT") or "study-guide-generator"
    return {
        "status": "ok",
        "service": "ai-study-assistant",
        "langsmith_tracing": tracing_active,
        "langsmith_project": project,
    }




from app.routes.integrations import router as integrations_router
from app.routes.tools import router as tools_router
from app.routes.web_research import router as web_research_router
from app.study_guide.router import router as study_guide_router

# API routes
app.include_router(github_auth.router)
app.include_router(integrations_router)
app.include_router(tools_router)
app.include_router(web_research_router)
app.include_router(documents.router)
app.include_router(study.router)
app.include_router(study_guide_router)
app.include_router(voice.router)
app.include_router(llm.router)

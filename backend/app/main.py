from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routes import documents, github_auth, integrations, llm, study, voice
from app.db.mongodb import connect_to_mongo, close_mongo_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.
    """
    # Startup
    await connect_to_mongo()

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
]

_frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
if _frontend_url and _frontend_url not in _allowed_origins:
    _allowed_origins.append(_frontend_url)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
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
    Health check endpoint.
    """
    return {
        "status": "ok",
        "service": "ai-study-assistant"
    }


from app.routes.integrations import router as integrations_router
from app.routes.tools import router as tools_router
from app.routes.web_research import router as web_research_router
from app.study_guide.router import router as study_guide_router

# API routes
app.include_router(github_auth.router)
app.include_router(github_auth.router, prefix="/api")
app.include_router(integrations_router)
app.include_router(tools_router)
app.include_router(web_research_router)
app.include_router(documents.router)
app.include_router(study.router)
app.include_router(study_guide_router)
app.include_router(voice.router)
app.include_router(llm.router)

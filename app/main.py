from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.routes import llm
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


# API routes
app.include_router(llm.router)

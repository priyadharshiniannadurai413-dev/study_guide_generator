import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Find .env in backend directory or parent directories
_current_dir = os.path.dirname(os.path.abspath(__file__))  # app/core
_backend_dir = os.path.dirname(os.path.dirname(_current_dir))  # backend
_env_path = os.path.join(_backend_dir, ".env")

if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()


class Settings(BaseSettings):
    """
    Application settings and environment configuration.
    Uses pydantic-settings to validate and read environment variables.
    """
    # Application metadata
    APP_NAME: str = "AI Study Assistant"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # LLM and Tool API Keys
    GEMINI_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None

    # LangSmith & LangChain Tracing
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "study-guide-generator"
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: Optional[str] = "study-guide-generator"
    LANGSMITH_TRACING: bool = False


    # MongoDB Configuration
    MONGODB_URL: Optional[str] = None
    MONGODB_URI: Optional[str] = None  # Backward-compatibility alias
    DB_NAME: str = "Study_plan_generator"

    # GitHub OAuth & Legacy PAT
    GITHUB_API_KEY: Optional[str] = None  # Legacy PAT (optional)
    GITHUB_CLIENT_ID: Optional[str] = None  # Standard OAuth alias
    GITHUB_OAUTH_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None  # Standard OAuth alias
    GITHUB_OAUTH_CLIENT_SECRET: Optional[str] = None
    GITHUB_OAUTH_REDIRECT_URI: Optional[str] = None
    GITHUB_REDIRECT_URI: Optional[str] = None  # Alias for GITHUB_OAUTH_REDIRECT_URI

    # Token Encryption Key for stored OAuth credentials
    TOKEN_ENCRYPTION_KEY: Optional[str] = None

    # Clerk Authentication
    CLERK_SECRET_KEY: Optional[str] = None
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_JWKS_URL: Optional[str] = None
    CLERK_ISSUER: Optional[str] = None

    # Frontend Integration
    FRONTEND_URL: Optional[str] = None

    # Ingestion Limits & Batching
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    MAX_PDF_PAGES: int = 50
    EMBEDDING_BATCH_SIZE: int = 64

    model_config = SettingsConfigDict(
        env_file=_env_path if os.path.exists(_env_path) else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def assemble_settings(self) -> "Settings":
        # Resolve MONGODB_URL from MONGODB_URI fallback if needed
        if not self.MONGODB_URL and self.MONGODB_URI:
            self.MONGODB_URL = self.MONGODB_URI

        # Resolve GitHub OAuth Client ID and Secret aliases
        if not self.GITHUB_OAUTH_CLIENT_ID and self.GITHUB_CLIENT_ID:
            self.GITHUB_OAUTH_CLIENT_ID = self.GITHUB_CLIENT_ID
        elif not self.GITHUB_CLIENT_ID and self.GITHUB_OAUTH_CLIENT_ID:
            self.GITHUB_CLIENT_ID = self.GITHUB_OAUTH_CLIENT_ID

        if not self.GITHUB_OAUTH_CLIENT_SECRET and self.GITHUB_CLIENT_SECRET:
            self.GITHUB_OAUTH_CLIENT_SECRET = self.GITHUB_CLIENT_SECRET
        elif not self.GITHUB_CLIENT_SECRET and self.GITHUB_OAUTH_CLIENT_SECRET:
            self.GITHUB_CLIENT_SECRET = self.GITHUB_OAUTH_CLIENT_SECRET

        # Resolve production redirect URI if running on Render
        render_url = (os.environ.get("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
        if render_url and (not self.GITHUB_OAUTH_REDIRECT_URI or "localhost" in (self.GITHUB_OAUTH_REDIRECT_URI or "")):
            self.GITHUB_OAUTH_REDIRECT_URI = f"{render_url}/auth/github/callback"

        # Resolve GITHUB_OAUTH_REDIRECT_URI from GITHUB_REDIRECT_URI or FRONTEND_URL
        if not self.GITHUB_OAUTH_REDIRECT_URI and self.GITHUB_REDIRECT_URI:
            self.GITHUB_OAUTH_REDIRECT_URI = self.GITHUB_REDIRECT_URI
        elif not self.GITHUB_OAUTH_REDIRECT_URI and self.FRONTEND_URL:
            frontend_clean = self.FRONTEND_URL.strip().rstrip("/")
            if frontend_clean:
                self.GITHUB_OAUTH_REDIRECT_URI = f"{frontend_clean}/github/callback"

        # Sync LangSmith & LangChain settings to os.environ for runtime tracing
        tracing_enabled = (
            self.LANGCHAIN_TRACING_V2
            or self.LANGSMITH_TRACING
            or os.environ.get("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1")
            or os.environ.get("LANGSMITH_TRACING", "").lower() in ("true", "1")
        )
        api_key = self.LANGCHAIN_API_KEY or self.LANGSMITH_API_KEY or os.environ.get("LANGCHAIN_API_KEY") or os.environ.get("LANGSMITH_API_KEY")
        if tracing_enabled and api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = api_key
            os.environ["LANGSMITH_API_KEY"] = api_key
            if self.LANGCHAIN_ENDPOINT:
                os.environ["LANGCHAIN_ENDPOINT"] = self.LANGCHAIN_ENDPOINT
            project = self.LANGCHAIN_PROJECT or self.LANGSMITH_PROJECT or os.environ.get("LANGCHAIN_PROJECT") or "study-guide-generator"
            os.environ["LANGCHAIN_PROJECT"] = project
            os.environ["LANGSMITH_PROJECT"] = project


        return self


settings = Settings()


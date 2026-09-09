from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """
    Application settings and environment configuration placeholders.
    """
    # Application metadata
    APP_NAME: str = "AI Study Assistant"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database configuration (placeholder for Phase 0)
    MONGODB_URI: Optional[str] = None
    MONGODB_DATABASE: str = "ai_study_assistant"

    # LLM configuration (placeholder for Phase 0)
    LLM_PROVIDER: Optional[str] = None
    LLM_MODEL: Optional[str] = None
    LLM_API_KEY: Optional[str] = None

    # Clerk Authentication (placeholder for Phase 0)
    CLERK_SECRET_KEY: Optional[str] = None
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_JWKS_URL: Optional[str] = None

    # Frontend integration
    FRONTEND_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

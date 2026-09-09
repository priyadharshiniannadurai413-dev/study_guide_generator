from typing import Optional
from dotenv import load_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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

    # MongoDB Configuration
    MONGODB_URL: Optional[str] = None
    MONGODB_URI: Optional[str] = None  # Backward-compatibility alias
    DB_NAME: str = "Chatbot"

    # GitHub OAuth & Legacy PAT
    GITHUB_API_KEY: Optional[str] = None  # Legacy PAT (optional)
    GITHUB_OAUTH_CLIENT_ID: Optional[str] = None
    GITHUB_OAUTH_CLIENT_SECRET: Optional[str] = None
    GITHUB_OAUTH_REDIRECT_URI: Optional[str] = None

    # Token Encryption Key for stored OAuth credentials
    TOKEN_ENCRYPTION_KEY: Optional[str] = None

    # Clerk Authentication
    CLERK_SECRET_KEY: Optional[str] = None
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_JWKS_URL: Optional[str] = None
    CLERK_ISSUER: Optional[str] = None

    # Frontend Integration
    FRONTEND_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def assemble_settings(self) -> "Settings":
        # Resolve MONGODB_URL from MONGODB_URI fallback if needed
        if not self.MONGODB_URL and self.MONGODB_URI:
            self.MONGODB_URL = self.MONGODB_URI

        # Derive GITHUB_OAUTH_REDIRECT_URI from FRONTEND_URL if not explicitly specified
        if not self.GITHUB_OAUTH_REDIRECT_URI and self.FRONTEND_URL:
            frontend_clean = self.FRONTEND_URL.strip().rstrip("/")
            if frontend_clean:
                self.GITHUB_OAUTH_REDIRECT_URI = f"{frontend_clean}/github/callback"

        return self


settings = Settings()

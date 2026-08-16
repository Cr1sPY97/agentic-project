import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Incident Response & Root Cause Analysis Platform"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database Settings
    # Default to sqlite:///./incident_platform.db for instant zero-dependency local runs & testing
    # In Docker/production, set DATABASE_URL=postgresql://postgres:postgres@db:5432/incident_platform
    DATABASE_URL: Optional[str] = "sqlite:///./incident_platform.db"
    POSTGRES_SERVER: Optional[str] = None
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "incident_platform"
    POSTGRES_PORT: str = "5432"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.POSTGRES_SERVER:
            return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self.DATABASE_URL or "sqlite:///./incident_platform.db"

    # Authentication & Security
    SECRET_KEY: str = "supersecretkey-incident-platform-production-change-me-32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # AI Provider Settings
    AI_PROVIDER: str = "heuristic"  # Options: 'openai', 'gemini', 'ollama', 'heuristic'
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    AI_TIMEOUT_SECONDS: float = 30.0
    PROMPT_VERSION: str = "incident_analysis_v1"

    # CORS Settings
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

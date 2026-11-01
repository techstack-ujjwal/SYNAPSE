"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""

    # OpenAI
    OPENAI_API_KEY: str

    # Queue settings
    MAX_QUESTIONS: int = 8
    ESTIMATED_MINUTES_PER_PERSON: int = 4
    BASE_WAIT_TIME: int = 8

    # Database
    DATABASE_URL: str = "sqlite:///./test.db"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

"""
Application configuration.
Centralises environment variables and system-level settings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global application settings loaded from environment or defaults."""

    APP_NAME: str = "English Buddy"
    APP_VERSION: str = "0.1.0"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # GPU / Model paths  (placeholders)
    WHISPER_MODEL: str = "large-v3"
    LLM_MODEL: str = "meta-llama/Meta-Llama-3-8B"
    TTS_MODEL: str = "styletts2"

    # Audio settings
    SAMPLE_RATE: int = 16_000
    CHUNK_DURATION_MS: int = 250

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

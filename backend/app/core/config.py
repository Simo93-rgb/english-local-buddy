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

    # GPU / Model paths
    WHISPER_MODEL: str = "medium.en"

    # LLM (LM Studio – OpenAI-compatible API)
    LLM_BASE_URL: str = "http://localhost:1234/v1"
    LLM_MODEL: str = "zai-org_glm-4.7-flash"

    # TTS
    TTS_VOICE: str = "en-US-AvaMultilingualNeural"

    # Audio settings
    SAMPLE_RATE: int = 16_000
    CHUNK_DURATION_MS: int = 250

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

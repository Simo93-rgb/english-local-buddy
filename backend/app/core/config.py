import json
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


def _get_unsloth_api_key() -> str:
    """Attempt to read the minted agent API key from Unsloth Studio."""
    key_path = Path.home() / ".unsloth" / "studio" / "auth" / "agent_api_key.json"
    if key_path.exists():
        try:
            data = json.loads(key_path.read_text(encoding="utf-8"))
            for _server, entry in data.get("servers", {}).items():
                minted = entry.get("minted", [])
                if minted:
                    return minted[0]
        except Exception:
            pass
    return "sk-unsloth-default"


class Settings(BaseSettings):
    """Global application settings loaded from environment or defaults."""

    APP_NAME: str = "English Buddy"
    APP_VERSION: str = "0.1.0"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # GPU / Model paths
    WHISPER_MODEL: str = "large-v3"
    DEFAULT_LANGUAGE: str = "en"

    # LLM (Unsloth Studio – OpenAI-compatible API)
    LLM_BASE_URL: str = "http://127.0.0.1:8888/v1"
    LLM_MODEL: str = "unsloth/gemma-4-12b-it-GGUF"
    LLM_API_KEY: str = Field(default_factory=_get_unsloth_api_key)

    # Prompts
    PROMPT_DIR: str = str(Path(__file__).parent / "prompts")
    SYSTEM_PROMPT_PATH: str = str(Path(__file__).parent / "prompts" / "english_partner.md")
    CHINESE_PROMPT_PATH: str = str(Path(__file__).parent / "prompts" / "chinese_tutor.md")

    # TTS (all female voices)
    TTS_VOICE: str = "en-US-AvaMultilingualNeural"
    TTS_VOICE_ZH: str = "zh-CN-XiaoxiaoNeural"
    TTS_VOICE_IT: str = "it-IT-ElsaNeural"

    # Audio settings
    SAMPLE_RATE: int = 16_000
    CHUNK_DURATION_MS: int = 250

    # User History & Progress tracking settings
    HISTORY_DIR: str = "user_history"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

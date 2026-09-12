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
    WHISPER_MODEL: str = "large-v3-turbo"
    WHISPER_DEVICE: str = "cuda"
    WHISPER_COMPUTE_TYPE: str = "int8_float16"
    DEFAULT_LANGUAGE: str = "en"

    # LLM (Unsloth Studio – OpenAI-compatible API)
    LLM_BASE_URL: str = "http://127.0.0.1:8888/v1"
    LLM_MODEL: str = "empero-ai/Qwen3.8-9B-Distill-GGUF"
    LLM_API_KEY: str = Field(default_factory=_get_unsloth_api_key)
    LLM_ENABLE_THINKING: bool = False

    # Prompts
    PROMPT_DIR: str = str(Path(__file__).parent / "prompts")
    SYSTEM_PROMPT_PATH: str = str(Path(__file__).parent / "prompts" / "english_partner.md")
    CHINESE_PROMPT_PATH: str = str(Path(__file__).parent / "prompts" / "chinese_tutor_beginner.md")
    CHINESE_BEGINNER_PROMPT_PATH: str = str(Path(__file__).parent / "prompts" / "chinese_tutor_beginner.md")
    CHINESE_INTERMEDIATE_PROMPT_PATH: str = str(Path(__file__).parent / "prompts" / "chinese_tutor_intermediate.md")
    CHINESE_ADVANCED_PROMPT_PATH: str = str(Path(__file__).parent / "prompts" / "chinese_buddy_advanced.md")

    # TTS (all female voices)
    TTS_VOICE: str = "en-US-AvaMultilingualNeural"
    TTS_VOICE_ZH: str = "zh-CN-XiaoxiaoNeural"
    TTS_VOICE_IT: str = "it-IT-ElsaNeural"

    # Audio settings
    SAMPLE_RATE: int = 16_000
    CHUNK_DURATION_MS: int = 250

    # User History & Progress tracking settings
    HISTORY_DIR: str = "user_history"
    REPORT_FILENAME: str = "user_report.md"
    CHINESE_REPORT_FILENAME: str = "user_chinese_report.md"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

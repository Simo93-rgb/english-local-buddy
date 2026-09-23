# Configuration & Environment Architecture

This document describes how configuration is structured, loaded, and overridden in English Buddy.

> [!IMPORTANT]
> **Single Source of Truth**: The application runtime configuration is exclusively managed and enforced by [`backend/app/core/config.py`](../backend/app/core/config.py) through Pydantic's `BaseSettings`. This file in `docs/` is a reference guide and does not execute or load configuration directly.

---

## 1. Runtime Configuration Architecture (`backend/app/core/config.py`)

All configuration is centralized in the `Settings` class (`BaseSettings`), which automatically:
1. Loads typed default values defined in Python.
2. Reads environment variables from the host operating system.
3. Parses an optional `.env` file located in the project root or backend directory.
4. Dynamically retrieves credentials (such as the Unsloth Studio local agent API key from `~/.unsloth/studio/auth/agent_api_key.json`).

Every backend component (`app.main`, `app.ai_pipeline.*`, `app.core.history_manager`) accesses configuration by importing the instantiated singleton:
```python
from app.core.config import settings
```

### Core Configuration Parameters

| Category | Key | Default Value | Description |
| :--- | :--- | :--- | :--- |
| **Server** | `HOST` | `"0.0.0.0"` | Host IP for FastAPI / Uvicorn server |
| | `PORT` | `8000` | Port for the backend API and WebSockets |
| **ASR (Speech-to-Text)** | `WHISPER_MODEL` | `"large-v3-turbo"` | Whisper model size (`tiny`, `base`, `medium`, `large-v3-turbo`) |
| | `WHISPER_DEVICE` | `"cuda"` | Execution hardware (`cuda` or `cpu`) |
| | `WHISPER_COMPUTE_TYPE` | `"int8_float16"` | Quantization compute type for CTranslate2 |
| | `DEFAULT_LANGUAGE` | `"en"` | Fallback session language (`en` or `zh`) |
| **LLM (Local Inference)** | `LLM_BASE_URL` | `"http://127.0.0.1:8888/v1"` | OpenAI-compatible endpoint (Unsloth Studio / vLLM / llama.cpp) |
| | `LLM_MODEL` | `"unsloth/Qwen3-8B-GGUF:UD-Q4_K_XL"` | Model identifier served by the local inference engine |
| | `LLM_API_KEY` | *(dynamic)* | Minted agent key from Unsloth Studio or fallback |
| | `LLM_ENABLE_THINKING`| `False` | Strip `<think>` reasoning tokens from student-facing output |
| **TTS (Speech Synthesis)** | `TTS_VOICE` | `"en-US-AvaMultilingualNeural"` | Default English female neural voice (Edge-TTS) |
| | `TTS_VOICE_ZH` | `"zh-CN-XiaoxiaoNeural"` | Native Mandarin female voice for Chinese tutor & TTS Studio |
| | `TTS_VOICE_IT` | `"it-IT-ElsaNeural"` | Native Italian female voice for pedagogical explanations |
| **Prompts** | `PROMPT_DIR` | `backend/app/core/prompts` | Path to prompt files directory |
| | `SYSTEM_PROMPT_PATH` | `.../english_partner.md` | English conversational buddy persona |
| | `CHINESE_BEGINNER_PROMPT_PATH` | `.../chinese_tutor_beginner.md`| Chinese beginner tutor persona (Pinyin, tones, Italian support) |
| | `CHINESE_INTERMEDIATE_PROMPT_PATH`| `.../chinese_tutor_intermediate.md`| Chinese intermediate tutor persona (bilingual dialogue) |
| | `CHINESE_ADVANCED_PROMPT_PATH` | `.../chinese_buddy_advanced.md`| Chinese advanced partner persona (full Mandarin immersion) |
| **Audio Processing** | `SAMPLE_RATE` | `16000` | Standard sample rate for Whisper and tone contour extraction |
| | `CHUNK_DURATION_MS` | `250` | Frontend streaming slice duration in milliseconds |
| **History & Reports** | `HISTORY_DIR` | `"user_history"` | Directory for persistent logs and rolling progress summaries |
| | `REPORT_FILENAME` | `"user_report.md"` | English student progress report |
| | `CHINESE_REPORT_FILENAME` | `"user_chinese_report.md"` | Chinese student progress report |

---

## 2. Overriding Configuration via `.env`

To override settings locally without altering the codebase, create a `.env` file in the `backend/` directory or project root:

```ini
# Example .env overrides
WHISPER_MODEL=medium.en
WHISPER_DEVICE=cuda
LLM_BASE_URL=http://127.0.0.1:8888/v1
LLM_MODEL=unsloth/Qwen3-8B-GGUF:UD-Q4_K_XL
TTS_VOICE=en-US-AvaMultilingualNeural
TTS_VOICE_ZH=zh-CN-XiaoxiaoNeural
```

Pydantic's `BaseSettings` automatically reads this file at startup.

---

## 3. Modular System Prompts

Rather than hardcoding prompt strings within Python files, all system personas are decoupled into dedicated Markdown files located in [`backend/app/core/prompts/`](../backend/app/core/prompts/):
- **`english_partner.md`**: Conversational English practice with gentle corrections.
- **`chinese_tutor_beginner.md`**: Pinyin breakdown, pronunciation diagnostics, tone emphasis, and Italian explanations.
- **`chinese_tutor_intermediate.md`**: Balanced conversational Mandarin with vocabulary hints.
- **`chinese_buddy_advanced.md`**: Native-level Mandarin discussion and idiom enrichment.

The `LLMManager` and `main.py` load these prompts dynamically via `load_system_prompt(path)` based on the active session language and user level.

---

## 4. Client-Side Store Configuration (`frontend/src/lib/stores/audioStore.ts`)

The frontend manages reactive connection and audio parameters through Svelte stores:
- **WebSocket URL**: Dynamically resolves against `window.location.hostname` (`ws://${backendHost}:8000/ws/audio`) to allow seamless local network or desktop execution.
- **Microphone Constraints**: Uses `ideal` constraints (`channelCount: { ideal: 1 }, sampleRate: { ideal: 16000 }`) rather than strict hardware locks, ensuring full compatibility with PipeWire, PulseAudio, and WebKitGTK on Linux/KDE.
- **Mode Switching**: Toggles cleanly between Conversational Tutor (`tutor`) and Audio Generator (`tts_studio`).

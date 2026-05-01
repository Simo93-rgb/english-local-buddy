# Configuration & Crucial Aspects

If you need to change how the app behaves, change the AI models, or adjust the behavior of the conversational buddy, here is where you need to look.

## 1. Global Settings (`backend/app/core/config.py`)

This is the most important file in the backend. It centralizes all paths and settings, preventing hardcoded values from breaking the app.

```python
# GPU / Model paths
WHISPER_MODEL: str = "medium.en"

# LLM (LM Studio – OpenAI-compatible API)
LLM_BASE_URL: str = "http://localhost:1234/v1"
LLM_MODEL: str = "google/gemma-4-e4b"

# TTS
TTS_VOICE: str = "en-US-AvaMultilingualNeural"
```
* **LLM_MODEL**: Ensure this exactly matches the ID of the model currently loaded in your LM Studio instance. If they misalign, the API might reject the request or LM Studio might return an error.
* **WHISPER_MODEL**: You can change this to `base.en`, `large-v3`, etc. It will auto-download on the next startup.
* **TTS_VOICE**: You can browse edge-tts available voices (e.g. `en-US-ChristopherNeural` or `en-GB-SoniaNeural`) and paste the ID here.

## 2. LLM System Prompt & Fallbacks (`backend/app/ai_pipeline/llm.py`)

To change the persona of the AI Buddy (e.g., make it stricter, more casual, or focus only on business English), modify the `SYSTEM_PROMPT` variable at the top of the file:

```python
SYSTEM_PROMPT = """\
You are a friendly and encouraging English conversation partner.
Your goal is to help the user practise speaking English naturally.
...
"""
```

### Handling Empty Responses
Sometimes, local models (especially when running locally via LM Studio) might fail to parse the chat template or crash, returning an empty string. The `LLMManager` catches this gracefully:
```python
if not assistant_text:
    logger.warning("LLM returned an empty response. Falling back to default message.")
    assistant_text = "I'm sorry, I didn't quite catch that. Could you say it again?"
```
This ensures the TTS doesn't crash and the conversation history (`self._history`) remains uncorrupted.

## 3. Frontend WebSocket Logic (`frontend/src/lib/stores/audioStore.ts`)

The entire client-side logic lives in a single Svelte store, ensuring that state is centralized and reactivity works seamlessly.
* **`WS_URL`**: Defines the backend WebSocket endpoint (`ws://localhost:8000/ws/audio`).
* **Audio Capture & WebM Flushing**: To prevent race conditions, the store carefully waits for all binary WebM chunk promises to resolve before sending the `STOP` string. This prevents the `ffmpeg` "Invalid data found" crashes.
* **Audio Playback**: Handled by the `playAudioBase64` function which converts the incoming Base64 JSON payload into a playable `Blob` automatically.

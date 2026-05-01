# Task: Complete the Conversational Loop (LLM + TTS)

## Context
We are building a local English pronunciation app. The infrastructure is solid: the Tauri/SvelteKit frontend streams audio to a FastAPI WebSocket, which successfully transcribes it using `faster-whisper` in a ThreadPoolExecutor. 
The user wants to prioritize closing the conversational loop immediately. We will temporarily park the Goodness of Pronunciation (GOP) module and focus on hooking up the LLM and TTS.

## Objectives for this turn
Implement the `llm.py` and `tts.py` modules and wire them into the existing `/ws/audio` pipeline in `main.py`.

Please execute the following steps:

### Step 1: Implement the LLM Module (`llm.py`)
1. Update `backend/requirements.txt` to include the `ollama` python package.
2. In `backend/app/ai_pipeline/llm.py`, implement an `LLMManager` class.
3. Write an async method `async def get_response(self, user_text: str) -> str`.
4. This method should call a local Ollama instance (assume it's running on `localhost:11434` with the model `llama3` or `phi3`). 
5. Inject a System Prompt that forces the LLM to act as a conversational English partner. Crucially, instruct it to keep responses very short (1-2 sentences max) to ensure low latency for the TTS.
6. (Optional but recommended) Maintain a small rolling context window of the last 4-5 messages so the bot remembers the conversation.

### Step 2: Implement the TTS Module (`tts.py`)
1. In `backend/app/ai_pipeline/tts.py`, implement a `TTSManager` class.
2. For maximum speed to MVP, implement a fast local TTS. You can use `parler-tts`, `speecht5`, or the `kokoro` TTS library if you are familiar with them. 
   - *Fallback:* If setting up a local deep-learning TTS is too complex for this single task, implement a temporary fallback using `edge-tts` (which is fast and requires zero model downloads) just to close the loop today. We have an RTX 4090, so a local model is the ultimate goal, but a working pipeline is today's priority.
3. Write an async method `async def generate_audio(self, text: str) -> bytes` that takes the LLM's text output and returns 16-bit PCM or WAV audio bytes.

### Step 3: Wire everything in the WebSocket (`main.py`)
1. Instantiate `LLMManager` and `TTSManager` globally alongside `WhisperASR`.
2. Update the `/ws/audio` endpoint:
   - When the ASR finishes transcribing the user's audio chunk and returns the text...
   - Pass that text to `await llm_manager.get_response(transcription)`.
   - Send a WebSocket JSON message to the frontend indicating the bot is "thinking/typing" and include the LLM's text response.
   - Pass the LLM response to `await tts_manager.generate_audio(llm_response)`.
   - Send the resulting audio bytes back to the frontend over the WebSocket (you can send it as binary data or base64 encoded within a JSON payload, whichever matches your current frontend store setup best).

### Step 4: Update Frontend Audio Playback (`audioStore.ts`)
1. In the Svelte frontend, ensure that the WebSocket `onmessage` handler can receive the audio payload from the backend.
2. If the message contains TTS audio data, decode it and play it immediately using the Web Audio API or a standard `Audio` object.

## Constraints
- **Latency is key:** Await the LLM and TTS sequentially for now, but ensure the code is clean enough that we could implement streaming (sentence-by-sentence TTS generation) in the future.
- **Robustness:** Add try/except blocks around the LLM and TTS calls. If Ollama is down, send a clean error JSON to the frontend.
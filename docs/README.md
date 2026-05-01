# English Buddy Documentation

Welcome to the documentation for English Buddy. This app serves as a local, privacy-first conversational AI trainer to help users practise and improve their spoken English.

## Available Documentation

* [Architecture & Data Flow](./architecture.md) - Learn how the frontend, backend, and external ML services interact via WebSockets. Includes Mermaid flowcharts.
* [Configuration & Crucial Settings](./configuration.md) - Find out where to edit the LLM, ASR, and TTS parameters, and how edge cases are handled.

## How the App Works (Brief Overview)

English Buddy is built using a decoupled architecture prioritizing speed and local execution:

1. **Frontend (Tauri + SvelteKit)**: The client captures audio via the browser's `MediaRecorder` API and streams it in extremely small chunks (WebM/Opus) to the backend over a single persistent WebSocket.
2. **Backend (FastAPI)**: The server holds the WebSocket connection open, efficiently buffering the audio chunks in memory to avoid disk I/O bottlenecks.
3. **ASR (Speech-to-Text)**: When the user clicks stop, the frontend ensures all chunks are flushed and sends a `STOP` signal. The backend then uses `faster-whisper` (on CUDA) to transcribe the entire audio buffer locally and extremely fast.
4. **LLM (Language Model)**: The transcribed text is sent to an external, locally-running instance of LM Studio (`localhost:1234`) via an OpenAI-compatible API to generate a conversational, short, and friendly response.
5. **TTS (Text-to-Speech)**: The text response is streamed to Microsoft Edge's TTS API, which returns high-quality, naturally spoken MP3 bytes.
6. **Delivery**: The MP3 is base64-encoded and sent back through the WebSocket as a JSON payload, where the frontend decodes and auto-plays it.

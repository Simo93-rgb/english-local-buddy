# English Buddy Documentation

Welcome to the documentation for **English Buddy**, a privacy-first, local AI conversational and pronunciation trainer designed to assist learners in acquiring English and Mandarin fluency.

---

## Available Documentation

- [Architecture & Data Flow](./architecture.md): Deep dive into the Tauri + SvelteKit frontend, FastAPI server, WebSocket streaming, and asynchronous AI pipeline with sequence diagrams.
- [Configuration & Environment Architecture](./configuration.md): Complete guide to application settings, Pydantic `BaseSettings`, environment variables, `.env` file overrides, and modular system prompts.

---

## High-Level Workflow

English Buddy leverages a decoupled, asynchronous architecture designed for sub-second conversational latency and local execution:

1. **Frontend (Tauri v2 + SvelteKit)**: Captures user microphone audio via the Web MediaRecorder API in small 250ms chunks (WebM/Opus) and streams them over a persistent WebSocket to the backend.
2. **Backend (FastAPI)**: Collects audio chunks in an in-memory byte buffer to eliminate disk I/O latency.
3. **ASR (Speech-to-Text)**: On receiving the `STOP` signal, `faster-whisper` (running with CUDA acceleration) transcribes the buffered speech with near-zero latency.
4. **Mandarin Tone Diagnostic (Optional)**: For Chinese sessions, `pypinyin` and `librosa` extract the speaker's F0 pitch contour, comparing it against canonical lexical tone trajectories.
5. **LLM Engine (Local Reasoning)**: The transcribed text and conversational history are evaluated by a local LLM served via Unsloth Studio (`127.0.0.1:8888`), utilizing modular prompt personas (`backend/app/core/prompts/`).
6. **Polyglot TTS (Speech Synthesis)**: Microsoft Edge's neural TTS engine synthesizes multilingual responses in parallel (e.g. Italian explanations accompanied by native Mandarin target pronunciations) and streams unified MP3 bytes back to the client.
7. **Session History & Assessment**: Background processes log every turn incrementally to prevent data loss and run asynchronous assessments to maintain rolling learner reports.

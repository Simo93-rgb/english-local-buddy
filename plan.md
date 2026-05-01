Ecco un documento tecnico (un vero e proprio *System Prompt* o *Project Specification Document*) ottimizzato per essere digerito da un agente LLM (come Aider, un Custom GPT, Cline o AutoGPT). 

Ho scritto il contenuto del documento in **inglese**, in quanto i modelli agentici performano molto meglio e commettono meno errori di scaffolding quando leggono istruzioni architetturali in inglese.

Puoi copiare e incollare l'intero blocco qui sotto direttamente nel prompt del tuo agente.

***

# Project Specification: Local English Pronunciation Trainer (Desktop App)

## 1. Project Overview
The goal is to build the skeleton of a local desktop application designed for English pronunciation and conversation practice. The app will run entirely locally on a machine equipped with an NVIDIA RTX 4090 (24GB VRAM). 
The core challenge is that standard ASR (like Whisper) normalizes pronunciation errors. Therefore, the backend requires a custom pipeline: ASR -> LLM -> Text-to-Speech (TTS), integrated with an advanced **Pronunciation Assessment Module** (Forced Alignment + Goodness of Pronunciation + Prosody analysis).

**Agent Goal for this Prompt:** You are acting as a Senior Full-Stack and AI Engineer. Your immediate task is to generate the **project skeleton**, configuration files, and API stubs. Do **NOT** implement the deep learning model loading/inference logic yet. Focus entirely on the boilerplate, communication protocols (WebSockets), directory structure, and UI scaffolding.

---

## 2. Technical Stack
*   **Frontend / Desktop Container:** Tauri (Rust) + SvelteKit (TypeScript) + TailwindCSS.
*   **Backend:** Python 3.11+ with FastAPI.
*   **Communication Protocol:** WebSockets (for low-latency audio streaming) and HTTP REST (for configuration/state).
*   **Package Management:** `pnpm` (Frontend), `cargo` (Tauri), `uv` or `pip` (Python Backend).

---

## 3. Directory Structure
Initialize a monorepo with the following structure:

```text
/
├── backend/                  # Python FastAPI application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI entrypoint & WebSocket routing
│   │   ├── core/
│   │   │   ├── config.py     # Environment and system configs
│   │   │   └── audio_processing.py # Stubs for librosa/parselmouth functions
│   │   ├── models/
│   │   │   └── schemas.py    # Pydantic models for I/O validation
│   │   └── ai_pipeline/
│   │       ├── asr.py        # Stub for faster-whisper
│   │       ├── llm.py        # Stub for vLLM/llama.cpp
│   │       ├── tts.py        # Stub for StyleTTS2/XTTS
│   │       └── pronunciation.py # Stub for Forced Alignment & GOP
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # SvelteKit + Tauri frontend
│   ├── src/
│   │   ├── lib/
│   │   │   ├── components/   # Svelte UI components (e.g., RecordButton.svelte)
│   │   │   └── stores/       # Svelte stores for WebSocket state management
│   │   ├── routes/
│   │   │   └── +page.svelte  # Main dashboard UI
│   │   └── app.html
│   ├── src-tauri/            # Rust backend for Tauri
│   │   ├── Cargo.toml
│   │   └── src/
│   │       └── main.rs       # Tauri entrypoint, system tray, window management
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── .gitignore
└── README.md
```

---

## 4. Agent Execution Steps

Please execute the following steps in order. Acknowledge when you finish each step or ask for permission to proceed if required by your execution environment.

### Step 1: Initialize the Python Backend
1. Create the `backend/` directory.
2. Generate `requirements.txt` including: `fastapi`, `uvicorn`, `websockets`, `pydantic`, `torch`, `torchaudio`, `librosa`, `numpy`.
3. Create `backend/app/main.py`. Set up a basic FastAPI server.
4. Implement a WebSocket endpoint (`/ws/audio`) in `main.py` that accepts incoming binary audio chunks, prints the size of the received chunk, and sends back a mocked JSON payload containing: `{ "status": "processing", "mock_transcription": "Hello", "mock_gop_score": 85 }`.
5. Create stubs for the AI modules in `backend/app/ai_pipeline/` with empty classes/functions (e.g., `def calculate_gop(audio_buffer, text): pass`), fully documented with docstrings.

### Step 2: Initialize the Tauri + SvelteKit Frontend
1. Create the `frontend/` directory.
2. Initialize a standard SvelteKit project (skeleton template, using TypeScript).
3. Initialize Tauri within the Svelte project (`src-tauri`).
4. Configure `vite.config.ts` to clear the `clearScreen` behavior and set the `server.port` to 1420 (standard Tauri setup).
5. Install `tailwindcss` and configure its skeleton files.

### Step 3: Implement the WebSocket UI Logic (Svelte)
1. In `frontend/src/lib/stores/`, create `audioStore.ts`. Implement logic to handle the Web Audio API (`MediaRecorder`) to capture microphone input.
2. Implement WebSocket connection logic in `audioStore.ts` to connect to `ws://localhost:8000/ws/audio` (the Python backend).
3. Ensure the store can stream audio chunks (e.g., 250ms intervals) over the socket.
4. In `frontend/src/routes/+page.svelte`, build a minimal UI:
    * A "Start/Stop Recording" button.
    * A visual log component to display the incoming JSON messages from the WebSocket (mock transcriptions and GOP scores).

### Step 4: Implement Rust Tauri Stubs
1. In `frontend/src-tauri/src/main.rs`, write the basic Tauri builder setup.
2. Ensure that Tauri requests microphone permissions on startup (if applicable for the OS context).

---

## 5. Constraints & Best Practices
*   **Asynchrony:** Use `async/await` heavily in FastAPI and Svelte. Audio processing must not block the main threads.
*   **Modularity:** Keep the AI model stubs strictly decoupled from the WebSocket routing. The `main.py` should only call functions from `ai_pipeline/`, not implement logic directly.
*   **Placeholders:** Do not attempt to write the actual PyTorch/Wav2Vec2 tensor logic. Output explicit comments like `# TODO: Implement Montreal Forced Aligner here` or `# TODO: Load Llama-3 8B 4-bit here`. 
*   **Error Handling:** Include basic `try/except` blocks in the WebSocket router to handle unexpected client disconnections safely.
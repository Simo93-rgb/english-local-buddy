# English Buddy – Local Pronunciation Trainer

A local desktop application for English pronunciation and conversation practice, powered by AI.

## Architecture

- **Frontend**: Tauri (Rust) + SvelteKit (TypeScript) + TailwindCSS
- **Backend**: Python 3.11+ with FastAPI
- **Communication**: WebSockets (audio streaming) + HTTP REST (config/state)

## Project Structure

```
/
├── backend/          # Python FastAPI application
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint & WebSocket routing
│   │   ├── core/             # Config, audio processing & history_manager
│   │   ├── models/           # Pydantic schemas
│   │   └── ai_pipeline/      # ASR, LLM, TTS, Pronunciation stubs
│   └── requirements.txt
│
├── frontend/         # SvelteKit + Tauri frontend
│   ├── src/
│   │   ├── lib/components/   # Svelte UI components
│   │   ├── lib/stores/       # WebSocket & audio state (includes disconnect)
│   │   └── routes/           # SvelteKit pages
│   └── src-tauri/            # Rust Tauri shell
│
├── user_history/     # User conversation logs & progress reports
│   ├── sessions/             # Incremental session markdown logs
│   └── user_report.md        # Persistent, LLM-updated progress report
│
├── .gitignore
├── start_app.sh      # Unified app launcher script
└── README.md
```

## Features

### User Progress Tracking & Logging
- **Incremental Logging**: Automatically records every conversational turn (user transcription and companion response) directly to `user_history/sessions/chat_log_YYYYMMDD_HHMMSS.md` on disk. This prevents data loss in the event of a crash or shutdown.
- **Persistent Progress Report**: Compiles conversational history into a single, rolling status report at `user_history/user_report.md` tracking active grammar/vocabulary errors, resolved mistakes, strengths, and focus areas.
- **Asynchronous LLM Assessment**: Runs a background assessor using the local LLM to update the report without stalling the real-time speech interaction loop. Report updates are triggered:
  - **Periodically**: Every 10 turns during the session.
  - **On Close**: Automatically when the client disconnects or manually when clicking the **"End Session"** button in the UI.

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ & pnpm
- Rust toolchain (for Tauri)
- NVIDIA GPU with CUDA support (RTX 4090 recommended)
- `uv` (Fast Python package installer)

### Unified Launcher
The easiest way to start both the backend and frontend is by running the launcher script from the project root:

```bash
./start_app.sh
```

This script will automatically:
1. Detect and repair any broken Python virtual environments (e.g. from folder relocations).
2. Sync dependencies with `uv`.
3. Set Wayland compatibility variables (`GDK_BACKEND=x11`) to prevent Tauri/GDK crashes.
4. Export CUDA library paths for GPU-accelerated speech-to-text.
5. Launch the FastAPI backend and Tauri developer console.

### Manual Backend Launch
```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
export PYTHONPATH="."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Manual Frontend Launch
```bash
cd frontend
pnpm install
pnpm tauri dev
```



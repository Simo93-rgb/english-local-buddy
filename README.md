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
│   │   ├── core/             # Config & audio processing utilities
│   │   ├── models/           # Pydantic schemas
│   │   └── ai_pipeline/      # ASR, LLM, TTS, Pronunciation stubs
│   └── requirements.txt
│
├── frontend/         # SvelteKit + Tauri frontend
│   ├── src/
│   │   ├── lib/components/   # Svelte UI components
│   │   ├── lib/stores/       # WebSocket & audio state
│   │   └── routes/           # SvelteKit pages
│   └── src-tauri/            # Rust Tauri shell
│
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ & pnpm
- Rust toolchain (for Tauri)
- NVIDIA GPU with CUDA support (RTX 4090 recommended)

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
pnpm install
pnpm dev          # SvelteKit dev server
pnpm tauri dev    # Full Tauri desktop app
```



#!/usr/bin/env bash
# English Buddy – Backend launch script
# Ensures CUDA 12 libraries are visible to ctranslate2 / faster-whisper

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate the virtual environment
source .venv/bin/activate

# Add CUDA 12 libs (bundled with Ollama) to the library path
# ctranslate2 requires libcublas.so.12 which is not in the default path
export LD_LIBRARY_PATH="/usr/local/lib/ollama/cuda_v12:${LD_LIBRARY_PATH:-}"

echo "Starting English Buddy backend on http://0.0.0.0:8000 ..."
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

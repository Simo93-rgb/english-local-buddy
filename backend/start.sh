#!/usr/bin/env bash
# English Buddy – Backend launch script
# Ensures CUDA 12 libraries are visible to ctranslate2 / faster-whisper

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate the virtual environment
source .venv/bin/activate

# Add CUDA 12 libs (from venv and Ollama) to the library path
NVIDIA_CU12_LIBS=$(find "$SCRIPT_DIR/.venv" -type d -name "lib" -path "*/site-packages/nvidia/*/lib" 2>/dev/null | tr '\n' ':')
export LD_LIBRARY_PATH="${NVIDIA_CU12_LIBS}/usr/local/lib/ollama/cuda_v12:${LD_LIBRARY_PATH:-}"

echo "Starting English Buddy backend on http://0.0.0.0:8000 ..."
exec uvicorn app.main:app --reload --reload-dir app --host 0.0.0.0 --port 8000

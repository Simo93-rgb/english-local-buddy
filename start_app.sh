#!/bin/bash

# English Buddy - Application Launcher
# This script starts both the backend and the frontend of the application.
# If the app is already running, it will be restarted.

set -e

# Configuration - Automatically detect project root
ROOT_DIR=$(pwd)
if [ ! -d "$ROOT_DIR/backend" ] || [ ! -d "$ROOT_DIR/frontend" ]; then
    # Try to find the project root by looking for the backend directory
    ROOT_DIR=$(find . -maxdepth 2 -name "backend" -type d | head -n 1 | sed 's|.*/||')
    if [ -z "$ROOT_DIR" ]; then
        echo -e "${RED}Error: Could not find project root. Please run this script from the project root directory (where the 'backend' and 'frontend' folders are located).${NC}"
        exit 1
    fi
    cd "$ROOT_DIR"
fi

BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PORT=8000

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}--- English Buddy Launcher ---${NC}"

# Function to kill existing backend and frontend processes
stop_app() {
    echo -e "${YELLOW}Stopping existing processes...${NC}"
    # Kill backend on port 8000
    lsof -t -i:$BACKEND_PORT >/dev/null 2>&1 && fuser -k $BACKEND_PORT/tcp >/dev/null 2>&1 || true
    
    # Kill frontend on port 1420
    lsof -t -i:1420 >/dev/null 2>&1 && fuser -k 1420/tcp >/dev/null 2>&1 || true
    
    # Kill tauri/node/vite processes
    pkill -f "pnpm tauri" >/dev/null 2>&1 || true
    pkill -f "tauri" >/dev/null 2>&1 || true
    pkill -f "vite" >/dev/null 2>&1 || true
    
    # Give it a second to release ports
    sleep 2
}

# Restart logic
if lsof -t -i:$BACKEND_PORT >/dev/null 2>&1 || lsof -t -i:1420 >/dev/null 2>&1; then
    echo -e "${YELLOW}App is already running. Restarting...${NC}"
    stop_app
else
    echo -e "${GREEN}Starting app for the first time...${NC}"
fi

# Start Backend
echo -e "${GREEN}Starting backend...${NC}"
cd "$BACKEND_DIR"

# Verify virtual environment path validity (handles project relocation)
if [ -d ".venv" ]; then
    if ! python3 -c "
import sys, os
from pathlib import Path
activate_file = Path('.venv/bin/activate')
if not activate_file.exists():
    sys.exit(1)
content = activate_file.read_text(encoding='utf-8')
for line in content.splitlines():
    if line.startswith('VIRTUAL_ENV='):
        env_path = line.split('=', 1)[1].strip('\"\'')
        expected_path = str(Path('.venv').resolve())
        if os.path.normpath(env_path) != os.path.normpath(expected_path):
            sys.exit(1)
        break
" 2>/dev/null; then
        echo -e "${YELLOW}Virtual environment .venv is broken (likely due to project relocation). Recreating...${NC}"
        rm -rf .venv
    fi
fi
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment with uv...${NC}"
    uv venv
fi

# Sync requirements with uv
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}Syncing requirements with uv...${NC}"
    uv pip install -r requirements.txt
fi

# Start uvicorn in the background using uv run
# We set PYTHONPATH to the current directory (backend/) so app.main can be resolved
export PYTHONPATH="$BACKEND_DIR"
export LD_LIBRARY_PATH="/usr/local/lib/ollama/cuda_v12:${LD_LIBRARY_PATH:-}"
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!
echo -e "${GREEN}Backend started with PID: $BACKEND_PID${NC}"

# Start Frontend
echo -e "${GREEN}Starting frontend...${NC}"
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    pnpm install
fi

# Run tauri dev in the foreground (force GDK to use x11 backend to avoid Wayland protocol errors under Wayland)
export GDK_BACKEND=x11
pnpm tauri dev


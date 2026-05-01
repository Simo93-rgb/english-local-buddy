"""
English Buddy – FastAPI Backend
================================
Main entrypoint for the FastAPI server.
Provides WebSocket endpoints for real-time audio streaming
and REST endpoints for configuration and state management.
"""

import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.ai_pipeline.asr import transcribe_audio
from app.ai_pipeline.llm import generate_response
from app.ai_pipeline.tts import synthesize_speech
from app.ai_pipeline.pronunciation import calculate_gop, run_forced_alignment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local English Pronunciation Trainer – Backend API",
)

# ---------------------------------------------------------------------------
# CORS – allow the Tauri/SvelteKit frontend to connect
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# REST health-check
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


# ---------------------------------------------------------------------------
# WebSocket endpoint – /ws/audio
# ---------------------------------------------------------------------------
@app.websocket("/ws/audio")
async def websocket_audio(ws: WebSocket):
    """
    Accept incoming binary audio chunks from the client, process them
    through the AI pipeline (ASR → LLM → TTS), and stream results back.

    Currently returns a **mock** JSON payload while the AI modules
    are still stubs.
    """
    await ws.accept()
    logger.info("WebSocket client connected.")

    try:
        while True:
            # Receive raw audio bytes from the client
            audio_chunk: bytes = await ws.receive_bytes()
            chunk_size = len(audio_chunk)
            logger.info(f"Received audio chunk: {chunk_size} bytes")

            # ------ AI Pipeline (stubs) ------
            # TODO: Replace mock responses with real pipeline calls:
            #   1. transcription = await transcribe_audio(audio_chunk)
            #   2. gop_result    = await calculate_gop(audio_chunk, transcription)
            #   3. feedback      = await generate_response(transcription, gop_result)
            #   4. speech        = await synthesize_speech(feedback)

            mock_response = {
                "status": "processing",
                "mock_transcription": "Hello",
                "mock_gop_score": 85,
            }

            await ws.send_text(json.dumps(mock_response))

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as exc:
        logger.error(f"Unexpected WebSocket error: {exc}")
        try:
            await ws.close(code=1011, reason="Internal server error")
        except Exception:
            pass

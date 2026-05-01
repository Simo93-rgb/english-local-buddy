"""
English Buddy – FastAPI Backend
================================
Main entrypoint for the FastAPI server.
Provides WebSocket endpoints for real-time audio streaming
and REST endpoints for configuration and state management.

Audio flow
----------
1. Frontend streams binary audio chunks (WebM/Opus, ~250 ms each)
   over WebSocket ``/ws/audio``.
2. Backend accumulates chunks in a per-connection buffer.
3. When the client sends a text message ``"STOP"`` (or the buffer
   exceeds ``MAX_BUFFER_BYTES``), the accumulated audio is decoded
   and passed through the ASR pipeline.
4. The transcription result is sent back as JSON.
"""

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.ai_pipeline.asr import WhisperASR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ASR singleton – loaded once into VRAM at startup
# ---------------------------------------------------------------------------
asr_engine: WhisperASR | None = None

# Maximum buffer size before we force a transcription (5 MB ≈ ~30 s WebM)
MAX_BUFFER_BYTES = 5 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler.
    Load heavy ML models into GPU memory on startup,
    release them on shutdown.
    """
    global asr_engine

    # ---- Startup ----
    logger.info("Loading ASR model …")
    asr_engine = WhisperASR(
        model_size=settings.WHISPER_MODEL,
        device="cuda",
        compute_type="float16",
    )
    asr_engine.load_model()
    logger.info("ASR model ready.")

    yield  # ← application runs here

    # ---- Shutdown ----
    logger.info("Shutting down – unloading models …")
    if asr_engine is not None:
        asr_engine.unload_model()
        asr_engine = None
    logger.info("Cleanup complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local English Pronunciation Trainer – Backend API",
    lifespan=lifespan,
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
    Accept incoming audio from the client and return ASR results.

    Protocol
    --------
    * **Binary messages** → raw audio chunks (appended to a buffer).
    * **Text message ``"STOP"``** → triggers transcription of the
      buffered audio, returns JSON result, and resets the buffer.
    * The buffer is also flushed automatically when it exceeds
      ``MAX_BUFFER_BYTES``.
    """
    await ws.accept()
    logger.info("WebSocket client connected.")

    audio_buffer = bytearray()

    try:
        while True:
            message = await ws.receive()

            # --- Binary frame: audio chunk --------------------------------
            if "bytes" in message and message["bytes"] is not None:
                chunk: bytes = message["bytes"]
                audio_buffer.extend(chunk)
                logger.debug(
                    "Buffered audio chunk: +%d B  (total %d B)",
                    len(chunk),
                    len(audio_buffer),
                )

                # Auto-flush if the buffer gets too large
                if len(audio_buffer) >= MAX_BUFFER_BYTES:
                    logger.info(
                        "Buffer exceeded %d B – auto-flushing for transcription.",
                        MAX_BUFFER_BYTES,
                    )
                    result = await _transcribe_buffer(audio_buffer)
                    await ws.send_text(json.dumps(result))
                    audio_buffer.clear()

            # --- Text frame: control message ------------------------------
            elif "text" in message and message["text"] is not None:
                text_msg = message["text"].strip().upper()

                if text_msg == "STOP":
                    if len(audio_buffer) == 0:
                        await ws.send_text(json.dumps({
                            "status": "empty",
                            "transcription": "",
                            "gop_score": None,
                        }))
                        continue

                    logger.info(
                        "STOP received – transcribing %d B of audio.",
                        len(audio_buffer),
                    )
                    result = await _transcribe_buffer(audio_buffer)
                    await ws.send_text(json.dumps(result))
                    audio_buffer.clear()
                else:
                    logger.warning("Unknown text command: %s", text_msg)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as exc:
        logger.error("Unexpected WebSocket error: %s", exc, exc_info=True)
        try:
            await ws.close(code=1011, reason="Internal server error")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _transcribe_buffer(buffer: bytearray) -> dict:
    """
    Run ASR on the accumulated audio buffer and return a JSON-ready dict.
    """
    if asr_engine is None:
        return {"status": "error", "message": "ASR engine not loaded"}

    try:
        result = await asr_engine.transcribe_audio_bytes(bytes(buffer))
        return {
            "status": "ok",
            "transcription": result["text"],
            "confidence": result["confidence"],
            "language": result["language"],
            "segments": result["segments"],
            # TODO: Replace with real GOP score once pronunciation module is ready
            "gop_score": None,
        }
    except Exception as exc:
        logger.error("Transcription failed: %s", exc, exc_info=True)
        return {"status": "error", "message": str(exc)}

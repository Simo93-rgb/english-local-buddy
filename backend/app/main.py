"""
English Buddy – FastAPI Backend
================================
Main entrypoint for the FastAPI server.

Full pipeline:  Audio chunks → ASR (Whisper) → LLM (LM Studio) → TTS (edge-tts)

Audio flow
----------
1. Frontend streams binary audio chunks (WebM/Opus, ~250 ms each)
   over WebSocket ``/ws/audio``.
2. Backend accumulates chunks in a per-connection buffer.
3. Client sends text ``"STOP"`` → buffer is transcribed via Whisper.
4. Transcription is sent to the LLM for a conversational reply.
5. LLM response is synthesised to speech via TTS.
6. JSON status messages + base64-encoded audio are sent back.
"""

import base64
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.ai_pipeline.asr import WhisperASR
from app.ai_pipeline.llm import LLMManager
from app.ai_pipeline.tts import TTSManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singletons – loaded once at startup
# ---------------------------------------------------------------------------
asr_engine: WhisperASR | None = None
llm_manager: LLMManager | None = None
tts_manager: TTSManager | None = None

# Maximum buffer size before auto-flush (5 MB ≈ ~30 s WebM)
MAX_BUFFER_BYTES = 5 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler.
    Load heavy ML models on startup, release on shutdown.
    """
    global asr_engine, llm_manager, tts_manager

    # ---- Startup ----
    logger.info("Loading ASR model …")
    asr_engine = WhisperASR(
        model_size=settings.WHISPER_MODEL,
        device="cuda",
        compute_type="float16",
    )
    asr_engine.load_model()
    logger.info("ASR model ready.")

    logger.info("Initialising LLM manager …")
    llm_manager = LLMManager(
        base_url=settings.LLM_BASE_URL,
        model=settings.LLM_MODEL,
    )
    logger.info("LLM manager ready.")

    logger.info("Initialising TTS manager …")
    tts_manager = TTSManager(voice=settings.TTS_VOICE)
    logger.info("TTS manager ready.")

    yield  # ← application runs here

    # ---- Shutdown ----
    logger.info("Shutting down – unloading models …")
    if asr_engine is not None:
        asr_engine.unload_model()
        asr_engine = None
    llm_manager = None
    tts_manager = None
    logger.info("Cleanup complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local English Pronunciation Trainer – Backend API",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
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
    Full conversational pipeline over a single WebSocket connection.

    Protocol
    --------
    * **Binary messages** → raw audio chunks (appended to buffer).
    * **Text ``"STOP"``** → trigger ASR → LLM → TTS pipeline.
    * **Text ``"CLEAR"``** → reset LLM conversation history.
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

                # Auto-flush if buffer gets too large
                if len(audio_buffer) >= MAX_BUFFER_BYTES:
                    logger.info("Buffer auto-flush at %d B", len(audio_buffer))
                    await _run_pipeline(ws, audio_buffer)
                    audio_buffer.clear()

            # --- Text frame: control message ------------------------------
            elif "text" in message and message["text"] is not None:
                text_msg = message["text"].strip().upper()

                if text_msg == "STOP":
                    if len(audio_buffer) == 0:
                        await ws.send_text(json.dumps({
                            "type": "result",
                            "status": "empty",
                            "transcription": "",
                        }))
                        continue

                    logger.info("STOP – transcribing %d B", len(audio_buffer))
                    await _run_pipeline(ws, audio_buffer)
                    audio_buffer.clear()

                elif text_msg == "CLEAR":
                    if llm_manager:
                        llm_manager.clear_history()
                    await ws.send_text(json.dumps({
                        "type": "status",
                        "status": "history_cleared",
                    }))

                else:
                    logger.warning("Unknown command: %s", text_msg)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except RuntimeError as exc:
        if "Cannot call \"receive\" once a disconnect message has been received" in str(exc):
            logger.info("WebSocket client disconnected.")
        else:
            logger.error("Unexpected RuntimeError: %s", exc, exc_info=True)
            try:
                await ws.close(code=1011, reason="Internal server error")
            except Exception:
                pass
    except Exception as exc:
        logger.error("Unexpected WebSocket error: %s", exc, exc_info=True)
        try:
            await ws.close(code=1011, reason="Internal server error")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Pipeline helper
# ---------------------------------------------------------------------------

async def _run_pipeline(ws: WebSocket, buffer: bytearray) -> None:
    """
    Execute the full ASR → LLM → TTS pipeline and send results
    back over the WebSocket.
    """

    # ---- 1. ASR (Speech-to-Text) ----------------------------------------
    if asr_engine is None:
        await ws.send_text(json.dumps({
            "type": "error",
            "status": "error",
            "message": "ASR engine not loaded",
        }))
        return

    await ws.send_text(json.dumps({
        "type": "status",
        "status": "transcribing",
    }))

    try:
        asr_result = await asr_engine.transcribe_audio_bytes(bytes(buffer))
        transcription = asr_result["text"]
    except Exception as exc:
        logger.error("ASR failed: %s", exc, exc_info=True)
        await ws.send_text(json.dumps({
            "type": "error",
            "status": "error",
            "message": f"Transcription failed: {exc}",
        }))
        return

    # Send the transcription immediately
    await ws.send_text(json.dumps({
        "type": "transcription",
        "status": "ok",
        "transcription": transcription,
        "confidence": asr_result.get("confidence", 0.0),
        "language": asr_result.get("language", "en"),
        "segments": asr_result.get("segments", []),
    }))

    if not transcription.strip():
        return

    # ---- 2. LLM (Conversational response) --------------------------------
    if llm_manager is None:
        await ws.send_text(json.dumps({
            "type": "error",
            "status": "error",
            "message": "LLM not available",
        }))
        return

    await ws.send_text(json.dumps({
        "type": "status",
        "status": "thinking",
    }))

    try:
        llm_response = await llm_manager.get_response(transcription)
    except Exception as exc:
        logger.error("LLM failed: %s", exc, exc_info=True)
        await ws.send_text(json.dumps({
            "type": "error",
            "status": "error",
            "message": f"LLM request failed: {exc}",
        }))
        return

    # Send the LLM text response
    await ws.send_text(json.dumps({
        "type": "llm_response",
        "status": "ok",
        "llm_text": llm_response,
    }))

    # ---- 3. TTS (Text-to-Speech) -----------------------------------------
    if tts_manager is None:
        return

    await ws.send_text(json.dumps({
        "type": "status",
        "status": "speaking",
    }))

    try:
        audio_bytes = await tts_manager.generate_audio(llm_response)
    except Exception as exc:
        logger.error("TTS failed: %s", exc, exc_info=True)
        await ws.send_text(json.dumps({
            "type": "error",
            "status": "error",
            "message": f"TTS synthesis failed: {exc}",
        }))
        return

    if audio_bytes:
        # Send audio as base64 inside JSON for easy frontend handling
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        await ws.send_text(json.dumps({
            "type": "tts_audio",
            "status": "ok",
            "audio_b64": audio_b64,
            "audio_format": "mp3",
        }))

    # ---- Done ----
    await ws.send_text(json.dumps({
        "type": "status",
        "status": "done",
    }))

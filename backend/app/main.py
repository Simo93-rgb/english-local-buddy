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
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.ai_pipeline.asr import WhisperASR
from app.ai_pipeline.llm import LLMManager, load_system_prompt
from app.ai_pipeline.tts import TTSManager, strip_language_tags
from app.core.history_manager import HistoryManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singletons – loaded once at startup
# ---------------------------------------------------------------------------
asr_engine: WhisperASR | None = None
llm_manager: LLMManager | None = None
tts_manager: TTSManager | None = None
history_manager: HistoryManager | None = None

# Maximum buffer size before auto-flush (5 MB ≈ ~30 s WebM)
MAX_BUFFER_BYTES = 5 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler.
    Load heavy ML models on startup, release on shutdown.
    """
    global asr_engine, llm_manager, tts_manager, history_manager

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
        api_key=settings.LLM_API_KEY,
        prompt_path=settings.SYSTEM_PROMPT_PATH,
    )
    logger.info("LLM manager ready.")

    logger.info("Initialising TTS manager …")
    tts_manager = TTSManager(voice=settings.TTS_VOICE)
    logger.info("TTS manager ready.")

    logger.info("Initialising History manager …")
    history_manager = HistoryManager()
    logger.info("History manager ready.")

    yield  # ← application runs here

    # ---- Shutdown ----
    logger.info("Shutting down – unloading models …")
    if asr_engine is not None:
        asr_engine.unload_model()
        asr_engine = None
    llm_manager = None
    tts_manager = None
    history_manager = None
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
    current_language = ws.query_params.get("lang", settings.DEFAULT_LANGUAGE).strip().lower()
    logger.info("WebSocket client connected (initial language=%s).", current_language)

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{current_language}"
    if history_manager:
        await history_manager.start_session(session_id)

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
                    await _run_pipeline(ws, audio_buffer, session_id, language=current_language)
                    audio_buffer.clear()

            # --- Text frame: control message ------------------------------
            elif "text" in message and message["text"] is not None:
                raw_text = message["text"].strip()

                # Check for JSON control messages (e.g. {"type": "SET_LANGUAGE", "language": "zh"})
                if raw_text.startswith("{") and raw_text.endswith("}"):
                    try:
                        parsed = json.loads(raw_text)
                        if parsed.get("type") == "SET_LANGUAGE":
                            new_lang = str(parsed.get("language", "")).strip().lower()
                            if new_lang:
                                current_language = new_lang
                                logger.info("Session %s switched language to: %s", session_id, current_language)
                                await ws.send_text(json.dumps({
                                    "type": "status",
                                    "status": "language_changed",
                                    "language": current_language,
                                }))
                                continue
                    except Exception:
                        pass

                text_msg = raw_text.upper()

                if text_msg == "STOP":
                    if len(audio_buffer) == 0:
                        await ws.send_text(json.dumps({
                            "type": "result",
                            "status": "empty",
                            "transcription": "",
                        }))
                        continue

                    logger.info("STOP – transcribing %d B (language=%s)", len(audio_buffer), current_language)
                    await _run_pipeline(ws, audio_buffer, session_id, language=current_language)
                    audio_buffer.clear()

                elif text_msg == "CLEAR":
                    if llm_manager:
                        llm_manager.clear_history()
                    await ws.send_text(json.dumps({
                        "type": "status",
                        "status": "history_cleared",
                    }))

                elif text_msg.startswith("LANG:"):
                    current_language = text_msg.split(":", 1)[1].strip().lower()
                    logger.info("Session %s language switched via command to: %s", session_id, current_language)
                    await ws.send_text(json.dumps({
                        "type": "status",
                        "status": "language_changed",
                        "language": current_language,
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
    finally:
        logger.info("WebSocket connection closed. Running final progress report update for session %s...", session_id)
        if history_manager:
            import asyncio
            async def _run_final_update():
                await history_manager.update_progress_report(session_id)
                history_manager.cleanup_session_state(session_id)
                logger.info("Progress report update finished for session %s.", session_id)
            asyncio.create_task(_run_final_update())


# ---------------------------------------------------------------------------
# Pipeline helper
# ---------------------------------------------------------------------------

async def _run_pipeline(ws: WebSocket, buffer: bytearray, session_id: str, language: str = "en") -> None:
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
        # If English, enforce English language. If Chinese, auto-detect allows user to speak Chinese or Italian.
        asr_lang = "en" if language == "en" else None
        asr_result = await asr_engine.transcribe_audio_bytes(bytes(buffer), language=asr_lang)
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
        "language": asr_result.get("language", language),
        "segments": asr_result.get("segments", []),
    }))

    if not transcription.strip():
        return

    # Log user turn
    if history_manager:
        await history_manager.add_turn_incremental(session_id, "user", transcription)

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
        if language == "zh":
            prompt = load_system_prompt(settings.CHINESE_PROMPT_PATH)
        else:
            prompt = load_system_prompt(settings.SYSTEM_PROMPT_PATH)
        llm_response = await llm_manager.get_response(transcription, system_prompt=prompt)
    except Exception as exc:
        logger.error("LLM failed: %s", exc, exc_info=True)
        await ws.send_text(json.dumps({
            "type": "error",
            "status": "error",
            "message": f"LLM request failed: {exc}",
        }))
    clean_llm_response = strip_language_tags(llm_response)

    # Log partner turn (cleaned of tags)
    if history_manager and clean_llm_response.strip():
        await history_manager.add_turn_incremental(session_id, "assistant", clean_llm_response)

    # Send the LLM text response (cleaned of tags)
    await ws.send_text(json.dumps({
        "type": "llm_response",
        "status": "ok",
        "llm_text": clean_llm_response,
        "language": language,
    }))

    # ---- 3. TTS (Text-to-Speech) -----------------------------------------
    if tts_manager is None:
        return

    await ws.send_text(json.dumps({
        "type": "status",
        "status": "speaking",
    }))

    try:
        audio_bytes = await tts_manager.generate_polyglot_audio(llm_response, default_language=language)
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

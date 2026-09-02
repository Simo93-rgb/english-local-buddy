"""
TTS (Text-to-Speech) Module
=============================
MVP implementation using ``edge-tts`` (Microsoft Edge online TTS).
Fast, zero model downloads, high-quality voices.

Future upgrade path: replace with a local GPU model (StyleTTS2, XTTS,
Kokoro) once the conversational loop is validated.
"""

from __future__ import annotations

import io
import logging

import edge_tts

logger = logging.getLogger(__name__)

from app.core.config import settings

# Default voice – natural-sounding US English female
# See full list: https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/voices/list
DEFAULT_VOICE = "en-US-AvaMultilingualNeural"


class TTSManager:
    """
    Text-to-Speech manager using edge-tts.

    Parameters
    ----------
    voice : str
        Edge TTS voice identifier.
    """

    def __init__(self, voice: str = DEFAULT_VOICE) -> None:
        self.voice = voice
        logger.info("TTSManager initialised (voice=%s)", voice)

    def get_voice_for_language(self, language: str) -> str:
        """Return recommended Edge TTS voice identifier for given language code."""
        lang = (language or "").strip().lower()
        if lang.startswith("zh"):
            return getattr(settings, "TTS_VOICE_ZH", "zh-CN-XiaoxiaoNeural")
        return self.voice

    async def generate_audio(self, text: str, voice: str | None = None) -> bytes:
        """
        Convert text to speech and return WAV-like audio bytes.

        Parameters
        ----------
        text : str
            The text to synthesise (typically the LLM's response).
        voice : str | None
            Optional voice override (defaults to instance default voice).

        Returns
        -------
        bytes
            MP3 audio bytes (edge-tts outputs MP3 natively).
            The frontend can play MP3 directly via ``Audio()``.
        """
        if not text or not text.strip():
            return b""

        target_voice = voice or self.voice
        try:
            communicate = edge_tts.Communicate(text=text, voice=target_voice)

            # Collect all audio chunks into a buffer
            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

            audio_bytes = audio_buffer.getvalue()
            logger.info(
                "TTS generated %d bytes of audio with voice '%s' for: %s",
                len(audio_bytes),
                target_voice,
                text[:60],
            )
            return audio_bytes

        except Exception as exc:
            logger.error("TTS synthesis failed (voice=%s): %s", target_voice, exc)
            raise

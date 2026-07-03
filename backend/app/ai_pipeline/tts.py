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

    def __init__(self, voice: str) -> None:
        self.voice = voice
        logger.info("TTSManager initialised (voice=%s)", voice)

    async def generate_audio(self, text: str) -> bytes:
        """
        Convert text to speech and return WAV-like audio bytes.

        Parameters
        ----------
        text : str
            The text to synthesise (typically the LLM's response).

        Returns
        -------
        bytes
            MP3 audio bytes (edge-tts outputs MP3 natively).
            The frontend can play MP3 directly via ``Audio()``.
        """
        if not text or not text.strip():
            return b""

        try:
            communicate = edge_tts.Communicate(text=text, voice=self.voice)

            # Collect all audio chunks into a buffer
            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

            audio_bytes = audio_buffer.getvalue()
            logger.info(
                "TTS generated %d bytes of audio for: %s",
                len(audio_bytes),
                text[:60],
            )
            return audio_bytes

        except Exception as exc:
            logger.error("TTS synthesis failed: %s", exc)
            raise

"""
ASR (Automatic Speech Recognition) Module
==========================================
Stub for the faster-whisper speech-to-text engine.
"""

from __future__ import annotations

from typing import Any


class ASREngine:
    """
    Wraps the faster-whisper model for real-time transcription.

    Attributes
    ----------
    model_size : str
        Whisper model variant (e.g. "large-v3").
    device : str
        Compute device ("cuda" or "cpu").
    model : Any
        The loaded faster-whisper model instance.
    """

    def __init__(self, model_size: str = "large-v3", device: str = "cuda") -> None:
        self.model_size = model_size
        self.device = device
        self.model: Any = None

    async def load_model(self) -> None:
        """
        Load the faster-whisper model into memory.

        This should be called once at application startup.
        """
        # TODO: Load faster-whisper model here
        # from faster_whisper import WhisperModel
        # self.model = WhisperModel(self.model_size, device=self.device, compute_type="float16")
        pass

    async def unload_model(self) -> None:
        """Release model resources."""
        # TODO: Implement model cleanup
        self.model = None


async def transcribe_audio(audio_buffer: bytes, language: str = "en") -> dict:
    """
    Transcribe an audio buffer to text using faster-whisper.

    Parameters
    ----------
    audio_buffer : bytes
        Raw PCM audio data (16 kHz, mono, float32).
    language : str, optional
        Expected language code (default "en").

    Returns
    -------
    dict
        Dictionary with keys: "text", "confidence", "language", "segments".
    """
    # TODO: Implement actual transcription with faster-whisper
    # 1. Convert bytes to numpy array
    # 2. Run inference with WhisperModel.transcribe()
    # 3. Return structured result
    return {
        "text": "",
        "confidence": 0.0,
        "language": language,
        "segments": [],
    }

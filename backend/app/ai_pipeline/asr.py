"""
ASR (Automatic Speech Recognition) Module
==========================================
Real implementation using faster-whisper for GPU-accelerated
speech-to-text on NVIDIA RTX 4090.
"""

from __future__ import annotations

import io
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

import numpy as np
import soundfile as sf
from pydub import AudioSegment

logger = logging.getLogger(__name__)

# Shared thread pool so we don't block the async event loop with
# synchronous CTranslate2 inference calls.
_executor = ThreadPoolExecutor(max_workers=1)


class WhisperASR:
    """
    GPU-accelerated ASR engine backed by faster-whisper (CTranslate2).

    Parameters
    ----------
    model_size : str
        Whisper model variant. Use ``"medium.en"`` for fast English-only
        transcription or ``"large-v3"`` for multilingual/higher accuracy.
    device : str
        ``"cuda"`` (default) or ``"cpu"``.
    compute_type : str
        CTranslate2 compute type. ``"float16"`` is optimal for RTX 4090.
    """

    def __init__(
        self,
        model_size: str = "medium.en",
        device: str = "cuda",
        compute_type: str = "float16",
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Any = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def load_model(self) -> None:
        """
        Load the faster-whisper model into VRAM.
        Call once at application startup.
        """
        from faster_whisper import WhisperModel

        logger.info(
            "Loading Whisper model '%s' on %s (%s) …",
            self.model_size,
            self.device,
            self.compute_type,
        )
        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )
        logger.info("Whisper model loaded successfully.")

    def unload_model(self) -> None:
        """Release model resources and free VRAM."""
        self._model = None
        logger.info("Whisper model unloaded.")

    # ------------------------------------------------------------------
    # Audio decoding helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_webm_to_array(audio_bytes: bytes) -> np.ndarray:
        """
        Decode WebM/Opus audio bytes (from MediaRecorder) into a
        16 kHz mono float32 numpy array suitable for Whisper.

        Strategy
        --------
        1. Try ``soundfile`` first – it handles WAV/FLAC/OGG natively.
        2. Fall back to ``pydub`` (which uses ffmpeg) for WebM/Opus and
           other container formats the browser may produce.

        Returns
        -------
        np.ndarray
            1-D float32 array, sample rate normalised to 16 000 Hz.
        """
        TARGET_SR = 16_000

        # --- Attempt 1: soundfile (fast, C-based) -----------------------
        try:
            data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
            if data.ndim > 1:
                data = data.mean(axis=1)  # stereo → mono
            if sr != TARGET_SR:
                # Simple linear resampling – good enough for short chunks
                import librosa
                data = librosa.resample(data, orig_sr=sr, target_sr=TARGET_SR)
            return data
        except Exception:
            pass  # Not a format soundfile can handle – try pydub

        # --- Attempt 2: pydub + ffmpeg (handles WebM/Opus) --------------
        try:
            audio_seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
            audio_seg = (
                audio_seg
                .set_channels(1)
                .set_frame_rate(TARGET_SR)
                .set_sample_width(2)  # 16-bit PCM
            )
            samples = np.frombuffer(audio_seg.raw_data, dtype=np.int16)
            return samples.astype(np.float32) / 32768.0
        except Exception as exc:
            raise ValueError(
                f"Failed to decode audio bytes ({len(audio_bytes)} B): {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def _transcribe_sync(self, audio_array: np.ndarray) -> dict:
        """
        Synchronous transcription (runs on the thread pool).

        Parameters
        ----------
        audio_array : np.ndarray
            16 kHz mono float32 waveform.

        Returns
        -------
        dict
            ``{"text": str, "confidence": float, "language": str, "segments": list}``
        """
        if self._model is None:
            raise RuntimeError("Whisper model not loaded – call load_model() first.")

        segments_iter, info = self._model.transcribe(
            audio_array,
            language="en",
            beam_size=5,
            vad_filter=True,          # skip silence
            vad_parameters=dict(
                min_silence_duration_ms=500,
            ),
        )

        segments = []
        full_text_parts: list[str] = []
        total_log_prob = 0.0
        n_tokens = 0

        for seg in segments_iter:
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
                "avg_logprob": seg.avg_logprob,
            })
            full_text_parts.append(seg.text.strip())
            total_log_prob += seg.avg_logprob
            n_tokens += 1

        avg_confidence = (
            np.exp(total_log_prob / n_tokens) if n_tokens > 0 else 0.0
        )

        return {
            "text": " ".join(full_text_parts),
            "confidence": float(avg_confidence),
            "language": info.language,
            "segments": segments,
        }

    async def transcribe_audio_bytes(self, audio_bytes: bytes) -> dict:
        """
        Decode raw audio bytes and transcribe asynchronously.

        This method decodes the incoming bytes (WebM/Opus from the
        browser's MediaRecorder), converts to 16 kHz mono float32,
        and runs Whisper inference on a background thread so the
        async event loop is never blocked.

        Parameters
        ----------
        audio_bytes : bytes
            Raw audio data (any format ffmpeg can decode).

        Returns
        -------
        dict
            ``{"text": str, "confidence": float, "language": str, "segments": list}``
        """
        import asyncio

        loop = asyncio.get_running_loop()

        # Decode audio (CPU-bound but fast – run inline)
        audio_array = self._decode_webm_to_array(audio_bytes)

        if audio_array.size == 0:
            return {"text": "", "confidence": 0.0, "language": "en", "segments": []}

        # Run CTranslate2 inference on the thread pool
        result = await loop.run_in_executor(
            _executor,
            partial(self._transcribe_sync, audio_array),
        )
        return result

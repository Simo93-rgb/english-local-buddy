"""
Audio processing utilities.
Provides librosa-based pitch (F0 contour) extraction, RMS energy calculation,
and audio resampling for tone and pronunciation assessment.
"""

from __future__ import annotations

import io
import logging
import numpy as np
import librosa
import soundfile as sf
from pydub import AudioSegment

logger = logging.getLogger(__name__)


def ensure_float32_array(audio_data: bytes | np.ndarray, target_sr: int = 16_000) -> np.ndarray:
    """
    Convert raw audio bytes (or existing array) into a 16 kHz mono float32 numpy array.
    Handles WebM/Opus, WAV, or raw PCM.
    """
    if isinstance(audio_data, np.ndarray):
        arr = audio_data.astype(np.float32)
        if arr.ndim > 1:
            arr = arr.mean(axis=1)
        return arr

    if not audio_data:
        return np.array([], dtype=np.float32)

    # Attempt 1: soundfile (WAV/FLAC)
    try:
        data, sr = sf.read(io.BytesIO(audio_data), dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        if sr != target_sr:
            data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
        return data.astype(np.float32)
    except Exception:
        pass

    # Attempt 2: pydub (WebM/Opus / MP3)
    try:
        audio_seg = AudioSegment.from_file(io.BytesIO(audio_data))
        audio_seg = audio_seg.set_channels(1).set_frame_rate(target_sr).set_sample_width(2)
        samples = np.frombuffer(audio_seg.raw_data, dtype=np.int16)
        return samples.astype(np.float32) / 32768.0
    except Exception as exc:
        logger.warning("Could not decode audio data: %s", exc)
        return np.array([], dtype=np.float32)


def extract_pitch_contour(
    audio_data: bytes | np.ndarray,
    sr: int = 16_000,
    fmin: float = 65.0,
    fmax: float = 500.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Extract the fundamental frequency (F0) contour in Hz across the audio signal
    using librosa's probabilistic YIN (pYIN) algorithm.

    Parameters
    ----------
    audio_data : bytes | np.ndarray
        Audio samples (PCM float32, or raw audio bytes).
    sr : int
        Sample rate (default 16 000 Hz).
    fmin : float
        Minimum fundamental frequency in Hz (default 65 Hz ~ C2).
    fmax : float
        Maximum fundamental frequency in Hz (default 500 Hz ~ B4).

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        - f0: Array of F0 values in Hz per frame (unvoiced frames are NaN).
        - voiced_flag: Boolean array indicating voiced speech frames.
    """
    y = ensure_float32_array(audio_data, target_sr=sr)
    if len(y) < 1024:
        return np.array([], dtype=np.float32), np.array([], dtype=bool)

    try:
        f0, voiced_flag, _ = librosa.pyin(
            y,
            fmin=fmin,
            fmax=fmax,
            sr=sr,
            frame_length=2048,
            hop_length=256,
        )
        return np.asarray(f0, dtype=np.float32), np.asarray(voiced_flag, dtype=bool)
    except Exception as exc:
        logger.error("Pitch extraction failed: %s", exc)
        return np.array([], dtype=np.float32), np.array([], dtype=bool)


def compute_energy(audio_data: bytes | np.ndarray, sr: int = 16_000) -> np.ndarray:
    """
    Compute short-time Root-Mean-Square (RMS) energy per frame.
    """
    y = ensure_float32_array(audio_data, target_sr=sr)
    if len(y) == 0:
        return np.array([], dtype=np.float32)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=256)
    return rms[0] if rms.ndim > 1 else rms


def resample_audio(audio_data: bytes | np.ndarray, original_sr: int, target_sr: int = 16_000) -> np.ndarray:
    """
    Resample audio waveform to target sample rate.
    """
    y = ensure_float32_array(audio_data, target_sr=original_sr)
    if len(y) == 0 or original_sr == target_sr:
        return y
    return librosa.resample(y, orig_sr=original_sr, target_sr=target_sr)

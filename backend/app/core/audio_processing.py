"""
Audio processing utilities.
Stubs for librosa / parselmouth helper functions used across the pipeline.
"""

import numpy as np


async def resample_audio(audio_buffer: bytes, original_sr: int, target_sr: int = 16_000) -> np.ndarray:
    """
    Resample raw audio bytes to the target sample rate.

    Parameters
    ----------
    audio_buffer : bytes
        Raw PCM audio data.
    original_sr : int
        Original sample rate of the incoming audio.
    target_sr : int, optional
        Target sample rate (default 16 000 Hz).

    Returns
    -------
    np.ndarray
        Resampled audio waveform as a 1-D float32 array.
    """
    # TODO: Implement resampling with librosa.resample()
    pass


async def extract_pitch_contour(audio_buffer: bytes, sr: int = 16_000) -> np.ndarray:
    """
    Extract the fundamental frequency (F0) contour from an audio buffer
    using Parselmouth / Praat.

    Parameters
    ----------
    audio_buffer : bytes
        Raw PCM audio data.
    sr : int, optional
        Sample rate (default 16 000 Hz).

    Returns
    -------
    np.ndarray
        Array of F0 values (Hz) per frame.
    """
    # TODO: Implement pitch extraction with parselmouth
    pass


async def compute_energy(audio_buffer: bytes, sr: int = 16_000) -> np.ndarray:
    """
    Compute short-time energy of an audio signal.

    Parameters
    ----------
    audio_buffer : bytes
        Raw PCM audio data.
    sr : int, optional
        Sample rate (default 16 000 Hz).

    Returns
    -------
    np.ndarray
        Energy values per frame.
    """
    # TODO: Implement energy computation with librosa.feature.rms()
    pass

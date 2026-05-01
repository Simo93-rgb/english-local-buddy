"""
Pydantic schemas for request / response validation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# WebSocket payloads
# ---------------------------------------------------------------------------

class AudioChunkMeta(BaseModel):
    """Metadata that can optionally accompany an audio chunk."""

    sample_rate: int = Field(default=16_000, description="Sample rate in Hz")
    encoding: str = Field(default="pcm_f32le", description="Audio encoding format")
    channel_count: int = Field(default=1, description="Number of audio channels")


class TranscriptionResult(BaseModel):
    """Result returned by the ASR module."""

    text: str = Field(..., description="Transcribed text")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Transcription confidence score")
    language: str = Field(default="en", description="Detected language code")


class GOPResult(BaseModel):
    """Goodness-of-Pronunciation assessment result."""

    overall_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Overall GOP score (0-100)")
    phoneme_scores: list[PhonemeScore] = Field(default_factory=list, description="Per-phoneme scores")


class PhonemeScore(BaseModel):
    """Score for an individual phoneme."""

    phoneme: str = Field(..., description="IPA phoneme symbol")
    score: float = Field(default=0.0, ge=0.0, le=100.0, description="GOP score for this phoneme")
    start_time: float = Field(default=0.0, description="Start time in seconds")
    end_time: float = Field(default=0.0, description="End time in seconds")


# Rebuild GOPResult so the forward-ref to PhonemeScore resolves
GOPResult.model_rebuild()


class ProsodyResult(BaseModel):
    """Prosody analysis result (pitch, rhythm, stress)."""

    pitch_mean: float = Field(default=0.0, description="Mean F0 in Hz")
    pitch_std: float = Field(default=0.0, description="Standard deviation of F0")
    speech_rate: float = Field(default=0.0, description="Syllables per second")
    naturalness_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Overall naturalness score")


class PipelineResponse(BaseModel):
    """Full response sent back to the client over WebSocket."""

    status: str = Field(default="processing", description="Pipeline status")
    transcription: TranscriptionResult | None = None
    gop: GOPResult | None = None
    prosody: ProsodyResult | None = None
    llm_feedback: str | None = Field(default=None, description="LLM-generated feedback text")
    tts_audio_b64: str | None = Field(default=None, description="Base64-encoded TTS audio")

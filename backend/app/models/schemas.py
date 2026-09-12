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


class ToneAssessmentItem(BaseModel):
    """Assessment of an individual Chinese syllable's pitch tone."""

    syllable: str = Field(..., description="Target syllable or pinyin (e.g. 'rén')")
    expected_tone: int = Field(..., description="Expected tone number (1-5)")
    detected_tone: int = Field(..., description="Acoustically detected tone number (1-5)")
    is_correct: bool = Field(..., description="Whether detected tone matches expected tone")
    pitch_contour: list[float] = Field(default_factory=list, description="Normalized F0 values across the syllable")
    feedback: str = Field(default="", description="Italian pedagogical feedback on tone production")


class ToneAnalysisResult(BaseModel):
    """Collection of tone assessments for the current utterance."""

    overall_accuracy: float = Field(default=0.0, ge=0.0, le=100.0, description="Overall tone accuracy (0-100)")
    tones: list[ToneAssessmentItem] = Field(default_factory=list, description="Individual syllable tone assessments")
    summary: str = Field(default="", description="Summary note for user and tutor")


class PipelineResponse(BaseModel):
    """Full response sent back to the client over WebSocket."""

    status: str = Field(default="processing", description="Pipeline status")
    transcription: TranscriptionResult | None = None
    gop: GOPResult | None = None
    prosody: ProsodyResult | None = None
    tone_analysis: ToneAnalysisResult | None = None
    llm_feedback: str | None = Field(default=None, description="LLM-generated feedback text")
    tts_audio_b64: str | None = Field(default=None, description="Base64-encoded TTS audio")

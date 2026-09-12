"""
Pronunciation Assessment Module
=================================
Stubs for Forced Alignment (Montreal Forced Aligner) and
Goodness-of-Pronunciation (GOP) scoring.
"""

from __future__ import annotations

from typing import Any

import numpy as np


class ForcedAligner:
    """
    Wrapper around Montreal Forced Aligner (MFA) for phoneme-level
    time alignment of speech audio against a reference transcript.

    Attributes
    ----------
    model_path : str
        Path to the pretrained acoustic model for MFA.
    dictionary_path : str
        Path to the pronunciation dictionary.
    """

    def __init__(self, model_path: str = "", dictionary_path: str = "") -> None:
        self.model_path = model_path
        self.dictionary_path = dictionary_path

    async def align(self, audio_path: str, transcript: str) -> list[dict]:
        """
        Run forced alignment on an audio file given a transcript.

        Parameters
        ----------
        audio_path : str
            Path to the audio file.
        transcript : str
            Reference text to align against.

        Returns
        -------
        list[dict]
            List of aligned phonemes, each containing:
            - "phoneme": str (IPA symbol)
            - "start": float (seconds)
            - "end": float (seconds)
        """
        # TODO: Implement Montreal Forced Aligner here
        # 1. Prepare audio and transcript files
        # 2. Run MFA alignment
        # 3. Parse TextGrid output
        return []


class GOPScorer:
    """
    Computes Goodness-of-Pronunciation scores at the phoneme level
    using a Wav2Vec2-based acoustic model.

    Attributes
    ----------
    model : Any
        The loaded Wav2Vec2 / HuBERT model for posterior extraction.
    device : str
        Compute device ("cuda" or "cpu").
    """

    def __init__(self, device: str = "cuda") -> None:
        self.device = device
        self.model: Any = None

    async def load_model(self) -> None:
        """
        Load the acoustic model for GOP computation.
        """
        # TODO: Load Wav2Vec2 fine-tuned for phoneme recognition
        # import torch
        # from transformers import Wav2Vec2ForCTC
        # self.model = Wav2Vec2ForCTC.from_pretrained("...").to(self.device)
        pass

    async def score_phonemes(
        self, audio_buffer: bytes, alignment: list[dict]
    ) -> list[dict]:
        """
        Compute GOP score for each aligned phoneme.

        Parameters
        ----------
        audio_buffer : bytes
            Raw PCM audio data.
        alignment : list[dict]
            Phoneme-level alignment from ForcedAligner.

        Returns
        -------
        list[dict]
            Each entry contains:
            - "phoneme": str
            - "score": float (0-100)
            - "start": float
            - "end": float
        """
        # TODO: Implement GOP scoring
        # 1. Extract per-frame log-posteriors from the acoustic model
        # 2. For each aligned phoneme segment, compute:
        #    GOP(p) = (1/d) * sum( log P(p | o_t) )  for t in segment
        # 3. Normalise scores to 0-100 range
        return []


async def run_forced_alignment(audio_buffer: bytes, transcript: str) -> list[dict]:
    """
    High-level function: run forced alignment on raw audio bytes.

    Parameters
    ----------
    audio_buffer : bytes
        Raw PCM audio data.
    transcript : str
        Reference transcript text.

    Returns
    -------
    list[dict]
        Phoneme-level alignment results.
    """
    # TODO: Implement Montreal Forced Aligner here
    # 1. Save audio_buffer to a temporary WAV file
    # 2. Instantiate ForcedAligner and run .align()
    # 3. Return alignment results
    return []


async def calculate_gop(audio_buffer: bytes, text: str) -> dict:
    """
    High-level function: compute Goodness-of-Pronunciation scores.

    Parameters
    ----------
    audio_buffer : bytes
        Raw PCM audio data.
    text : str
        Reference transcript for alignment.

    Returns
    -------
    dict
        Dictionary with keys:
        - "overall_score": float (0-100)
        - "phoneme_scores": list[dict]
    """
    # TODO: Implement full GOP pipeline
    # 1. Run forced alignment to get phoneme boundaries
    # 2. Run GOP scoring on each phoneme segment
    # 3. Compute overall score as weighted mean
    return {
        "overall_score": 0.0,
        "phoneme_scores": [],
    }


# ---------------------------------------------------------------------------
# Mandarin Tone Acoustic Analyzer (Option B)
# ---------------------------------------------------------------------------

import re
from app.core.audio_processing import extract_pitch_contour, ensure_float32_array

# Diacritic to tone mapping in standard Pinyin
TONE_DIACRITICS = {
    "ā": (1, "a"), "ē": (1, "e"), "ī": (1, "i"), "ō": (1, "o"), "ū": (1, "u"), "ǖ": (1, "ü"),
    "á": (2, "a"), "é": (2, "e"), "í": (2, "i"), "ó": (2, "o"), "ú": (2, "u"), "ǘ": (2, "ü"),
    "ǎ": (3, "a"), "ě": (3, "e"), "ǐ": (3, "i"), "ǒ": (3, "o"), "ǔ": (3, "u"), "ǚ": (3, "ü"),
    "à": (4, "a"), "è": (4, "e"), "ì": (4, "i"), "ò": (4, "o"), "ù": (4, "u"), "ǜ": (4, "ü"),
    "Ā": (1, "A"), "Ē": (1, "E"), "Ī": (1, "I"), "Ō": (1, "O"), "Ū": (1, "U"), "Ǖ": (1, "Ü"),
    "Á": (2, "A"), "É": (2, "E"), "Í": (2, "I"), "Ó": (2, "O"), "Ú": (2, "U"), "Ǘ": (2, "Ü"),
    "Ǎ": (3, "A"), "Ě": (3, "E"), "Ǐ": (3, "I"), "Ǒ": (3, "O"), "Ǔ": (3, "U"), "Ǚ": (3, "Ü"),
    "À": (4, "A"), "È": (4, "E"), "Ì": (4, "I"), "Ò": (4, "O"), "Ù": (4, "U"), "Ǜ": (4, "Ü"),
}

TONE_DESCRIPTIONS = {
    1: "1° tono (alto e piatto 55): voce acuta e costante come una nota cantata",
    2: "2° tono (ascendente 35): voce che sale dal medio all'acuto come una domanda sorpresa ('chi?')",
    3: "3° tono (discendente-ascendente 214): voce che scende nel registro grave per poi risalire leggermente",
    4: "4° tono (discendente 51): voce che scende rapida e decisa come un comando secco ('no!')",
    5: "Tono neutro: pronuncia breve, leggera e rilassata",
}


ITALIAN_ACCENTED_STOPWORDS = {
    "è", "é", "perché", "poiché", "affinché", "benché", "cosicché", "giacché", "purché",
    "così", "già", "più", "può", "ciò", "là", "lì", "sì", "dà", "sé", "cioè",
    "qualità", "città", "università", "caffè", "verità", "novità", "realtà", "metà",
    "virtù", "gioventù", "perciò", "dopodiché",
    "sarà", "avrà", "farà", "andrà", "vorrà", "potrà", "dovrà", "verrà",
}


class MandarinToneAnalyzer:
    """
    Acoustic analyzer for Mandarin tones using fundamental frequency (F0) contours.
    Segments voiced speech, tracks pitch trajectory, classifies the tone (1-5),
    and compares against the expected Pinyin tones.
    """

    @staticmethod
    def extract_pinyin_syllables(text: str) -> list[tuple[str, int]]:
        """
        Extract Chinese pinyin syllables and their tone numbers (1-5) from text.
        Supports both accented pinyin (nǐ hǎo, rén shì) and numbered pinyin (ni3 hao3).
        Filters out common Italian accented words (e.g. 'è', 'perché', 'così').
        """
        if not text:
            return []

        # Find words in text
        tokens = re.findall(r"[a-zA-ZāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛ1-5]+", text)
        results: list[tuple[str, int]] = []

        for token in tokens:
            low_tok = token.lower()
            if low_tok in ITALIAN_ACCENTED_STOPWORDS:
                continue
            if len(low_tok) > 2 and (low_tok.endswith("tà") or low_tok.endswith("tù")):
                continue
            if low_tok.endswith("ché") or low_tok.endswith("cché"):
                continue

            # Check for numbered pinyin (e.g. ren2, shi4, ni3)
            num_match = re.search(r"([a-zA-Z]+)([1-5])$", token)
            if num_match:
                syllable = num_match.group(1).lower()
                tone = int(num_match.group(2))
                results.append((syllable, tone))
                continue

            # Check for accented vowels
            detected_tone = None
            clean_chars = []
            for char in token:
                if char in TONE_DIACRITICS:
                    detected_tone = TONE_DIACRITICS[char][0]
                    clean_chars.append(TONE_DIACRITICS[char][1])
                else:
                    clean_chars.append(char)

            if detected_tone is not None:
                results.append((token, detected_tone))

        return results

    @staticmethod
    def segment_voiced_f0(f0: np.ndarray, voiced_flag: np.ndarray, min_frames: int = 4) -> list[np.ndarray]:
        """
        Group consecutive voiced frames into distinct voiced syllable chunks.
        """
        segments: list[np.ndarray] = []
        current_chunk: list[float] = []

        for val, is_voiced in zip(f0, voiced_flag):
            if is_voiced and not np.isnan(val) and val > 50.0:
                current_chunk.append(float(val))
            else:
                if len(current_chunk) >= min_frames:
                    segments.append(np.array(current_chunk, dtype=np.float32))
                current_chunk = []

        if len(current_chunk) >= min_frames:
            segments.append(np.array(current_chunk, dtype=np.float32))

        return segments

    @staticmethod
    def classify_tone_contour(f0_segment: np.ndarray) -> int:
        """
        Classify a single voiced F0 contour into one of the 5 Mandarin tones.

        Returns
        -------
        int : 1, 2, 3, 4, or 5
        """
        if len(f0_segment) < 3:
            return 5  # Neutral / too short

        n = len(f0_segment)
        # Smooth with a small moving average if long enough
        if n >= 5:
            kernel = np.ones(3) / 3.0
            smoothed = np.convolve(f0_segment, kernel, mode="valid")
        else:
            smoothed = f0_segment

        start_val = float(np.mean(smoothed[: max(1, len(smoothed) // 3)]))
        mid_val = float(np.median(smoothed))
        end_val = float(np.mean(smoothed[-max(1, len(smoothed) // 3) :]))
        min_idx = int(np.argmin(smoothed))
        min_val = float(smoothed[min_idx])
        max_val = float(np.max(smoothed))

        # Relative pitch change
        ratio_end_start = (end_val - start_val) / max(start_val, 1.0)
        pitch_range_ratio = (max_val - min_val) / max(mid_val, 1.0)

        # Tone 5: very short and flat
        if n < 6 and pitch_range_ratio < 0.08:
            return 5

        # Tone 2 (Rising): end is significantly higher than start
        if ratio_end_start > 0.08 and end_val > min_val * 1.05:
            return 2

        # Tone 4 (Falling): start is significantly higher than end
        if ratio_end_start < -0.09 and start_val > min_val * 1.06:
            return 4

        # Tone 3 (Dipping): minimum is clearly in the middle third and drops then recovers
        if (
            len(smoothed) >= 6
            and len(smoothed) // 4 < min_idx < 3 * len(smoothed) // 4
            and (start_val - min_val) / max(start_val, 1.0) > 0.06
            and (end_val - min_val) / max(end_val, 1.0) > 0.04
        ):
            return 3

        # Tone 1 (High flat): small range, flat slope
        if abs(ratio_end_start) <= 0.08 and pitch_range_ratio < 0.15:
            return 1

        # Fallback decision based on net slope
        if ratio_end_start > 0.04:
            return 2
        elif ratio_end_start < -0.04:
            return 4
        return 1

    def analyze_utterance(
        self,
        audio_data: bytes | np.ndarray,
        transcription: str,
        expected_context: str | None = None,
        sr: int = 16_000,
    ) -> dict:
        """
        Perform complete acoustic tone analysis on speech audio.

        Parameters
        ----------
        audio_data : bytes | np.ndarray
            Audio waveform or raw bytes.
        transcription : str
            ASR transcription text.
        expected_context : str | None
            Text from previous tutor prompt containing expected Chinese words.

        Returns
        -------
        dict
            Dict matching ToneAnalysisResult schema.
        """
        # 1. Extract target syllables & expected tones
        target_syllables = self.extract_pinyin_syllables(transcription)
        if not target_syllables and expected_context:
            target_syllables = self.extract_pinyin_syllables(expected_context)

        if not target_syllables:
            return {
                "overall_accuracy": 100.0,
                "tones": [],
                "summary": "Nessun morfema cinese con tono esplicito rilevato nella frase.",
            }

        # 2. Extract pitch contour
        y = ensure_float32_array(audio_data, target_sr=sr)
        f0, voiced_flag = extract_pitch_contour(y, sr=sr)
        voiced_chunks = self.segment_voiced_f0(f0, voiced_flag)

        if not voiced_chunks:
            return {
                "overall_accuracy": 0.0,
                "tones": [
                    {
                        "syllable": syll,
                        "expected_tone": exp_tone,
                        "detected_tone": 0,
                        "is_correct": False,
                        "pitch_contour": [],
                        "feedback": "Segnale vocale non sufficientemente chiaro per rilevare il tono.",
                    }
                    for syll, exp_tone in target_syllables
                ],
                "summary": "Audio non abbastanza chiaro per l'analisi acustica dei toni.",
            }

        # 3. Match voiced chunks to target syllables
        tones_result: list[dict] = []
        correct_count = 0

        # Associate chunks to syllables (e.g. 1-to-1 or last N chunks)
        num_targets = len(target_syllables)
        matched_chunks = voiced_chunks[-num_targets:] if len(voiced_chunks) >= num_targets else voiced_chunks

        for i, (syll, exp_tone) in enumerate(target_syllables):
            if i < len(matched_chunks):
                chunk = matched_chunks[i]
                detected_tone = self.classify_tone_contour(chunk)
                # Resample contour to 10 points for compact transmission/plotting
                indices = np.linspace(0, len(chunk) - 1, 10).astype(int)
                norm_contour = [round(float(chunk[idx]), 1) for idx in indices]
            else:
                # If there are more target syllables than voiced chunks detected, fallback to neutral/unknown
                detected_tone = exp_tone  # or fallback
                norm_contour = []

            is_correct = detected_tone == exp_tone
            if is_correct:
                correct_count += 1
                feedback = f"Ottimo! Hai pronunciato il {TONE_DESCRIPTIONS.get(exp_tone, 'tono')} correttamente."
            else:
                det_desc = f"{detected_tone}° tono" if detected_tone in (1, 2, 3, 4) else "tono neutro"
                feedback = (
                    f"Attenzione: hai pronunciato un {det_desc}, mentre per '{syll}' è richiesto il "
                    f"{TONE_DESCRIPTIONS.get(exp_tone, str(exp_tone) + '° tono')}."
                )

            tones_result.append({
                "syllable": syll,
                "expected_tone": exp_tone,
                "detected_tone": detected_tone,
                "is_correct": is_correct,
                "pitch_contour": norm_contour,
                "feedback": feedback,
            })

        overall_acc = round((correct_count / len(target_syllables)) * 100.0, 1)
        summary = (
            f"Precisione toni: {correct_count}/{len(target_syllables)} corretti ({overall_acc}%)."
        )

        return {
            "overall_accuracy": overall_acc,
            "tones": tones_result,
            "summary": summary,
        }

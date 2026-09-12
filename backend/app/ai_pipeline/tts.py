"""
TTS (Text-to-Speech) Module
=============================
MVP implementation using ``edge-tts`` (Microsoft Edge online TTS).
Fast, zero model downloads, high-quality voices.

Future upgrade path: replace with a local GPU model (StyleTTS2, XTTS,
Kokoro) once the conversational loop is validated.
"""

from __future__ import annotations

import asyncio
import io
import logging
import re

import edge_tts

logger = logging.getLogger(__name__)

from app.core.config import settings

# Default voice – natural-sounding US English female
# See full list: https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/voices/list
DEFAULT_VOICE = "en-US-AvaMultilingualNeural"


def strip_language_tags(text: str) -> str:
    """
    Remove inline language tags (e.g. <it>...</it>, <zh>...</zh>) and return clean text.
    Ensures proper word separation between adjacent tags and removes spaces before punctuation.
    Suitable for frontend UI display and chat logs.
    """
    if not text:
        return ""
    # Replace adjacent tag boundaries like </it><zh> with a space so words don't stick together
    cleaned = re.sub(r"</(?:it|zh|en)>\s*<(?:it|zh|en)>", " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"</?(?:it|zh|en)>", " ", cleaned, flags=re.IGNORECASE)
    # Ensure punctuation doesn't get separated from words
    cleaned = re.sub(r"\s+([.,!?;:])", r"\1", cleaned)
    return re.sub(r"[ \t]+", " ", cleaned).strip()


ITALIAN_ACCENTED_WORDS = {
    "è", "é", "perché", "poiché", "affinché", "benché", "cosicché", "giacché", "purché",
    "così", "già", "più", "può", "ciò", "là", "lì", "sì", "dà", "sé", "cioè",
    "qualità", "città", "università", "caffè", "verità", "novità", "realtà", "metà",
    "virtù", "gioventù", "perciò", "dopodiché",
    "sarà", "avrà", "farà", "andrà", "vorrà", "potrà", "dovrà", "verrà",
}

PINYIN_TONE_CHARS = set("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ")


def is_chinese_or_pinyin(word: str) -> bool:
    """
    Detect whether a token is Chinese text (Hanzi) or a Mandarin Pinyin word with tones.
    Strictly excludes common Italian accented words.
    """
    clean = re.sub(r"[^\w\u4e00-\u9fff\u3400-\u4dbfāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]", "", word)
    if not clean:
        return False
    # Check for Hanzi
    if re.search(r"[\u4e00-\u9fff\u3400-\u4dbf]", clean):
        return True
    low = clean.lower()
    if low in ITALIAN_ACCENTED_WORDS:
        return False
    # Italian words ending in -tà or -tù (umiltà, sincerità, onestà, difficoltà, etc.)
    if len(low) > 2 and (low.endswith("tà") or low.endswith("tù")):
        return False
    if low.endswith("ché") or low.endswith("cché"):
        return False
    # Check for Pinyin tone diacritics (e.g. nǐ, hǎo, duì, buqǐ, bàoràn)
    if any(c in PINYIN_TONE_CHARS for c in low):
        return True
    # Check for numbered pinyin (e.g. ren2, shi4, hao3)
    if re.match(r"^[a-z]+[1-5]$", low):
        return True
    return False


def split_italian_segment_by_chinese(it_text: str) -> list[tuple[str, str]]:
    """
    Sub-segment an Italian text fragment by rescuing any Hanzi or Pinyin tokens that were
    accidentally embedded without <zh> tags or placed inside an <it> tag block.
    """
    tokens = re.split(r"(\s+|[.,;:!?\"'“”«»()]+)", it_text)
    sub_segments: list[tuple[str, str]] = []
    current_lang = "it"
    current_buffer: list[str] = []

    for tok in tokens:
        if not tok:
            continue
        if is_chinese_or_pinyin(tok):
            if current_lang == "it" and current_buffer:
                flushed = clean_speech_segment("".join(current_buffer))
                if flushed:
                    sub_segments.append(("it", flushed))
                current_buffer = []
            current_lang = "zh"
            current_buffer.append(tok)
        elif re.match(r"^[\s.,;:!?\"'“”«»()]+$", tok):
            current_buffer.append(tok)
        else:
            if current_lang == "zh" and current_buffer:
                flushed = clean_speech_segment("".join(current_buffer))
                if flushed:
                    sub_segments.append(("zh", flushed))
                current_buffer = []
            current_lang = "it"
            current_buffer.append(tok)

    if current_buffer:
        flushed = clean_speech_segment("".join(current_buffer))
        if flushed:
            sub_segments.append((current_lang, flushed))

    return sub_segments


def clean_speech_segment(text: str) -> str:
    """
    Strip markdown formatting and standalone bullet markers for natural speech synthesis.
    Prevents TTS from reading out dashes, asterisks, or markdown symbols.
    """
    if not text:
        return ""
    # Remove markdown bold/italics markers, backticks, quotes, and header symbols
    t = re.sub(r"[\*_~`#\"'“”«»]", "", text)
    # Remove leading bullet symbols or standalone dashes
    t = re.sub(r"^\s*[-•]\s*", "", t)
    # Clean whitespace
    t = re.sub(r"\s+", " ", t).strip()
    # If the remaining string is only punctuation or symbols (e.g. "-", ".", ":"), drop it
    if re.match(r"^[\s\-_.,;:!?•*~#=]+$", t):
        return ""
    return t


def parse_language_tags(text: str, default_lang: str = "it") -> list[tuple[str, str]]:
    """
    Parse text containing <it>...</it> and <zh>...</zh> tags into sequential (language, text) segments.
    Uses token stream parsing and automatically rescues untagged Chinese characters / Pinyin from Italian text.
    Cleans markdown formatting from each segment for natural TTS synthesis.
    """
    if not text:
        return []

    # Check if any tags are present
    has_tags = bool(re.search(r"</?(?:it|zh|en)>", text, re.IGNORECASE))

    if not has_tags:
        # Fallback: if no tags present, split Italian text by Chinese/Pinyin
        return split_italian_segment_by_chinese(text) if default_lang in ("it", "zh") else [(default_lang, clean_speech_segment(text))]

    # Tokenize by tags
    tokens = re.split(r"(</?[a-zA-Z]+>)", text)
    raw_segments: list[tuple[str, str]] = []
    current_lang = default_lang

    for tok in tokens:
        if not tok:
            continue
        m_open = re.match(r"^<(it|zh|en)>$", tok, re.IGNORECASE)
        m_close = re.match(r"^</(it|zh|en)>$", tok, re.IGNORECASE)
        if m_open:
            current_lang = m_open.group(1).lower()
        elif m_close:
            current_lang = default_lang
        else:
            clean = clean_speech_segment(tok)
            if clean:
                raw_segments.append((current_lang, clean))

    # Secondary rescue pass: rescue any Chinese characters or Pinyin trapped inside "it" segments
    expanded_segments: list[tuple[str, str]] = []
    for lang, content in raw_segments:
        if lang == "it" and default_lang in ("it", "zh"):
            sub_segs = split_italian_segment_by_chinese(content)
            expanded_segments.extend(sub_segs)
        else:
            expanded_segments.append((lang, content))

    # Merge consecutive segments with the same language
    merged: list[tuple[str, str]] = []
    for lang, content in expanded_segments:
        if not content:
            continue
        if merged and merged[-1][0] == lang:
            merged[-1] = (lang, f"{merged[-1][1]} {content}")
        else:
            merged.append((lang, content))

    return merged


class TTSManager:
    """
    Text-to-Speech manager using edge-tts.
    Supports multi-voice polyglot synthesis using high-quality female voices.

    Parameters
    ----------
    voice : str
        Default Edge TTS voice identifier.
    """

    def __init__(self, voice: str = DEFAULT_VOICE) -> None:
        self.voice = voice
        logger.info("TTSManager initialised (voice=%s)", voice)

    def get_voice_for_language(self, language: str) -> str:
        """Return recommended female Edge TTS voice identifier for given language code."""
        lang = (language or "").strip().lower()
        if lang.startswith("zh"):
            return getattr(settings, "TTS_VOICE_ZH", "zh-CN-XiaoxiaoNeural")
        elif lang.startswith("it"):
            return getattr(settings, "TTS_VOICE_IT", "it-IT-ElsaNeural")
        elif lang.startswith("en"):
            return getattr(settings, "TTS_VOICE", "en-US-AvaMultilingualNeural")
        return self.voice

    async def generate_audio(self, text: str, voice: str | None = None) -> bytes:
        """
        Convert text to speech with a single voice and return MP3 audio bytes.

        Parameters
        ----------
        text : str
            The text to synthesise.
        voice : str | None
            Optional voice override (defaults to instance default voice).

        Returns
        -------
        bytes
            MP3 audio bytes.
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
            logger.debug(
                "TTS generated %d bytes of audio with voice '%s' for: %s",
                len(audio_bytes),
                target_voice,
                text[:60],
            )
            return audio_bytes

        except Exception as exc:
            logger.error("TTS synthesis failed (voice=%s): %s", target_voice, exc)
            raise

    async def generate_polyglot_audio(self, text: str, default_language: str = "en") -> bytes:
        """
        Synthesize text containing language tags (e.g. <it>...</it>, <zh>...</zh>)
        using distinct female native voices for each language segment, and
        concatenate into a single seamless audio stream.

        Parameters
        ----------
        text : str
            The raw text from LLM, possibly containing <it> or <zh> tags.
        default_language : str
            Session language ("zh" or "en").

        Returns
        -------
        bytes
            Concatenated MP3 audio bytes.
        """
        if not text or not text.strip():
            return b""

        # In English mode without tags, use simple single-voice fast path
        if default_language == "en" and not re.search(r"<(?:it|zh)>", text, re.IGNORECASE):
            return await self.generate_audio(text, voice=self.get_voice_for_language("en"))

        segments = parse_language_tags(text, default_lang="it" if default_language == "zh" else default_language)
        if not segments:
            clean_text = strip_language_tags(text)
            return await self.generate_audio(clean_text, voice=self.get_voice_for_language(default_language))

        # Synthesize each language segment concurrently
        async def _synth_segment(lang: str, seg_text: str) -> bytes:
            voice = self.get_voice_for_language(lang)
            try:
                return await self.generate_audio(seg_text, voice=voice)
            except Exception as exc:
                logger.warning("Failed to synthesize segment '%s' with voice '%s': %s", seg_text[:30], voice, exc)
                return b""

        tasks = [_synth_segment(lang, seg_text) for lang, seg_text in segments if seg_text.strip()]
        audio_chunks = await asyncio.gather(*tasks)

        full_audio = b"".join(chunk for chunk in audio_chunks if chunk)
        logger.info(
            "Polyglot TTS synthesized %d segments (%d bytes total audio) for text length %d",
            len(segments),
            len(full_audio),
            len(text),
        )
        return full_audio


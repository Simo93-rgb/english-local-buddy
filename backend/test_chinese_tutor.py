"""
Test script for Chinese Tutor, MandarinToneAnalyzer, ASR bilingual prompts,
and Polyglot TTS parsing.
"""

import sys
from pathlib import Path
import numpy as np

# Add backend directory to sys.path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.ai_pipeline.pronunciation import MandarinToneAnalyzer
from app.ai_pipeline.tts import parse_language_tags, strip_language_tags
from app.core.history_manager import HistoryManager


def test_settings_and_prompts():
    assert settings.LLM_MODEL and isinstance(settings.LLM_MODEL, str), f"Invalid LLM_MODEL: {settings.LLM_MODEL}"
    assert Path(settings.CHINESE_BEGINNER_PROMPT_PATH).exists(), "Beginner prompt does not exist"
    assert Path(settings.CHINESE_INTERMEDIATE_PROMPT_PATH).exists(), "Intermediate prompt does not exist"
    assert Path(settings.CHINESE_ADVANCED_PROMPT_PATH).exists(), "Advanced prompt does not exist"
    print("  -> Settings and prompt files verified successfully!")


def test_pinyin_tone_extraction():
    print("Testing pinyin tone extraction...")
    analyzer = MandarinToneAnalyzer()

    # Test 1: standard accented pinyin
    text1 = "Sto pronunciando bene rén shì?"
    syllables1 = analyzer.extract_pinyin_syllables(text1)
    assert ("rén", 2) in syllables1, f"Expected ('rén', 2), got {syllables1}"
    assert ("shì", 4) in syllables1, f"Expected ('shì', 4), got {syllables1}"

    # Test 2: 4 tones on ma
    text2 = "Ripeti: mā, má, mǎ, mà"
    syllables2 = analyzer.extract_pinyin_syllables(text2)
    assert syllables2 == [("mā", 1), ("má", 2), ("mǎ", 3), ("mà", 4)], f"Got {syllables2}"

    # Test 3: numbered pinyin
    text3 = "ni3 hao3 ma5"
    syllables3 = analyzer.extract_pinyin_syllables(text3)
    assert syllables3 == [("ni", 3), ("hao", 3), ("ma", 5)], f"Got {syllables3}"

    # Test 4: Italian accented stopwords are not falsely recognized as pinyin
    text4 = "Sì, è vero, perché così va bene"
    syllables4 = analyzer.extract_pinyin_syllables(text4)
    assert syllables4 == [], f"Expected no pinyin syllables from Italian stopwords, got {syllables4}"

    print("  -> Pinyin tone extraction verified successfully!")


def test_tone_contour_classification():
    print("Testing acoustic F0 contour classification...")
    analyzer = MandarinToneAnalyzer()

    # Tone 1: High flat (e.g. 250 Hz throughout)
    f0_tone1 = np.full(20, 250.0, dtype=np.float32)
    assert analyzer.classify_tone_contour(f0_tone1) == 1, "Failed Tone 1 classification"

    # Tone 2: Rising (e.g. 200 Hz -> 260 Hz)
    f0_tone2 = np.linspace(200.0, 265.0, 20, dtype=np.float32)
    assert analyzer.classify_tone_contour(f0_tone2) == 2, "Failed Tone 2 classification"

    # Tone 3: Dipping (e.g. 220 Hz -> 170 Hz -> 210 Hz)
    f0_tone3 = np.array([220, 210, 190, 175, 168, 172, 185, 205, 215], dtype=np.float32)
    assert analyzer.classify_tone_contour(f0_tone3) == 3, "Failed Tone 3 classification"

    # Tone 4: Falling (e.g. 280 Hz -> 180 Hz)
    f0_tone4 = np.linspace(280.0, 175.0, 20, dtype=np.float32)
    assert analyzer.classify_tone_contour(f0_tone4) == 4, "Failed Tone 4 classification"

    print("  -> Tone contour classification verified successfully!")


def test_tts_language_tags():
    print("Testing polyglot TTS tag parsing...")
    text = "<it>Benvenuto! In cinese ciao si dice</it> <zh>你好, nǐ hǎo</zh><it>. Prova a pronunciarlo!</it>"

    clean = strip_language_tags(text)
    assert "<it>" not in clean and "<zh>" not in clean
    assert "Benvenuto! In cinese ciao si dice 你好, nǐ hǎo. Prova a pronunciarlo!" == clean

    segments = parse_language_tags(text)
    assert len(segments) == 3
    assert segments[0][0] == "it"
    assert segments[1][0] == "zh"
    assert segments[2][0] == "it"

    # Nested / unclosed tag test
    nested = "<it>Ora prova con me: ripeti dopo di me, <zh>nǐ hǎo</zh><it>, sentendo il tono.</it>"
    nested_segs = parse_language_tags(nested)
    assert any(lang == "zh" and "nǐ hǎo" in s for lang, s in nested_segs), f"Failed to isolate zh in {nested_segs}"

    print("  -> Polyglot TTS tag parsing verified successfully!")


def test_pinyin_rescue_in_tts():
    print("Testing automatic pinyin and Hanzi rescue from Italian text...")
    sample = (
        'Certo! In cinese ci sono due modi molto comuni per scusarsi. '
        '对不起，duìbuqǐ è il modo più completo e formale... '
        'La pronuncia è delicata: "duì" come in "dietro"... "buqǐ" è veloce... '
        'L\'altro modo è: 抱歉，bàoràn... Ora prova a ripetere dopo di me: duìbuqǐ.'
    )
    segs = parse_language_tags(sample, default_lang="it")
    zh_texts = " ".join(s for lang, s in segs if lang == "zh")
    assert "duì" in zh_texts, f"duì not found in zh segments: {segs}"
    assert "buqǐ" in zh_texts, f"buqǐ not found in zh segments: {segs}"
    assert "bàoràn" in zh_texts, f"bàoràn not found in zh segments: {segs}"
    assert "对不起" in zh_texts, f"对不起 not found in zh segments: {segs}"
    assert "抱歉" in zh_texts, f"抱歉 not found in zh segments: {segs}"
    print("  -> Pinyin and Hanzi rescue verified successfully!")


def test_history_manager_routing():
    print("Testing HistoryManager report routing...")
    hm = HistoryManager()
    en_path = hm.get_report_file_path("20260912_120000_en")
    zh_path = hm.get_report_file_path("20260912_120000_zh")

    assert en_path.name == "user_report.md"
    assert zh_path.name == "user_chinese_report.md"
    print("  -> HistoryManager report routing verified successfully!")


if __name__ == "__main__":
    test_settings_and_prompts()
    test_pinyin_tone_extraction()
    test_tone_contour_classification()
    test_tts_language_tags()
    test_pinyin_rescue_in_tts()
    test_history_manager_routing()
    print("\nALL BACKEND TESTS PASSED SUCCESSFULLY! ✅")

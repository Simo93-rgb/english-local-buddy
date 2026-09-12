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
    print("Testing settings and prompt files...")
    assert settings.LLM_MODEL == "empero-ai/Qwen3.8-9B-Distill-GGUF", f"Unexpected LLM_MODEL: {settings.LLM_MODEL}"
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
    print("  -> Polyglot TTS tag parsing verified successfully!")


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
    test_history_manager_routing()
    print("\nALL BACKEND TESTS PASSED SUCCESSFULLY! ✅")

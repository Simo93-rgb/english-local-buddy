"""
Tests for HD TTS Audio Generator
Tests pinyin conversion, audio synthesis with rate/pitch, and the /api/tts/generate endpoint.
"""

import asyncio
from fastapi.testclient import TestClient

from app.main import app
from app.ai_pipeline.tts import TTSManager, pinyin_numbered_to_tone, parse_language_tags
from app.core.config import settings


def test_pinyin_conversion():
    print("Testing pinyin_numbered_to_tone...")
    assert pinyin_numbered_to_tone("ni3 hao3") == "nǐ hǎo"
    assert pinyin_numbered_to_tone("zhong1 wen2") == "zhōng wén"
    assert pinyin_numbered_to_tone("xue2 sheng1") == "xué shēng"
    assert pinyin_numbered_to_tone("lu:4") == "lǜ"
    assert pinyin_numbered_to_tone("lv4") == "lǜ"
    assert pinyin_numbered_to_tone("ma5") == "ma"
    assert pinyin_numbered_to_tone("nǐ hǎo") == "nǐ hǎo"
    assert pinyin_numbered_to_tone("你好世界") == "你好世界"
    print("  -> pinyin_numbered_to_tone verified successfully! ✅")


def test_tts_audio_synthesis():
    print("Testing TTSManager.generate_audio with rate/pitch...")
    manager = TTSManager(voice=settings.TTS_VOICE_ZH)

    async def _run():
        audio_hanzi = await manager.generate_audio("你好", rate="-10%", pitch="+0Hz")
        assert len(audio_hanzi) > 0, "Generated audio for Hanzi should not be empty"

        audio_pinyin = await manager.generate_audio("nǐ hǎo", rate="+0%", pitch="+0Hz")
        assert len(audio_pinyin) > 0, "Generated audio for Pinyin should not be empty"

    asyncio.run(_run())
    print("  -> TTSManager.generate_audio verified successfully! ✅")


def test_api_tts_endpoint():
    print("Testing /api/tts/generate endpoint...")
    client = TestClient(app)

    # 1. Pinyin with numbers test
    resp = client.post("/api/tts/generate", json={
        "text": "ni3 hao3 ma5?",
        "language": "zh",
        "rate": "-10%"
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "ok"
    assert data["processed_text"] == "nǐ hǎo ma?"
    assert data["audio_b64"] is not None
    assert len(data["audio_b64"]) > 100
    assert data["filename"].endswith(".mp3")

    # 2. Chinese characters test
    resp2 = client.post("/api/tts/generate", json={
        "text": "很高兴认识你",
        "language": "zh"
    })
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "ok"
    assert data2["processed_text"] == "很高兴认识你"
    assert len(data2["audio_b64"]) > 100

    # 3. Empty text validation
    resp3 = client.post("/api/tts/generate", json={
        "text": "   ",
        "language": "zh"
    })
    assert resp3.status_code == 400

    print("  -> /api/tts/generate endpoint verified successfully! ✅")


def test_polyglot_regression_voice_mapping():
    print("Testing polyglot regression voice mapping...")
    tts_manager = TTSManager(voice=settings.TTS_VOICE)

    text = "Bravissimo! <it>Sei stato davvero fantastico.</it> <zh>你好</zh> <it>continuiamo!</it>"
    segments = parse_language_tags(text, default_lang="it")

    expected_segments = [
        ("it", "Bravissimo! Sei stato davvero fantastico."),
        ("zh", "你好"),
        ("it", "continuiamo!"),
    ]
    assert segments == expected_segments, f"Expected {expected_segments}, got {segments}"

    mapped_voices = [
        (lang, seg, tts_manager.get_voice_for_language(lang, default_fallback="it"))
        for lang, seg in segments
    ]

    for lang, seg, voice in mapped_voices:
        if lang == "it":
            assert voice == settings.TTS_VOICE_IT, f"Expected Italian voice {settings.TTS_VOICE_IT}, got {voice} for segment '{seg}'"
        elif lang == "zh":
            assert voice == settings.TTS_VOICE_ZH, f"Expected Chinese voice {settings.TTS_VOICE_ZH}, got {voice} for segment '{seg}'"

        # Crucial regression check: NO segment in Chinese tutor session should map to Ava (en-US-AvaMultilingualNeural)
        assert voice != settings.TTS_VOICE, f"Segment '{seg}' incorrectly mapped to default Ava English voice {settings.TTS_VOICE}"

    # Also verify polyglot audio generation produces valid concatenated audio
    async def _test_gen():
        audio = await tts_manager.generate_polyglot_audio(text, default_language="zh", default_fallback_language="it")
        assert len(audio) > 1000, "Polyglot audio output should not be empty"

    asyncio.run(_test_gen())
    print("  -> test_polyglot_regression_voice_mapping verified successfully! ✅")


if __name__ == "__main__":
    test_pinyin_conversion()
    test_polyglot_regression_voice_mapping()
    test_tts_audio_synthesis()
    test_api_tts_endpoint()
    print("\nALL TTS GENERATOR TESTS PASSED! 🎉")


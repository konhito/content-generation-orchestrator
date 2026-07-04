import json

import pytest

from src.config import Config
from src.short.beat_mode import build_beat_mode_plan
from src.short.character import (
    attach_character_tracks,
    build_character_track,
    mouth_cues_from_gentle,
    mouth_cues_from_words,
    request_gentle_alignment,
)
from src.short.component_plan import build_component_plan
from src.short.generator import ShortGenerator
from src.short.models import (
    CharacterEvent,
    CharacterTrack,
    ShortBeatMode,
    ShortsBeat,
    ShortsVisual,
    VisualType,
)


def test_character_beat_contract():
    beat = ShortsBeat(
        id="beat_001",
        start_seconds=0,
        end_seconds=3,
        mode=ShortBeatMode.CHARACTER,
        character_track="character/tracks/beat_001.json",
        visual=ShortsVisual(
            type=VisualType.TEXT_HIGHLIGHT,
            primary_text="Why?",
        ),
        caption_text="Why does this happen?",
    )

    assert beat.mode == ShortBeatMode.CHARACTER
    assert beat.character_track.endswith(".json")


def test_character_track_rejects_overlapping_events():
    with pytest.raises(ValueError, match="overlap"):
        CharacterTrack(
            character_id="character_1",
            duration_seconds=2,
            events=[
                CharacterEvent(start=0, end=1.5),
                CharacterEvent(start=1, end=2),
            ],
        )


def test_mode_plan_limits_character_runs_and_memes():
    beats = [
        {"beat_id": f"beat_{index:03d}", "intent": "hook", "script_text": "Look at this"}
        for index in range(1, 6)
    ]

    plan = build_beat_mode_plan(beats, meme_slots={2})
    modes = [item["mode"] for item in plan]

    assert modes[2] == "meme"
    assert all(modes[index:index + 3] != ["character"] * 3 for index in range(len(modes) - 2))
    assert all(modes[index:index + 2] != ["meme"] * 2 for index in range(len(modes) - 1))


def test_mode_plan_uses_components_for_visual_mechanisms():
    plan = build_beat_mode_plan(
        [{"beat_id": "beat_001", "intent": "mechanism", "script_text": "The code transforms 10 tokens"}],
        meme_slots=set(),
    )

    assert plan[0]["mode"] == "component"


def test_mode_plan_keeps_a_component_in_short_sequences():
    beats = [
        {"beat_id": f"beat_{index:03d}", "intent": "context", "script_text": "Direct explanation"}
        for index in range(1, 4)
    ]

    plan = build_beat_mode_plan(beats, meme_slots={1})

    assert "component" in [item["mode"] for item in plan]


def test_word_timing_fallback_emits_bounded_mouth_cues():
    cues = mouth_cues_from_words(
        [{"word": "Hello", "start_seconds": 0.2, "end_seconds": 0.8}],
        emotion="happy",
        duration_seconds=1.0,
        mouth_map={"HH": {"happy": "d_j_ch_h"}, "EH": {"happy": "a_e_h"}},
    )

    assert cues
    assert all(0 <= cue.start < cue.end <= 1.0 for cue in cues)


def test_word_timing_fallback_matches_stressed_sync_toon_phonemes():
    cues = mouth_cues_from_words(
        [{"word": "apple", "start_seconds": 0, "end_seconds": 1}],
        emotion="happy",
        duration_seconds=1,
        mouth_map={"AE0": {"happy": "a_e_h"}, "M": {"happy": "m_b_close_h"}},
    )

    assert cues[0].shape == "a_e_h"


def test_gentle_phone_durations_drive_mouth_intervals():
    cues = mouth_cues_from_gentle(
        [{
            "word": "map",
            "start": 0.5,
            "end": 1.1,
            "phones": [{"phone": "M", "duration": 0.2}, {"phone": "AE1", "duration": 0.25}, {"phone": "P", "duration": 0.15}],
        }],
        emotion="happy",
        duration_seconds=2,
        mouth_map={"M": {"happy": "m_b_close_h"}, "AE1": {"happy": "a_e_h"}, "P": {"happy": "m_b_close_h"}},
    )

    assert [cue.shape for cue in cues] == ["m_b_close_h", "a_e_h", "m_b_close_h"]
    assert [(cue.start, cue.end) for cue in cues] == [(0.5, 0.7), (0.7, 0.95), (0.95, 1.1)]


def test_gentle_request_sends_audio_and_transcript(tmp_path):
    audio = tmp_path / "voice.mp3"
    audio.write_bytes(b"audio")
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"words": [{"word": "hello"}]}

    def fake_post(url, *, files, timeout):
        captured.update(url=url, files=files, timeout=timeout)
        return Response()

    words = request_gentle_alignment(audio, "hello", "http://gentle/transcriptions", 3, post=fake_post)

    assert words == [{"word": "hello"}]
    assert captured["files"]["transcript"][1] == "hello"
    assert captured["timeout"] == 3


def test_character_config_defaults_to_short_first_integration():
    config = Config()

    assert config.character.enabled is True
    assert config.character.character_id == "character_1"
    assert config.character.word_timing_fallback is True


def test_track_uses_manifest_fallback_for_unknown_pose():
    manifest = {
        "fallbacks": {"body": "body1", "head": "M", "eyes": "content_M", "mouth": "m_b_close_h"},
        "assets": {
            "body": {"body1": {}},
            "head": {"M": {}},
            "eyes": {"content_M": {}},
            "mouth": {"m_b_close_h": {}, "a_e_h": {}},
        },
        "mouth_map": {},
    }

    track, warnings = build_character_track(
        beat_id="beat_001",
        duration_seconds=2.0,
        word_timestamps=[],
        cue={"pose": "missing", "emotion": "content", "head": "M"},
        manifest=manifest,
    )

    assert track.events[0].pose == "body1"
    assert warnings
    assert track.blink_cues


def test_storyboard_loader_preserves_character_mode_and_track(tmp_path):
    path = tmp_path / "storyboard.json"
    path.write_text(
        json.dumps(
            {
                "id": "short",
                "title": "Character short",
                "total_duration_seconds": 3,
                "beats": [
                    {
                        "id": "beat_001",
                        "start_seconds": 0,
                        "end_seconds": 3,
                        "mode": "character",
                        "character_track": "character/tracks/beat_001.json",
                        "character_data": {
                            "character_id": "character_1",
                            "duration_seconds": 3,
                            "events": [{"start": 0, "end": 3, "pose": "body1", "emotion": "content", "head": "M"}],
                        },
                        "caption_text": "Hello",
                        "visual": {"type": "text_highlight", "primary_text": "Hello"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    storyboard = ShortGenerator.load_shorts_storyboard(path)

    assert storyboard.beats[0].mode == ShortBeatMode.CHARACTER
    assert storyboard.beats[0].character_track == "character/tracks/beat_001.json"
    assert storyboard.beats[0].character_data.character_id == "character_1"


def test_component_plan_uses_one_full_frame_item_per_mode():
    beats = [
        {"beat_id": "beat_001", "script_text": "Hello", "intent": "hook", "entities": []},
        {"beat_id": "beat_002", "script_text": "That failed", "intent": "reaction", "entities": []},
    ]
    modes = [
        {"id": "beat_001", "mode": "character"},
        {"id": "beat_002", "mode": "meme"},
    ]
    memes = [{"meme_text_top": "EXPECTATION", "meme_text_bottom": "REALITY"}]

    plan = build_component_plan(beats, memes, duration=6, niche="tech", mode_plan=modes)

    assert len(plan["components"]) == 2
    assert [item["mode"] for item in plan["components"]] == ["character", "meme"]
    assert plan["components"][1]["visual"]["type"] == "meme_card"


def test_attach_character_tracks_writes_artifact_and_reference(tmp_path):
    manifest_path = tmp_path / "character-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "fallbacks": {"body": "body1", "head": "M", "eyes": "content_M", "mouth": "m_b_close_h"},
                "assets": {
                    "body": {"body1": {}}, "head": {"M": {}},
                    "eyes": {"content_M": {}}, "mouth": {"m_b_close_h": {}},
                },
                "mouth_map": {},
            }
        ),
        encoding="utf-8",
    )
    beat = ShortsBeat(
        id="beat_001", start_seconds=1, end_seconds=3, mode=ShortBeatMode.CHARACTER,
        visual=ShortsVisual(type=VisualType.TEXT_HIGHLIGHT, primary_text="Hello"),
        caption_text="Hello", word_timestamps=[{"word": "Hello", "start_seconds": 1.2, "end_seconds": 1.8}],
    )

    attach_character_tracks([beat], manifest_path, tmp_path / "character/tracks")

    assert beat.character_track == "character/tracks/beat_001.json"
    assert beat.character_data is not None
    assert (tmp_path / beat.character_track).exists()

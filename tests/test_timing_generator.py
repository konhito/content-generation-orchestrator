"""Tests for the timing generator module."""

import pytest
from pathlib import Path
import tempfile
import json

from src.short.timing_generator import (
    find_word_frame,
    find_word_frame_fuzzy,
    calculate_beat_timing,
    generate_timing_data,
    generate_timing_typescript,
    generate_timing_file,
    add_phase_markers_to_beat,
    update_storyboard_with_markers,
)
from src.short.models import (
    ShortsBeat,
    ShortsStoryboard,
    ShortsVisual,
    VisualType,
    PhaseMarker,
)


class TestFindWordFrame:
    """Tests for find_word_frame function."""

    @pytest.fixture
    def sample_timestamps(self):
        """Sample word timestamps for testing."""
        return [
            {"word": "Hello", "start_seconds": 0.0, "end_seconds": 0.5},
            {"word": "world,", "start_seconds": 0.5, "end_seconds": 1.0},
            {"word": "GPT,", "start_seconds": 1.0, "end_seconds": 1.5},
            {"word": "Claude", "start_seconds": 1.5, "end_seconds": 2.0},
            {"word": "Gemini.", "start_seconds": 2.0, "end_seconds": 2.5},
        ]

    def test_exact_match(self, sample_timestamps):
        """Test exact word matching."""
        frame = find_word_frame(sample_timestamps, "Hello", fps=30, match_mode="exact")
        assert frame == 15  # 0.5s * 30fps = 15 frames (end time)

    def test_exact_match_with_punctuation(self, sample_timestamps):
        """Test exact matching strips punctuation."""
        frame = find_word_frame(sample_timestamps, "GPT", fps=30, match_mode="exact")
        assert frame == 45  # 1.5s * 30fps

    def test_contains_match(self, sample_timestamps):
        """Test contains matching."""
        frame = find_word_frame(sample_timestamps, "ello", fps=30, match_mode="contains")
        assert frame == 15  # Matches "Hello"

    def test_starts_with_match(self, sample_timestamps):
        """Test starts_with matching."""
        frame = find_word_frame(sample_timestamps, "Gem", fps=30, match_mode="starts_with")
        assert frame == 75  # 2.5s * 30fps

    def test_use_start_time(self, sample_timestamps):
        """Test using word start time instead of end time."""
        frame = find_word_frame(sample_timestamps, "GPT", fps=30, use_start=True)
        assert frame == 30  # 1.0s * 30fps (start time)

    def test_offset_frames(self, sample_timestamps):
        """Test applying frame offset."""
        frame = find_word_frame(sample_timestamps, "GPT", fps=30, use_start=True, offset_frames=-3)
        assert frame == 27  # 30 - 3 = 27

    def test_word_not_found(self, sample_timestamps):
        """Test returning None for missing word."""
        frame = find_word_frame(sample_timestamps, "NotFound", fps=30)
        assert frame is None

    def test_case_insensitive(self, sample_timestamps):
        """Test case-insensitive matching."""
        frame = find_word_frame(sample_timestamps, "hello", fps=30, match_mode="exact")
        assert frame == 15

    def test_target_with_punctuation(self, sample_timestamps):
        """Test matching when target has punctuation."""
        frame = find_word_frame(sample_timestamps, "GPT,", fps=30, match_mode="exact")
        assert frame == 45


class TestFindWordFrameFuzzy:
    """Tests for find_word_frame_fuzzy function."""

    @pytest.fixture
    def sample_timestamps(self):
        return [
            {"word": "Transformers", "start_seconds": 0.0, "end_seconds": 0.76},
            {"word": "power", "start_seconds": 0.76, "end_seconds": 1.02},
            {"word": "GPT,", "start_seconds": 1.0, "end_seconds": 1.5},
        ]

    def test_exact_match_preferred(self, sample_timestamps):
        """Test that exact match is preferred over fuzzy."""
        frame = find_word_frame_fuzzy(sample_timestamps, "GPT", fps=30)
        assert frame == 45  # Exact match on "GPT" (stripped from "GPT,")

    def test_fuzzy_fallback(self, sample_timestamps):
        """Test fuzzy matching when exact fails."""
        frame = find_word_frame_fuzzy(sample_timestamps, "Trans", fps=30)
        assert frame is not None  # Should match "Transformers" via starts_with

    def test_not_found_returns_none(self, sample_timestamps):
        """Test returning None when no match found."""
        frame = find_word_frame_fuzzy(sample_timestamps, "NotFound", fps=30)
        assert frame is None


class TestCalculateBeatTiming:
    """Tests for calculate_beat_timing function."""

    def test_basic_timing_calculation(self):
        """Test basic timing calculation with phase markers."""
        beat = ShortsBeat(
            id="beat_1",
            start_seconds=0.0,
            end_seconds=5.0,
            visual=ShortsVisual(type=VisualType.BIG_NUMBER, primary_text="Test"),
            caption_text="Test caption",
            word_timestamps=[
                {"word": "GPT,", "start_seconds": 1.0, "end_seconds": 1.5},
                {"word": "Claude", "start_seconds": 2.0, "end_seconds": 2.5},
            ],
            phase_markers=[
                PhaseMarker(id="gptAppear", end_word="GPT,"),
                PhaseMarker(id="claudeAppear", end_word="Claude"),
            ],
        )

        timing = calculate_beat_timing(beat, fps=30)

        assert timing["duration"] == 150  # 5s * 30fps
        assert timing["gptAppear"] == 27  # 1.0s * 30fps - 3 offset = 27
        assert timing["claudeAppear"] == 57  # 2.0s * 30fps - 3 offset = 57

    def test_missing_word_uses_default(self):
        """Test that missing words fall back to middle of beat."""
        beat = ShortsBeat(
            id="beat_1",
            start_seconds=0.0,
            end_seconds=4.0,
            visual=ShortsVisual(type=VisualType.BIG_NUMBER, primary_text="Test"),
            caption_text="Test caption",
            word_timestamps=[
                {"word": "Hello", "start_seconds": 0.0, "end_seconds": 0.5},
            ],
            phase_markers=[
                PhaseMarker(id="missingPhase", end_word="NotFound"),
            ],
        )

        timing = calculate_beat_timing(beat, fps=30)

        assert timing["duration"] == 120
        assert timing["missingPhase"] == 60  # Default to middle: 120 / 2

    def test_negative_offset_clamped_to_zero(self):
        """Test that negative frame results are clamped to 0."""
        beat = ShortsBeat(
            id="beat_1",
            start_seconds=0.0,
            end_seconds=1.0,
            visual=ShortsVisual(type=VisualType.BIG_NUMBER, primary_text="Test"),
            caption_text="Test",
            word_timestamps=[
                {"word": "Early", "start_seconds": 0.0, "end_seconds": 0.1},
            ],
            phase_markers=[
                PhaseMarker(id="earlyPhase", end_word="Early"),
            ],
        )

        timing = calculate_beat_timing(beat, fps=30, animation_lead_frames=-5)

        assert timing["earlyPhase"] >= 0  # Should not be negative


class TestGenerateTimingData:
    """Tests for generate_timing_data function."""

    def test_generates_timing_for_beats_with_markers(self):
        """Test that timing is generated only for beats with markers."""
        storyboard = ShortsStoryboard(
            id="test_short",
            title="Test Short",
            total_duration_seconds=10.0,
            beats=[
                ShortsBeat(
                    id="beat_1",
                    start_seconds=0.0,
                    end_seconds=5.0,
                    visual=ShortsVisual(type=VisualType.BIG_NUMBER, primary_text="Test"),
                    caption_text="Test",
                    word_timestamps=[{"word": "Test", "start_seconds": 0.0, "end_seconds": 0.5}],
                    phase_markers=[PhaseMarker(id="phase1", end_word="Test")],
                ),
                ShortsBeat(
                    id="beat_2",
                    start_seconds=5.0,
                    end_seconds=10.0,
                    visual=ShortsVisual(type=VisualType.BIG_NUMBER, primary_text="Test2"),
                    caption_text="No markers",
                    word_timestamps=[],
                    phase_markers=[],  # No markers
                ),
            ],
        )

        timing_data = generate_timing_data(storyboard, fps=30)

        assert "beat_1" in timing_data
        assert "beat_2" not in timing_data  # No markers, not included


class TestGenerateTimingTypescript:
    """Tests for generate_timing_typescript function."""

    def test_generates_valid_typescript(self):
        """Test that generated TypeScript is syntactically correct."""
        timing_data = {
            "beat_1": {"duration": 150, "phase1End": 50},
            "beat_2": {"duration": 100, "gptAppear": 30},
        }

        typescript = generate_timing_typescript(timing_data)

        assert "export const TIMING = {" in typescript
        assert "beat_1: {" in typescript
        assert "duration: 150," in typescript
        assert "} as const;" in typescript
        assert "export type BeatTiming" in typescript

    def test_includes_header_comment(self):
        """Test that generated code includes header comment."""
        timing_data = {"beat_1": {"duration": 100}}

        typescript = generate_timing_typescript(timing_data)

        assert "Auto-generated" in typescript
        assert "DO NOT EDIT MANUALLY" in typescript


class TestGenerateTimingFile:
    """Tests for generate_timing_file function."""

    def test_writes_file_to_path(self):
        """Test that timing file is written to specified path."""
        storyboard = ShortsStoryboard(
            id="test_short",
            title="Test",
            total_duration_seconds=5.0,
            beats=[
                ShortsBeat(
                    id="beat_1",
                    start_seconds=0.0,
                    end_seconds=5.0,
                    visual=ShortsVisual(type=VisualType.BIG_NUMBER, primary_text="Test"),
                    caption_text="Test",
                    word_timestamps=[{"word": "Test", "start_seconds": 0.0, "end_seconds": 0.5}],
                    phase_markers=[PhaseMarker(id="testPhase", end_word="Test")],
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "timing.ts"
            timing_data = generate_timing_file(storyboard, output_path, fps=30)

            assert output_path.exists()
            content = output_path.read_text()
            assert "TIMING" in content
            assert "beat_1" in content
            assert timing_data["beat_1"]["duration"] == 150


class TestPhaseMarkerHelpers:
    """Tests for phase marker helper functions."""

    def test_add_phase_markers_to_beat(self):
        """Test adding phase markers to a beat."""
        beat = ShortsBeat(
            id="beat_1",
            start_seconds=0.0,
            end_seconds=5.0,
            visual=ShortsVisual(type=VisualType.BIG_NUMBER, primary_text="Test"),
            caption_text="Test",
            word_timestamps=[],
        )

        markers = [
            {"id": "phase1", "end_word": "word1", "description": "Phase 1"},
            {"id": "phase2", "end_word": "word2"},
        ]

        updated_beat = add_phase_markers_to_beat(beat, markers)

        assert len(updated_beat.phase_markers) == 2
        assert updated_beat.phase_markers[0].id == "phase1"
        assert updated_beat.phase_markers[0].end_word == "word1"
        assert updated_beat.phase_markers[0].description == "Phase 1"
        assert updated_beat.phase_markers[1].description == ""

    def test_update_storyboard_with_markers(self):
        """Test updating storyboard beats with markers."""
        storyboard = ShortsStoryboard(
            id="test_short",
            title="Test",
            total_duration_seconds=10.0,
            beats=[
                ShortsBeat(
                    id="beat_1",
                    start_seconds=0.0,
                    end_seconds=5.0,
                    visual=ShortsVisual(type=VisualType.BIG_NUMBER, primary_text="Test"),
                    caption_text="Test",
                    word_timestamps=[],
                ),
                ShortsBeat(
                    id="beat_2",
                    start_seconds=5.0,
                    end_seconds=10.0,
                    visual=ShortsVisual(type=VisualType.BIG_NUMBER, primary_text="Test2"),
                    caption_text="Test2",
                    word_timestamps=[],
                ),
            ],
        )

        beat_markers = {
            "beat_1": [{"id": "p1", "end_word": "w1"}],
            "beat_2": [{"id": "p2", "end_word": "w2"}, {"id": "p3", "end_word": "w3"}],
        }

        updated = update_storyboard_with_markers(storyboard, beat_markers)

        assert len(updated.beats[0].phase_markers) == 1
        assert len(updated.beats[1].phase_markers) == 2


class TestIntegrationWithRealData:
    """Integration tests using realistic data patterns."""

    def test_beat1_llm_logos_timing(self):
        """Test timing calculation for Beat 1 (LLM logos) pattern."""
        beat = ShortsBeat(
            id="beat_1",
            start_seconds=0.0,
            end_seconds=5.3,
            visual=ShortsVisual(type=VisualType.FLOW_DIAGRAM, primary_text=""),
            caption_text="Transformers power every major language model, GPT, Claude Gemini.",
            word_timestamps=[
                {"word": "Transformers", "start_seconds": 0.0, "end_seconds": 0.76},
                {"word": "power", "start_seconds": 0.76, "end_seconds": 1.02},
                {"word": "every", "start_seconds": 1.02, "end_seconds": 1.6},
                {"word": "major", "start_seconds": 1.6, "end_seconds": 2.0},
                {"word": "language", "start_seconds": 2.0, "end_seconds": 2.38},
                {"word": "model,", "start_seconds": 2.38, "end_seconds": 2.88},
                {"word": "GPT,", "start_seconds": 3.28, "end_seconds": 4.06},
                {"word": "Claude", "start_seconds": 4.5, "end_seconds": 4.76},
                {"word": "Gemini.", "start_seconds": 4.76, "end_seconds": 5.3},
            ],
            phase_markers=[
                PhaseMarker(id="gptAppear", end_word="GPT,"),
                PhaseMarker(id="claudeAppear", end_word="Claude"),
                PhaseMarker(id="geminiAppear", end_word="Gemini."),
            ],
        )

        timing = calculate_beat_timing(beat, fps=30, animation_lead_frames=-3)

        # GPT starts at 3.28s = 98 frames, with -3 offset = 95 frames
        assert timing["gptAppear"] == 95
        # Claude starts at 4.5s = 135 frames, with -3 offset = 132 frames
        assert timing["claudeAppear"] == 132
        # Gemini starts at 4.76s = 142 frames, with -3 offset = 139 frames
        assert timing["geminiAppear"] == 139
        # Duration: 5.3s * 30fps = 159 frames
        assert timing["duration"] == 159

    def test_beat6_multi_phase_timing(self):
        """Test timing calculation for Beat 6 (complex multi-phase) pattern."""
        beat = ShortsBeat(
            id="beat_6",
            start_seconds=29.04,
            end_seconds=55.0,
            visual=ShortsVisual(type=VisualType.PATCH_GRID, primary_text=""),
            caption_text="In 2020, vision transformers solve this with one key insight.",
            word_timestamps=[
                {"word": "In", "start_seconds": 0.0, "end_seconds": 0.58},
                {"word": "2020,", "start_seconds": 0.58, "end_seconds": 1.16},
                {"word": "vision", "start_seconds": 1.62, "end_seconds": 1.86},
                {"word": "transformers", "start_seconds": 1.86, "end_seconds": 2.5},
                {"word": "solve", "start_seconds": 2.5, "end_seconds": 2.76},
                {"word": "this", "start_seconds": 2.76, "end_seconds": 3.08},
                {"word": "with", "start_seconds": 3.08, "end_seconds": 3.32},
                {"word": "one", "start_seconds": 3.32, "end_seconds": 3.6},
                {"word": "key", "start_seconds": 3.6, "end_seconds": 3.88},
                {"word": "insight.", "start_seconds": 3.88, "end_seconds": 4.42},
            ],
            phase_markers=[
                PhaseMarker(id="phase1End", end_word="insight."),
            ],
        )

        timing = calculate_beat_timing(beat, fps=30, animation_lead_frames=-3)

        # "insight." starts at 3.88s = 116 frames, with -3 offset = 113 frames
        assert timing["phase1End"] == 113
        # Duration: (55.0 - 29.04) = 25.96s * 30fps = 778 frames
        assert timing["duration"] == 778


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_word_timestamps(self):
        """Test handling of empty word timestamps."""
        beat = ShortsBeat(
            id="beat_1",
            start_seconds=0.0,
            end_seconds=5.0,
            visual=ShortsVisual(type=VisualType.BIG_NUMBER, primary_text="Test"),
            caption_text="Test",
            word_timestamps=[],
            phase_markers=[PhaseMarker(id="phase1", end_word="missing")],
        )

        timing = calculate_beat_timing(beat, fps=30)

        # Should fall back to middle of beat
        assert timing["phase1"] == 75  # 150 / 2

    def test_empty_storyboard(self):
        """Test handling of storyboard with no beats."""
        storyboard = ShortsStoryboard(
            id="empty",
            title="Empty",
            total_duration_seconds=0.0,
            beats=[],
        )

        timing_data = generate_timing_data(storyboard)

        assert timing_data == {}

    def test_unicode_in_words(self):
        """Test handling of unicode characters in words."""
        timestamps = [
            {"word": "café", "start_seconds": 0.0, "end_seconds": 0.5},
            {"word": "naïve", "start_seconds": 0.5, "end_seconds": 1.0},
        ]

        frame = find_word_frame(timestamps, "café", fps=30, match_mode="exact")
        assert frame == 15

    def test_very_long_duration(self):
        """Test handling of very long beat durations."""
        beat = ShortsBeat(
            id="beat_1",
            start_seconds=0.0,
            end_seconds=3600.0,  # 1 hour
            visual=ShortsVisual(type=VisualType.BIG_NUMBER, primary_text="Test"),
            caption_text="Test",
            word_timestamps=[],
            phase_markers=[],
        )

        timing = calculate_beat_timing(beat, fps=30)

        assert timing["duration"] == 108000  # 3600 * 30

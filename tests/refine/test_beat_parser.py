"""Tests for beat parser."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.refine.models import Beat
from src.refine.visual.beat_parser import BeatParser, MockBeatParser


class TestBeatParser:
    """Tests for BeatParser class."""

    def test_parser_initialization(self, mock_llm_provider):
        """Test BeatParser initialization."""
        parser = BeatParser(llm_provider=mock_llm_provider)
        assert parser.llm == mock_llm_provider

    def test_parse_narration_basic(self, mock_llm_provider):
        """Test parsing a simple narration."""
        # Mock the generate_json method
        mock_llm_provider.generate_json = MagicMock(
            return_value={
                "beats": [
                    {
                        "index": 0,
                        "start_seconds": 0,
                        "end_seconds": 5,
                        "text": "First beat",
                        "expected_visual": "Visual 1"
                    },
                    {
                        "index": 1,
                        "start_seconds": 5,
                        "end_seconds": 10,
                        "text": "Second beat",
                        "expected_visual": "Visual 2"
                    }
                ]
            }
        )

        parser = BeatParser(llm_provider=mock_llm_provider)
        beats = parser.parse(
            narration_text="First beat. Second beat.",
            duration_seconds=10.0,
        )

        assert len(beats) == 2
        assert beats[0].text == "First beat"
        assert beats[1].text == "Second beat"

    def test_parse_narration_empty(self, mock_llm_provider):
        """Test parsing empty narration."""
        mock_llm_provider.generate_json = MagicMock(return_value={"beats": []})

        parser = BeatParser(llm_provider=mock_llm_provider)
        beats = parser.parse(narration_text="", duration_seconds=0)

        assert len(beats) == 0

    def test_fallback_parsing_on_llm_error(self, mock_llm_provider):
        """Test fallback heuristic parsing when LLM fails."""
        mock_llm_provider.generate_json = MagicMock(side_effect=Exception("LLM error"))

        parser = BeatParser(llm_provider=mock_llm_provider)
        beats = parser.parse(
            narration_text="First sentence. Second sentence. Third sentence.",
            duration_seconds=15.0,
        )

        # Should use fallback parsing
        assert len(beats) >= 1

    def test_fallback_parsing_on_invalid_response(self, mock_llm_provider):
        """Test fallback when LLM returns invalid response."""
        mock_llm_provider.generate_json = MagicMock(side_effect=ValueError("Invalid JSON"))

        parser = BeatParser(llm_provider=mock_llm_provider)
        beats = parser.parse(
            narration_text="Some narration text here.",
            duration_seconds=10.0,
        )

        # Should use fallback parsing
        assert len(beats) >= 1


class TestMockBeatParser:
    """Tests for MockBeatParser class."""

    def test_mock_parser_initialization(self):
        """Test MockBeatParser initialization."""
        parser = MockBeatParser()
        assert parser is not None

    def test_mock_parser_generates_beats(self):
        """Test that mock parser generates consistent beats."""
        parser = MockBeatParser()

        beats = parser.parse(
            narration_text="Test narration text.",
            duration_seconds=10.0,
        )

        assert len(beats) == 4  # MockBeatParser creates 4 beats
        assert all(isinstance(b, Beat) for b in beats)

    def test_mock_parser_respects_duration(self):
        """Test that mock beats fit within duration."""
        parser = MockBeatParser()

        duration = 20.0
        beats = parser.parse(
            narration_text="Longer test narration with multiple sentences.",
            duration_seconds=duration,
        )

        # All beats should end within duration
        for beat in beats:
            assert beat.end_seconds <= duration

        # Last beat should end at duration
        assert beats[-1].end_seconds == duration

    def test_mock_parser_sequential_beats(self):
        """Test that mock beats are sequential."""
        parser = MockBeatParser()

        beats = parser.parse(
            narration_text="First. Second. Third.",
            duration_seconds=15.0,
        )

        # Beats should be sequential with no gaps
        for i in range(1, len(beats)):
            assert beats[i].start_seconds == beats[i - 1].end_seconds


class TestBeatParserPrompt:
    """Tests for beat parser prompt construction."""

    def test_parser_has_parse_method(self, mock_llm_provider):
        """Test that parser has parse method."""
        parser = BeatParser(llm_provider=mock_llm_provider)
        assert hasattr(parser, "parse")
        assert callable(parser.parse)


class TestBeatValidation:
    """Tests for beat validation."""

    def test_beats_have_required_fields(self, sample_beats):
        """Test that beats have all required fields."""
        for beat in sample_beats:
            assert hasattr(beat, "index")
            assert hasattr(beat, "start_seconds")
            assert hasattr(beat, "end_seconds")
            assert hasattr(beat, "text")

    def test_beats_have_valid_timing(self, sample_beats):
        """Test that beats have valid timing."""
        for beat in sample_beats:
            assert beat.start_seconds >= 0
            assert beat.end_seconds > beat.start_seconds
            assert beat.duration_seconds > 0

    def test_beats_are_contiguous(self, sample_beats):
        """Test that beats are contiguous without gaps."""
        for i in range(1, len(sample_beats)):
            # Each beat should start where previous ended
            # (or very close for floating point)
            gap = abs(sample_beats[i].start_seconds - sample_beats[i - 1].end_seconds)
            assert gap < 0.1, f"Gap of {gap}s between beats {i-1} and {i}"


class TestBeatTimingValidation:
    """Tests for beat timing validation and fixing."""

    def test_validate_fixes_out_of_order_beats(self, mock_llm_provider):
        """Test that validation sorts beats by start time."""
        mock_llm_provider.generate_json = MagicMock(
            return_value={
                "beats": [
                    {"index": 0, "start_seconds": 5, "end_seconds": 10, "text": "Second"},
                    {"index": 1, "start_seconds": 0, "end_seconds": 5, "text": "First"},
                ]
            }
        )

        parser = BeatParser(llm_provider=mock_llm_provider)
        beats = parser.parse("Test", 10.0)

        # Should be sorted by start time
        assert beats[0].start_seconds < beats[1].start_seconds

    def test_validate_fixes_gaps(self, mock_llm_provider):
        """Test that validation removes gaps between beats."""
        mock_llm_provider.generate_json = MagicMock(
            return_value={
                "beats": [
                    {"index": 0, "start_seconds": 0, "end_seconds": 3, "text": "First"},
                    {"index": 1, "start_seconds": 5, "end_seconds": 10, "text": "Second"},
                ]
            }
        )

        parser = BeatParser(llm_provider=mock_llm_provider)
        beats = parser.parse("Test", 10.0)

        # First beat's end should equal second beat's start (no gap)
        assert beats[0].end_seconds == beats[1].start_seconds

    def test_validate_ensures_duration_coverage(self, mock_llm_provider):
        """Test that last beat ends at duration."""
        mock_llm_provider.generate_json = MagicMock(
            return_value={
                "beats": [
                    {"index": 0, "start_seconds": 0, "end_seconds": 5, "text": "First"},
                ]
            }
        )

        parser = BeatParser(llm_provider=mock_llm_provider)
        beats = parser.parse("Test", 10.0)

        assert beats[-1].end_seconds == 10.0

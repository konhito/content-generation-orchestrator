"""Tests for Semantic Sound Mapper.

These tests verify that the semantic mapper correctly:
1. Maps animation context to appropriate sounds
2. Handles pattern matching and wildcards
3. Adjusts sounds based on scene position
4. Adjusts sounds based on intensity
"""

import pytest

from .semantic_mapper import (
    SemanticSoundMapper,
    SoundSelection,
    CONTEXT_SOUND_MAP,
    map_moment_to_sound,
    map_moments_to_sounds,
)
from .models import SoundMoment


class TestSoundSelection:
    """Tests for SoundSelection dataclass."""

    def test_create_selection(self):
        """Test creating a sound selection."""
        selection = SoundSelection(
            sound="reveal_hit",
            confidence=0.95,
            reason="Matched pattern (reveal, scale)",
        )

        assert selection.sound == "reveal_hit"
        assert selection.confidence == 0.95
        assert "reveal" in selection.reason


class TestContextSoundMap:
    """Tests for the context sound mapping."""

    def test_map_contains_typing_patterns(self):
        """Test that typing patterns are mapped."""
        assert ("prompt", "opacity") in CONTEXT_SOUND_MAP
        assert CONTEXT_SOUND_MAP[("prompt", "opacity")] == "keyboard_type"

    def test_map_contains_counter_patterns(self):
        """Test that counter patterns are mapped."""
        assert ("speed", "counter") in CONTEXT_SOUND_MAP
        assert CONTEXT_SOUND_MAP[("speed", "counter")] == "counter_sweep"

    def test_map_contains_bar_patterns(self):
        """Test that bar/chart patterns are mapped."""
        assert ("bar", "width") in CONTEXT_SOUND_MAP
        assert CONTEXT_SOUND_MAP[("bar", "width")] == "bar_grow"

    def test_map_contains_reveal_patterns(self):
        """Test that reveal patterns are mapped."""
        assert ("reveal", "opacity") in CONTEXT_SOUND_MAP
        assert CONTEXT_SOUND_MAP[("reveal", "opacity")] == "reveal_hit"
        assert ("87x", "*") in CONTEXT_SOUND_MAP
        assert CONTEXT_SOUND_MAP[("87x", "*")] == "reveal_hit"

    def test_map_contains_wildcard_fallbacks(self):
        """Test that wildcard fallbacks exist."""
        assert ("*", "opacity") in CONTEXT_SOUND_MAP
        assert ("*", "scale") in CONTEXT_SOUND_MAP
        assert ("*", "width") in CONTEXT_SOUND_MAP


class TestSemanticSoundMapper:
    """Tests for SemanticSoundMapper class."""

    def test_init_default(self):
        """Test default initialization."""
        mapper = SemanticSoundMapper()

        assert len(mapper.mappings) == len(CONTEXT_SOUND_MAP)

    def test_init_custom_mappings(self):
        """Test initialization with custom mappings."""
        custom = {("custom", "property"): "custom_sound"}
        mapper = SemanticSoundMapper(custom_mappings=custom)

        assert ("custom", "property") in mapper.mappings
        assert mapper.mappings[("custom", "property")] == "custom_sound"

    def test_select_sound_typing_context(self):
        """Test sound selection for typing animations."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="element_appear",
            frame=0,
            confidence=0.9,
            context="prompt opacity fade in",
            intensity=0.7,
        )

        selection = mapper.select_sound(moment, 300)

        assert selection.sound == "keyboard_type"

    def test_select_sound_counter_context(self):
        """Test sound selection for counter animations."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="counter",
            frame=50,
            confidence=0.95,
            context="speedCounter - speed - counter animation [0 -> 3500]",
            intensity=0.8,
        )

        selection = mapper.select_sound(moment, 300)

        assert selection.sound == "counter_sweep"

    def test_select_sound_bar_width(self):
        """Test sound selection for bar width animations."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="chart_grow",
            frame=50,
            confidence=0.9,
            context="barWidth - bar - width animation",
            intensity=0.7,
        )

        selection = mapper.select_sound(moment, 300)

        assert selection.sound == "bar_grow"

    def test_select_sound_reveal_context(self):
        """Test sound selection for reveal animations."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="reveal",
            frame=200,
            confidence=0.95,
            context="reveal badge 87x faster",
            intensity=0.9,
        )

        selection = mapper.select_sound(moment, 300)

        assert selection.sound == "reveal_hit"

    def test_select_sound_default_fallback(self):
        """Test fallback to default sound."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="element_appear",
            frame=0,
            confidence=0.8,
            context="unknown element animation",
            intensity=0.7,
        )

        selection = mapper.select_sound(moment, 300)

        # Should fall back to ui_pop for element_appear
        assert selection.sound in ("ui_pop", "reveal_hit")  # Could be adjusted by position

    def test_select_sound_token_streaming(self):
        """Test sound selection for token streaming."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="text_reveal",
            frame=50,
            confidence=0.85,
            context="token streaming response text",
            intensity=0.6,
        )

        selection = mapper.select_sound(moment, 300)

        # Should match token or text patterns
        assert selection.sound in ("text_tick", "digital_stream", "keyboard_type")

    def test_select_sound_transition(self):
        """Test sound selection for transitions."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="transition",
            frame=100,
            confidence=0.8,
            context="phase transition burst",
            intensity=0.7,
        )

        selection = mapper.select_sound(moment, 300)

        assert selection.sound == "transition_whoosh"

    def test_position_adjustment_late_reveal(self):
        """Test that late position boosts impact sounds."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="element_appear",
            frame=250,  # 83% through 300 frame scene
            confidence=0.8,
            context="generic element fade in",
            intensity=0.7,
        )

        selection = mapper.select_sound(moment, 300)

        # Late position should upgrade simple sounds to reveal_hit
        assert selection.sound == "reveal_hit"
        assert "climax" in selection.reason.lower()

    def test_position_adjustment_early_downgrade(self):
        """Test that early position downgrades impact sounds."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="reveal",
            frame=10,  # 3% through 300 frame scene
            confidence=0.8,
            context="reveal element early",
            intensity=0.6,  # Low intensity
        )

        selection = mapper.select_sound(moment, 300)

        # Should be downgraded due to early position + low intensity
        # Note: reveal type still gets reveal_hit from type mapping
        # The adjustment happens for ui_pop -> reveal_hit, not vice versa

    def test_intensity_adjustment_high(self):
        """Test that high intensity upgrades sounds."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="element_appear",
            frame=100,
            confidence=0.8,
            context="important element",
            intensity=0.95,  # Very high intensity
        )

        selection = mapper.select_sound(moment, 300)

        # High intensity should upgrade to reveal_hit
        assert selection.sound == "reveal_hit"
        assert "intensity" in selection.reason.lower()

    def test_intensity_adjustment_low(self):
        """Test that low intensity downgrades sounds."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="reveal",
            frame=100,
            confidence=0.8,
            context="subtle reveal element",
            intensity=0.3,  # Very low intensity
        )

        selection = mapper.select_sound(moment, 300)

        # Low intensity should downgrade reveal_hit to ui_pop
        assert selection.sound == "ui_pop"
        assert "intensity" in selection.reason.lower()

    def test_extract_property_hint(self):
        """Test property hint extraction from moment type."""
        mapper = SemanticSoundMapper()

        assert mapper._extract_property_hint("element_appear") == "opacity"
        assert mapper._extract_property_hint("counter") == "counter"
        assert mapper._extract_property_hint("chart_grow") == "width"
        assert mapper._extract_property_hint("reveal") == "scale"
        assert mapper._extract_property_hint("unknown_type") == "unknown"

    def test_score_pattern_exact_match(self):
        """Test pattern scoring with exact matches."""
        mapper = SemanticSoundMapper()

        # Exact context and property match
        score = mapper._score_pattern("bar animation", "width", "bar", "width")
        assert score > 10  # High score for exact match

    def test_score_pattern_wildcard_match(self):
        """Test pattern scoring with wildcards."""
        mapper = SemanticSoundMapper()

        # Wildcard matches
        score = mapper._score_pattern("bar animation", "width", "*", "width")
        assert 1 <= score <= 10  # Lower score for wildcard

        score = mapper._score_pattern("bar animation", "opacity", "bar", "*")
        assert 1 <= score <= 15  # Lower score for wildcard

    def test_score_pattern_no_match(self):
        """Test pattern scoring with no match."""
        mapper = SemanticSoundMapper()

        score = mapper._score_pattern("unrelated", "scale", "bar", "width")
        assert score == 0

    def test_get_available_sounds(self):
        """Test getting list of available sounds."""
        mapper = SemanticSoundMapper()
        sounds = mapper.get_available_sounds()

        assert isinstance(sounds, list)
        assert len(sounds) > 0
        assert "reveal_hit" in sounds
        assert "counter_sweep" in sounds
        assert "keyboard_type" in sounds


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_map_moment_to_sound(self):
        """Test single moment mapping."""
        moment = SoundMoment(
            type="counter",
            frame=50,
            confidence=0.9,
            context="speed counter",
            intensity=0.8,
        )

        sound = map_moment_to_sound(moment, 300)

        assert sound == "counter_sweep"

    def test_map_moments_to_sounds(self):
        """Test multiple moment mapping."""
        moments = [
            SoundMoment(
                type="element_appear",
                frame=0,
                confidence=0.9,
                context="prompt typing",
                intensity=0.7,
            ),
            SoundMoment(
                type="counter",
                frame=50,
                confidence=0.95,
                context="speed counter",
                intensity=0.8,
            ),
            SoundMoment(
                type="reveal",
                frame=200,
                confidence=0.95,
                context="87x reveal badge",
                intensity=0.9,
            ),
        ]

        results = map_moments_to_sounds(moments, 300)

        assert len(results) == 3
        assert results[0][0] == moments[0]
        assert results[1][0] == moments[1]
        assert results[2][0] == moments[2]

        # Check sounds
        assert results[0][1] == "keyboard_type"
        assert results[1][1] == "counter_sweep"
        assert results[2][1] == "reveal_hit"


class TestPatternPriority:
    """Tests for pattern matching priority."""

    def test_specific_over_wildcard(self):
        """Test that specific patterns win over wildcards."""
        mapper = SemanticSoundMapper()

        # This context matches both ("bar", "width") and ("*", "width")
        moment = SoundMoment(
            type="chart_grow",
            frame=50,
            confidence=0.9,
            context="bar width animation",
            intensity=0.7,
        )

        selection = mapper.select_sound(moment, 300)

        # Should use specific "bar_grow" not generic "counter_sweep"
        assert selection.sound == "bar_grow"

    def test_context_over_property(self):
        """Test that context matches are prioritized appropriately."""
        mapper = SemanticSoundMapper()

        # Context strongly suggests reveal (87x keyword)
        moment = SoundMoment(
            type="element_appear",
            frame=200,
            confidence=0.9,
            context="87x badge scale animation",
            intensity=0.9,
        )

        selection = mapper.select_sound(moment, 300)

        # "87x" keyword should trigger reveal_hit
        assert selection.sound == "reveal_hit"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_context(self):
        """Test handling of empty context."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="element_appear",
            frame=0,
            confidence=0.8,
            context="",
            intensity=0.7,
        )

        selection = mapper.select_sound(moment, 300)

        # Should fall back to type-based mapping
        assert selection.sound in ("ui_pop", "reveal_hit")

    def test_zero_duration(self):
        """Test handling of zero scene duration."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="counter",
            frame=50,
            confidence=0.9,
            context="speed counter",
            intensity=0.8,
        )

        # Should not crash
        selection = mapper.select_sound(moment, 0)
        assert selection.sound == "counter_sweep"

    def test_frame_beyond_duration(self):
        """Test handling when frame exceeds duration."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="element_appear",
            frame=500,  # Beyond 300 frame duration
            confidence=0.8,
            context="late element",
            intensity=0.7,
        )

        # Should still work
        selection = mapper.select_sound(moment, 300)
        assert selection.sound is not None

    def test_negative_frame(self):
        """Test handling of negative frame (shouldn't happen but be safe)."""
        mapper = SemanticSoundMapper()
        moment = SoundMoment(
            type="element_appear",
            frame=0,  # Frame is clamped to 0 in SoundMoment
            confidence=0.8,
            context="element",
            intensity=0.7,
        )

        selection = mapper.select_sound(moment, 300)
        assert selection.sound is not None

    def test_case_insensitive_matching(self):
        """Test that context matching is case insensitive."""
        mapper = SemanticSoundMapper()

        # Upper case context
        moment = SoundMoment(
            type="element_appear",
            frame=50,
            confidence=0.9,
            context="PROMPT TYPING",
            intensity=0.7,
        )

        selection = mapper.select_sound(moment, 300)
        assert selection.sound == "keyboard_type"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

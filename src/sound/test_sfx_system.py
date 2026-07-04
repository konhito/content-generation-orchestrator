"""Tests for the SFX system components."""

import json
import tempfile
from pathlib import Path

import pytest

from .models import (
    SoundMoment,
    SFXCue,
    WordTimestamp,
    SceneAnalysisResult,
    calculate_volume,
    get_sound_for_moment,
)
from .scene_analyzer import SceneAnalyzer
from .narration_sync import (
    NarrationSyncAnalyzer,
    sync_to_narration,
    analyze_narration_text,
)
from .aggregator import aggregate_moments, get_density_report
from .cue_generator import CueGenerator
from .storyboard_updater import StoryboardUpdater


class TestModels:
    """Tests for data models."""

    def test_sound_moment_creation(self):
        """Test SoundMoment creation and validation."""
        moment = SoundMoment(
            type="element_appear",
            frame=30,
            confidence=0.9,
            context="Test moment",
            intensity=0.8,
        )
        assert moment.type == "element_appear"
        assert moment.frame == 30
        assert moment.confidence == 0.9
        assert moment.intensity == 0.8
        assert moment.source == "code"

    def test_sound_moment_clamps_values(self):
        """Test that SoundMoment clamps values to valid ranges."""
        moment = SoundMoment(
            type="test",
            frame=-10,
            confidence=1.5,
            context="",
            intensity=-0.5,
        )
        assert moment.frame == 0
        assert moment.confidence == 1.0
        assert moment.intensity == 0.0

    def test_sfx_cue_to_dict(self):
        """Test SFXCue serialization."""
        cue = SFXCue(
            sound="ui_pop",
            frame=45,
            volume=0.08,
            duration_frames=30,
        )
        data = cue.to_dict()
        assert data == {
            "sound": "ui_pop",
            "frame": 45,
            "volume": 0.08,
            "duration_frames": 30,
        }

    def test_sfx_cue_from_dict(self):
        """Test SFXCue deserialization."""
        data = {"sound": "reveal_hit", "frame": 100, "volume": 0.12}
        cue = SFXCue.from_dict(data)
        assert cue.sound == "reveal_hit"
        assert cue.frame == 100
        assert cue.volume == 0.12
        assert cue.duration_frames is None

    def test_calculate_volume(self):
        """Test volume calculation."""
        moment = SoundMoment(
            type="reveal",
            frame=0,
            confidence=1.0,
            context="",
            intensity=1.0,
        )
        volume = calculate_volume(moment)
        assert 0 < volume <= 0.15

        # Low intensity should have lower volume
        low_moment = SoundMoment(
            type="reveal",
            frame=0,
            confidence=1.0,
            context="",
            intensity=0.3,
        )
        low_volume = calculate_volume(low_moment)
        assert low_volume < volume

    def test_get_sound_for_moment(self):
        """Test moment type to sound mapping."""
        assert get_sound_for_moment("element_appear") == "ui_pop"
        assert get_sound_for_moment("reveal") == "reveal_hit"
        assert get_sound_for_moment("counter") == "counter_sweep"
        assert get_sound_for_moment("unknown") == "ui_pop"  # Default


class TestSceneAnalyzer:
    """Tests for scene code analyzer."""

    def test_analyze_opacity_fade_in(self):
        """Test detection of opacity fade-in patterns."""
        code = '''
        const MyComponent = () => {
            return (
                <div style={{
                    opacity: interpolate(frame, [0, 15], [0, 1])
                }}>
                    Content
                </div>
            );
        };
        '''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.tsx', delete=False) as f:
            f.write(code)
            f.flush()

            analyzer = SceneAnalyzer(fps=30)
            result = analyzer.analyze_scene(Path(f.name))

            appear_moments = [m for m in result.moments if m.type == "element_appear"]
            assert len(appear_moments) >= 1
            assert appear_moments[0].frame == 0

    def test_analyze_counter_animation(self):
        """Test detection of counter animations."""
        code = '''
        const Counter = () => {
            const count = Math.round(interpolate(frame, [30, 90], [0, 1000]));
            return <div>{count}</div>;
        };
        '''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.tsx', delete=False) as f:
            f.write(code)
            f.flush()

            analyzer = SceneAnalyzer(fps=30)
            result = analyzer.analyze_scene(Path(f.name))

            counter_moments = [m for m in result.moments if m.type == "counter"]
            assert len(counter_moments) >= 1
            assert counter_moments[0].frame == 30


class TestNarrationSync:
    """Tests for narration sync analyzer."""

    def test_detect_numbers(self):
        """Test detection of numbers in narration."""
        narration = "This system is 87x faster than the baseline."
        timestamps = [
            WordTimestamp("This", 0.0, 0.2),
            WordTimestamp("system", 0.2, 0.5),
            WordTimestamp("is", 0.5, 0.6),
            WordTimestamp("87x", 0.6, 0.9),
            WordTimestamp("faster", 0.9, 1.2),
            WordTimestamp("than", 1.2, 1.4),
            WordTimestamp("the", 1.4, 1.5),
            WordTimestamp("baseline", 1.5, 1.9),
        ]

        moments = sync_to_narration(narration, timestamps)

        # Should detect the "87x" as a reveal or counter moment
        number_moments = [m for m in moments if m.type in ("reveal", "counter")]
        assert len(number_moments) >= 1

    def test_detect_problem_words(self):
        """Test detection of problem-related words."""
        narration = "The main bottleneck is memory bandwidth."
        moments = analyze_narration_text(narration)

        warning_moments = [m for m in moments if m.type == "warning"]
        assert len(warning_moments) >= 1

    def test_detect_solution_words(self):
        """Test detection of solution-related words."""
        narration = "The key solution is to cache the results."
        moments = analyze_narration_text(narration)

        success_moments = [m for m in moments if m.type == "success"]
        assert len(success_moments) >= 1


class TestAggregator:
    """Tests for moment aggregator."""

    def test_merge_nearby_moments(self):
        """Test that nearby moments are merged."""
        # Create moments far enough apart to not be affected by min_gap
        moments_code = [
            SoundMoment("element_appear", 10, 0.9, "A", source="code"),
            SoundMoment("element_appear", 100, 0.8, "C", source="code"),
        ]
        moments_narration = [
            SoundMoment("element_appear", 12, 0.7, "B", source="narration"),
        ]

        aggregated = aggregate_moments(
            code_moments=moments_code,
            narration_moments=moments_narration,
            llm_moments=[],
            merge_window_frames=10,
            min_gap_frames=5,
        )

        # First two should be merged (within 10 frame window), third remains
        # So we expect 2 moments: one merged from frames 10+12, one at frame 100
        assert len(aggregated) == 2
        # The merged moment should be the higher confidence one
        assert aggregated[0].confidence == 0.9

    def test_enforce_density(self):
        """Test that density constraints are enforced."""
        # Create many moments in a short span
        moments = [
            SoundMoment(f"type_{i}", i * 5, 0.8, f"M{i}", source="code")
            for i in range(10)
        ]

        aggregated = aggregate_moments(
            code_moments=moments,
            narration_moments=[],
            llm_moments=[],
            max_per_second=2.0,
            min_gap_frames=10,
        )

        # Should be significantly fewer due to density constraints
        assert len(aggregated) < len(moments)

    def test_get_density_report(self):
        """Test density report generation."""
        moments = [
            SoundMoment("a", 0, 0.9, ""),
            SoundMoment("b", 30, 0.8, ""),
            SoundMoment("a", 60, 0.7, ""),
            SoundMoment("c", 90, 0.6, ""),
        ]

        report = get_density_report(moments, fps=30)

        assert report["total_moments"] == 4
        assert "type_distribution" in report
        assert report["type_distribution"]["a"] == 2


class TestCueGenerator:
    """Tests for cue generator."""

    def test_generate_library_cues(self):
        """Test cue generation using library sounds."""
        moments = [
            SoundMoment("element_appear", 15, 0.9, "Test 1", intensity=0.8),
            SoundMoment("reveal", 60, 0.95, "Test 2", intensity=1.0),
        ]

        generator = CueGenerator(use_library=True)
        cues = generator.generate_cues(moments, "test_scene")

        assert len(cues) == 2
        assert cues[0].sound == "ui_pop"
        assert cues[0].frame == 15
        assert cues[1].sound == "reveal_hit"
        assert cues[1].frame == 60


class TestStoryboardUpdater:
    """Tests for storyboard updater."""

    def test_load_and_update(self):
        """Test loading storyboard and updating cues."""
        storyboard_data = {
            "title": "Test Video",
            "scenes": [
                {
                    "id": "scene1",
                    "type": "test/hook",
                    "title": "Test Scene",
                    "audio_file": "test.mp3",
                    "audio_duration_seconds": 10.0,
                    "sfx_cues": [],
                }
            ],
            "audio": {"buffer_between_scenes_seconds": 1.0},
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(storyboard_data, f)
            f.flush()

            updater = StoryboardUpdater(Path(f.name))
            updater.load()

            # Update with new cues
            cues = [
                SFXCue("ui_pop", 15, 0.08),
                SFXCue("reveal_hit", 90, 0.12),
            ]
            success = updater.update_scene_cues("scene1", cues)
            assert success

            # Verify update
            scene_cues = updater.get_scene_cues("scene1")
            assert len(scene_cues) == 2
            assert scene_cues[0].sound == "ui_pop"

    def test_merge_mode(self):
        """Test merge mode for updating cues."""
        storyboard_data = {
            "scenes": [
                {
                    "id": "scene1",
                    "sfx_cues": [
                        {"sound": "existing", "frame": 30, "volume": 0.1}
                    ],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(storyboard_data, f)
            f.flush()

            updater = StoryboardUpdater(Path(f.name))
            updater.load()

            # Merge new cues
            new_cues = [
                SFXCue("new_sound", 60, 0.08),
            ]
            updater.update_scene_cues("scene1", new_cues, mode="merge")

            scene_cues = updater.get_scene_cues("scene1")
            assert len(scene_cues) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

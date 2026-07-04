"""Tests for the storyboard module."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.storyboard import (
    load_storyboard,
    validate_storyboard,
    StoryboardError,
    Storyboard,
    Beat,
    Element,
    Animation,
    Position,
    Transition,
    SyncPoint,
    AudioConfig,
    StyleConfig,
    StoryboardRenderer,
    StoryboardGenerator,
)
from src.storyboard.loader import (
    parse_storyboard,
    StoryboardLoadError,
    StoryboardValidationError,
    storyboard_to_dict,
    save_storyboard,
)
from src.audio.tts import TTSResult, WordTimestamp
from src.models import Script, ScriptScene, VisualCue


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def minimal_storyboard_data():
    """Minimal valid storyboard data."""
    return {
        "id": "test_storyboard",
        "title": "Test Storyboard",
        "duration_seconds": 10,
        "beats": [
            {
                "id": "beat_1",
                "start_seconds": 0,
                "end_seconds": 10,
            }
        ],
    }


@pytest.fixture
def full_storyboard_data():
    """Complete storyboard data with all fields."""
    return {
        "id": "full_storyboard",
        "title": "Full Test Storyboard",
        "description": "A complete storyboard for testing",
        "duration_seconds": 30,
        "audio": {
            "file": "test_audio.mp3",
            "duration_seconds": 28.5,
            "word_timestamps": [
                {"word": "hello", "start": 0.0, "end": 0.5},
                {"word": "world", "start": 0.6, "end": 1.0},
            ],
        },
        "style": {
            "background_color": "#0f0f1a",
            "primary_color": "#00d9ff",
            "secondary_color": "#ff6b35",
            "font_family": "Inter, sans-serif",
        },
        "beats": [
            {
                "id": "intro",
                "start_seconds": 0,
                "end_seconds": 10,
                "voiceover": "Welcome to this test.",
                "elements": [
                    {
                        "id": "title",
                        "component": "title_card",
                        "props": {"text": "Hello World"},
                        "position": {"x": "center", "y": "center"},
                        "enter": {"type": "fade", "duration_seconds": 0.5},
                        "exit": {"type": "fade", "duration_seconds": 0.3},
                        "animations": [
                            {
                                "action": "scale",
                                "at_seconds": 2,
                                "duration_seconds": 1,
                                "easing": "ease-out",
                                "params": {"from": 0.8, "to": 1.0},
                            }
                        ],
                    }
                ],
                "sync_points": [
                    {
                        "trigger_word": "hello",
                        "trigger_seconds": 0.0,
                        "target": "title",
                        "action": "activate",
                    }
                ],
            },
            {
                "id": "main",
                "start_seconds": 10,
                "end_seconds": 25,
                "voiceover": "This is the main content.",
                "elements": [
                    {
                        "id": "tokens",
                        "component": "token_row",
                        "props": {
                            "tokens": ["Test", "tokens"],
                            "mode": "prefill",
                        },
                        "position": {"x": 960, "y": 540},
                    }
                ],
            },
            {
                "id": "outro",
                "start_seconds": 25,
                "end_seconds": 30,
                "voiceover": "That's all!",
            },
        ],
    }


@pytest.fixture
def sample_storyboard(full_storyboard_data):
    """Parsed storyboard object."""
    return parse_storyboard(full_storyboard_data)


# ============================================================================
# Model Tests
# ============================================================================


class TestPosition:
    """Tests for Position model."""

    def test_default_position(self):
        pos = Position()
        assert pos.x == "center"
        assert pos.y == "center"
        assert pos.anchor == "center"

    def test_numeric_position(self):
        pos = Position(x=100, y=200)
        assert pos.x == 100
        assert pos.y == 200

    def test_named_position(self):
        pos = Position(x="left", y="top", anchor="top-left")
        assert pos.x == "left"
        assert pos.y == "top"
        assert pos.anchor == "top-left"


class TestTransition:
    """Tests for Transition model."""

    def test_default_transition(self):
        trans = Transition()
        assert trans.type == "fade"
        assert trans.duration_seconds == 0.3
        assert trans.delay_seconds == 0

    def test_slide_transition(self):
        trans = Transition(type="slide", direction="up", duration_seconds=0.5)
        assert trans.type == "slide"
        assert trans.direction == "up"


class TestAnimation:
    """Tests for Animation model."""

    def test_minimal_animation(self):
        anim = Animation(action="fade_in", at_seconds=1.0)
        assert anim.action == "fade_in"
        assert anim.at_seconds == 1.0
        assert anim.duration_seconds == 0.3
        assert anim.easing == "ease-out"

    def test_full_animation(self):
        anim = Animation(
            action="scale",
            at_seconds=2.0,
            duration_seconds=1.0,
            easing="spring",
            params={"from": 0.5, "to": 1.0},
        )
        assert anim.params["from"] == 0.5
        assert anim.easing == "spring"


class TestElement:
    """Tests for Element model."""

    def test_minimal_element(self):
        el = Element(id="test", component="token_row")
        assert el.id == "test"
        assert el.component == "token_row"
        assert el.props is None

    def test_full_element(self):
        el = Element(
            id="test",
            component="token_row",
            props={"tokens": ["a", "b"]},
            position=Position(x="center", y="center"),
            animations=[Animation(action="activate", at_seconds=1)],
            enter=Transition(type="fade"),
            exit=Transition(type="fade"),
        )
        assert el.props["tokens"] == ["a", "b"]
        assert len(el.animations) == 1


class TestBeat:
    """Tests for Beat model."""

    def test_minimal_beat(self):
        beat = Beat(id="test", start_seconds=0, end_seconds=5)
        assert beat.id == "test"
        assert beat.duration_seconds == 5

    def test_beat_with_elements(self):
        beat = Beat(
            id="test",
            start_seconds=0,
            end_seconds=10,
            voiceover="Test voiceover",
            elements=[Element(id="el1", component="title_card")],
            sync_points=[
                SyncPoint(trigger_seconds=1.0, target="el1", action="activate")
            ],
        )
        assert len(beat.elements) == 1
        assert len(beat.sync_points) == 1


class TestStoryboard:
    """Tests for Storyboard model."""

    def test_minimal_storyboard(self, minimal_storyboard_data):
        sb = parse_storyboard(minimal_storyboard_data)
        assert sb.id == "test_storyboard"
        assert sb.duration_seconds == 10
        assert len(sb.beats) == 1

    def test_full_storyboard(self, full_storyboard_data):
        sb = parse_storyboard(full_storyboard_data)
        assert sb.id == "full_storyboard"
        assert sb.audio is not None
        assert sb.audio.file == "test_audio.mp3"
        assert len(sb.audio.word_timestamps) == 2
        assert sb.style.background_color == "#0f0f1a"
        assert len(sb.beats) == 3

    def test_total_frames(self, sample_storyboard):
        assert sample_storyboard.total_frames == 900  # 30 seconds * 30 fps

    def test_get_beat_at_time(self, sample_storyboard):
        beat = sample_storyboard.get_beat_at_time(5)
        assert beat.id == "intro"

        beat = sample_storyboard.get_beat_at_time(15)
        assert beat.id == "main"

        beat = sample_storyboard.get_beat_at_time(100)
        assert beat is None

    def test_get_all_elements(self, sample_storyboard):
        elements = sample_storyboard.get_all_elements()
        assert len(elements) == 2  # title + tokens

    def test_get_used_components(self, sample_storyboard):
        components = sample_storyboard.get_used_components()
        assert "title_card" in components
        assert "token_row" in components


# ============================================================================
# Loader Tests
# ============================================================================


class TestParseStoryboard:
    """Tests for parse_storyboard function."""

    def test_parse_valid_storyboard(self, minimal_storyboard_data):
        sb = parse_storyboard(minimal_storyboard_data)
        assert isinstance(sb, Storyboard)

    def test_parse_invalid_storyboard_missing_id(self):
        with pytest.raises(StoryboardValidationError) as exc_info:
            parse_storyboard({"title": "Test", "duration_seconds": 10, "beats": []})
        assert "id" in str(exc_info.value.errors)

    def test_parse_invalid_storyboard_missing_beats(self):
        with pytest.raises(StoryboardValidationError):
            parse_storyboard({"id": "test", "title": "Test", "duration_seconds": 10})

    def test_parse_invalid_storyboard_empty_beats(self):
        with pytest.raises(StoryboardValidationError):
            parse_storyboard({
                "id": "test",
                "title": "Test",
                "duration_seconds": 10,
                "beats": [],
            })

    def test_parse_invalid_id_format(self):
        with pytest.raises(StoryboardValidationError):
            parse_storyboard({
                "id": "Invalid ID With Spaces",
                "title": "Test",
                "duration_seconds": 10,
                "beats": [{"id": "b1", "start_seconds": 0, "end_seconds": 5}],
            })


class TestLoadStoryboard:
    """Tests for load_storyboard function."""

    def test_load_valid_file(self, tmp_path, minimal_storyboard_data):
        file_path = tmp_path / "test.json"
        with open(file_path, "w") as f:
            json.dump(minimal_storyboard_data, f)

        sb = load_storyboard(file_path)
        assert sb.id == "test_storyboard"

    def test_load_nonexistent_file(self):
        with pytest.raises(StoryboardLoadError) as exc_info:
            load_storyboard("/nonexistent/path.json")
        assert "not found" in str(exc_info.value)

    def test_load_non_json_file(self, tmp_path):
        file_path = tmp_path / "test.yaml"
        file_path.write_text("key: value")

        with pytest.raises(StoryboardLoadError) as exc_info:
            load_storyboard(file_path)
        assert "must be JSON" in str(exc_info.value)

    def test_load_invalid_json(self, tmp_path):
        file_path = tmp_path / "test.json"
        file_path.write_text("{ invalid json }")

        with pytest.raises(StoryboardLoadError) as exc_info:
            load_storyboard(file_path)
        assert "Invalid JSON" in str(exc_info.value)


class TestValidateStoryboard:
    """Tests for validate_storyboard function."""

    def test_valid_storyboard(self, sample_storyboard):
        issues = validate_storyboard(sample_storyboard)
        assert len(issues) == 0

    def test_beat_end_before_start(self):
        sb = Storyboard(
            id="test",
            title="Test",
            duration_seconds=10,
            beats=[Beat(id="b1", start_seconds=5, end_seconds=3)],
        )
        issues = validate_storyboard(sb)
        assert any("start_seconds" in issue for issue in issues)

    def test_duplicate_element_ids(self):
        sb = Storyboard(
            id="test",
            title="Test",
            duration_seconds=10,
            beats=[
                Beat(
                    id="b1",
                    start_seconds=0,
                    end_seconds=10,
                    elements=[
                        Element(id="dup", component="c1"),
                        Element(id="dup", component="c2"),
                    ],
                )
            ],
        )
        issues = validate_storyboard(sb)
        assert any("duplicate" in issue.lower() for issue in issues)

    def test_sync_point_unknown_target(self):
        sb = Storyboard(
            id="test",
            title="Test",
            duration_seconds=10,
            beats=[
                Beat(
                    id="b1",
                    start_seconds=0,
                    end_seconds=10,
                    elements=[Element(id="el1", component="c1")],
                    sync_points=[
                        SyncPoint(
                            trigger_seconds=1,
                            target="unknown_element",
                            action="activate",
                        )
                    ],
                )
            ],
        )
        issues = validate_storyboard(sb)
        assert any("unknown element" in issue for issue in issues)

    def test_animation_before_beat_start(self):
        sb = Storyboard(
            id="test",
            title="Test",
            duration_seconds=10,
            beats=[
                Beat(
                    id="b1",
                    start_seconds=5,
                    end_seconds=10,
                    elements=[
                        Element(
                            id="el1",
                            component="c1",
                            animations=[Animation(action="x", at_seconds=2)],
                        )
                    ],
                )
            ],
        )
        issues = validate_storyboard(sb)
        assert any("before beat start" in issue for issue in issues)


class TestSaveStoryboard:
    """Tests for save_storyboard function."""

    def test_save_and_reload(self, tmp_path, sample_storyboard):
        file_path = tmp_path / "output.json"
        save_storyboard(sample_storyboard, file_path)

        assert file_path.exists()

        reloaded = load_storyboard(file_path)
        assert reloaded.id == sample_storyboard.id
        assert reloaded.title == sample_storyboard.title
        assert len(reloaded.beats) == len(sample_storyboard.beats)

    def test_save_creates_directories(self, tmp_path, sample_storyboard):
        file_path = tmp_path / "nested" / "dir" / "output.json"
        save_storyboard(sample_storyboard, file_path)
        assert file_path.exists()


class TestStoryboardToDict:
    """Tests for storyboard_to_dict function."""

    def test_converts_to_dict(self, sample_storyboard):
        d = storyboard_to_dict(sample_storyboard)
        assert isinstance(d, dict)
        assert d["id"] == sample_storyboard.id

    def test_excludes_none_values(self, minimal_storyboard_data):
        sb = parse_storyboard(minimal_storyboard_data)
        d = storyboard_to_dict(sb)
        assert "audio" not in d  # None values excluded
        assert "description" not in d


# ============================================================================
# Renderer Tests
# ============================================================================


class TestStoryboardRenderer:
    """Tests for StoryboardRenderer class."""

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess for tests."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            yield mock_run

    @pytest.fixture
    def renderer(self, mock_subprocess):
        """Create renderer with mocked dependencies."""
        with patch.object(StoryboardRenderer, "_check_dependencies"):
            return StoryboardRenderer()

    def test_renderer_init(self, mock_subprocess):
        """Test renderer initialization checks dependencies."""
        mock_subprocess.return_value = MagicMock(returncode=0)
        renderer = StoryboardRenderer()
        assert renderer.remotion_dir.exists()

    def test_render_success(
        self, renderer, mock_subprocess, sample_storyboard, tmp_path
    ):
        """Test successful render."""
        output_path = tmp_path / "output.mp4"

        # Make mock create the output file
        def create_output(*args, **kwargs):
            output_path.write_bytes(b"fake video")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = create_output

        result = renderer.render(sample_storyboard, output_path)

        assert result.success
        assert result.output_path == output_path
        assert result.duration_seconds == sample_storyboard.duration_seconds

    def test_render_failure(
        self, renderer, mock_subprocess, sample_storyboard, tmp_path
    ):
        """Test render failure handling."""
        mock_subprocess.return_value = MagicMock(
            returncode=1, stdout="", stderr="Error occurred"
        )

        result = renderer.render(sample_storyboard, tmp_path / "output.mp4")

        assert not result.success
        assert "Error" in result.error_message

    def test_render_timeout(
        self, renderer, mock_subprocess, sample_storyboard, tmp_path
    ):
        """Test render timeout handling."""
        import subprocess

        mock_subprocess.side_effect = subprocess.TimeoutExpired(
            cmd="node", timeout=600
        )

        result = renderer.render(sample_storyboard, tmp_path / "output.mp4")

        assert not result.success
        assert "timeout" in result.error_message.lower()

    def test_render_from_file(
        self, renderer, mock_subprocess, full_storyboard_data, tmp_path
    ):
        """Test rendering from file."""
        storyboard_path = tmp_path / "storyboard.json"
        output_path = tmp_path / "output.mp4"

        with open(storyboard_path, "w") as f:
            json.dump(full_storyboard_data, f)

        # Make mock create the output file
        def create_output(*args, **kwargs):
            output_path.write_bytes(b"fake video")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = create_output

        result = renderer.render_from_file(storyboard_path, output_path)

        assert result.success


# ============================================================================
# Integration Tests
# ============================================================================


class TestStoryboardIntegration:
    """Integration tests for the storyboard module."""

    def test_load_example_storyboard(self):
        """Test loading the example storyboard file."""
        example_path = Path(
            "/Users/prajwal/Desktop/Learning/video_explainer/"
            "storyboards/examples/prefill_vs_decode.json"
        )

        if not example_path.exists():
            pytest.skip("Example storyboard not found")

        sb = load_storyboard(example_path)

        assert sb.id == "prefill_vs_decode"
        assert sb.duration_seconds == 60
        assert len(sb.beats) == 8

        # Validate it
        issues = validate_storyboard(sb)
        # May have some warnings but should be mostly valid
        assert len([i for i in issues if "error" in i.lower()]) == 0

    def test_roundtrip_storyboard(self, tmp_path, full_storyboard_data):
        """Test that a storyboard survives save/load roundtrip."""
        original = parse_storyboard(full_storyboard_data)
        file_path = tmp_path / "roundtrip.json"

        save_storyboard(original, file_path)
        reloaded = load_storyboard(file_path)

        assert original.id == reloaded.id
        assert original.duration_seconds == reloaded.duration_seconds
        assert len(original.beats) == len(reloaded.beats)

        # Check nested structures
        assert original.beats[0].id == reloaded.beats[0].id
        if original.beats[0].elements and reloaded.beats[0].elements:
            assert (
                original.beats[0].elements[0].component
                == reloaded.beats[0].elements[0].component
            )


# ============================================================================
# Generator Tests
# ============================================================================


class TestStoryboardGenerator:
    """Tests for StoryboardGenerator class."""

    @pytest.fixture
    def sample_script(self):
        """Create a sample script for testing."""
        return Script(
            title="Test Script",
            total_duration_seconds=20,
            source_document="test.md",
            scenes=[
                ScriptScene(
                    scene_id="scene_1",
                    scene_type="hook",
                    title="Introduction",
                    voiceover="This is the first scene with some content.",
                    visual_cue=VisualCue(
                        description="Title card appears",
                        visual_type="animation",
                        elements=["title", "subtitle"],
                        duration_seconds=10,
                    ),
                    duration_seconds=10,
                ),
                ScriptScene(
                    scene_id="scene_2",
                    scene_type="explanation",
                    title="Main Content",
                    voiceover="This is the second scene with more content.",
                    visual_cue=VisualCue(
                        description="Token animation",
                        visual_type="animation",
                        elements=["tokens", "flow"],
                        duration_seconds=10,
                    ),
                    duration_seconds=10,
                ),
            ],
        )

    @pytest.fixture
    def sample_tts_results(self, tmp_path):
        """Create sample TTS results for testing."""
        audio1 = tmp_path / "scene1.mp3"
        audio2 = tmp_path / "scene2.mp3"
        audio1.touch()
        audio2.touch()

        return [
            TTSResult(
                audio_path=audio1,
                duration_seconds=10.0,
                word_timestamps=[
                    WordTimestamp("This", 0.0, 0.2),
                    WordTimestamp("is", 0.3, 0.4),
                    WordTimestamp("the", 0.5, 0.6),
                    WordTimestamp("first", 0.7, 0.9),
                    WordTimestamp("scene", 1.0, 1.3),
                ],
            ),
            TTSResult(
                audio_path=audio2,
                duration_seconds=10.0,
                word_timestamps=[
                    WordTimestamp("This", 0.0, 0.2),
                    WordTimestamp("is", 0.3, 0.4),
                    WordTimestamp("the", 0.5, 0.6),
                    WordTimestamp("second", 0.7, 1.0),
                    WordTimestamp("scene", 1.1, 1.4),
                ],
            ),
        ]

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM that returns valid storyboard beats."""
        mock = MagicMock()
        mock.generate_json.return_value = {
            "beats": [
                {
                    "id": "beat_1",
                    "start_seconds": 0,
                    "end_seconds": 10,
                    "voiceover": "Test voiceover",
                    "elements": [
                        {
                            "id": "element_1",
                            "component": "title_card",
                            "props": {"title": "Test"},
                            "position": {"x": "center", "y": "center"},
                        }
                    ],
                }
            ]
        }
        return mock

    def test_generator_init(self):
        """Test generator initialization."""
        generator = StoryboardGenerator()
        assert generator.config is not None
        assert generator.llm is not None
        # examples_dir may or may not exist, but should be a Path
        assert generator.examples_dir is not None

    def test_generate_id_from_title(self):
        """Test ID generation from title."""
        generator = StoryboardGenerator()

        assert generator._generate_id("Test Title") == "test_title"
        assert generator._generate_id("Hello World!") == "hello_world"
        assert generator._generate_id("123 Numbers") == "s_123_numbers"
        assert generator._generate_id("") == "storyboard"

    def test_calculate_scene_timing(self, sample_tts_results):
        """Test scene timing calculation."""
        generator = StoryboardGenerator()
        timings = generator._calculate_scene_timing(sample_tts_results)

        assert len(timings) == 2
        assert timings[0] == (0.0, 10.0)
        assert timings[1] == (10.0, 20.0)

    def test_generate_with_mock_llm(
        self, sample_script, sample_tts_results, mock_llm
    ):
        """Test generating storyboard with mock LLM."""
        generator = StoryboardGenerator(llm=mock_llm)

        storyboard = generator.generate(sample_script, sample_tts_results)

        assert isinstance(storyboard, Storyboard)
        assert storyboard.title == "Test Script"
        assert storyboard.duration_seconds == 20.0
        # Should have beats (2 scenes, each generating beats)
        assert len(storyboard.beats) >= 2

    def test_generate_validates_input_length(self, sample_script, sample_tts_results):
        """Test that generator validates TTS results match scenes."""
        generator = StoryboardGenerator()

        # Remove one TTS result to create mismatch
        with pytest.raises(ValueError, match="must match"):
            generator.generate(sample_script, sample_tts_results[:1])

    def test_generate_from_beats(self):
        """Test creating storyboard from pre-generated beats."""
        generator = StoryboardGenerator()

        beats = [
            {
                "id": "beat_1",
                "start_seconds": 0,
                "end_seconds": 5,
                "voiceover": "Hello",
            },
            {
                "id": "beat_2",
                "start_seconds": 5,
                "end_seconds": 10,
                "voiceover": "World",
            },
        ]

        storyboard = generator.generate_from_beats(
            title="Test Storyboard",
            beats=beats,
            duration_seconds=10.0,
            audio_file="test.mp3",
        )

        assert isinstance(storyboard, Storyboard)
        assert storyboard.title == "Test Storyboard"
        assert storyboard.duration_seconds == 10.0
        assert len(storyboard.beats) == 2
        assert storyboard.audio is not None
        assert storyboard.audio.file == "test.mp3"

    def test_load_example_context(self):
        """Test loading example storyboards for context."""
        generator = StoryboardGenerator()
        context = generator._load_example_context()

        # Should load examples if they exist
        if generator.examples_dir.exists():
            assert "Example from" in context or context == ""
        else:
            assert context == ""

    def test_generate_scene_beats_with_mock(
        self, sample_script, sample_tts_results, mock_llm
    ):
        """Test generating beats for a single scene."""
        generator = StoryboardGenerator(llm=mock_llm)

        beats = generator._generate_scene_beats(
            scene=sample_script.scenes[0],
            tts_result=sample_tts_results[0],
            start_seconds=0,
            end_seconds=10,
            example_context="",
        )

        assert isinstance(beats, list)
        assert len(beats) > 0
        assert all("id" in beat for beat in beats)

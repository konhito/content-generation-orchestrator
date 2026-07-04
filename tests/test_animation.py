"""Tests for animation rendering module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.animation import (
    AnimationRenderer,
    MockRenderer,
    RemotionRenderer,
    RenderResult,
    get_renderer,
)
from src.config import Config
from src.models import Script, ScriptScene, VisualCue


@pytest.fixture
def sample_script():
    """Create a sample script for testing."""
    return Script(
        title="Test Video",
        total_duration_seconds=35.0,
        scenes=[
            ScriptScene(
                scene_id="scene_1",
                scene_type="hook",
                title="Introduction",
                voiceover="Welcome to this test video.",
                visual_cue=VisualCue(
                    description="Title card with animation",
                    visual_type="animation",
                    elements=["title", "subtitle"],
                    duration_seconds=15.0,
                ),
                duration_seconds=15.0,
            ),
            ScriptScene(
                scene_id="scene_2",
                scene_type="explanation",
                title="Main Content",
                voiceover="This is the main explanation.",
                visual_cue=VisualCue(
                    description="Diagram showing concept",
                    visual_type="diagram",
                    elements=["box", "arrow"],
                    duration_seconds=20.0,
                ),
                duration_seconds=20.0,
            ),
        ],
        source_document="test.md",
    )


class TestRenderResult:
    """Tests for RenderResult dataclass."""

    def test_render_result_creation(self, tmp_path):
        """Test creating a render result."""
        result = RenderResult(
            output_path=tmp_path / "video.mp4",
            duration_seconds=10.5,
            frame_count=315,
            success=True,
        )

        assert result.success
        assert result.duration_seconds == 10.5
        assert result.frame_count == 315
        assert result.error_message is None

    def test_render_result_with_error(self, tmp_path):
        """Test creating a failed render result."""
        result = RenderResult(
            output_path=tmp_path / "video.mp4",
            duration_seconds=0,
            frame_count=0,
            success=False,
            error_message="Something went wrong",
        )

        assert not result.success
        assert result.error_message == "Something went wrong"


class TestMockRenderer:
    """Tests for MockRenderer class."""

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess for tests."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            yield mock_run

    def test_render_mock_creates_video(self, mock_subprocess, tmp_path):
        """Test that mock rendering creates a video file."""
        # Make FFmpeg create an actual file
        def create_output(*args, **kwargs):
            output_path = None
            cmd = args[0]
            for i, arg in enumerate(cmd):
                if arg == str(tmp_path / "test.mp4"):
                    output_path = Path(arg)
                    break
            if output_path:
                output_path.write_bytes(b"fake video data")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = create_output

        renderer = MockRenderer()
        output_path = tmp_path / "test.mp4"

        result = renderer.render_mock(output_path, duration_seconds=5.0)

        assert result.success
        assert result.duration_seconds == 5.0
        assert result.frame_count == 150  # 5 seconds * 30 fps

    def test_render_mock_handles_error(self, mock_subprocess, tmp_path):
        """Test that mock rendering handles FFmpeg errors."""
        mock_subprocess.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="FFmpeg error",
        )

        renderer = MockRenderer()
        output_path = tmp_path / "test.mp4"

        result = renderer.render_mock(output_path)

        assert not result.success
        assert "FFmpeg" in result.error_message

    def test_render_from_script(self, mock_subprocess, tmp_path, sample_script):
        """Test rendering from a script."""
        # Make FFmpeg create an actual file
        def create_output(*args, **kwargs):
            cmd = args[0]
            for arg in cmd:
                if str(tmp_path) in str(arg) and arg.endswith(".mp4"):
                    Path(arg).write_bytes(b"fake video data")
            return MagicMock(returncode=0, stdout="", stderr="")

        mock_subprocess.side_effect = create_output

        renderer = MockRenderer()
        output_path = tmp_path / "test.mp4"

        result = renderer.render_from_script(sample_script, output_path)

        assert result.success
        # Duration should match sum of scene durations
        expected_duration = sum(s.duration_seconds for s in sample_script.scenes)
        assert result.duration_seconds == expected_duration


class TestRemotionRenderer:
    """Tests for RemotionRenderer class."""

    def test_remotion_renderer_init(self):
        """Test RemotionRenderer initialization."""
        # Should check for dependencies
        renderer = RemotionRenderer()
        assert renderer.remotion_dir.exists()

    def test_script_to_props_conversion(self, sample_script):
        """Test converting script to Remotion props."""
        renderer = RemotionRenderer()
        props = renderer._script_to_props(sample_script)

        assert props["title"] == sample_script.title
        assert len(props["scenes"]) == len(sample_script.scenes)
        assert "style" in props

        # Check scene conversion
        first_scene = props["scenes"][0]
        assert first_scene["sceneId"] == sample_script.scenes[0].scene_id
        assert first_scene["voiceover"] == sample_script.scenes[0].voiceover
        assert "visualCue" in first_scene

    def test_script_to_props_visual_cue_fields(self, sample_script):
        """Test that visual cue fields are correctly converted."""
        renderer = RemotionRenderer()
        props = renderer._script_to_props(sample_script)

        visual_cue = props["scenes"][0]["visualCue"]
        assert "description" in visual_cue
        assert "visualType" in visual_cue
        assert "elements" in visual_cue
        assert "durationInSeconds" in visual_cue

    def test_script_to_props_style_defaults(self, sample_script):
        """Test that default styles are included in props."""
        renderer = RemotionRenderer()
        props = renderer._script_to_props(sample_script)

        style = props["style"]
        assert style["backgroundColor"] == "#f4f4f5"
        assert style["primaryColor"] == "#00d9ff"
        assert style["secondaryColor"] == "#ff6b35"
        assert style["accentColor"] == "#00ff88"
        assert "fontFamily" in style

    def test_render_from_script_creates_props_file(self, sample_script, tmp_path):
        """Test that render_from_script creates a props file."""
        renderer = RemotionRenderer()
        output_path = tmp_path / "test_video.mp4"

        # Mock the subprocess to avoid actual rendering
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="test")
            renderer.render_from_script(sample_script, output_path)

            # Verify subprocess was called with correct args
            assert mock_run.called
            call_args = mock_run.call_args[0][0]
            assert "node" in call_args
            assert "scripts/render.mjs" in call_args

    def test_render_from_script_handles_subprocess_error(self, sample_script, tmp_path):
        """Test that render handles subprocess errors gracefully."""
        renderer = RemotionRenderer()
        output_path = tmp_path / "test_video.mp4"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="some output",
                stderr="Error: Something failed",
            )
            result = renderer.render_from_script(sample_script, output_path)

            assert not result.success
            assert "Error" in result.error_message or "failed" in result.error_message.lower()

    def test_render_from_script_handles_timeout(self, sample_script, tmp_path):
        """Test that render handles timeout gracefully."""
        renderer = RemotionRenderer()
        output_path = tmp_path / "test_video.mp4"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="node", timeout=600)
            result = renderer.render_from_script(sample_script, output_path)

            assert not result.success
            assert "timeout" in result.error_message.lower()

    def test_render_from_script_cleans_up_props_file(self, sample_script, tmp_path):
        """Test that props file is cleaned up after render."""
        renderer = RemotionRenderer()
        output_path = tmp_path / "test_video.mp4"
        props_path = renderer.remotion_dir / "temp_props.json"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            renderer.render_from_script(sample_script, output_path)

            # Props file should be cleaned up
            assert not props_path.exists()

    def test_get_video_duration(self, tmp_path):
        """Test getting video duration."""
        renderer = RemotionRenderer()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="10.5\n")
            duration = renderer._get_video_duration(tmp_path / "test.mp4")
            assert duration == 10.5

    def test_get_video_duration_handles_error(self, tmp_path):
        """Test that duration returns 0 on error."""
        renderer = RemotionRenderer()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            duration = renderer._get_video_duration(tmp_path / "test.mp4")
            assert duration == 0.0


class TestRendererIntegration:
    """Integration tests for renderer (require FFmpeg)."""

    @pytest.fixture
    def check_ffmpeg(self):
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
            )
            if result.returncode != 0:
                pytest.skip("FFmpeg not available")
        except FileNotFoundError:
            pytest.skip("FFmpeg not available")

    def test_real_mock_render(self, check_ffmpeg, tmp_path):
        """Test actual mock rendering with FFmpeg."""
        renderer = MockRenderer()
        output_path = tmp_path / "test_video.mp4"

        result = renderer.render_mock(
            output_path,
            duration_seconds=2.0,
        )

        assert result.success
        assert output_path.exists()
        assert result.duration_seconds == 2.0
        assert result.frame_count == 60


class TestGetRenderer:
    """Tests for get_renderer factory function."""

    def test_get_renderer_default(self):
        """Test getting default renderer (Remotion)."""
        renderer = get_renderer()
        assert isinstance(renderer, RemotionRenderer)

    def test_get_renderer_mock(self):
        """Test getting mock renderer."""
        config = Config()
        # Would need animation config to switch, for now test default
        renderer = get_renderer(config)
        assert isinstance(renderer, (RemotionRenderer, MockRenderer))

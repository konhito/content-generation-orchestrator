"""Tests for video composition module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.composition import VideoComposer
from src.composition.composer import CompositionResult, VideoSegment
from src.config import Config


class TestVideoComposer:
    """Tests for VideoComposer class."""

    @pytest.fixture
    def mock_ffmpeg(self):
        """Mock FFmpeg availability check."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            yield mock_run

    @pytest.fixture
    def composer(self, mock_ffmpeg):
        return VideoComposer()

    def test_init_checks_ffmpeg(self, mock_ffmpeg):
        """Test that initialization checks for FFmpeg."""
        VideoComposer()
        # Should have called ffmpeg -version
        calls = [c for c in mock_ffmpeg.call_args_list if "ffmpeg" in str(c)]
        assert len(calls) > 0

    def test_init_raises_without_ffmpeg(self):
        """Test that initialization fails without FFmpeg."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            with pytest.raises(RuntimeError, match="FFmpeg not found"):
                VideoComposer()


class TestVideoSegment:
    """Tests for VideoSegment dataclass."""

    def test_segment_creation(self, tmp_path):
        video_path = tmp_path / "video.mp4"
        audio_path = tmp_path / "audio.mp3"

        segment = VideoSegment(
            scene_id="test_scene",
            video_path=video_path,
            audio_path=audio_path,
            duration_seconds=10.5,
            start_time=0.0,
        )

        assert segment.scene_id == "test_scene"
        assert segment.duration_seconds == 10.5

    def test_segment_without_audio(self, tmp_path):
        video_path = tmp_path / "video.mp4"

        segment = VideoSegment(
            scene_id="test_scene",
            video_path=video_path,
            audio_path=None,
            duration_seconds=5.0,
        )

        assert segment.audio_path is None


class TestCompositionResult:
    """Tests for CompositionResult dataclass."""

    def test_result_creation(self, tmp_path):
        result = CompositionResult(
            output_path=tmp_path / "output.mp4",
            duration_seconds=120.5,
            resolution=(1920, 1080),
            file_size_bytes=50_000_000,
            segments_used=8,
        )

        assert result.duration_seconds == 120.5
        assert result.resolution == (1920, 1080)
        assert result.segments_used == 8


class TestCompose:
    """Tests for video composition."""

    @pytest.fixture
    def mock_ffmpeg(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            yield mock_run

    @pytest.fixture
    def composer(self, mock_ffmpeg):
        return VideoComposer()

    def test_compose_creates_output(self, composer, mock_ffmpeg, tmp_path):
        """Test that compose creates output file."""
        # Create mock video files
        video1 = tmp_path / "scene1.mp4"
        video2 = tmp_path / "scene2.mp4"
        video1.touch()
        video2.touch()

        output = tmp_path / "output.mp4"
        output.write_bytes(b"fake video data")  # Simulate FFmpeg creating file

        segments = [
            VideoSegment(
                scene_id="scene_1",
                video_path=video1,
                audio_path=None,
                duration_seconds=10.0,
            ),
            VideoSegment(
                scene_id="scene_2",
                video_path=video2,
                audio_path=None,
                duration_seconds=15.0,
            ),
        ]

        result = composer.compose(segments, output)

        assert result.output_path == output
        assert result.duration_seconds == 25.0
        assert result.segments_used == 2

    def test_compose_raises_without_segments(self, composer, tmp_path):
        """Test that compose fails with empty segments."""
        with pytest.raises(ValueError, match="No segments"):
            composer.compose([], tmp_path / "output.mp4")

    def test_compose_with_background_music(self, composer, mock_ffmpeg, tmp_path):
        """Test composition with background music."""
        video = tmp_path / "video.mp4"
        music = tmp_path / "music.mp3"
        video.touch()
        music.touch()

        output = tmp_path / "output.mp4"
        output.write_bytes(b"fake")

        segments = [
            VideoSegment(scene_id="scene_1", video_path=video, audio_path=None, duration_seconds=30.0)
        ]

        result = composer.compose(
            segments, output, background_music=music, music_volume=0.2
        )

        assert result is not None
        # Check FFmpeg was called with filter_complex for mixing
        call_args = str(mock_ffmpeg.call_args_list)
        assert "filter_complex" in call_args or "amix" in call_args


class TestAudioOverlay:
    """Tests for audio overlay functionality."""

    @pytest.fixture
    def mock_ffmpeg(self):
        with patch("subprocess.run") as mock_run:
            def run_side_effect(*args, **kwargs):
                result = MagicMock()
                result.returncode = 0
                result.stdout = '{"format": {"duration": "30.5"}}'
                result.stderr = ""
                return result

            mock_run.side_effect = run_side_effect
            yield mock_run

    @pytest.fixture
    def composer(self, mock_ffmpeg):
        return VideoComposer()

    def test_compose_with_audio_overlay(self, composer, mock_ffmpeg, tmp_path):
        """Test combining video with audio track."""
        video = tmp_path / "video.mp4"
        audio = tmp_path / "narration.mp3"
        output = tmp_path / "final.mp4"

        video.touch()
        audio.touch()
        output.write_bytes(b"output video")

        result = composer.compose_with_audio_overlay(video, audio, output)

        assert result.output_path == output


class TestThumbnail:
    """Tests for thumbnail generation."""

    @pytest.fixture
    def mock_ffmpeg(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            yield mock_run

    @pytest.fixture
    def composer(self, mock_ffmpeg):
        return VideoComposer()

    def test_generate_thumbnail(self, composer, mock_ffmpeg, tmp_path):
        """Test thumbnail generation."""
        video = tmp_path / "video.mp4"
        thumbnail = tmp_path / "thumb.jpg"

        video.touch()
        thumbnail.touch()  # Simulate FFmpeg creating file

        result = composer.generate_thumbnail(video, thumbnail, timestamp=10.0)

        assert result == thumbnail
        # Check FFmpeg was called with -ss for timestamp
        call_args = str(mock_ffmpeg.call_args_list)
        assert "-ss" in call_args


class TestCaptions:
    """Tests for caption/subtitle functionality."""

    @pytest.fixture
    def mock_ffmpeg(self):
        with patch("subprocess.run") as mock_run:
            def run_side_effect(*args, **kwargs):
                result = MagicMock()
                result.returncode = 0
                result.stdout = '{"format": {"duration": "60.0"}}'
                result.stderr = ""
                return result

            mock_run.side_effect = run_side_effect
            yield mock_run

    @pytest.fixture
    def composer(self, mock_ffmpeg):
        return VideoComposer()

    def test_add_captions(self, composer, mock_ffmpeg, tmp_path):
        """Test adding captions to video."""
        video = tmp_path / "video.mp4"
        captions = tmp_path / "captions.srt"
        output = tmp_path / "captioned.mp4"

        video.touch()
        captions.write_text("1\n00:00:00,000 --> 00:00:05,000\nHello world")
        output.write_bytes(b"captioned video")

        result = composer.add_captions(video, captions, output)

        assert result.output_path == output

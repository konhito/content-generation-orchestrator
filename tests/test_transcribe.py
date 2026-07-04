"""Tests for audio transcription module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.audio.transcribe import (
    WhisperTranscriber,
    FasterWhisperTranscriber,
    TranscriptionResult,
    get_audio_duration,
    get_transcriber,
)
from src.audio.tts import WordTimestamp


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_create_result(self):
        """Test creating a transcription result."""
        timestamps = [
            WordTimestamp(word="Hello", start_seconds=0.0, end_seconds=0.5),
            WordTimestamp(word="world", start_seconds=0.6, end_seconds=1.0),
        ]
        result = TranscriptionResult(
            text="Hello world",
            word_timestamps=timestamps,
            duration_seconds=1.0,
            language="en",
        )

        assert result.text == "Hello world"
        assert len(result.word_timestamps) == 2
        assert result.duration_seconds == 1.0
        assert result.language == "en"

    def test_default_language(self):
        """Test that language defaults to 'en'."""
        result = TranscriptionResult(
            text="Test",
            word_timestamps=[],
            duration_seconds=1.0,
        )
        assert result.language == "en"


class TestWhisperTranscriber:
    """Tests for WhisperTranscriber."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        transcriber = WhisperTranscriber()
        assert transcriber.model_name == "base"
        assert transcriber.device == "auto"
        assert transcriber._model is None

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        transcriber = WhisperTranscriber(model="small", device="cpu")
        assert transcriber.model_name == "small"
        assert transcriber.device == "cpu"

    @patch("src.audio.transcribe.WhisperTranscriber._load_model")
    def test_transcribe_file_not_found(self, mock_load):
        """Test that transcribe raises error for missing file."""
        transcriber = WhisperTranscriber()

        with pytest.raises(FileNotFoundError):
            transcriber.transcribe("/nonexistent/audio.mp3")

    def test_transcribe_success(self, tmp_path):
        """Test successful transcription with mocked whisper."""
        # Create a dummy audio file
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"\x00" * 1000)

        # Mock whisper module
        mock_whisper = MagicMock()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "Hello world",
            "language": "en",
            "segments": [
                {
                    "text": "Hello world",
                    "start": 0.0,
                    "end": 1.0,
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 0.4},
                        {"word": "world", "start": 0.5, "end": 1.0},
                    ],
                }
            ],
        }
        mock_whisper.load_model.return_value = mock_model

        with patch.dict("sys.modules", {"whisper": mock_whisper}):
            transcriber = WhisperTranscriber()
            result = transcriber.transcribe(audio_file)

            assert result.text == "Hello world"
            assert len(result.word_timestamps) == 2
            assert result.word_timestamps[0].word == "Hello"
            assert result.word_timestamps[1].word == "world"
            assert result.duration_seconds == 1.0


class TestFasterWhisperTranscriber:
    """Tests for FasterWhisperTranscriber."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        transcriber = FasterWhisperTranscriber()
        assert transcriber.model_name == "base"
        assert transcriber.device == "auto"
        assert transcriber._model is None

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        transcriber = FasterWhisperTranscriber(model="medium", device="cuda")
        assert transcriber.model_name == "medium"
        assert transcriber.device == "cuda"

    def test_transcribe_file_not_found(self):
        """Test that transcribe raises error for missing file."""
        transcriber = FasterWhisperTranscriber()

        with pytest.raises(FileNotFoundError):
            transcriber.transcribe("/nonexistent/audio.mp3")


class TestGetAudioDuration:
    """Tests for get_audio_duration function."""

    def test_file_not_found(self):
        """Test that function raises error for missing file."""
        with pytest.raises(FileNotFoundError):
            get_audio_duration("/nonexistent/audio.mp3")

    @patch("subprocess.run")
    def test_successful_duration(self, mock_run, tmp_path):
        """Test getting duration successfully."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"\x00" * 1000)

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="10.5\n",
        )

        duration = get_audio_duration(audio_file)
        assert duration == 10.5

    @patch("subprocess.run")
    def test_ffprobe_failure(self, mock_run, tmp_path):
        """Test error when ffprobe fails."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"\x00" * 1000)

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
        )

        with pytest.raises(RuntimeError):
            get_audio_duration(audio_file)


class TestGetTranscriber:
    """Tests for get_transcriber factory function."""

    def test_explicit_whisper_backend(self):
        """Test selecting whisper backend explicitly."""
        with patch.dict("sys.modules", {"whisper": MagicMock()}):
            transcriber = get_transcriber(backend="whisper")
            assert isinstance(transcriber, WhisperTranscriber)

    def test_explicit_faster_whisper_backend(self):
        """Test selecting faster-whisper backend explicitly."""
        with patch.dict("sys.modules", {"faster_whisper": MagicMock()}):
            transcriber = get_transcriber(backend="faster-whisper")
            assert isinstance(transcriber, FasterWhisperTranscriber)

    def test_unknown_backend_raises(self):
        """Test that unknown backend raises ValueError."""
        with pytest.raises(ValueError, match="Unknown transcription backend"):
            get_transcriber(backend="unknown")

    def test_custom_model_and_device(self):
        """Test passing custom model and device."""
        with patch.dict("sys.modules", {"whisper": MagicMock()}):
            transcriber = get_transcriber(
                backend="whisper",
                model="medium",
                device="cpu",
            )
            assert transcriber.model_name == "medium"
            assert transcriber.device == "cpu"

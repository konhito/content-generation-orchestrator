"""Tests for screenshot capture."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from src.refine.models import Beat
from src.refine.visual.screenshot import (
    MockScreenshotCapture,
    CapturedScreenshot,
    check_remotion_running,
    start_remotion_studio,
)


class TestMockScreenshotCapture:
    """Tests for MockScreenshotCapture class."""

    def test_mock_capture_initialization(self, temp_project_dir):
        """Test MockScreenshotCapture initialization."""
        screenshots_dir = temp_project_dir / "screenshots"
        capture = MockScreenshotCapture(screenshots_dir=screenshots_dir)
        assert capture.screenshots_dir == screenshots_dir
        assert screenshots_dir.exists()

    def test_mock_capture_returns_screenshot(self, temp_project_dir):
        """Test that mock capture returns a valid screenshot."""
        screenshots_dir = temp_project_dir / "screenshots"
        capture = MockScreenshotCapture(screenshots_dir=screenshots_dir)

        screenshot = capture.capture_screenshot(
            frame_number=120,
            filename="test_frame_120.png"
        )

        assert screenshot is not None
        assert isinstance(screenshot, CapturedScreenshot)
        assert screenshot.path.exists()
        assert screenshot.frame_number == 120

    def test_mock_capture_multiple_screenshots(self, temp_project_dir):
        """Test capturing multiple screenshots."""
        screenshots_dir = temp_project_dir / "screenshots"
        capture = MockScreenshotCapture(screenshots_dir=screenshots_dir)

        screenshots = []
        for i in range(3):
            screenshot = capture.capture_screenshot(
                frame_number=i * 30,
                filename=f"test_frame_{i * 30}.png"
            )
            screenshots.append(screenshot)

        # All paths should be unique
        paths = [s.path for s in screenshots]
        assert len(set(paths)) == 3
        # All files should exist
        assert all(s.path.exists() for s in screenshots)

    def test_mock_capture_beat(self, temp_project_dir):
        """Test capturing screenshot for a beat."""
        screenshots_dir = temp_project_dir / "screenshots"
        capture = MockScreenshotCapture(screenshots_dir=screenshots_dir)

        beat = Beat(
            index=0,
            start_seconds=0,
            end_seconds=4,
            text="Test beat",
            expected_visual="Test visual"
        )

        screenshot = capture.capture_beat(
            beat=beat,
            scene_start_frame=0,
            scene_index=0
        )

        assert screenshot is not None
        assert screenshot.beat_index == 0
        assert screenshot.path.exists()

    def test_mock_capture_beats(self, temp_project_dir, sample_beats):
        """Test capturing screenshots for multiple beats."""
        screenshots_dir = temp_project_dir / "screenshots"
        capture = MockScreenshotCapture(screenshots_dir=screenshots_dir)

        screenshots = capture.capture_beats(
            beats=sample_beats,
            scene_start_frame=0,
            scene_index=0
        )

        assert len(screenshots) == len(sample_beats)
        for i, screenshot in enumerate(screenshots):
            assert screenshot.beat_index == i
            assert screenshot.path.exists()


class TestContextManager:
    """Tests for context manager usage."""

    def test_context_manager_enter_exit(self, temp_project_dir):
        """Test context manager protocol."""
        screenshots_dir = temp_project_dir / "screenshots"

        with MockScreenshotCapture(screenshots_dir=screenshots_dir) as capture:
            screenshot = capture.capture_screenshot(100, "test.png")
            assert screenshot.path.exists()


class TestRemotionHelpers:
    """Tests for Remotion helper functions."""

    def test_check_remotion_running_not_running(self):
        """Test check when Remotion is not running."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Connection refused")
            result = check_remotion_running()
            assert result is False

    def test_check_remotion_running_success(self):
        """Test check when Remotion is running."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_response)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            result = check_remotion_running()
            assert result is True

    def test_start_remotion_studio_success(self, temp_project_dir):
        """Test starting Remotion studio successfully."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process

            with patch("time.sleep"):  # Don't actually wait
                with patch(
                    "src.refine.visual.screenshot.check_remotion_running",
                    return_value=True,
                ):
                    result = start_remotion_studio(temp_project_dir)

            assert result == mock_process
            mock_popen.assert_called_once()

    def test_start_remotion_studio_timeout(self, temp_project_dir):
        """Test Remotion studio startup timeout."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process

            with patch("time.sleep"):
                with patch(
                    "src.refine.visual.screenshot.check_remotion_running",
                    return_value=False,  # Never starts
                ):
                    with pytest.raises(RuntimeError, match="failed to start"):
                        start_remotion_studio(temp_project_dir, wait_seconds=2)

            # Process should be terminated on failure
            mock_process.terminate.assert_called_once()


class TestCapturedScreenshot:
    """Tests for CapturedScreenshot dataclass."""

    def test_captured_screenshot_creation(self, temp_project_dir):
        """Test creating a CapturedScreenshot."""
        screenshot = CapturedScreenshot(
            path=temp_project_dir / "test.png",
            beat_index=0,
            frame_number=120,
            expected_frame=120,
            timestamp_seconds=4.0,
            verified=True
        )

        assert screenshot.beat_index == 0
        assert screenshot.frame_number == 120
        assert screenshot.timestamp_seconds == 4.0
        assert screenshot.verified is True

    def test_captured_screenshot_unverified(self, temp_project_dir):
        """Test unverified screenshot."""
        screenshot = CapturedScreenshot(
            path=temp_project_dir / "test.png",
            beat_index=0,
            frame_number=119,  # Slightly off
            expected_frame=120,
            timestamp_seconds=4.0,
            verified=False
        )

        assert screenshot.verified is False
        assert screenshot.frame_number != screenshot.expected_frame


class TestScreenshotFilenames:
    """Tests for screenshot filename generation."""

    def test_beat_screenshot_filename_format(self, temp_project_dir):
        """Test that beat screenshots have proper naming."""
        screenshots_dir = temp_project_dir / "screenshots"
        capture = MockScreenshotCapture(screenshots_dir=screenshots_dir)

        beat = Beat(
            index=2,
            start_seconds=10,
            end_seconds=15,
            text="Test beat",
        )

        screenshot = capture.capture_beat(
            beat=beat,
            scene_start_frame=0,
            scene_index=1  # Scene 2
        )

        filename = screenshot.path.name
        # Should include scene number, beat number, and frame
        assert "scene2" in filename
        assert "beat3" in filename  # beat.index + 1
        assert ".png" in filename

"""
Screenshot capture for visual refinement.

Uses Playwright to control Remotion Studio and capture screenshots at specific frames.
"""

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import Browser, Page, Playwright, sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    Page = None
    Playwright = None

from ..models import Beat


class PlaywrightNotAvailableError(Exception):
    """Raised when Playwright is not installed."""
    pass


class RemotionNotRunningError(Exception):
    """Raised when Remotion Studio is not running."""
    pass


class FrameMismatchError(Exception):
    """Raised when the captured frame doesn't match expected frame."""
    pass


@dataclass
class CapturedScreenshot:
    """Information about a captured screenshot."""

    path: Path
    beat_index: int
    frame_number: int
    expected_frame: int
    timestamp_seconds: float
    verified: bool = False


class ScreenshotCapture:
    """Captures screenshots from Remotion Studio using Playwright."""

    DEFAULT_REMOTION_URL = "http://localhost:3000"
    DEFAULT_COMPOSITION = "ScenePlayer"

    def __init__(
        self,
        screenshots_dir: Path,
        fps: int = 30,
        remotion_url: str = DEFAULT_REMOTION_URL,
        composition: str = DEFAULT_COMPOSITION,
        headless: bool = True,
    ):
        """
        Initialize the screenshot capture.

        Args:
            screenshots_dir: Directory to save screenshots.
            fps: Frames per second of the video.
            remotion_url: URL of Remotion Studio.
            composition: Remotion composition ID.
            headless: Whether to run browser in headless mode.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise PlaywrightNotAvailableError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            )

        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.fps = fps
        self.remotion_url = remotion_url
        self.composition = composition
        self.headless = headless

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    def __enter__(self):
        """Context manager entry - start browser."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close browser."""
        self.stop()
        return False

    def start(self) -> None:
        """Start the browser and connect to Remotion Studio."""
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._page = self._browser.new_page()

        # Set viewport to match typical video dimensions
        self._page.set_viewport_size({"width": 1920, "height": 1080})

        # Navigate to Remotion Studio
        self._navigate_to_remotion()

    def stop(self) -> None:
        """Stop the browser."""
        if self._page:
            self._page.close()
            self._page = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def _navigate_to_remotion(self) -> None:
        """Navigate to Remotion Studio and verify it's running."""
        # Remotion Studio 4.x URL format: http://localhost:3000/{compositionId}
        url = f"{self.remotion_url}/{self.composition}"

        try:
            self._page.goto(url, timeout=20000)
            self._page.wait_for_load_state("networkidle", timeout=20000)
            # Extra wait for React/Remotion to fully render
            time.sleep(2)
        except Exception as e:
            raise RemotionNotRunningError(
                f"Could not connect to Remotion Studio at {url}. "
                f"Make sure it's running with: cd remotion && npm run dev\n"
                f"Error: {e}"
            )

    def navigate_to_frame(self, frame_number: int) -> None:
        """
        Navigate to a specific frame.

        Args:
            frame_number: The frame number to navigate to.
        """
        # Method: Click on the frame number button and type the new frame
        # In Remotion Studio 4.x, the frame number is a clickable button
        # that turns into an input field when clicked
        try:
            # Find the frame number button - it's typically a button with digits
            # located in the bottom left area near the time display
            frame_button = self._page.locator('button').filter(
                has_text=self._page.locator('text=/^\\d+$/')
            ).first

            # Alternative: look for buttons containing only numbers
            if frame_button.count() == 0:
                # Try to find any button that looks like a frame counter
                buttons = self._page.locator('button').all()
                for btn in buttons:
                    try:
                        text = btn.inner_text(timeout=500)
                        if text.isdigit() and len(text) >= 1:
                            frame_button = btn
                            break
                    except Exception:
                        continue

            # Click the frame button to turn it into an input
            frame_button.click(timeout=3000)
            time.sleep(0.3)

            # Select all and type the new frame number
            # Use Meta+a on Mac, Control+a on others
            import platform
            select_all = "Meta+a" if platform.system() == "Darwin" else "Control+a"
            self._page.keyboard.press(select_all)
            time.sleep(0.1)
            self._page.keyboard.type(str(frame_number))
            self._page.keyboard.press("Enter")
            time.sleep(1)
            return

        except Exception as e:
            print(f"Method 1 (click frame button) failed: {e}")

        # Fallback: Try pressing Home then using arrow keys or direct input
        try:
            # Press Home to go to frame 0
            self._page.keyboard.press("Home")
            time.sleep(0.5)

            # For short videos, we could navigate frame by frame, but that's slow
            # Instead, try clicking on the timeline at the approximate position
            print(f"Warning: Could not navigate to exact frame {frame_number}, at frame 0")

        except Exception as e:
            print(f"Warning: Could not navigate to frame {frame_number}: {e}")

    def get_current_frame(self) -> int:
        """
        Get the current frame number from Remotion Studio.

        Returns:
            Current frame number, or -1 if unable to determine.
        """
        try:
            # Try to read frame from URL
            url = self._page.url
            if "frame=" in url:
                frame_str = url.split("frame=")[1].split("&")[0]
                return int(frame_str)

            # Fallback: Try to read from the UI
            # Remotion shows frame number in the timeline area
            frame_indicator = self._page.query_selector('[data-testid="frame-indicator"]')
            if frame_indicator:
                text = frame_indicator.inner_text()
                # Parse frame number from text like "Frame: 120"
                if ":" in text:
                    return int(text.split(":")[1].strip())
                return int(text.strip())

        except (ValueError, AttributeError, TypeError):
            pass

        return -1

    def capture_screenshot(
        self,
        frame_number: int,
        filename: str,
        verify: bool = True,
    ) -> CapturedScreenshot:
        """
        Navigate to a frame and capture a screenshot.

        Args:
            frame_number: The frame number to capture.
            filename: Filename for the screenshot.
            verify: Whether to verify the frame number matches.

        Returns:
            CapturedScreenshot with path and metadata.

        Raises:
            FrameMismatchError: If verification fails and frame doesn't match.
        """
        self.navigate_to_frame(frame_number)

        # Capture screenshot
        screenshot_path = self.screenshots_dir / filename
        self._page.screenshot(path=str(screenshot_path))

        # Verify frame number if requested
        verified = False
        actual_frame = -1
        if verify:
            actual_frame = self.get_current_frame()
            if actual_frame >= 0:
                # Allow 1 frame tolerance
                if abs(actual_frame - frame_number) <= 1:
                    verified = True
                else:
                    raise FrameMismatchError(
                        f"Frame mismatch: expected {frame_number}, got {actual_frame}"
                    )
            else:
                # Couldn't verify, but screenshot was taken
                verified = False
        else:
            verified = True  # Skip verification

        return CapturedScreenshot(
            path=screenshot_path,
            beat_index=-1,  # Will be set by caller
            frame_number=actual_frame if actual_frame >= 0 else frame_number,
            expected_frame=frame_number,
            timestamp_seconds=frame_number / self.fps,
            verified=verified,
        )

    def capture_beat(
        self,
        beat: Beat,
        scene_start_frame: int,
        scene_index: int,
    ) -> CapturedScreenshot:
        """
        Capture a screenshot for a specific beat.

        Uses the middle of the beat for the screenshot to capture
        the most representative state.

        Args:
            beat: The beat to capture.
            scene_start_frame: Starting frame of the scene.
            scene_index: Index of the scene (for filename).

        Returns:
            CapturedScreenshot with beat information.
        """
        # Calculate the target frame (middle of the beat)
        beat_mid_seconds = beat.mid_seconds
        beat_frame = int(beat_mid_seconds * self.fps)
        target_frame = scene_start_frame + beat_frame

        # Generate descriptive filename
        filename = (
            f"scene{scene_index + 1}_beat{beat.index + 1}_"
            f"frame{target_frame}.png"
        )

        screenshot = self.capture_screenshot(target_frame, filename, verify=True)
        screenshot.beat_index = beat.index

        return screenshot

    def capture_beats(
        self,
        beats: list[Beat],
        scene_start_frame: int,
        scene_index: int,
    ) -> list[CapturedScreenshot]:
        """
        Capture screenshots for all beats in a scene.

        Args:
            beats: List of beats to capture.
            scene_start_frame: Starting frame of the scene.
            scene_index: Index of the scene.

        Returns:
            List of CapturedScreenshot objects.
        """
        screenshots = []
        for beat in beats:
            try:
                screenshot = self.capture_beat(beat, scene_start_frame, scene_index)
                screenshots.append(screenshot)
            except FrameMismatchError as e:
                print(f"Warning: {e}")
                # Still include the screenshot with verification failed
                beat_mid_seconds = beat.mid_seconds
                beat_frame = int(beat_mid_seconds * self.fps)
                target_frame = scene_start_frame + beat_frame
                filename = f"scene{scene_index + 1}_beat{beat.index + 1}_frame{target_frame}_unverified.png"
                screenshot_path = self.screenshots_dir / filename
                if screenshot_path.exists():
                    screenshots.append(
                        CapturedScreenshot(
                            path=screenshot_path,
                            beat_index=beat.index,
                            frame_number=-1,
                            expected_frame=target_frame,
                            timestamp_seconds=beat_mid_seconds,
                            verified=False,
                        )
                    )

        return screenshots


class MockScreenshotCapture:
    """Mock screenshot capture for testing without a browser."""

    def __init__(self, screenshots_dir: Path, fps: int = 30):
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.fps = fps

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def navigate_to_frame(self, frame_number: int) -> None:
        pass

    def get_current_frame(self) -> int:
        return 0

    def capture_screenshot(
        self,
        frame_number: int,
        filename: str,
        verify: bool = True,
    ) -> CapturedScreenshot:
        """Create a mock screenshot file."""
        screenshot_path = self.screenshots_dir / filename

        # Create a simple placeholder image (1x1 pixel PNG)
        # In real tests, you might want to copy a fixture image
        placeholder = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
            0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
            0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82,
        ])
        screenshot_path.write_bytes(placeholder)

        return CapturedScreenshot(
            path=screenshot_path,
            beat_index=-1,
            frame_number=frame_number,
            expected_frame=frame_number,
            timestamp_seconds=frame_number / self.fps,
            verified=True,
        )

    def capture_beat(
        self,
        beat: Beat,
        scene_start_frame: int,
        scene_index: int,
    ) -> CapturedScreenshot:
        beat_mid_seconds = beat.mid_seconds
        beat_frame = int(beat_mid_seconds * self.fps)
        target_frame = scene_start_frame + beat_frame

        filename = f"scene{scene_index + 1}_beat{beat.index + 1}_frame{target_frame}.png"
        screenshot = self.capture_screenshot(target_frame, filename, verify=True)
        screenshot.beat_index = beat.index

        return screenshot

    def capture_beats(
        self,
        beats: list[Beat],
        scene_start_frame: int,
        scene_index: int,
    ) -> list[CapturedScreenshot]:
        screenshots = []
        for beat in beats:
            screenshot = self.capture_beat(beat, scene_start_frame, scene_index)
            screenshots.append(screenshot)
        return screenshots


def check_remotion_running(url: str = "http://localhost:3000") -> bool:
    """
    Check if Remotion Studio is running.

    Args:
        url: URL to check.

    Returns:
        True if Remotion is running, False otherwise.
    """
    import urllib.request

    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except Exception:
        return False


def start_remotion_studio(remotion_dir: Path, wait_seconds: int = 10) -> subprocess.Popen:
    """
    Start Remotion Studio in the background.

    Args:
        remotion_dir: Path to the remotion directory.
        wait_seconds: Seconds to wait for startup.

    Returns:
        Subprocess handle for the Remotion dev server.

    Raises:
        RuntimeError: If Remotion fails to start.
    """
    # Check if npm is available
    if not shutil.which("npm"):
        raise RuntimeError("npm not found. Please install Node.js and npm.")

    # Start the dev server
    process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(remotion_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for it to start
    for _ in range(wait_seconds):
        time.sleep(1)
        if check_remotion_running():
            return process

    # Cleanup if failed
    process.terminate()
    raise RuntimeError(
        f"Remotion Studio failed to start within {wait_seconds} seconds"
    )

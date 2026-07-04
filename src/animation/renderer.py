"""Animation renderer abstraction and implementations."""

import json
import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import Config, load_config
from ..models import Script


@dataclass
class RenderResult:
    """Result of rendering an animation."""

    output_path: Path
    duration_seconds: float
    frame_count: int
    success: bool
    error_message: str | None = None


class AnimationRenderer(ABC):
    """Abstract base class for animation renderers.

    This interface allows swapping between different rendering backends
    (Remotion, Motion Canvas, etc.) without changing the pipeline code.
    """

    def __init__(self, config: Config | None = None):
        self.config = config or load_config()

    @abstractmethod
    def render_from_script(
        self,
        script: Script,
        output_path: Path | str,
    ) -> RenderResult:
        """Render a video from a script.

        Args:
            script: The video script with scenes and visual cues
            output_path: Path for the output video file

        Returns:
            RenderResult with output info
        """
        pass

    @abstractmethod
    def render_mock(
        self,
        output_path: Path | str,
        duration_seconds: float = 10.0,
    ) -> RenderResult:
        """Generate a mock/test video.

        Args:
            output_path: Path for the output video file
            duration_seconds: Duration of the mock video

        Returns:
            RenderResult with output info
        """
        pass


class RemotionRenderer(AnimationRenderer):
    """Render animations using Remotion (React-based).

    This renderer generates videos by:
    1. Converting the script to Remotion props (JSON)
    2. Running the Remotion render script
    3. Returning the rendered video path
    """

    def __init__(self, config: Config | None = None):
        super().__init__(config)
        self.remotion_dir = Path(__file__).parent.parent.parent / "remotion"
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check if required dependencies are available."""
        # Check Node.js
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError("Node.js not working properly")
        except FileNotFoundError:
            raise RuntimeError("Node.js not found. Required for Remotion.")

        # Check if Remotion project exists
        if not (self.remotion_dir / "package.json").exists():
            raise RuntimeError(f"Remotion project not found at {self.remotion_dir}")

    def _script_to_props(self, script: Script) -> dict[str, Any]:
        """Convert a Script to Remotion props format."""
        scenes = []
        for scene in script.scenes:
            scenes.append({
                "sceneId": scene.scene_id,
                "sceneType": scene.scene_type,
                "title": scene.title,
                "voiceover": scene.voiceover,
                "visualCue": {
                    "description": scene.visual_cue.description,
                    "visualType": scene.visual_cue.visual_type,
                    "elements": scene.visual_cue.elements,
                    "durationInSeconds": scene.visual_cue.duration_seconds,
                },
                "durationInSeconds": scene.duration_seconds,
                "notes": scene.notes or "",
            })

        return {
            "title": script.title,
            "scenes": scenes,
            "style": {
                "backgroundColor": "#f4f4f5",
                "primaryColor": "#00d9ff",
                "secondaryColor": "#ff6b35",
                "accentColor": "#00ff88",
                "fontFamily": "Inter, sans-serif",
            },
        }

    def render_from_script(
        self,
        script: Script,
        output_path: Path | str,
    ) -> RenderResult:
        """Render a video from a script using Remotion."""
        output_path = Path(output_path).absolute()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert script to props
        props = self._script_to_props(script)

        # Write props to temp file in remotion dir (where render script runs)
        props_path = self.remotion_dir / "temp_props.json"
        with open(props_path, "w") as f:
            json.dump(props, f, indent=2)

        try:
            # Run Remotion render script
            cmd = [
                "node",
                "scripts/render.mjs",
                "--props", str(props_path),
                "--output", str(output_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                cwd=self.remotion_dir,
            )

            if result.returncode != 0:
                return RenderResult(
                    output_path=output_path,
                    duration_seconds=0,
                    frame_count=0,
                    success=False,
                    error_message=f"Render failed: {result.stderr}\n{result.stdout}",
                )

            # Verify output was created
            if not output_path.exists():
                return RenderResult(
                    output_path=output_path,
                    duration_seconds=0,
                    frame_count=0,
                    success=False,
                    error_message="Render completed but output file not found",
                )

            # Get video duration
            duration = self._get_video_duration(output_path)

            return RenderResult(
                output_path=output_path,
                duration_seconds=duration,
                frame_count=int(duration * 30),
                success=True,
            )

        except subprocess.TimeoutExpired:
            return RenderResult(
                output_path=output_path,
                duration_seconds=0,
                frame_count=0,
                success=False,
                error_message="Render timeout exceeded (10 minutes)",
            )
        finally:
            # Clean up props file
            props_path.unlink(missing_ok=True)

    def render_mock(
        self,
        output_path: Path | str,
        duration_seconds: float = 10.0,
    ) -> RenderResult:
        """Generate a mock video using FFmpeg test pattern."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fps = self.config.video.fps
        width = self.config.video.width
        height = self.config.video.height

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"testsrc2=size={width}x{height}:rate={fps}:duration={duration_seconds}",
            "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={duration_seconds}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return RenderResult(
                    output_path=output_path,
                    duration_seconds=0,
                    frame_count=0,
                    success=False,
                    error_message=f"FFmpeg failed: {result.stderr}",
                )

            return RenderResult(
                output_path=output_path,
                duration_seconds=duration_seconds,
                frame_count=int(duration_seconds * fps),
                success=True,
            )

        except subprocess.TimeoutExpired:
            return RenderResult(
                output_path=output_path,
                duration_seconds=0,
                frame_count=0,
                success=False,
                error_message="Render timeout",
            )

    def _get_video_duration(self, video_path: Path) -> float:
        """Get the duration of a video file using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except (ValueError, subprocess.SubprocessError):
            pass

        return 0.0


class MockRenderer(AnimationRenderer):
    """Mock renderer that generates test pattern videos.

    Used for testing the pipeline without actual rendering.
    """

    def render_from_script(
        self,
        script: Script,
        output_path: Path | str,
    ) -> RenderResult:
        """Generate a mock video matching script duration."""
        total_duration = sum(s.duration_seconds for s in script.scenes)
        return self.render_mock(output_path, duration_seconds=total_duration)

    def render_mock(
        self,
        output_path: Path | str,
        duration_seconds: float = 10.0,
    ) -> RenderResult:
        """Generate a test pattern video."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fps = self.config.video.fps
        width = self.config.video.width
        height = self.config.video.height

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"testsrc2=size={width}x{height}:rate={fps}:duration={duration_seconds}",
            "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={duration_seconds}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return RenderResult(
                    output_path=output_path,
                    duration_seconds=0,
                    frame_count=0,
                    success=False,
                    error_message=f"FFmpeg failed: {result.stderr}",
                )

            return RenderResult(
                output_path=output_path,
                duration_seconds=duration_seconds,
                frame_count=int(duration_seconds * fps),
                success=True,
            )

        except subprocess.TimeoutExpired:
            return RenderResult(
                output_path=output_path,
                duration_seconds=0,
                frame_count=0,
                success=False,
                error_message="Render timeout",
            )


def get_renderer(config: Config | None = None) -> AnimationRenderer:
    """Get the appropriate renderer based on configuration.

    Args:
        config: Configuration object. If None, uses default config.

    Returns:
        An AnimationRenderer instance
    """
    if config is None:
        config = load_config()

    renderer_type = getattr(config, "animation", {})
    if hasattr(renderer_type, "renderer"):
        renderer_name = renderer_type.renderer.lower()
    else:
        renderer_name = "remotion"  # Default to Remotion

    if renderer_name == "remotion":
        return RemotionRenderer(config)
    elif renderer_name == "mock":
        return MockRenderer(config)
    else:
        # Default to Remotion
        return RemotionRenderer(config)

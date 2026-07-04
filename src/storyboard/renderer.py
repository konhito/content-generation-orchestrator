"""Storyboard renderer.

This module handles rendering storyboards to video using Remotion's
StoryboardPlayer component.
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .loader import storyboard_to_dict
from .models import Storyboard


@dataclass
class RenderResult:
    """Result of rendering a storyboard."""

    success: bool
    output_path: Path | None
    duration_seconds: float
    error_message: str | None = None


class StoryboardRenderer:
    """Renders storyboards to video using Remotion."""

    def __init__(self, remotion_dir: Path | None = None):
        """Initialize the renderer.

        Args:
            remotion_dir: Path to the Remotion project directory.
                          Defaults to the project's remotion/ directory.
        """
        if remotion_dir is None:
            # Default to project's remotion directory
            self.remotion_dir = (
                Path(__file__).parent.parent.parent / "remotion"
            )
        else:
            self.remotion_dir = Path(remotion_dir)

        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check that required dependencies are available."""
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

        # Check Remotion project
        if not (self.remotion_dir / "package.json").exists():
            raise RuntimeError(
                f"Remotion project not found at {self.remotion_dir}"
            )

    def render(
        self,
        storyboard: Storyboard,
        output_path: Path | str,
        composition_id: str = "StoryboardPlayer",
    ) -> RenderResult:
        """Render a storyboard to video.

        Args:
            storyboard: The storyboard to render.
            output_path: Path for the output video file.
            composition_id: Remotion composition ID to use.

        Returns:
            RenderResult with output info.
        """
        output_path = Path(output_path).absolute()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write storyboard to temp file
        props_path = self.remotion_dir / "temp_storyboard.json"
        props = {"storyboard": storyboard_to_dict(storyboard)}

        with open(props_path, "w") as f:
            json.dump(props, f, indent=2)

        try:
            # Run Remotion render
            cmd = [
                "node",
                "scripts/render.mjs",
                "--composition",
                composition_id,
                "--props",
                str(props_path),
                "--output",
                str(output_path),
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
                    success=False,
                    output_path=None,
                    duration_seconds=0,
                    error_message=f"Render failed: {result.stderr}\n{result.stdout}",
                )

            # Verify output was created
            if not output_path.exists():
                return RenderResult(
                    success=False,
                    output_path=None,
                    duration_seconds=0,
                    error_message="Render completed but output file not found",
                )

            return RenderResult(
                success=True,
                output_path=output_path,
                duration_seconds=storyboard.duration_seconds,
            )

        except subprocess.TimeoutExpired:
            return RenderResult(
                success=False,
                output_path=None,
                duration_seconds=0,
                error_message="Render timeout exceeded (10 minutes)",
            )
        finally:
            # Clean up temp file
            props_path.unlink(missing_ok=True)

    def render_from_file(
        self,
        storyboard_path: Path | str,
        output_path: Path | str,
    ) -> RenderResult:
        """Render a storyboard from a JSON file.

        Args:
            storyboard_path: Path to the storyboard JSON file.
            output_path: Path for the output video file.

        Returns:
            RenderResult with output info.
        """
        from .loader import load_storyboard

        storyboard = load_storyboard(storyboard_path)
        return self.render(storyboard, output_path)

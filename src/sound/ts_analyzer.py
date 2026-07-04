"""TypeScript AST Analyzer wrapper for Python.

This module provides a Python interface to the Node.js AST parser
that extracts animation timings from TSX scene files.

The TypeScript analyzer overcomes regex limitations by:
1. Parsing actual TypeScript/JSX AST
2. Evaluating expressions like Math.round(durationInFrames * 0.10)
3. Resolving variable references
4. Extracting component context for semantic mapping
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .models import SoundMoment, SceneAnalysisResult


@dataclass
class AnimationContext:
    """Context information about an animation."""

    component_hint: str
    variable_name: Optional[str] = None
    line_number: int = 0
    nearby_text: Optional[str] = None
    property_path: Optional[str] = None


@dataclass
class ExtractedAnimation:
    """An animation extracted from TSX code."""

    type: str  # 'interpolate', 'spring', 'counter', 'opacity', 'width', etc.
    property: str
    frame_start: int
    frame_end: Optional[int]
    from_value: Optional[float]
    to_value: Optional[float]
    context: AnimationContext


class TypeScriptAnalyzer:
    """Analyzes TSX scene files using Node.js AST parsing.

    This analyzer provides more accurate animation detection than
    regex by actually parsing and evaluating the TypeScript code.
    """

    def __init__(self, fps: int = 30, remotion_dir: Optional[Path] = None):
        """Initialize the analyzer.

        Args:
            fps: Frames per second (default 30)
            remotion_dir: Path to remotion directory (auto-detected if None)
        """
        self.fps = fps
        self._remotion_dir = remotion_dir
        self._script_path: Optional[Path] = None

    def _find_remotion_dir(self) -> Path:
        """Find the remotion directory."""
        if self._remotion_dir:
            return self._remotion_dir

        # Try common locations
        candidates = [
            Path.cwd() / "remotion",
            Path.cwd().parent / "remotion",
            Path(__file__).parent.parent.parent / "remotion",
        ]

        for candidate in candidates:
            if candidate.exists() and (candidate / "package.json").exists():
                return candidate

        raise FileNotFoundError("Could not find remotion directory")

    def _get_script_path(self) -> Path:
        """Get path to the extraction script."""
        if self._script_path:
            return self._script_path

        remotion_dir = self._find_remotion_dir()
        script_path = remotion_dir / "scripts" / "extract-animations.ts"

        if not script_path.exists():
            raise FileNotFoundError(f"Animation extraction script not found: {script_path}")

        self._script_path = script_path
        return script_path

    def _check_dependencies(self) -> bool:
        """Check if required Node.js dependencies are installed."""
        remotion_dir = self._find_remotion_dir()

        # Check for @babel/parser in node_modules
        babel_parser = remotion_dir / "node_modules" / "@babel" / "parser"
        babel_traverse = remotion_dir / "node_modules" / "@babel" / "traverse"

        return babel_parser.exists() and babel_traverse.exists()

    def analyze_scene(
        self,
        scene_path: Path,
        duration_frames: int,
    ) -> SceneAnalysisResult:
        """Analyze a TSX scene file for animation patterns.

        Args:
            scene_path: Path to the TSX scene file
            duration_frames: Total duration of the scene in frames

        Returns:
            SceneAnalysisResult with detected moments

        Raises:
            FileNotFoundError: If scene file or script not found
            RuntimeError: If Node.js execution fails
        """
        scene_path = Path(scene_path)
        if not scene_path.exists():
            raise FileNotFoundError(f"Scene file not found: {scene_path}")

        # Extract animations using Node.js script
        animations = self._run_extraction(scene_path, duration_frames)

        # Convert to SceneAnalysisResult
        return self._build_result(scene_path, duration_frames, animations)

    def _run_extraction(
        self,
        scene_path: Path,
        duration_frames: int,
    ) -> list[ExtractedAnimation]:
        """Run the Node.js extraction script.

        Args:
            scene_path: Path to the TSX file
            duration_frames: Scene duration in frames

        Returns:
            List of extracted animations
        """
        script_path = self._get_script_path()
        remotion_dir = self._find_remotion_dir()

        # Build command - use npx to run ts-node
        cmd = [
            "npx",
            "ts-node",
            "--transpile-only",
            str(script_path),
            str(scene_path.absolute()),
            str(duration_frames),
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(remotion_dir),
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Animation extraction timed out")
        except FileNotFoundError:
            raise RuntimeError("Node.js/npx not found. Ensure Node.js is installed.")

        if result.returncode != 0:
            # Try to parse any error output
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise RuntimeError(f"Animation extraction failed: {error_msg}")

        # Parse JSON output
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse extraction output: {e}")

        # Check for errors in the result
        if data.get("errors"):
            # Log errors but continue with partial results
            for err in data["errors"]:
                print(f"Warning: {err}")

        # Convert to ExtractedAnimation objects
        animations = []
        for anim_data in data.get("animations", []):
            context_data = anim_data.get("context", {})
            context = AnimationContext(
                component_hint=context_data.get("componentHint", "unknown"),
                variable_name=context_data.get("variableName"),
                line_number=context_data.get("lineNumber", 0),
                nearby_text=context_data.get("nearbyText"),
                property_path=context_data.get("propertyPath"),
            )

            animations.append(
                ExtractedAnimation(
                    type=anim_data.get("type", "interpolate"),
                    property=anim_data.get("property", "unknown"),
                    frame_start=anim_data.get("frameStart", 0),
                    frame_end=anim_data.get("frameEnd"),
                    from_value=anim_data.get("fromValue"),
                    to_value=anim_data.get("toValue"),
                    context=context,
                )
            )

        return animations

    def _build_result(
        self,
        scene_path: Path,
        duration_frames: int,
        animations: list[ExtractedAnimation],
    ) -> SceneAnalysisResult:
        """Build a SceneAnalysisResult from extracted animations.

        Args:
            scene_path: Path to the TSX file
            duration_frames: Scene duration in frames
            animations: Extracted animations

        Returns:
            SceneAnalysisResult with SoundMoments
        """
        # Extract scene info from path
        scene_id = scene_path.stem
        scene_type = self._extract_scene_type(scene_path)

        result = SceneAnalysisResult(
            scene_id=scene_id,
            scene_type=scene_type,
            duration_frames=duration_frames,
            source_file=str(scene_path),
        )

        # Convert each animation to appropriate SoundMoments
        for anim in animations:
            moments = self._animation_to_moments(anim, duration_frames)
            for moment in moments:
                result.add_moment(moment)

        # Sort by frame
        result.moments.sort(key=lambda m: m.frame)

        return result

    def _extract_scene_type(self, path: Path) -> str:
        """Extract scene type from file path."""
        parts = path.parts
        try:
            scenes_idx = parts.index("scenes")
            if scenes_idx + 2 < len(parts):
                project = parts[scenes_idx + 1]
                scene = path.stem
                return f"{project}/{scene}"
        except ValueError:
            pass
        return path.stem

    def _animation_to_moments(
        self,
        anim: ExtractedAnimation,
        duration_frames: int,
    ) -> list[SoundMoment]:
        """Convert an extracted animation to SoundMoments.

        Args:
            anim: The extracted animation
            duration_frames: Scene duration for calculating relative importance

        Returns:
            List of SoundMoments for this animation
        """
        moments = []

        # Determine moment type based on animation type and context
        moment_type = self._determine_moment_type(anim)
        intensity = self._calculate_intensity(anim, duration_frames)
        confidence = self._calculate_confidence(anim)

        # Build context string
        context_parts = []
        if anim.context.component_hint and anim.context.component_hint != "unknown":
            context_parts.append(anim.context.component_hint)
        if anim.context.nearby_text:
            context_parts.append(anim.context.nearby_text)
        context_parts.append(f"{anim.type} animation")
        if anim.from_value is not None and anim.to_value is not None:
            context_parts.append(f"[{anim.from_value} -> {anim.to_value}]")

        context_str = " - ".join(context_parts)

        # Create the main moment at animation start
        moments.append(
            SoundMoment(
                type=moment_type,
                frame=anim.frame_start,
                confidence=confidence,
                context=context_str,
                intensity=intensity,
                source="code",
                duration_frames=anim.frame_end - anim.frame_start if anim.frame_end else None,
            )
        )

        # For certain animation types, add additional moments
        if anim.type == "spring" and anim.context.nearby_text:
            # Spring animations often accompany reveals
            if any(kw in anim.context.nearby_text.lower() for kw in ["reveal", "badge", "87x"]):
                moments[-1].type = "reveal"
                moments[-1].intensity = min(1.0, intensity + 0.2)

        return moments

    def _determine_moment_type(self, anim: ExtractedAnimation) -> str:
        """Determine the moment type from animation characteristics.

        Args:
            anim: The extracted animation

        Returns:
            Moment type string
        """
        # Check animation type first
        anim_type = anim.type.lower()
        hint = (anim.context.component_hint or "").lower()
        nearby = (anim.context.nearby_text or "").lower()
        prop = (anim.property or "").lower()

        # Counter animations
        if anim_type == "counter" or "speed" in hint or "counter" in hint or "count" in hint:
            return "counter"

        # Width animations (bars, charts)
        if anim_type == "width" or "bar" in hint or "chart" in hint or prop == "width":
            return "chart_grow"

        # Opacity animations
        if anim_type == "opacity" or prop == "opacity":
            if anim.from_value is not None and anim.to_value is not None:
                if anim.from_value < anim.to_value:
                    # Check for reveal hints
                    if any(kw in nearby for kw in ["reveal", "badge", "sparkle"]):
                        return "reveal"
                    return "element_appear"
                else:
                    return "element_disappear"
            return "element_appear"

        # Spring animations (pop-in effects)
        if anim_type == "spring":
            if any(kw in nearby for kw in ["reveal", "badge"]):
                return "reveal"
            if any(kw in nearby for kw in ["burst", "particle"]):
                return "transition"
            return "element_appear"

        # Scale animations
        if anim_type == "scale" or "scale" in prop:
            if any(kw in nearby for kw in ["reveal", "zoom"]):
                return "reveal"
            return "element_appear"

        # Transform animations
        if anim_type == "transform":
            return "transition"

        # Default to element_appear
        return "element_appear"

    def _calculate_intensity(
        self,
        anim: ExtractedAnimation,
        duration_frames: int,
    ) -> float:
        """Calculate the intensity/prominence of an animation.

        Args:
            anim: The extracted animation
            duration_frames: Scene duration for relative calculations

        Returns:
            Intensity value between 0 and 1
        """
        intensity = 0.7  # Default

        # Value range impacts intensity
        if anim.from_value is not None and anim.to_value is not None:
            value_range = abs(anim.to_value - anim.from_value)

            # Large numeric changes (counters) are more prominent
            if value_range > 100:
                intensity = min(1.0, 0.8 + (value_range / 5000) * 0.2)
            elif value_range > 1:
                intensity = 0.7 + (value_range / 100) * 0.1

        # Context-based adjustments
        nearby = (anim.context.nearby_text or "").lower()
        hint = (anim.context.component_hint or "").lower()

        if any(kw in nearby for kw in ["reveal", "87x", "badge"]):
            intensity = max(intensity, 0.9)
        if any(kw in nearby for kw in ["burst", "dramatic", "fast"]):
            intensity = max(intensity, 0.8)
        if any(kw in nearby for kw in ["slow", "subtle"]):
            intensity = min(intensity, 0.6)

        # Later animations tend to be more important (build to climax)
        position_factor = anim.frame_start / max(duration_frames, 1)
        if position_factor > 0.7:
            intensity = min(1.0, intensity + 0.1)

        return max(0.0, min(1.0, intensity))

    def _calculate_confidence(self, anim: ExtractedAnimation) -> float:
        """Calculate confidence score for the detection.

        Args:
            anim: The extracted animation

        Returns:
            Confidence value between 0 and 1
        """
        confidence = 0.85  # Base confidence for AST-based detection

        # Higher confidence for specific animation types
        if anim.type in ("counter", "opacity", "width"):
            confidence = 0.95

        # Higher confidence with good context
        if anim.context.component_hint and anim.context.component_hint != "unknown":
            confidence = min(1.0, confidence + 0.05)

        if anim.context.nearby_text:
            confidence = min(1.0, confidence + 0.05)

        return confidence


def analyze_scene_with_ast(
    scene_path: Path,
    duration_frames: int,
    fps: int = 30,
) -> SceneAnalysisResult:
    """Analyze a TSX scene file using AST parsing.

    Convenience function that creates an analyzer and runs analysis.

    Args:
        scene_path: Path to the TSX file
        duration_frames: Scene duration in frames
        fps: Frames per second

    Returns:
        SceneAnalysisResult with detected moments
    """
    analyzer = TypeScriptAnalyzer(fps=fps)
    return analyzer.analyze_scene(scene_path, duration_frames)

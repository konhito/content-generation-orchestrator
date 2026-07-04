"""Scene code analyzer for detecting animation patterns.

This module parses TSX scene code to detect animation patterns
that should have sound effects.

Supported patterns:
- Opacity interpolations (element appearing/disappearing)
- Spring animations with scale
- Number/counter animations (Math.round(interpolate(...)))
- Width/height interpolations in charts
- Phase transitions (localFrame > phaseXStart)
- Glow/highlight animations
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .models import SoundMoment, SceneAnalysisResult


@dataclass
class AnimationPattern:
    """A detected animation pattern in TSX code."""
    pattern_type: str
    frame_start: int
    frame_end: Optional[int]
    line_number: int
    code_snippet: str
    context: str
    confidence: float = 0.8


class SceneAnalyzer:
    """Analyzes TSX scene code to detect animation events.

    Uses regex patterns to find common Remotion animation patterns
    and extract frame timing information.
    """

    # Regex patterns for detecting animations

    # Opacity fade in: interpolate(frame, [X, Y], [0, 1])
    OPACITY_FADE_IN = re.compile(
        r"opacity:\s*interpolate\s*\(\s*(?:local)?[fF]rame\s*,\s*\[(\d+)\s*,\s*(\d+)\]\s*,\s*\[0\s*,\s*1\]",
        re.IGNORECASE
    )

    # Opacity fade out: interpolate(frame, [X, Y], [1, 0])
    OPACITY_FADE_OUT = re.compile(
        r"opacity:\s*interpolate\s*\(\s*(?:local)?[fF]rame\s*,\s*\[(\d+)\s*,\s*(\d+)\]\s*,\s*\[1\s*,\s*0\]",
        re.IGNORECASE
    )

    # Generic opacity with variables: opacity: interpolate(frame, [...], ...)
    OPACITY_GENERIC = re.compile(
        r"opacity:\s*interpolate\s*\(\s*(?:local)?[fF]rame\s*,\s*\[([^\]]+)\]\s*,\s*\[([^\]]+)\]",
        re.IGNORECASE
    )

    # Spring animation: spring({ frame: ..., fps: ..., from: 0, to: 1 })
    SPRING_SCALE = re.compile(
        r"spring\s*\(\s*\{[^}]*frame[^}]*\}\s*\)",
        re.IGNORECASE | re.DOTALL
    )

    # Counter/number animation: Math.round(interpolate(...))
    COUNTER_ANIMATION = re.compile(
        r"Math\.(?:round|floor|ceil)\s*\(\s*interpolate\s*\(\s*(?:local)?[fF]rame\s*,\s*\[(\d+)\s*,\s*(\d+)\]",
        re.IGNORECASE
    )

    # Width interpolation (for bars/charts): width: interpolate(...)
    WIDTH_INTERPOLATE = re.compile(
        r"width:\s*(?:interpolate|`\$\{interpolate)\s*\(\s*(?:local)?[fF]rame\s*,\s*\[(\d+)\s*,\s*(\d+)\]",
        re.IGNORECASE
    )

    # Height interpolation
    HEIGHT_INTERPOLATE = re.compile(
        r"height:\s*(?:interpolate|`\$\{interpolate)\s*\(\s*(?:local)?[fF]rame\s*,\s*\[(\d+)\s*,\s*(\d+)\]",
        re.IGNORECASE
    )

    # Phase transition: localFrame > phaseStart or frame > PHASE_X_START
    PHASE_TRANSITION = re.compile(
        r"(?:local)?[fF]rame\s*(?:>|>=)\s*(?:phase\d*Start|PHASE_\w+_START|(\d+))",
        re.IGNORECASE
    )

    # Scale interpolation
    SCALE_INTERPOLATE = re.compile(
        r"(?:scale|transform:\s*`scale\()\s*(?:interpolate|`\$\{interpolate)?\s*\(\s*(?:local)?[fF]rame\s*,\s*\[(\d+)\s*,\s*(\d+)\]",
        re.IGNORECASE
    )

    # BoxShadow/glow animation
    GLOW_ANIMATION = re.compile(
        r"boxShadow:\s*(?:`|').*(?:interpolate|rgb|rgba)",
        re.IGNORECASE
    )

    # TranslateX/Y animations
    TRANSLATE_ANIMATION = re.compile(
        r"translate[XY]:\s*interpolate\s*\(\s*(?:local)?[fF]rame\s*,\s*\[(\d+)\s*,\s*(\d+)\]",
        re.IGNORECASE
    )

    # Constant definitions: const PHASE_X_START = N
    CONST_DEFINITION = re.compile(
        r"const\s+(\w+)\s*=\s*(\d+)",
        re.IGNORECASE
    )

    # Variable frame ranges in array form
    FRAME_RANGE_VARS = re.compile(
        r"\[(\w+)(?:Start)?\s*,\s*(\w+)(?:End)?\]",
        re.IGNORECASE
    )

    def __init__(self, fps: int = 30):
        """Initialize the analyzer.

        Args:
            fps: Frames per second (default 30)
        """
        self.fps = fps

    def analyze_scene(self, scene_path: Path) -> SceneAnalysisResult:
        """Analyze a TSX scene file for animation patterns.

        Args:
            scene_path: Path to the TSX file

        Returns:
            SceneAnalysisResult with detected moments
        """
        if not scene_path.exists():
            raise FileNotFoundError(f"Scene file not found: {scene_path}")

        code = scene_path.read_text()

        # Extract scene info from path
        scene_id = scene_path.stem
        scene_type = self._extract_scene_type(scene_path)

        # Estimate duration from code constants
        duration_frames = self._estimate_duration(code)

        result = SceneAnalysisResult(
            scene_id=scene_id,
            scene_type=scene_type,
            duration_frames=duration_frames,
            source_file=str(scene_path),
        )

        # Parse constants for resolving variable frame references
        constants = self._parse_constants(code)

        # Detect various animation patterns
        self._detect_opacity_fades(code, result, constants)
        self._detect_counter_animations(code, result, constants)
        self._detect_chart_animations(code, result, constants)
        self._detect_phase_transitions(code, result, constants)
        self._detect_spring_animations(code, result)
        self._detect_scale_animations(code, result, constants)
        self._detect_glow_animations(code, result)

        # Sort moments by frame
        result.moments.sort(key=lambda m: m.frame)

        return result

    def _extract_scene_type(self, path: Path) -> str:
        """Extract scene type from file path."""
        # Assume structure like: remotion/src/scenes/<project>/<scene>.tsx
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

    def _estimate_duration(self, code: str) -> int:
        """Estimate scene duration from code constants."""
        # Look for total duration or phase end constants
        duration_patterns = [
            r"const\s+(?:TOTAL_)?DURATION\s*=\s*(\d+)",
            r"durationInFrames\s*[=:]\s*(\d+)",
            r"const\s+SCENE_DURATION\s*=\s*(\d+)",
        ]

        for pattern in duration_patterns:
            match = re.search(pattern, code, re.IGNORECASE)
            if match:
                return int(match.group(1))

        # Default to 10 seconds if not found
        return 10 * self.fps

    def _parse_constants(self, code: str) -> dict[str, int]:
        """Parse constant definitions from code."""
        constants = {}
        for match in self.CONST_DEFINITION.finditer(code):
            name = match.group(1)
            value = int(match.group(2))
            constants[name] = value
        return constants

    def _resolve_frame(self, value: str, constants: dict[str, int]) -> Optional[int]:
        """Resolve a frame value that might be a constant name."""
        # Direct number
        if value.isdigit():
            return int(value)

        # Constant reference
        if value in constants:
            return constants[value]

        # Try common suffixes
        for suffix in ["Start", "End", "_START", "_END"]:
            if value + suffix in constants:
                return constants[value + suffix]

        return None

    def _detect_opacity_fades(
        self, code: str, result: SceneAnalysisResult, constants: dict[str, int]
    ) -> None:
        """Detect opacity interpolation patterns."""
        # Fade in
        for match in self.OPACITY_FADE_IN.finditer(code):
            frame_start = int(match.group(1))
            result.add_moment(SoundMoment(
                type="element_appear",
                frame=frame_start,
                confidence=0.9,
                context="Opacity fade in detected",
                intensity=0.7,
                source="code",
            ))

        # Fade out
        for match in self.OPACITY_FADE_OUT.finditer(code):
            frame_start = int(match.group(1))
            result.add_moment(SoundMoment(
                type="element_disappear",
                frame=frame_start,
                confidence=0.8,
                context="Opacity fade out detected",
                intensity=0.5,
                source="code",
            ))

        # Generic opacity (analyze direction)
        for match in self.OPACITY_GENERIC.finditer(code):
            frame_range = match.group(1)
            opacity_range = match.group(2)

            # Parse frame range
            frames = [f.strip() for f in frame_range.split(",")]
            if len(frames) >= 2:
                start_frame = self._resolve_frame(frames[0], constants)
                if start_frame is not None:
                    # Check if fading in or out
                    opacities = [o.strip() for o in opacity_range.split(",")]
                    if len(opacities) >= 2:
                        try:
                            start_opacity = float(opacities[0])
                            end_opacity = float(opacities[-1])

                            if start_opacity < end_opacity:
                                moment_type = "element_appear"
                                confidence = 0.85
                            else:
                                moment_type = "element_disappear"
                                confidence = 0.75

                            result.add_moment(SoundMoment(
                                type=moment_type,
                                frame=start_frame,
                                confidence=confidence,
                                context=f"Opacity change from {start_opacity} to {end_opacity}",
                                intensity=0.7 if moment_type == "element_appear" else 0.5,
                                source="code",
                            ))
                        except ValueError:
                            pass

    def _detect_counter_animations(
        self, code: str, result: SceneAnalysisResult, constants: dict[str, int]
    ) -> None:
        """Detect number counter animations."""
        for match in self.COUNTER_ANIMATION.finditer(code):
            frame_start = int(match.group(1))
            frame_end = int(match.group(2))

            result.add_moment(SoundMoment(
                type="counter",
                frame=frame_start,
                confidence=0.95,
                context="Number counter animation",
                intensity=0.8,
                source="code",
                duration_frames=frame_end - frame_start,
            ))

    def _detect_chart_animations(
        self, code: str, result: SceneAnalysisResult, constants: dict[str, int]
    ) -> None:
        """Detect chart/bar width/height animations."""
        for match in self.WIDTH_INTERPOLATE.finditer(code):
            frame_start = int(match.group(1))
            result.add_moment(SoundMoment(
                type="chart_grow",
                frame=frame_start,
                confidence=0.85,
                context="Width animation (bar/chart growth)",
                intensity=0.7,
                source="code",
            ))

        for match in self.HEIGHT_INTERPOLATE.finditer(code):
            frame_start = int(match.group(1))
            result.add_moment(SoundMoment(
                type="chart_grow",
                frame=frame_start,
                confidence=0.85,
                context="Height animation (bar/chart growth)",
                intensity=0.7,
                source="code",
            ))

    def _detect_phase_transitions(
        self, code: str, result: SceneAnalysisResult, constants: dict[str, int]
    ) -> None:
        """Detect phase/section transitions."""
        # Look for phase start constants
        phase_constants = {
            name: value
            for name, value in constants.items()
            if "PHASE" in name.upper() or "START" in name.upper()
        }

        # Add moments for each phase start
        seen_frames: set[int] = set()
        for name, frame in sorted(phase_constants.items(), key=lambda x: x[1]):
            # Skip if this frame is too close to one we've seen
            if any(abs(frame - f) < 15 for f in seen_frames):
                continue

            seen_frames.add(frame)
            result.add_moment(SoundMoment(
                type="transition",
                frame=frame,
                confidence=0.8,
                context=f"Phase transition: {name}",
                intensity=0.7,
                source="code",
            ))

    def _detect_spring_animations(self, code: str, result: SceneAnalysisResult) -> None:
        """Detect spring() animations."""
        # Spring animations are often used for pop-in effects
        # Look for spring with scale transform

        spring_with_scale = re.finditer(
            r"spring\s*\(\s*\{[^}]*frame:\s*(?:local)?[fF]rame\s*-?\s*(\d+)?",
            code,
            re.IGNORECASE | re.DOTALL
        )

        for match in spring_with_scale:
            frame_offset = match.group(1)
            frame = int(frame_offset) if frame_offset else 0

            result.add_moment(SoundMoment(
                type="element_appear",
                frame=frame,
                confidence=0.85,
                context="Spring animation (pop-in effect)",
                intensity=0.8,
                source="code",
            ))

    def _detect_scale_animations(
        self, code: str, result: SceneAnalysisResult, constants: dict[str, int]
    ) -> None:
        """Detect scale interpolations."""
        for match in self.SCALE_INTERPOLATE.finditer(code):
            frame_start = int(match.group(1))
            result.add_moment(SoundMoment(
                type="element_appear",
                frame=frame_start,
                confidence=0.8,
                context="Scale animation",
                intensity=0.75,
                source="code",
            ))

    def _detect_glow_animations(self, code: str, result: SceneAnalysisResult) -> None:
        """Detect glow/highlight box-shadow animations."""
        for match in self.GLOW_ANIMATION.finditer(code):
            # Extract approximate frame from nearby code context
            start = max(0, match.start() - 200)
            context = code[start:match.start()]

            # Look for nearby frame references
            frame_match = re.search(r"(?:local)?[fF]rame\s*[><=]+\s*(\d+)", context)
            if frame_match:
                frame = int(frame_match.group(1))
                result.add_moment(SoundMoment(
                    type="highlight",
                    frame=frame,
                    confidence=0.7,
                    context="Glow/highlight animation",
                    intensity=0.6,
                    source="code",
                ))


def analyze_scene(scene_path: Path, fps: int = 30) -> SceneAnalysisResult:
    """Analyze a TSX scene file for animation patterns.

    Convenience function that creates an analyzer and runs analysis.

    Args:
        scene_path: Path to the TSX file
        fps: Frames per second (default 30)

    Returns:
        SceneAnalysisResult with detected moments
    """
    analyzer = SceneAnalyzer(fps=fps)
    return analyzer.analyze_scene(scene_path)


def find_scene_files(project_dir: Path, project_id: str) -> list[Path]:
    """Find all scene TSX files for a project.

    Args:
        project_dir: Path to the project root
        project_id: Project identifier

    Returns:
        List of paths to scene TSX files
    """
    # Look in remotion/src/scenes/<project_id>/
    scenes_dir = project_dir.parent.parent / "remotion" / "src" / "scenes" / project_id

    if not scenes_dir.exists():
        return []

    # Find all TSX files except index files
    scene_files = [
        f for f in scenes_dir.glob("*.tsx")
        if f.stem not in ("index", "Index", "_index")
    ]

    return sorted(scene_files)

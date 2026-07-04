"""Tests for TypeScript AST Analyzer.

These tests verify that the Python wrapper correctly:
1. Invokes the Node.js extraction script
2. Parses JSON output into Python objects
3. Handles errors and edge cases gracefully
4. Falls back appropriately when AST analysis fails
"""

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from .ts_analyzer import (
    TypeScriptAnalyzer,
    ExtractedAnimation,
    AnimationContext,
    analyze_scene_with_ast,
)
from .models import SceneAnalysisResult, SoundMoment


class TestAnimationContext:
    """Tests for AnimationContext dataclass."""

    def test_create_with_defaults(self):
        """Test creating context with only required fields."""
        ctx = AnimationContext(component_hint="test")

        assert ctx.component_hint == "test"
        assert ctx.variable_name is None
        assert ctx.line_number == 0
        assert ctx.nearby_text is None
        assert ctx.property_path is None

    def test_create_with_all_fields(self):
        """Test creating context with all fields."""
        ctx = AnimationContext(
            component_hint="barWidth",
            variable_name="slowBarWidth",
            line_number=42,
            nearby_text="bar",
            property_path="width",
        )

        assert ctx.component_hint == "barWidth"
        assert ctx.variable_name == "slowBarWidth"
        assert ctx.line_number == 42
        assert ctx.nearby_text == "bar"
        assert ctx.property_path == "width"


class TestExtractedAnimation:
    """Tests for ExtractedAnimation dataclass."""

    def test_create_interpolate_animation(self):
        """Test creating an interpolate animation."""
        ctx = AnimationContext(component_hint="opacity")
        anim = ExtractedAnimation(
            type="interpolate",
            property="opacity",
            frame_start=0,
            frame_end=30,
            from_value=0.0,
            to_value=1.0,
            context=ctx,
        )

        assert anim.type == "interpolate"
        assert anim.property == "opacity"
        assert anim.frame_start == 0
        assert anim.frame_end == 30
        assert anim.from_value == 0.0
        assert anim.to_value == 1.0

    def test_create_spring_animation(self):
        """Test creating a spring animation (no frame_end)."""
        ctx = AnimationContext(component_hint="scale")
        anim = ExtractedAnimation(
            type="spring",
            property="scale",
            frame_start=50,
            frame_end=None,
            from_value=0.0,
            to_value=1.0,
            context=ctx,
        )

        assert anim.type == "spring"
        assert anim.frame_end is None

    def test_create_counter_animation(self):
        """Test creating a counter animation with large value range."""
        ctx = AnimationContext(
            component_hint="speedCounter",
            nearby_text="speed",
        )
        anim = ExtractedAnimation(
            type="counter",
            property="value",
            frame_start=60,
            frame_end=200,
            from_value=0,
            to_value=3500,
            context=ctx,
        )

        assert anim.type == "counter"
        assert anim.from_value == 0
        assert anim.to_value == 3500


class TestTypeScriptAnalyzer:
    """Tests for TypeScriptAnalyzer class."""

    def test_init_default(self):
        """Test default initialization."""
        analyzer = TypeScriptAnalyzer()

        assert analyzer.fps == 30
        assert analyzer._remotion_dir is None

    def test_init_custom_fps(self):
        """Test initialization with custom fps."""
        analyzer = TypeScriptAnalyzer(fps=60)

        assert analyzer.fps == 60

    def test_init_custom_remotion_dir(self):
        """Test initialization with custom remotion dir."""
        analyzer = TypeScriptAnalyzer(remotion_dir=Path("/custom/path"))

        assert analyzer._remotion_dir == Path("/custom/path")

    def test_extract_scene_type_with_project_path(self):
        """Test scene type extraction from file path."""
        analyzer = TypeScriptAnalyzer()

        # Test with typical scene path
        path = Path("/project/remotion/src/scenes/llm-inference/HookScene.tsx")
        scene_type = analyzer._extract_scene_type(path)

        assert scene_type == "llm-inference/HookScene"

    def test_extract_scene_type_without_scenes_dir(self):
        """Test scene type extraction when scenes dir not in path."""
        analyzer = TypeScriptAnalyzer()

        path = Path("/project/components/MyComponent.tsx")
        scene_type = analyzer._extract_scene_type(path)

        assert scene_type == "MyComponent"

    def test_determine_moment_type_counter(self):
        """Test moment type determination for counters."""
        analyzer = TypeScriptAnalyzer()

        ctx = AnimationContext(
            component_hint="speedCounter",
            nearby_text="speed",
        )
        anim = ExtractedAnimation(
            type="counter",
            property="value",
            frame_start=0,
            frame_end=100,
            from_value=0,
            to_value=100,
            context=ctx,
        )

        moment_type = analyzer._determine_moment_type(anim)
        assert moment_type == "counter"

    def test_determine_moment_type_chart_grow(self):
        """Test moment type determination for chart growth."""
        analyzer = TypeScriptAnalyzer()

        ctx = AnimationContext(
            component_hint="barWidth",
            property_path="width",
        )
        anim = ExtractedAnimation(
            type="width",
            property="width",
            frame_start=0,
            frame_end=50,
            from_value=0,
            to_value=100,
            context=ctx,
        )

        moment_type = analyzer._determine_moment_type(anim)
        assert moment_type == "chart_grow"

    def test_determine_moment_type_reveal(self):
        """Test moment type determination for reveals."""
        analyzer = TypeScriptAnalyzer()

        ctx = AnimationContext(
            component_hint="badge",
            nearby_text="reveal",
        )
        anim = ExtractedAnimation(
            type="spring",
            property="scale",
            frame_start=200,
            frame_end=None,
            from_value=0,
            to_value=1,
            context=ctx,
        )

        moment_type = analyzer._determine_moment_type(anim)
        assert moment_type == "reveal"

    def test_determine_moment_type_opacity_appear(self):
        """Test moment type determination for opacity fade in."""
        analyzer = TypeScriptAnalyzer()

        ctx = AnimationContext(component_hint="title")
        anim = ExtractedAnimation(
            type="opacity",
            property="opacity",
            frame_start=0,
            frame_end=30,
            from_value=0,
            to_value=1,
            context=ctx,
        )

        moment_type = analyzer._determine_moment_type(anim)
        assert moment_type == "element_appear"

    def test_determine_moment_type_opacity_disappear(self):
        """Test moment type determination for opacity fade out."""
        analyzer = TypeScriptAnalyzer()

        ctx = AnimationContext(component_hint="element")
        anim = ExtractedAnimation(
            type="opacity",
            property="opacity",
            frame_start=100,
            frame_end=130,
            from_value=1,
            to_value=0,
            context=ctx,
        )

        moment_type = analyzer._determine_moment_type(anim)
        assert moment_type == "element_disappear"

    def test_calculate_intensity_large_value_range(self):
        """Test intensity calculation for large value changes."""
        analyzer = TypeScriptAnalyzer()

        ctx = AnimationContext(component_hint="counter")
        anim = ExtractedAnimation(
            type="counter",
            property="value",
            frame_start=0,
            frame_end=100,
            from_value=0,
            to_value=3500,  # Large range
            context=ctx,
        )

        intensity = analyzer._calculate_intensity(anim, 500)
        assert intensity > 0.8  # Should be high for large range

    def test_calculate_intensity_reveal_context(self):
        """Test intensity calculation for reveal keywords."""
        analyzer = TypeScriptAnalyzer()

        ctx = AnimationContext(
            component_hint="badge",
            nearby_text="87x",  # Reveal keyword
        )
        anim = ExtractedAnimation(
            type="spring",
            property="scale",
            frame_start=200,
            frame_end=None,
            from_value=0,
            to_value=1,
            context=ctx,
        )

        intensity = analyzer._calculate_intensity(anim, 500)
        assert intensity >= 0.9  # Should be high for reveal

    def test_calculate_intensity_late_position(self):
        """Test intensity boost for late scene position."""
        analyzer = TypeScriptAnalyzer()

        ctx = AnimationContext(component_hint="element")
        anim = ExtractedAnimation(
            type="opacity",
            property="opacity",
            frame_start=400,  # Late in 500 frame scene
            frame_end=450,
            from_value=0,
            to_value=1,
            context=ctx,
        )

        intensity = analyzer._calculate_intensity(anim, 500)
        assert intensity > 0.7  # Should be boosted

    def test_calculate_confidence_high_for_counter(self):
        """Test high confidence for counter animations."""
        analyzer = TypeScriptAnalyzer()

        ctx = AnimationContext(component_hint="counter")
        anim = ExtractedAnimation(
            type="counter",
            property="value",
            frame_start=0,
            frame_end=100,
            from_value=0,
            to_value=100,
            context=ctx,
        )

        confidence = analyzer._calculate_confidence(anim)
        assert confidence >= 0.95

    def test_calculate_confidence_with_context(self):
        """Test confidence boost with good context."""
        analyzer = TypeScriptAnalyzer()

        ctx = AnimationContext(
            component_hint="barWidth",  # Good hint
            nearby_text="bar",  # Good nearby text
        )
        anim = ExtractedAnimation(
            type="width",
            property="width",
            frame_start=0,
            frame_end=50,
            from_value=0,
            to_value=100,
            context=ctx,
        )

        confidence = analyzer._calculate_confidence(anim)
        assert confidence >= 0.9

    def test_animation_to_moments_basic(self):
        """Test conversion of animation to SoundMoments."""
        analyzer = TypeScriptAnalyzer()

        ctx = AnimationContext(
            component_hint="title",
            nearby_text="title",
        )
        anim = ExtractedAnimation(
            type="opacity",
            property="opacity",
            frame_start=0,
            frame_end=30,
            from_value=0,
            to_value=1,
            context=ctx,
        )

        moments = analyzer._animation_to_moments(anim, 300)

        assert len(moments) >= 1
        assert moments[0].frame == 0
        assert moments[0].type == "element_appear"
        assert "title" in moments[0].context.lower()

    def test_animation_to_moments_with_duration(self):
        """Test that duration is preserved in moments."""
        analyzer = TypeScriptAnalyzer()

        ctx = AnimationContext(component_hint="counter")
        anim = ExtractedAnimation(
            type="counter",
            property="value",
            frame_start=50,
            frame_end=200,
            from_value=0,
            to_value=100,
            context=ctx,
        )

        moments = analyzer._animation_to_moments(anim, 300)

        assert len(moments) >= 1
        assert moments[0].duration_frames == 150  # 200 - 50

    @patch("subprocess.run")
    def test_run_extraction_success(self, mock_run):
        """Test successful extraction via subprocess."""
        analyzer = TypeScriptAnalyzer()
        analyzer._script_path = Path("/fake/script.ts")
        analyzer._remotion_dir = Path("/fake/remotion")

        mock_output = {
            "sceneId": "TestScene",
            "durationFrames": 300,
            "animations": [
                {
                    "type": "opacity",
                    "property": "opacity",
                    "frameStart": 0,
                    "frameEnd": 30,
                    "fromValue": 0,
                    "toValue": 1,
                    "context": {
                        "componentHint": "title",
                        "lineNumber": 10,
                    },
                }
            ],
            "phases": {},
            "errors": [],
        }

        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_output),
            stderr="",
        )

        # Create a temp file to avoid mocking Path.exists
        with tempfile.NamedTemporaryFile(suffix=".tsx", delete=False) as f:
            f.write(b"// test scene")
            scene_path = Path(f.name)

        try:
            animations = analyzer._run_extraction(scene_path, 300)

            assert len(animations) == 1
            assert animations[0].type == "opacity"
            assert animations[0].frame_start == 0
        finally:
            scene_path.unlink()

    @patch("subprocess.run")
    def test_run_extraction_timeout(self, mock_run):
        """Test extraction timeout handling."""
        analyzer = TypeScriptAnalyzer()
        analyzer._script_path = Path("/fake/script.ts")
        analyzer._remotion_dir = Path("/fake/remotion")

        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)

        with pytest.raises(RuntimeError, match="timed out"):
            analyzer._run_extraction(Path("/fake/scene.tsx"), 300)

    @patch("subprocess.run")
    def test_run_extraction_node_not_found(self, mock_run):
        """Test handling when Node.js is not found."""
        analyzer = TypeScriptAnalyzer()
        analyzer._script_path = Path("/fake/script.ts")
        analyzer._remotion_dir = Path("/fake/remotion")

        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(RuntimeError, match="Node.js"):
            analyzer._run_extraction(Path("/fake/scene.tsx"), 300)

    @patch("subprocess.run")
    def test_run_extraction_script_error(self, mock_run):
        """Test handling of script execution errors."""
        analyzer = TypeScriptAnalyzer()
        analyzer._script_path = Path("/fake/script.ts")
        analyzer._remotion_dir = Path("/fake/remotion")

        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Script error: something went wrong",
        )

        with pytest.raises(RuntimeError, match="failed"):
            analyzer._run_extraction(Path("/fake/scene.tsx"), 300)

    def test_analyze_scene_file_not_found(self):
        """Test error when scene file doesn't exist."""
        analyzer = TypeScriptAnalyzer()

        with pytest.raises(FileNotFoundError):
            analyzer.analyze_scene(Path("/nonexistent/scene.tsx"), 300)


class TestAnalyzeSceneWithAst:
    """Tests for the convenience function."""

    @patch.object(TypeScriptAnalyzer, "analyze_scene")
    def test_convenience_function(self, mock_analyze):
        """Test that convenience function creates analyzer correctly."""
        mock_result = SceneAnalysisResult(
            scene_id="test",
            scene_type="test",
            duration_frames=300,
        )
        mock_analyze.return_value = mock_result

        with tempfile.NamedTemporaryFile(suffix=".tsx", delete=False) as f:
            f.write(b"// test")
            scene_path = Path(f.name)

        try:
            result = analyze_scene_with_ast(scene_path, 300, fps=30)
            assert result == mock_result
        finally:
            scene_path.unlink()


class TestBuildResult:
    """Tests for result building."""

    def test_build_result_sorts_moments(self):
        """Test that moments are sorted by frame."""
        analyzer = TypeScriptAnalyzer()

        animations = [
            ExtractedAnimation(
                type="opacity",
                property="opacity",
                frame_start=100,
                frame_end=130,
                from_value=0,
                to_value=1,
                context=AnimationContext(component_hint="late"),
            ),
            ExtractedAnimation(
                type="opacity",
                property="opacity",
                frame_start=0,
                frame_end=30,
                from_value=0,
                to_value=1,
                context=AnimationContext(component_hint="early"),
            ),
            ExtractedAnimation(
                type="opacity",
                property="opacity",
                frame_start=50,
                frame_end=80,
                from_value=0,
                to_value=1,
                context=AnimationContext(component_hint="middle"),
            ),
        ]

        with tempfile.NamedTemporaryFile(suffix=".tsx", delete=False) as f:
            f.write(b"// test")
            scene_path = Path(f.name)

        try:
            result = analyzer._build_result(scene_path, 300, animations)

            # Verify moments are sorted
            frames = [m.frame for m in result.moments]
            assert frames == sorted(frames)
        finally:
            scene_path.unlink()

    def test_build_result_includes_metadata(self):
        """Test that result includes proper metadata."""
        analyzer = TypeScriptAnalyzer()

        animations = [
            ExtractedAnimation(
                type="opacity",
                property="opacity",
                frame_start=0,
                frame_end=30,
                from_value=0,
                to_value=1,
                context=AnimationContext(component_hint="test"),
            ),
        ]

        with tempfile.NamedTemporaryFile(suffix=".tsx", delete=False) as f:
            f.write(b"// test")
            scene_path = Path(f.name)

        try:
            result = analyzer._build_result(scene_path, 300, animations)

            assert result.scene_id == scene_path.stem
            assert result.duration_frames == 300
            assert result.source_file == str(scene_path)
        finally:
            scene_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

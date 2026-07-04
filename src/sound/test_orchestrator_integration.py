"""Integration tests for SFX Orchestrator with new analyzers.

These tests verify that the orchestrator correctly:
1. Integrates TypeScript AST analyzer with fallback
2. Applies semantic sound mapping
3. Handles various scene types and configurations
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from .sfx_orchestrator import (
    SFXOrchestrator,
    SFXGenerationResult,
    generate_project_sfx,
    analyze_project_scenes,
)
from .models import SoundMoment, SceneAnalysisResult, SFXCue
from .ts_analyzer import TypeScriptAnalyzer, ExtractedAnimation, AnimationContext
from .semantic_mapper import SemanticSoundMapper
from .scene_analyzer import SceneAnalyzer


class TestSFXOrchestratorInit:
    """Tests for orchestrator initialization."""

    def test_init_default(self):
        """Test default initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            orchestrator = SFXOrchestrator(project_dir)

            assert orchestrator.fps == 30
            assert orchestrator.use_library is True
            assert orchestrator.use_ast_analyzer is True
            assert orchestrator.ts_analyzer is not None
            assert orchestrator.regex_analyzer is not None
            assert orchestrator.semantic_mapper is not None

    def test_init_without_ast_analyzer(self):
        """Test initialization without AST analyzer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            orchestrator = SFXOrchestrator(project_dir, use_ast_analyzer=False)

            assert orchestrator.ts_analyzer is None
            assert orchestrator.regex_analyzer is not None

    def test_init_custom_fps(self):
        """Test initialization with custom fps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)

            orchestrator = SFXOrchestrator(project_dir, fps=60)

            assert orchestrator.fps == 60


class TestAnalyzeSceneFile:
    """Tests for _analyze_scene_file method."""

    def create_mock_ts_result(self, scene_id: str, moments: list) -> SceneAnalysisResult:
        """Create a mock TypeScript analyzer result."""
        result = SceneAnalysisResult(
            scene_id=scene_id,
            scene_type=f"test/{scene_id}",
            duration_frames=300,
        )
        for moment in moments:
            result.add_moment(moment)
        return result

    def test_uses_ast_analyzer_first(self):
        """Test that AST analyzer is tried first."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            orchestrator = SFXOrchestrator(project_dir)

            # Create a test scene file
            scene_file = Path(tmpdir) / "TestScene.tsx"
            scene_file.write_text("// test scene")

            # Mock the TS analyzer
            mock_moments = [
                SoundMoment(
                    type="element_appear",
                    frame=0,
                    confidence=0.9,
                    context="title fade in",
                    intensity=0.7,
                )
            ]
            mock_result = self.create_mock_ts_result("TestScene", mock_moments)

            with patch.object(orchestrator.ts_analyzer, "analyze_scene", return_value=mock_result):
                result = orchestrator._analyze_scene_file(
                    scene_file, "test-scene", "test/scene", 300
                )

            assert len(result.moments) == 1
            assert "TypeScript AST" in " ".join(result.analysis_notes)

    def test_falls_back_to_regex_on_ast_failure(self):
        """Test fallback to regex when AST analyzer fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            orchestrator = SFXOrchestrator(project_dir)

            # Create a test scene file
            scene_file = Path(tmpdir) / "TestScene.tsx"
            scene_file.write_text("// test scene with opacity: interpolate(frame, [0, 30], [0, 1])")

            # Mock TS analyzer to fail
            with patch.object(orchestrator.ts_analyzer, "analyze_scene", side_effect=RuntimeError("AST failed")):
                # Mock regex analyzer to succeed
                regex_result = SceneAnalysisResult(
                    scene_id="TestScene",
                    scene_type="test/TestScene",
                    duration_frames=300,
                )
                regex_result.add_moment(SoundMoment(
                    type="element_appear",
                    frame=0,
                    confidence=0.85,
                    context="regex detected",
                    intensity=0.7,
                ))

                with patch.object(orchestrator.regex_analyzer, "analyze_scene", return_value=regex_result):
                    result = orchestrator._analyze_scene_file(
                        scene_file, "test-scene", "test/scene", 300
                    )

            assert len(result.moments) == 1
            # Should mention fallback
            notes_text = " ".join(result.analysis_notes)
            assert "falling back" in notes_text.lower() or "regex" in notes_text.lower()

    def test_applies_semantic_mapping(self):
        """Test that semantic mapping is applied to moments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            orchestrator = SFXOrchestrator(project_dir)

            # Create test scene file
            scene_file = Path(tmpdir) / "TestScene.tsx"
            scene_file.write_text("// test")

            # Create moments that should get specific sound mappings
            mock_moments = [
                SoundMoment(
                    type="element_appear",
                    frame=0,
                    confidence=0.9,
                    context="prompt typing animation",
                    intensity=0.7,
                ),
                SoundMoment(
                    type="counter",
                    frame=50,
                    confidence=0.95,
                    context="speed counter animation",
                    intensity=0.8,
                ),
            ]
            mock_result = self.create_mock_ts_result("TestScene", mock_moments)

            with patch.object(orchestrator.ts_analyzer, "analyze_scene", return_value=mock_result):
                result = orchestrator._analyze_scene_file(
                    scene_file, "test-scene", "test/scene", 300
                )

            # Check that mapping info is added to context
            assert any("[mapped:" in m.context for m in result.moments)


class TestAnalyzeScenes:
    """Tests for analyze_scenes method."""

    def create_test_project(self, tmpdir: str) -> tuple[Path, Path]:
        """Create a test project structure."""
        project_dir = Path(tmpdir) / "test-project"
        project_dir.mkdir()

        # Create storyboard
        storyboard_dir = project_dir / "storyboard"
        storyboard_dir.mkdir()

        storyboard = {
            "project": "test-project",
            "scenes": [
                {
                    "id": "scene-1",
                    "type": "test/hook",
                    "audio_duration_seconds": 10.0,
                },
                {
                    "id": "scene-2",
                    "type": "test/main",
                    "audio_duration_seconds": 15.0,
                },
            ],
        }

        storyboard_path = storyboard_dir / "storyboard.json"
        storyboard_path.write_text(json.dumps(storyboard))

        # Create scenes directory
        scenes_dir = project_dir / "scenes"
        scenes_dir.mkdir()

        # Create scene files
        (scenes_dir / "HookScene.tsx").write_text("// hook scene")
        (scenes_dir / "MainScene.tsx").write_text("// main scene")

        return project_dir, storyboard_path

    def test_analyze_all_scenes(self):
        """Test analyzing all scenes from storyboard."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir, storyboard_path = self.create_test_project(tmpdir)

            orchestrator = SFXOrchestrator(project_dir, use_ast_analyzer=False)

            # Mock regex analyzer to return simple results
            def mock_analyze(scene_file):
                result = SceneAnalysisResult(
                    scene_id=scene_file.stem,
                    scene_type="test",
                    duration_frames=300,
                )
                result.add_moment(SoundMoment(
                    type="element_appear",
                    frame=0,
                    confidence=0.8,
                    context="test moment",
                    intensity=0.7,
                ))
                return result

            with patch.object(orchestrator.regex_analyzer, "analyze_scene", side_effect=mock_analyze):
                results = orchestrator.analyze_scenes()

            assert len(results) == 2
            assert "scene-1" in results
            assert "scene-2" in results

    def test_analyze_filtered_scenes(self):
        """Test analyzing specific scene types only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir, storyboard_path = self.create_test_project(tmpdir)

            orchestrator = SFXOrchestrator(project_dir, use_ast_analyzer=False)

            def mock_analyze(scene_file):
                return SceneAnalysisResult(
                    scene_id=scene_file.stem,
                    scene_type="test",
                    duration_frames=300,
                )

            with patch.object(orchestrator.regex_analyzer, "analyze_scene", side_effect=mock_analyze):
                results = orchestrator.analyze_scenes(scene_types=["test/hook"])

            assert len(results) == 1
            assert "scene-1" in results


class TestGenerateSFXCues:
    """Tests for generate_sfx_cues method."""

    def create_test_project_with_storyboard(self, tmpdir: str) -> Path:
        """Create a minimal test project."""
        project_dir = Path(tmpdir) / "test-project"
        project_dir.mkdir()

        storyboard_dir = project_dir / "storyboard"
        storyboard_dir.mkdir()

        storyboard = {
            "project": "test-project",
            "scenes": [
                {
                    "id": "hook",
                    "type": "test/hook",
                    "audio_duration_seconds": 10.0,
                },
            ],
        }

        (storyboard_dir / "storyboard.json").write_text(json.dumps(storyboard))

        scenes_dir = project_dir / "scenes"
        scenes_dir.mkdir()
        (scenes_dir / "HookScene.tsx").write_text("// test")

        return project_dir

    def test_dry_run_does_not_modify(self):
        """Test that dry run doesn't modify storyboard."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self.create_test_project_with_storyboard(tmpdir)

            orchestrator = SFXOrchestrator(project_dir, use_ast_analyzer=False)

            # Mock analyzer
            def mock_analyze(scene_file):
                result = SceneAnalysisResult(
                    scene_id="hook",
                    scene_type="test/hook",
                    duration_frames=300,
                )
                result.add_moment(SoundMoment(
                    type="element_appear",
                    frame=0,
                    confidence=0.9,
                    context="test",
                    intensity=0.7,
                ))
                return result

            with patch.object(orchestrator.regex_analyzer, "analyze_scene", side_effect=mock_analyze):
                result = orchestrator.generate_sfx_cues(dry_run=True)

            assert result.cues_generated > 0
            assert len(result.scenes_updated) == 0  # Dry run doesn't update

    def test_returns_generation_result(self):
        """Test that generation returns proper result object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self.create_test_project_with_storyboard(tmpdir)

            orchestrator = SFXOrchestrator(project_dir, use_ast_analyzer=False)

            def mock_analyze(scene_file):
                result = SceneAnalysisResult(
                    scene_id="hook",
                    scene_type="test/hook",
                    duration_frames=300,
                )
                return result

            with patch.object(orchestrator.regex_analyzer, "analyze_scene", side_effect=mock_analyze):
                result = orchestrator.generate_sfx_cues(dry_run=True)

            assert isinstance(result, SFXGenerationResult)
            assert result.project_id == "test-project"
            assert result.scenes_analyzed >= 1


class TestSFXGenerationResult:
    """Tests for SFXGenerationResult dataclass."""

    def test_success_with_no_errors(self):
        """Test success property with no errors."""
        result = SFXGenerationResult(
            project_id="test",
            scenes_analyzed=2,
            moments_detected=10,
            cues_generated=8,
            scenes_updated={"scene-1": True, "scene-2": True},
            errors=[],
        )

        assert result.success is True

    def test_failure_with_errors(self):
        """Test success property with errors."""
        result = SFXGenerationResult(
            project_id="test",
            scenes_analyzed=2,
            moments_detected=10,
            cues_generated=8,
            scenes_updated={"scene-1": True, "scene-2": True},
            errors=["Something went wrong"],
        )

        assert result.success is False

    def test_failure_with_failed_scene(self):
        """Test success property with failed scene update."""
        result = SFXGenerationResult(
            project_id="test",
            scenes_analyzed=2,
            moments_detected=10,
            cues_generated=8,
            scenes_updated={"scene-1": True, "scene-2": False},
            errors=[],
        )

        assert result.success is False


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_generate_project_sfx_creates_orchestrator(self):
        """Test that generate_project_sfx creates and uses orchestrator."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test-project"
            project_dir.mkdir()

            # Create minimal storyboard
            storyboard_dir = project_dir / "storyboard"
            storyboard_dir.mkdir()

            storyboard = {"project": "test", "scenes": []}
            (storyboard_dir / "storyboard.json").write_text(json.dumps(storyboard))

            result = generate_project_sfx(project_dir, dry_run=True)

            assert isinstance(result, SFXGenerationResult)

    def test_analyze_project_scenes_returns_preview(self):
        """Test that analyze_project_scenes returns preview dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "test-project"
            project_dir.mkdir()

            storyboard_dir = project_dir / "storyboard"
            storyboard_dir.mkdir()

            storyboard = {"project": "test", "scenes": []}
            (storyboard_dir / "storyboard.json").write_text(json.dumps(storyboard))

            preview = analyze_project_scenes(project_dir)

            assert isinstance(preview, dict)


class TestSemanticMappingIntegration:
    """Tests for semantic mapping integration with orchestrator."""

    def test_mapping_preserves_moment_info(self):
        """Test that semantic mapping adds info without losing moment data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            orchestrator = SFXOrchestrator(project_dir)

            # Create test scene
            scene_file = Path(tmpdir) / "Test.tsx"
            scene_file.write_text("// test")

            original_moment = SoundMoment(
                type="counter",
                frame=50,
                confidence=0.95,
                context="speed counter",
                intensity=0.8,
            )

            mock_result = SceneAnalysisResult(
                scene_id="Test",
                scene_type="test/Test",
                duration_frames=300,
            )
            mock_result.add_moment(original_moment)

            with patch.object(orchestrator.ts_analyzer, "analyze_scene", return_value=mock_result):
                result = orchestrator._analyze_scene_file(
                    scene_file, "test", "test/Test", 300
                )

            assert len(result.moments) == 1
            moment = result.moments[0]

            # Original data preserved
            assert moment.type == "counter"
            assert moment.frame == 50
            assert moment.confidence == 0.95

            # Mapping info added
            assert "[mapped:" in moment.context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

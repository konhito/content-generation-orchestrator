"""Tests for Visual Cue Refiner."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.refine.visual_cue import VisualCueRefiner, VisualCueRefinerResult
from src.refine.models import UpdateVisualCuePatch, ScriptPatchType


class TestVisualCueRefinerResult:
    """Tests for VisualCueRefinerResult dataclass."""

    def test_result_creation(self):
        """Test creating a VisualCueRefinerResult."""
        result = VisualCueRefinerResult(
            project_id="test-project",
            scenes_analyzed=5,
            scenes_needing_update=2,
            patches=[],
            analysis_notes="Test notes",
        )
        assert result.project_id == "test-project"
        assert result.scenes_analyzed == 5
        assert result.scenes_needing_update == 2
        assert result.analysis_notes == "Test notes"

    def test_result_to_dict(self):
        """Test VisualCueRefinerResult serialization."""
        patch = UpdateVisualCuePatch(
            reason="Test reason",
            scene_id="scene1",
            scene_title="Test Scene",
            new_visual_cue={"description": "Test"},
        )
        result = VisualCueRefinerResult(
            project_id="test",
            scenes_analyzed=1,
            patches=[patch],
        )
        data = result.to_dict()
        assert data["project_id"] == "test"
        assert data["scenes_analyzed"] == 1
        assert len(data["patches"]) == 1
        assert data["patches"][0]["scene_id"] == "scene1"

    def test_result_with_error(self):
        """Test result with error message."""
        result = VisualCueRefinerResult(
            project_id="test",
            error_message="Something went wrong",
        )
        assert result.error_message == "Something went wrong"
        data = result.to_dict()
        assert data["error_message"] == "Something went wrong"


class TestVisualCueRefiner:
    """Tests for VisualCueRefiner class."""

    def test_refiner_initialization(self, project_with_files, mock_llm_provider):
        """Test VisualCueRefiner initialization."""
        refiner = VisualCueRefiner(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )
        assert refiner.project == project_with_files
        assert refiner.verbose is False

    def test_load_script(self, project_with_files, mock_llm_provider):
        """Test loading script.json."""
        refiner = VisualCueRefiner(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )
        script_data = refiner._load_script()
        assert script_data is not None
        assert "scenes" in script_data
        assert len(script_data["scenes"]) == 2

    def test_load_script_not_found(self, temp_project_dir, mock_llm_provider):
        """Test loading script when file doesn't exist."""
        from src.project import load_project

        # Create a minimal project without script.json
        project = load_project(temp_project_dir)
        refiner = VisualCueRefiner(
            project=project,
            llm_provider=mock_llm_provider,
            verbose=False,
        )
        script_data = refiner._load_script()
        assert script_data is None

    def test_analyze_returns_result(self, project_with_files, mock_llm_provider):
        """Test that analyze returns a VisualCueRefinerResult."""
        # Mock the LLM to return no updates needed
        mock_llm_provider.generate_json = MagicMock(return_value={
            "needs_update": False,
            "reason": "Visual cue is already well-specified",
        })

        refiner = VisualCueRefiner(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )
        result = refiner.analyze()

        assert isinstance(result, VisualCueRefinerResult)
        assert result.project_id == project_with_files.id
        assert result.scenes_analyzed == 2

    def test_analyze_specific_scenes(self, project_with_files, mock_llm_provider):
        """Test analyzing specific scenes by index."""
        mock_llm_provider.generate_json = MagicMock(return_value={
            "needs_update": False,
        })

        refiner = VisualCueRefiner(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )
        result = refiner.analyze(scene_indices=[0])

        assert result.scenes_analyzed == 1

    def test_analyze_generates_patches(self, project_with_files, mock_llm_provider):
        """Test that analyze generates patches when LLM suggests updates."""
        mock_llm_provider.generate_json = MagicMock(return_value={
            "needs_update": True,
            "reason": "Visual cue needs dark glass specification",
            "improved_visual_cue": {
                "description": "Dark glass panels with 3D depth",
                "visual_type": "animation",
                "elements": ["Dark glass panels", "Multi-layer shadows"],
                "duration_seconds": 22.0,
            },
        })

        refiner = VisualCueRefiner(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )
        result = refiner.analyze(scene_indices=[0])

        assert result.scenes_needing_update == 1
        assert len(result.patches) == 1
        assert result.patches[0].patch_type == ScriptPatchType.UPDATE_VISUAL_CUE
        assert result.patches[0].new_visual_cue["description"] == "Dark glass panels with 3D depth"

    def test_apply_patches(self, project_with_files, mock_llm_provider):
        """Test applying patches to script.json."""
        refiner = VisualCueRefiner(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )

        # Create a patch
        patch = UpdateVisualCuePatch(
            reason="Test update",
            scene_id="the_impossible_leap",  # First scene's scene_id
            scene_title="The Impossible Leap",
            new_visual_cue={
                "description": "Updated description",
                "elements": ["New element"],
            },
        )

        applied = refiner.apply_patches([patch])
        assert applied == 1

        # Verify the script.json was updated
        script_path = project_with_files.root_dir / "script" / "script.json"
        with open(script_path) as f:
            updated_script = json.load(f)

        assert updated_script["scenes"][0]["visual_cue"]["description"] == "Updated description"

    def test_save_result(self, project_with_files, mock_llm_provider):
        """Test saving analysis result to file."""
        refiner = VisualCueRefiner(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )

        result = VisualCueRefinerResult(
            project_id=project_with_files.id,
            scenes_analyzed=2,
            analysis_notes="Test save",
        )

        output_path = refiner.save_result(result)
        assert output_path.exists()

        with open(output_path) as f:
            saved_data = json.load(f)

        assert saved_data["project_id"] == project_with_files.id
        assert saved_data["analysis_notes"] == "Test save"


class TestVisualCueRefinerSceneFileFinder:
    """Tests for scene file finding functionality."""

    def test_find_scene_file(self, project_with_files, mock_llm_provider):
        """Test finding scene implementation file."""
        refiner = VisualCueRefiner(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )

        scene = {"title": "The Impossible Leap"}
        scene_file = refiner._find_scene_file(scene)

        # The fixture creates TheImpossibleLeapScene.tsx
        assert scene_file is not None
        assert "ImpossibleLeap" in scene_file.name

    def test_find_scene_file_not_found(self, project_with_files, mock_llm_provider):
        """Test finding scene file when it doesn't exist."""
        refiner = VisualCueRefiner(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )

        scene = {"title": "Non Existent Scene"}
        scene_file = refiner._find_scene_file(scene)

        assert scene_file is None


class TestVisualCueRefinerErrorHandling:
    """Tests for error handling in VisualCueRefiner."""

    def test_analyze_handles_llm_error(self, project_with_files, mock_llm_provider):
        """Test that analyze handles LLM errors gracefully."""
        mock_llm_provider.generate_json = MagicMock(side_effect=Exception("LLM error"))

        refiner = VisualCueRefiner(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )

        # Should not raise, but return result with no patches
        result = refiner.analyze(scene_indices=[0])
        assert result.scenes_analyzed == 1
        assert len(result.patches) == 0  # No patch generated due to error

    def test_analyze_empty_script(self, temp_project_dir, mock_llm_provider):
        """Test analyze with no script.json."""
        from src.project import load_project

        project = load_project(temp_project_dir)
        refiner = VisualCueRefiner(
            project=project,
            llm_provider=mock_llm_provider,
            verbose=False,
        )

        result = refiner.analyze()
        assert result.error_message is not None
        assert "Could not load" in result.error_message

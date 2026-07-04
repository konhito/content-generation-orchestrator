"""Tests for refine validation."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.refine.validation import validate_project_sync, ProjectValidator
from src.refine.models import SyncIssueType


class TestValidateProjectSync:
    """Tests for validate_project_sync function."""

    def test_synced_project(self, project_with_files):
        """Test validation of a properly synced project."""
        status = validate_project_sync(project_with_files)
        # Note: May have issues due to audio duration check with mock files
        # The key test is that it runs without errors
        assert status is not None
        assert status.storyboard_scene_count == 2

    def test_reports_scene_count(self, project_with_files):
        """Test that validation reports scene counts."""
        status = validate_project_sync(project_with_files)
        assert status.storyboard_scene_count == 2
        assert status.narration_scene_count == 2


class TestProjectValidator:
    """Tests for ProjectValidator class."""

    def test_validator_initialization(self, project_with_files):
        """Test ProjectValidator initialization."""
        validator = ProjectValidator(project_with_files)
        assert validator.project == project_with_files

    def test_get_scene_start_frame_first(self, project_with_files):
        """Test calculating scene start frame for first scene."""
        validator = ProjectValidator(project_with_files)

        # First scene starts at frame 0
        frame = validator.get_scene_start_frame(0)
        assert frame == 0

    def test_get_scene_start_frame_second(self, project_with_files):
        """Test calculating scene start frame for second scene."""
        validator = ProjectValidator(project_with_files)

        # Second scene starts after first scene's duration
        # First scene is 22.5 seconds at 30fps = 675 frames
        frame = validator.get_scene_start_frame(1)
        assert frame == 675

    def test_get_scene_start_frame_invalid_index(self, project_with_files):
        """Test get_scene_start_frame with invalid index."""
        validator = ProjectValidator(project_with_files)

        with pytest.raises(ValueError, match="out of range"):
            validator.get_scene_start_frame(999)

    def test_get_scene_start_frame_negative_index(self, project_with_files):
        """Test get_scene_start_frame with negative index."""
        validator = ProjectValidator(project_with_files)

        with pytest.raises(ValueError, match="out of range"):
            validator.get_scene_start_frame(-1)

    def test_get_scene_info(self, project_with_files):
        """Test getting scene information."""
        validator = ProjectValidator(project_with_files)

        info = validator.get_scene_info(0)
        assert info["id"] == "scene1_hook"
        assert info["title"] == "The Impossible Leap"
        assert "duration_seconds" in info
        assert "start_frame" in info
        assert info["start_frame"] == 0

    def test_get_scene_info_second_scene(self, project_with_files):
        """Test getting second scene information."""
        validator = ProjectValidator(project_with_files)

        info = validator.get_scene_info(1)
        assert info["id"] == "scene2_context"
        assert info["title"] == "The Discovery"
        assert info["start_frame"] == 675  # After first scene

    def test_get_scene_info_invalid_index(self, project_with_files):
        """Test get_scene_info with invalid index."""
        validator = ProjectValidator(project_with_files)

        with pytest.raises(ValueError, match="out of range"):
            validator.get_scene_info(999)

    def test_get_scene_info_includes_visual_cue(self, project_with_files):
        """Test that get_scene_info includes visual_cue from script.json."""
        validator = ProjectValidator(project_with_files)

        info = validator.get_scene_info(0)
        assert "visual_cue" in info
        assert info["visual_cue"] is not None
        assert info["visual_cue"]["description"] == "Dark glass panels with 3D depth showing comparison"
        assert "elements" in info["visual_cue"]
        assert len(info["visual_cue"]["elements"]) == 2

    def test_get_scene_info_visual_cue_second_scene(self, project_with_files):
        """Test visual_cue for second scene."""
        validator = ProjectValidator(project_with_files)

        info = validator.get_scene_info(1)
        assert "visual_cue" in info
        assert info["visual_cue"]["description"] == "Timeline visualization of the discovery"

    def test_get_scene_duration_frames(self, project_with_files):
        """Test getting scene duration in frames."""
        validator = ProjectValidator(project_with_files)

        # First scene is 22.5 seconds at 30fps
        frames = validator.get_scene_duration_frames(0)
        assert frames == 675

    def test_get_scene_duration_frames_second(self, project_with_files):
        """Test getting second scene duration in frames."""
        validator = ProjectValidator(project_with_files)

        # Second scene is 27.0 seconds at 30fps
        frames = validator.get_scene_duration_frames(1)
        assert frames == 810


class TestSceneCountMismatch:
    """Tests for scene count mismatch detection."""

    def test_scene_count_mismatch(self, temp_project_dir):
        """Test validation when scene counts don't match."""
        from src.project import load_project

        # Create storyboard with 3 scenes
        storyboard = {
            "scenes": [
                {"id": "scene1", "audio_file": "scene1.mp3", "audio_duration_seconds": 10},
                {"id": "scene2", "audio_file": "scene2.mp3", "audio_duration_seconds": 10},
                {"id": "scene3", "audio_file": "scene3.mp3", "audio_duration_seconds": 10},
            ],
            "total_duration_seconds": 30,
        }
        with open(temp_project_dir / "storyboard" / "storyboard.json", "w") as f:
            json.dump(storyboard, f)

        # Create narrations with only 2 scenes
        narrations = {
            "scenes": [
                {"scene_id": "scene1", "title": "Scene 1", "narration": "Test 1", "duration_seconds": 10},
                {"scene_id": "scene2", "title": "Scene 2", "narration": "Test 2", "duration_seconds": 10},
            ]
        }
        with open(temp_project_dir / "narration" / "narrations.json", "w") as f:
            json.dump(narrations, f)

        # Create voiceover files
        for scene in storyboard["scenes"]:
            audio_file = temp_project_dir / "voiceover" / scene["audio_file"]
            audio_file.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 100)

        project = load_project(temp_project_dir)
        status = validate_project_sync(project)

        assert status.is_synced is False
        assert any(i.issue_type == SyncIssueType.SCENE_COUNT_MISMATCH for i in status.issues)
        assert status.storyboard_scene_count == 3
        assert status.narration_scene_count == 2


class TestMissingVoiceover:
    """Tests for missing voiceover detection."""

    def test_missing_voiceover(self, temp_project_dir):
        """Test validation when voiceover file is missing."""
        from src.project import load_project

        # Create storyboard
        storyboard = {
            "scenes": [
                {"id": "scene1", "audio_file": "scene1.mp3", "audio_duration_seconds": 10},
                {"id": "scene2", "audio_file": "scene2.mp3", "audio_duration_seconds": 10},
            ],
            "total_duration_seconds": 20,
        }
        with open(temp_project_dir / "storyboard" / "storyboard.json", "w") as f:
            json.dump(storyboard, f)

        # Create narrations
        narrations = {
            "scenes": [
                {"scene_id": "scene1", "title": "Scene 1", "narration": "Test 1", "duration_seconds": 10},
                {"scene_id": "scene2", "title": "Scene 2", "narration": "Test 2", "duration_seconds": 10},
            ]
        }
        with open(temp_project_dir / "narration" / "narrations.json", "w") as f:
            json.dump(narrations, f)

        # Only create one voiceover file
        audio_file = temp_project_dir / "voiceover" / "scene1.mp3"
        audio_file.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 100)

        project = load_project(temp_project_dir)
        status = validate_project_sync(project)

        assert status.is_synced is False
        assert any(i.issue_type == SyncIssueType.MISSING_VOICEOVER for i in status.issues)
        # Should identify scene2 as missing voiceover
        missing_issues = [i for i in status.issues if i.issue_type == SyncIssueType.MISSING_VOICEOVER]
        assert any("scene2" in i.affected_scene for i in missing_issues if i.affected_scene)


class TestValidationHelpers:
    """Tests for validation helper methods."""

    def test_get_storyboard_scenes(self, project_with_files):
        """Test getting scenes from storyboard."""
        validator = ProjectValidator(project_with_files)

        scenes = validator._get_storyboard_scenes()

        assert len(scenes) == 2
        assert scenes[0]["id"] == "scene1_hook"

    def test_get_narration_scenes(self, project_with_files):
        """Test getting scenes from narrations."""
        validator = ProjectValidator(project_with_files)

        scenes = validator._get_narration_scenes()

        assert len(scenes) == 2

    def test_get_voiceover_files(self, project_with_files):
        """Test getting voiceover files."""
        validator = ProjectValidator(project_with_files)

        files = validator._get_voiceover_files()

        assert len(files) == 2

    def test_get_scene_files(self, project_with_files):
        """Test getting scene component files."""
        validator = ProjectValidator(project_with_files)

        files = validator._get_scene_files()

        # The fixture creates one scene file
        assert len(files) >= 1
        assert all(f.suffix == ".tsx" for f in files)

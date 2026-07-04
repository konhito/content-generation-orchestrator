"""Tests for project loader module."""

import json
from pathlib import Path

import pytest

from src.project import Project, load_project, list_projects
from src.project.loader import create_project


class TestProjectLoader:
    """Tests for project loading functionality."""

    @pytest.fixture
    def sample_project(self, tmp_path):
        """Create a sample project for testing."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Create config
        config = {
            "id": "test-project",
            "title": "Test Project",
            "description": "A test project",
            "version": "1.0.0",
            "video": {
                "resolution": {"width": 1920, "height": 1080},
                "fps": 30,
                "target_duration_seconds": 120,
            },
            "tts": {
                "provider": "mock",
                "voice_id": "test-voice",
            },
            "style": {
                "background_color": "#000000",
                "primary_color": "#ffffff",
            },
            "paths": {
                "narration": "narration/narrations.json",
                "storyboard": "storyboard/storyboard.json",
                "voiceover_manifest": "voiceover/manifest.json",
            },
        }

        config_path = project_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        # Create narration file
        narration_dir = project_dir / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [
                {
                    "scene_id": "scene1",
                    "title": "Scene 1",
                    "duration_seconds": 10,
                    "narration": "This is scene one.",
                },
                {
                    "scene_id": "scene2",
                    "title": "Scene 2",
                    "duration_seconds": 15,
                    "narration": "This is scene two.",
                },
            ]
        }
        with open(narration_dir / "narrations.json", "w") as f:
            json.dump(narrations, f)

        return project_dir

    def test_load_project(self, sample_project):
        """Test loading a project from directory."""
        project = load_project(sample_project)

        assert project.id == "test-project"
        assert project.title == "Test Project"
        assert project.description == "A test project"
        assert project.version == "1.0.0"

    def test_load_project_video_config(self, sample_project):
        """Test that video config is loaded correctly."""
        project = load_project(sample_project)

        assert project.video.width == 1920
        assert project.video.height == 1080
        assert project.video.fps == 30
        assert project.video.target_duration_seconds == 120

    def test_load_project_tts_config(self, sample_project):
        """Test that TTS config is loaded correctly."""
        project = load_project(sample_project)

        assert project.tts.provider == "mock"
        assert project.tts.voice_id == "test-voice"

    def test_load_project_style_config(self, sample_project):
        """Test that style config is loaded correctly."""
        project = load_project(sample_project)

        assert project.style.background_color == "#000000"
        assert project.style.primary_color == "#ffffff"

    def test_load_project_from_config_file(self, sample_project):
        """Test loading project from config file path."""
        config_path = sample_project / "config.json"
        project = load_project(config_path)

        assert project.id == "test-project"

    def test_load_project_not_found(self, tmp_path):
        """Test error when project not found."""
        with pytest.raises(FileNotFoundError):
            load_project(tmp_path / "nonexistent")

    def test_project_directories(self, sample_project):
        """Test project directory properties."""
        project = load_project(sample_project)

        assert project.input_dir == sample_project / "input"
        assert project.script_dir == sample_project / "script"
        assert project.narration_dir == sample_project / "narration"
        assert project.voiceover_dir == sample_project / "voiceover"
        assert project.storyboard_dir == sample_project / "storyboard"
        assert project.output_dir == sample_project / "output"

    def test_load_narrations(self, sample_project):
        """Test loading narrations from project."""
        project = load_project(sample_project)
        narrations = project.load_narrations()

        assert len(narrations) == 2
        assert narrations[0].scene_id == "scene1"
        assert narrations[0].title == "Scene 1"
        assert narrations[1].scene_id == "scene2"

    def test_get_path(self, sample_project):
        """Test getting paths from project config."""
        project = load_project(sample_project)

        narration_path = project.get_path("narration")
        assert narration_path == sample_project / "narration" / "narrations.json"

    def test_ensure_directories(self, sample_project):
        """Test creating project directories."""
        project = load_project(sample_project)
        project.ensure_directories()

        assert project.input_dir.exists()
        assert project.script_dir.exists()
        assert project.voiceover_dir.exists()
        assert project.storyboard_dir.exists()
        assert project.output_dir.exists()
        assert (project.output_dir / "preview").exists()


class TestListProjects:
    """Tests for listing projects."""

    def test_list_projects_empty(self, tmp_path):
        """Test listing projects from empty directory."""
        projects = list_projects(tmp_path)
        assert projects == []

    def test_list_projects(self, tmp_path):
        """Test listing multiple projects."""
        # Create two projects
        for name in ["project-a", "project-b"]:
            project_dir = tmp_path / name
            project_dir.mkdir()
            config = {"id": name, "title": name.title()}
            with open(project_dir / "config.json", "w") as f:
                json.dump(config, f)

        projects = list_projects(tmp_path)

        assert len(projects) == 2
        ids = [p.id for p in projects]
        assert "project-a" in ids
        assert "project-b" in ids


class TestCreateProject:
    """Tests for project creation."""

    def test_create_project(self, tmp_path):
        """Test creating a new project."""
        project = create_project(
            project_id="new-project",
            title="New Project",
            projects_dir=tmp_path,
            description="A new project",
        )

        assert project.id == "new-project"
        assert project.title == "New Project"
        assert (tmp_path / "new-project" / "config.json").exists()

    def test_create_project_directories_exist(self, tmp_path):
        """Test that created project has all directories."""
        project = create_project(
            project_id="new-project",
            title="New Project",
            projects_dir=tmp_path,
        )

        assert project.input_dir.exists()
        assert project.narration_dir.exists()
        assert project.voiceover_dir.exists()
        assert project.storyboard_dir.exists()
        assert project.output_dir.exists()

    def test_create_project_already_exists(self, tmp_path):
        """Test error when project already exists."""
        # Create first project
        create_project("existing", "Existing", tmp_path)

        # Try to create again
        with pytest.raises(ValueError, match="already exists"):
            create_project("existing", "Existing", tmp_path)


class TestLLMInferenceProject:
    """Tests for the actual llm-inference project."""

    def test_llm_inference_project_exists(self):
        """Test that the llm-inference project can be loaded."""
        project_path = Path("projects/llm-inference")
        if not project_path.exists():
            pytest.skip("llm-inference project not found")

        project = load_project(project_path)
        assert project.id == "llm-inference"

    def test_llm_inference_narrations(self):
        """Test loading narrations from llm-inference project."""
        project_path = Path("projects/llm-inference")
        if not project_path.exists():
            pytest.skip("llm-inference project not found")

        project = load_project(project_path)
        narrations = project.load_narrations()

        assert len(narrations) == 18
        assert narrations[0].scene_id == "scene1_hook"

    def test_llm_inference_voiceover_files(self):
        """Test voiceover files exist in llm-inference project."""
        project_path = Path("projects/llm-inference")
        if not project_path.exists():
            pytest.skip("llm-inference project not found")

        project = load_project(project_path)
        voiceover_files = project.get_voiceover_files()

        assert len(voiceover_files) == 18

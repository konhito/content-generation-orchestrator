"""Tests for narration generation module."""

from pathlib import Path

import pytest

from src.config import Config
from src.models import Script, ScriptScene, VisualCue
from src.narration import NarrationGenerator


class TestNarrationGenerator:
    """Tests for the narration generator."""

    @pytest.fixture
    def generator(self, mock_config):
        return NarrationGenerator(config=mock_config)

    @pytest.fixture
    def sample_script(self) -> Script:
        """Create a sample script for testing."""
        return Script(
            title="Test Video Script",
            total_duration_seconds=110,
            scenes=[
                ScriptScene(
                    scene_id="scene_1",
                    scene_type="hook",
                    title="The Hook",
                    voiceover="Every day, we encounter this challenge.",
                    visual_cue=VisualCue(
                        description="Show the problem visually",
                        visual_type="animation",
                        elements=["problem_illustration"],
                        duration_seconds=15.0,
                    ),
                    duration_seconds=15.0,
                    notes="Build intrigue",
                ),
                ScriptScene(
                    scene_id="scene_2",
                    scene_type="context",
                    title="Background",
                    voiceover="To understand the solution, we first need context.",
                    visual_cue=VisualCue(
                        description="Show background context",
                        visual_type="animation",
                        elements=["context_diagram"],
                        duration_seconds=20.0,
                    ),
                    duration_seconds=20.0,
                    notes="Set the stage",
                ),
                ScriptScene(
                    scene_id="scene_3",
                    scene_type="explanation",
                    title="The Core Concept",
                    voiceover="Here's how it works.",
                    visual_cue=VisualCue(
                        description="Explain the core concept",
                        visual_type="animation",
                        elements=["concept_visualization"],
                        duration_seconds=30.0,
                    ),
                    duration_seconds=30.0,
                    notes="Main explanation",
                ),
                ScriptScene(
                    scene_id="scene_4",
                    scene_type="conclusion",
                    title="Conclusion",
                    voiceover="Now you understand the concept.",
                    visual_cue=VisualCue(
                        description="Summary and application",
                        visual_type="animation",
                        elements=["summary"],
                        duration_seconds=20.0,
                    ),
                    duration_seconds=20.0,
                    notes="Wrap up",
                ),
            ],
            source_document="test.md",
        )

    def test_generate_returns_dict(self, generator, sample_script):
        narrations = generator.generate(sample_script)
        assert isinstance(narrations, dict)

    def test_narrations_have_scenes(self, generator, sample_script):
        narrations = generator.generate(sample_script)
        assert "scenes" in narrations
        assert len(narrations["scenes"]) > 0

    def test_narration_scenes_have_required_fields(self, generator, sample_script):
        narrations = generator.generate(sample_script)
        for scene in narrations["scenes"]:
            assert "scene_id" in scene
            assert "title" in scene
            assert "duration_seconds" in scene
            assert "narration" in scene

    def test_narrations_have_total_duration(self, generator, sample_script):
        narrations = generator.generate(sample_script)
        assert "total_duration_seconds" in narrations
        assert narrations["total_duration_seconds"] > 0

    def test_generate_with_source_documents(self, generator, sample_script):
        from src.models import ParsedDocument, Section

        # Create a simple source document
        doc = ParsedDocument(
            raw_content="# Sample\nSome content for the narration generator.",
            title="Sample Document",
            content_type="markdown",
            source_type="markdown",
            source_path="test.md",
            sections=[Section(heading="Sample", content="Some content", level=1)],
            metadata={},
        )
        narrations = generator.generate(sample_script, source_documents=[doc])
        assert isinstance(narrations, dict)
        assert "scenes" in narrations

    def test_generate_with_topic(self, generator, sample_script):
        narrations = generator.generate(sample_script, topic="Machine Learning")
        assert isinstance(narrations, dict)


class TestNarrationGeneratorMock:
    """Tests for mock narration generation."""

    @pytest.fixture
    def generator(self, mock_config):
        return NarrationGenerator(config=mock_config)

    def test_generate_mock_returns_dict(self, generator):
        narrations = generator.generate_mock("Test Topic")
        assert isinstance(narrations, dict)

    def test_mock_has_scenes(self, generator):
        narrations = generator.generate_mock("Test Topic")
        assert "scenes" in narrations
        assert len(narrations["scenes"]) > 0

    def test_mock_scenes_have_required_fields(self, generator):
        narrations = generator.generate_mock("Test Topic")
        for scene in narrations["scenes"]:
            assert "scene_id" in scene
            assert "title" in scene
            assert "duration_seconds" in scene
            assert "narration" in scene

    def test_mock_has_total_duration(self, generator):
        narrations = generator.generate_mock("Test Topic")
        assert "total_duration_seconds" in narrations

    def test_mock_topic_appears_in_narrations(self, generator):
        topic = "Quantum Computing"
        narrations = generator.generate_mock(topic)
        all_narration = " ".join(s["narration"] for s in narrations["scenes"])
        assert topic in all_narration


class TestNarrationPersistence:
    """Tests for narration save/load operations."""

    @pytest.fixture
    def generator(self, mock_config):
        return NarrationGenerator(config=mock_config)

    @pytest.fixture
    def sample_narrations(self) -> dict:
        return {
            "scenes": [
                {
                    "scene_id": "scene1_hook",
                    "title": "The Hook",
                    "duration_seconds": 15,
                    "narration": "What if there's a better way?",
                },
                {
                    "scene_id": "scene2_context",
                    "title": "Context",
                    "duration_seconds": 20,
                    "narration": "Let's understand the background.",
                },
            ],
            "total_duration_seconds": 35,
        }

    def test_save_narrations(self, generator, sample_narrations, tmp_path):
        narration_path = tmp_path / "narrations.json"
        generator.save_narrations(sample_narrations, narration_path)
        assert narration_path.exists()

    def test_save_creates_parent_directories(self, generator, sample_narrations, tmp_path):
        narration_path = tmp_path / "nested" / "dir" / "narrations.json"
        generator.save_narrations(sample_narrations, narration_path)
        assert narration_path.exists()

    def test_load_narrations(self, generator, sample_narrations, tmp_path):
        narration_path = tmp_path / "narrations.json"
        generator.save_narrations(sample_narrations, narration_path)

        loaded = NarrationGenerator.load_narrations(narration_path)
        assert loaded == sample_narrations

    def test_save_and_load_round_trip(self, generator, sample_narrations, tmp_path):
        narration_path = tmp_path / "narrations.json"
        generator.save_narrations(sample_narrations, narration_path)
        loaded = NarrationGenerator.load_narrations(narration_path)

        assert len(loaded["scenes"]) == len(sample_narrations["scenes"])
        assert loaded["total_duration_seconds"] == sample_narrations["total_duration_seconds"]
        for original, loaded_scene in zip(sample_narrations["scenes"], loaded["scenes"]):
            assert original["scene_id"] == loaded_scene["scene_id"]
            assert original["narration"] == loaded_scene["narration"]

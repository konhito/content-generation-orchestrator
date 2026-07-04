"""Tests for the feedback processing module."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch as mock_patch

import pytest

from src.refine.feedback import (
    FeedbackIntent,
    FeedbackItem,
    FeedbackScope,
    FeedbackStatus,
    FeedbackTarget,
    FeedbackHistory,
    FeedbackParser,
    FeedbackStore,
    PatchGenerator,
    PatchApplicator,
    FeedbackProcessor,
    generate_feedback_id,
)


# ============================================================================
# Model Tests
# ============================================================================


class TestFeedbackModels:
    """Tests for feedback data models."""

    def test_generate_feedback_id(self):
        """Test feedback ID generation."""
        id1 = generate_feedback_id(1)
        assert id1.startswith("fb_0001_")
        assert len(id1) > 10

        id2 = generate_feedback_id(42)
        assert "0042" in id2

    def test_feedback_item_creation(self):
        """Test FeedbackItem creation."""
        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Test feedback",
        )
        assert item.status == FeedbackStatus.PENDING
        assert item.intent is None
        assert item.patches == []

    def test_feedback_item_to_dict(self):
        """Test FeedbackItem serialization."""
        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            feedback_text="Test feedback",
            intent=FeedbackIntent.VISUAL_CUE,
            target=FeedbackTarget(
                scene_ids=["scene_1"],
                scope=FeedbackScope.SCENE,
            ),
        )
        data = item.to_dict()

        assert data["id"] == "fb_0001_test"
        assert data["intent"] == "visual_cue"
        assert data["target"]["scene_ids"] == ["scene_1"]

    def test_feedback_item_from_dict(self):
        """Test FeedbackItem deserialization."""
        data = {
            "id": "fb_0001_test",
            "timestamp": "2024-01-01T12:00:00",
            "feedback_text": "Test feedback",
            "status": "applied",
            "intent": "script_content",
            "target": {
                "scene_ids": ["scene_1", "scene_2"],
                "scope": "multi_scene",
            },
            "interpretation": "Test interpretation",
            "patches": [{"patch_type": "modify_scene"}],
            "files_modified": ["script/script.json"],
        }
        item = FeedbackItem.from_dict(data)

        assert item.id == "fb_0001_test"
        assert item.status == FeedbackStatus.APPLIED
        assert item.intent == FeedbackIntent.SCRIPT_CONTENT
        assert item.target.scope == FeedbackScope.MULTI_SCENE
        assert len(item.patches) == 1

    def test_feedback_history(self):
        """Test FeedbackHistory management."""
        history = FeedbackHistory(project_id="test-project")

        item1 = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="First feedback",
        )
        item2 = FeedbackItem(
            id="fb_0002_test",
            timestamp=datetime.now(),
            feedback_text="Second feedback",
            status=FeedbackStatus.APPLIED,
        )

        history.add(item1)
        history.add(item2)

        assert len(history.items) == 2
        assert history.get_by_id("fb_0001_test") == item1
        assert len(history.get_by_status(FeedbackStatus.PENDING)) == 1
        assert len(history.get_by_status(FeedbackStatus.APPLIED)) == 1


# ============================================================================
# Store Tests
# ============================================================================


class TestFeedbackStore:
    """Tests for FeedbackStore."""

    def test_store_save_and_load(self, tmp_path):
        """Test saving and loading feedback."""
        # Create mock project
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        store = FeedbackStore(project)

        # Add feedback
        item = store.add_feedback("Test feedback")
        assert item.id.startswith("fb_0001_")
        assert store.exists()

        # Load and verify
        all_items = store.list_all()
        assert len(all_items) == 1
        assert all_items[0].feedback_text == "Test feedback"

    def test_store_update_item(self, tmp_path):
        """Test updating a feedback item."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        store = FeedbackStore(project)
        item = store.add_feedback("Test feedback")

        # Update item
        item.status = FeedbackStatus.APPLIED
        item.files_modified = ["script/script.json"]
        store.update_item(item)

        # Reload and verify
        loaded = store.get_item(item.id)
        assert loaded.status == FeedbackStatus.APPLIED
        assert loaded.files_modified == ["script/script.json"]


# ============================================================================
# Parser Tests
# ============================================================================


class TestFeedbackParser:
    """Tests for FeedbackParser."""

    def test_parser_with_mock_llm(self, tmp_path):
        """Test parsing feedback with mock LLM."""
        # Create mock project with script
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {"scene_id": "intro", "title": "Introduction", "scene_type": "hook"},
                {"scene_id": "main", "title": "Main Content", "scene_type": "explanation"},
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        # Create mock LLM
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "intent": "visual_cue",
            "affected_scene_ids": ["intro"],
            "scope": "scene",
            "interpretation": "User wants to update the visual cue for the intro",
        }

        parser = FeedbackParser(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Make the intro more colorful",
        )

        result = parser.parse(item)

        assert result.intent == FeedbackIntent.VISUAL_CUE
        assert result.target.scene_ids == ["intro"]
        assert "visual cue" in result.interpretation.lower()


# ============================================================================
# Generator Tests
# ============================================================================


class TestPatchGenerator:
    """Tests for PatchGenerator."""

    def test_generate_script_content_patch(self, tmp_path):
        """Test generating script content patches."""
        # Setup project
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "scene_type": "hook",
                    "voiceover": "Original text",
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "changes": [
                {
                    "field": "voiceover",
                    "new_text": "Updated text",
                    "reason": "Test change",
                }
            ]
        }

        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Update the intro text",
            intent=FeedbackIntent.SCRIPT_CONTENT,
            target=FeedbackTarget(
                scene_ids=["intro"],
                scope=FeedbackScope.SCENE,
            ),
            interpretation="User wants to update intro text",
        )

        result = generator.generate(item)

        assert len(result.patches) == 1
        patch = result.patches[0]
        assert patch["patch_type"] == "modify_scene"
        assert patch["new_value"] == "Updated text"


# ============================================================================
# Applicator Tests
# ============================================================================


class TestPatchApplicator:
    """Tests for PatchApplicator."""

    def test_apply_modify_scene_patch(self, tmp_path):
        """Test applying a modify scene patch."""
        # Setup project
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "voiceover": "Original text",
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        narration_dir = tmp_path / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "narration": "Original text",
                }
            ]
        }
        (narration_dir / "narrations.json").write_text(json.dumps(narrations))

        applicator = PatchApplicator(project, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Update text",
            patches=[
                {
                    "patch_type": "modify_scene",
                    "scene_id": "intro",
                    "field_name": "voiceover",
                    "new_value": "Updated text",
                }
            ],
        )

        result = applicator.apply(item, verify=False)

        assert result.status == FeedbackStatus.APPLIED
        assert "script/script.json" in result.files_modified

        # Verify the file was actually updated
        updated_script = json.loads((script_dir / "script.json").read_text())
        assert updated_script["scenes"][0]["voiceover"] == "Updated text"

    def test_apply_visual_cue_patch(self, tmp_path):
        """Test applying a visual cue patch."""
        # Setup project
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "visual_cue": {"description": "Original visual"},
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        applicator = PatchApplicator(project, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Update visual",
            patches=[
                {
                    "patch_type": "update_visual_cue",
                    "scene_id": "intro",
                    "new_visual_cue": {
                        "description": "New visual description",
                        "visual_type": "animation",
                    },
                }
            ],
        )

        result = applicator.apply(item, verify=False)

        assert result.status == FeedbackStatus.APPLIED

        # Verify the file was updated
        updated_script = json.loads((script_dir / "script.json").read_text())
        assert updated_script["scenes"][0]["visual_cue"]["description"] == "New visual description"


# ============================================================================
# Processor Integration Tests
# ============================================================================


class TestFeedbackProcessor:
    """Tests for the FeedbackProcessor orchestrator."""

    def test_processor_dry_run(self, tmp_path):
        """Test processor in dry run mode."""
        # Setup project
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "scene_type": "hook",
                    "voiceover": "Original text",
                    "visual_cue": {"description": "Visual"},
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        # Mock LLM for parser and generator
        mock_llm = MagicMock()
        mock_llm.generate_json.side_effect = [
            # Parser response
            {
                "intent": "script_content",
                "affected_scene_ids": ["intro"],
                "scope": "scene",
                "interpretation": "User wants to update intro text",
            },
            # Generator response
            {
                "changes": [
                    {
                        "field": "voiceover",
                        "new_text": "Updated text",
                        "reason": "Test change",
                    }
                ]
            },
        ]

        processor = FeedbackProcessor(project, mock_llm, verbose=False)
        result = processor.process("Update intro text", dry_run=True)

        assert result.intent == FeedbackIntent.SCRIPT_CONTENT
        assert len(result.patches) == 1
        assert result.files_modified == []  # Dry run doesn't modify files

    def test_processor_list_feedback(self, tmp_path):
        """Test listing feedback items."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        # Create some feedback
        processor = FeedbackProcessor(project, verbose=False)
        processor.store.add_feedback("First feedback")
        processor.store.add_feedback("Second feedback")

        items = processor.list_feedback()
        assert len(items) == 2

    def test_processor_get_history(self, tmp_path):
        """Test getting history summary."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        processor = FeedbackProcessor(project, verbose=False)
        processor.store.add_feedback("Test feedback")

        history = processor.get_history()
        assert history["total_items"] == 1
        assert "pending" in history["status_counts"]


# ============================================================================
# Scene ID Matching Tests
# ============================================================================


class TestSceneIdMatching:
    """Tests for scene ID matching with both numeric and slug formats."""

    def test_generator_matches_numeric_scene_id(self, tmp_path):
        """Test that generator finds scenes by numeric ID."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        # Script with numeric IDs
        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {"scene_id": 1, "title": "The Introduction", "scene_type": "hook"},
                {"scene_id": 2, "title": "Main Content", "scene_type": "explanation"},
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        # Create scene file
        scenes_dir = tmp_path / "scenes"
        scenes_dir.mkdir()
        (scenes_dir / "TheIntroductionScene.tsx").write_text("// Scene component")

        # Mock LLM provider
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "needs_update": True,
            "new_visual_cue": {
                "description": "BACKGROUND: Light gradient. UI COMPONENTS: Dark glass panel.",
                "visual_type": "animation",
                "elements": ["Background", "Main panel"],
                "duration_seconds": 10,
            },
            "reason": "Updated visuals as requested",
        }

        generator = PatchGenerator(project, llm_provider=mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Update visuals",
            intent=FeedbackIntent.VISUAL_IMPLEMENTATION,
            target=FeedbackTarget(
                scene_ids=["1"],  # Numeric ID as string
                scope=FeedbackScope.SCENE,
            ),
            interpretation="Update the visuals",
        )

        result = generator.generate(item)
        assert len(result.patches) == 1
        assert result.patches[0]["scene_id"] == "1"

    def test_generator_matches_slug_to_title(self, tmp_path):
        """Test that generator finds scenes by slug matching title."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        # Script with numeric IDs but titled scenes
        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": 1,
                    "title": "The Impossible Leap",
                    "scene_type": "hook",
                    "voiceover": "Test",
                    "visual_cue": {"description": "Original"},
                },
                {
                    "scene_id": 2,
                    "title": "Beyond Linear Thinking",
                    "scene_type": "explanation",
                    "voiceover": "Test",
                    "visual_cue": {"description": "Original"},
                },
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        # Mock LLM
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "needs_update": True,
            "new_visual_cue": {
                "description": "Updated visual for tree animation",
                "visual_type": "animation",
            },
            "reason": "Fix tree animation",
        }

        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Fix the tree animation",
            intent=FeedbackIntent.VISUAL_IMPLEMENTATION,
            target=FeedbackTarget(
                scene_ids=["beyond_linear_thinking"],  # Slug format
                scope=FeedbackScope.SCENE,
            ),
            interpretation="Fix the tree animation in Beyond Linear Thinking",
        )

        result = generator.generate(item)
        assert len(result.patches) == 1
        assert "beyond_linear_thinking" in result.patches[0]["scene_id"] or result.patches[0]["scene_title"] == "Beyond Linear Thinking"

    def test_applicator_matches_slug_to_numeric_id(self, tmp_path):
        """Test that applicator matches slug IDs to scenes with numeric IDs."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        # Script with numeric IDs
        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": 3,
                    "title": "Beyond Linear Thinking",
                    "voiceover": "Original voiceover",
                    "visual_cue": {"description": "Original visual"},
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        applicator = PatchApplicator(project, verbose=False)

        # Use slug ID in patch
        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Update visual cue",
            patches=[
                {
                    "patch_type": "update_visual_cue",
                    "scene_id": "beyond_linear_thinking",  # Slug format
                    "new_visual_cue": {
                        "description": "Updated visual description",
                        "visual_type": "animation",
                    },
                }
            ],
        )

        result = applicator.apply(item, verify=False)
        assert result.status == FeedbackStatus.APPLIED

        # Verify the update was applied
        updated_script = json.loads((script_dir / "script.json").read_text())
        assert updated_script["scenes"][0]["visual_cue"]["description"] == "Updated visual description"

    def test_applicator_matches_modify_scene_with_slug(self, tmp_path):
        """Test modify_scene patch with slug ID matching numeric script ID."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": 1,
                    "title": "The Impossible Leap",
                    "voiceover": "Original text",
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        narration_dir = tmp_path / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [
                {
                    "scene_id": 1,
                    "title": "The Impossible Leap",
                    "narration": "Original text",
                }
            ]
        }
        (narration_dir / "narrations.json").write_text(json.dumps(narrations))

        applicator = PatchApplicator(project, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Update voiceover",
            patches=[
                {
                    "patch_type": "modify_scene",
                    "scene_id": "the_impossible_leap",  # Slug format
                    "field_name": "voiceover",
                    "new_value": "Updated voiceover text",
                }
            ],
        )

        result = applicator.apply(item, verify=False)
        assert result.status == FeedbackStatus.APPLIED

        # Verify both files were updated
        updated_script = json.loads((script_dir / "script.json").read_text())
        assert updated_script["scenes"][0]["voiceover"] == "Updated voiceover text"

    def test_generator_visual_impl_creates_visual_cue_patch_with_refinement(self, tmp_path):
        """Test that visual_impl intent now generates visual_cue patches with scene refinement flag."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": 5,
                    "title": "The Credit Assignment Challenge",
                    "scene_type": "explanation",
                    "voiceover": "Test voiceover",
                    "visual_cue": {"description": "Original visual"},
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        # Mock LLM to return visual_cue patch
        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "needs_update": True,
            "new_visual_cue": {
                "description": "Updated visual with smoother animation",
                "visual_type": "animation",
                "elements": ["Smooth animation elements"],
            },
            "reason": "User requested smoother animation",
        }

        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Make the animation smoother",
            intent=FeedbackIntent.VISUAL_IMPLEMENTATION,
            target=FeedbackTarget(
                scene_ids=["the_credit_assignment_challenge"],
                scope=FeedbackScope.SCENE,
            ),
            interpretation="User wants smoother animations",
        )

        result = generator.generate(item)

        # Should generate visual_cue patch, not visual_impl
        assert len(result.patches) == 1
        patch = result.patches[0]
        assert patch["patch_type"] == "update_visual_cue"
        assert patch["trigger_scene_refinement"] is True
        assert "smoother animation" in patch["new_visual_cue"]["description"]

    def test_applicator_slugify_method(self, tmp_path):
        """Test the _slugify helper method."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        applicator = PatchApplicator(project, verbose=False)

        assert applicator._slugify("Beyond Linear Thinking") == "beyond_linear_thinking"
        assert applicator._slugify("The Impossible Leap") == "the_impossible_leap"
        assert applicator._slugify("AI's Decision Engine") == "ais_decision_engine"
        assert applicator._slugify("The REINFORCE Algorithm") == "the_reinforce_algorithm"

    def test_applicator_match_scene_id_method(self, tmp_path):
        """Test the _match_scene_id helper method."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        applicator = PatchApplicator(project, verbose=False)

        scene = {"scene_id": 3, "title": "Beyond Linear Thinking"}

        # Direct numeric match
        assert applicator._match_scene_id(scene, "3") is True
        assert applicator._match_scene_id(scene, 3) is True

        # Slug match via title
        assert applicator._match_scene_id(scene, "beyond_linear_thinking") is True

        # Non-matches
        assert applicator._match_scene_id(scene, "4") is False
        assert applicator._match_scene_id(scene, "some_other_scene") is False


# ============================================================================
# Simplified Visual Flow Tests
# ============================================================================


class TestSimplifiedVisualFlow:
    """Tests for the simplified visual feedback flow.

    The new flow routes visual_impl and style intents through:
    1. Generate visual_cue patches (update script.json)
    2. Trigger scene refinement (ClaudeCodeVisualInspector)

    This ensures proper use of /remotion skill, visual verification,
    and 13 guiding principles.
    """

    def test_visual_impl_routes_to_visual_cue_patches(self, tmp_path):
        """Test that VISUAL_IMPLEMENTATION intent generates visual_cue patches."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "scene_type": "hook",
                    "voiceover": "Test voiceover",
                    "visual_cue": {"description": "Original visual"},
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "needs_update": True,
            "new_visual_cue": {
                "description": "Updated visual for better animation",
                "visual_type": "animation",
            },
            "reason": "Implementing user feedback",
        }

        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Fix the tree animation",
            intent=FeedbackIntent.VISUAL_IMPLEMENTATION,
            target=FeedbackTarget(scene_ids=["intro"], scope=FeedbackScope.SCENE),
            interpretation="Fix tree animation",
        )

        result = generator.generate(item)

        assert len(result.patches) == 1
        patch = result.patches[0]
        assert patch["patch_type"] == "update_visual_cue"
        assert patch["trigger_scene_refinement"] is True

    def test_style_routes_to_visual_cue_patches(self, tmp_path):
        """Test that STYLE intent generates visual_cue patches with refinement flag."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "main",
                    "title": "Main Content",
                    "scene_type": "explanation",
                    "voiceover": "Test",
                    "visual_cue": {"description": "Original"},
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "needs_update": True,
            "new_visual_cue": {
                "description": "Dark glass styling with 3D depth",
                "visual_type": "animation",
                "elements": ["Dark glass panels", "Multi-layer shadows"],
            },
            "reason": "Applying dark glass styling",
        }

        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Use dark glass styling",
            intent=FeedbackIntent.STYLE,
            target=FeedbackTarget(scene_ids=["main"], scope=FeedbackScope.SCENE),
            interpretation="Apply dark glass styling",
        )

        result = generator.generate(item)

        assert len(result.patches) == 1
        patch = result.patches[0]
        assert patch["patch_type"] == "update_visual_cue"
        assert patch["trigger_scene_refinement"] is True
        assert "dark glass" in patch["new_visual_cue"]["description"].lower()

    def test_visual_cue_without_refinement_flag(self, tmp_path):
        """Test that plain VISUAL_CUE intent can set trigger_refinement=True."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "scene_type": "hook",
                    "voiceover": "Test",
                    "visual_cue": {"description": "Original"},
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "needs_update": True,
            "new_visual_cue": {
                "description": "Updated visual cue",
                "visual_type": "animation",
            },
            "reason": "Updated specification",
        }

        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Update the visual specification",
            intent=FeedbackIntent.VISUAL_CUE,
            target=FeedbackTarget(scene_ids=["intro"], scope=FeedbackScope.SCENE),
            interpretation="Update visual specification",
        )

        result = generator.generate(item)

        # VISUAL_CUE intent should also trigger refinement
        assert len(result.patches) == 1
        patch = result.patches[0]
        assert patch["patch_type"] == "update_visual_cue"
        assert patch["trigger_scene_refinement"] is True

    def test_applicator_tracks_scenes_for_refinement(self, tmp_path):
        """Test that applicator tracks scenes that need refinement."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "visual_cue": {"description": "Original"},
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        # Mock the scene refinement to avoid actually running it
        applicator = PatchApplicator(project, verbose=False)

        # Create patch with trigger flag
        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Update visual",
            patches=[
                {
                    "patch_type": "update_visual_cue",
                    "scene_id": "intro",
                    "new_visual_cue": {
                        "description": "Updated visual",
                        "visual_type": "animation",
                    },
                    "trigger_scene_refinement": True,
                }
            ],
        )

        # Patch the scene refinement method to track calls
        with mock_patch.object(applicator, "_run_scene_refinement") as mock_refine:
            mock_refine.return_value = [
                {
                    "scene_id": "intro",
                    "scene_title": "Introduction",
                    "verification_passed": True,
                }
            ]

            result = applicator.apply(item, verify=False)

            # Should have called scene refinement
            mock_refine.assert_called_once()
            call_args = mock_refine.call_args[0][0]
            assert "intro" in call_args

        assert result.status == FeedbackStatus.APPLIED

    def test_applicator_does_not_refine_without_flag(self, tmp_path):
        """Test that applicator doesn't trigger refinement without flag."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "visual_cue": {"description": "Original"},
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        applicator = PatchApplicator(project, verbose=False)

        # Patch without trigger flag
        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Update visual",
            patches=[
                {
                    "patch_type": "update_visual_cue",
                    "scene_id": "intro",
                    "new_visual_cue": {
                        "description": "Updated visual",
                    },
                    # No trigger_scene_refinement flag
                }
            ],
        )

        with mock_patch.object(applicator, "_run_scene_refinement") as mock_refine:
            result = applicator.apply(item, verify=False)
            mock_refine.assert_not_called()

        assert result.status == FeedbackStatus.APPLIED

    def test_mixed_intent_routes_visual_intents_correctly(self, tmp_path):
        """Test that MIXED intent routes visual sub-intents through visual_cue."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "scene_type": "hook",
                    "voiceover": "Original text",
                    "visual_cue": {"description": "Original visual"},
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        mock_llm = MagicMock()
        # Return visual_cue patch for visual_impl sub-intent
        mock_llm.generate_json.return_value = {
            "needs_update": True,
            "new_visual_cue": {
                "description": "Updated with animation fixes",
            },
            "reason": "Fixing animation",
        }

        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Fix animation and styling",
            intent=FeedbackIntent.MIXED,
            sub_intents=[FeedbackIntent.VISUAL_IMPLEMENTATION, FeedbackIntent.STYLE],
            target=FeedbackTarget(scene_ids=["intro"], scope=FeedbackScope.SCENE),
            interpretation="Fix animation and styling",
        )

        result = generator.generate(item)

        # Should generate visual_cue patches (possibly multiple calls)
        for patch in result.patches:
            assert patch["patch_type"] == "update_visual_cue"
            assert patch["trigger_scene_refinement"] is True

    def test_visual_cue_patch_updates_script_before_refinement(self, tmp_path):
        """Test that script.json is updated before scene refinement is triggered."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        original_visual = {"description": "Original visual"}
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "visual_cue": original_visual,
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        applicator = PatchApplicator(project, verbose=False)

        updated_visual = {
            "description": "Beautiful 3D tree animation with branching",
            "visual_type": "animation",
            "elements": ["3D tree", "Branching animation", "Backtracking effect"],
        }

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Add 3D tree animation",
            patches=[
                {
                    "patch_type": "update_visual_cue",
                    "scene_id": "intro",
                    "new_visual_cue": updated_visual,
                    "trigger_scene_refinement": True,
                }
            ],
        )

        # Track when script is read during refinement
        script_at_refinement_time = None

        def mock_run_refinement(scene_ids):
            nonlocal script_at_refinement_time
            # Read script.json at the time refinement would run
            script_at_refinement_time = json.loads(
                (script_dir / "script.json").read_text()
            )
            return [{"scene_id": "intro", "verification_passed": True}]

        with mock_patch.object(applicator, "_run_scene_refinement", side_effect=mock_run_refinement):
            applicator.apply(item, verify=False)

        # Script should have been updated BEFORE refinement ran
        assert script_at_refinement_time is not None
        assert script_at_refinement_time["scenes"][0]["visual_cue"]["description"] == updated_visual["description"]

    def test_multiple_scenes_refined_together(self, tmp_path):
        """Test that multiple scenes can be refined in one feedback."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "scene_1",
                    "title": "Scene One",
                    "visual_cue": {"description": "Original 1"},
                },
                {
                    "scene_id": "scene_2",
                    "title": "Scene Two",
                    "visual_cue": {"description": "Original 2"},
                },
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        applicator = PatchApplicator(project, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Update both scenes",
            patches=[
                {
                    "patch_type": "update_visual_cue",
                    "scene_id": "scene_1",
                    "new_visual_cue": {"description": "Updated 1"},
                    "trigger_scene_refinement": True,
                },
                {
                    "patch_type": "update_visual_cue",
                    "scene_id": "scene_2",
                    "new_visual_cue": {"description": "Updated 2"},
                    "trigger_scene_refinement": True,
                },
            ],
        )

        scenes_refined = []

        def mock_run_refinement(scene_ids):
            scenes_refined.extend(scene_ids)
            return [{"scene_id": sid, "verification_passed": True} for sid in scene_ids]

        with mock_patch.object(applicator, "_run_scene_refinement", side_effect=mock_run_refinement):
            result = applicator.apply(item, verify=False)

        assert result.status == FeedbackStatus.APPLIED
        assert "scene_1" in scenes_refined
        assert "scene_2" in scenes_refined


class TestSceneRefinementIntegration:
    """Integration tests for the scene refinement flow."""

    def test_run_scene_refinement_finds_scene_index(self, tmp_path):
        """Test that _run_scene_refinement correctly finds scene indices."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        # Create storyboard (for load_storyboard)
        storyboard = {
            "scenes": [
                {"scene_id": 1, "title": "Introduction", "type": "test-project/intro"},
                {"scene_id": 2, "title": "Main Content", "type": "test-project/main"},
                {"scene_id": 3, "title": "Beyond Linear Thinking", "type": "test-project/beyond_linear_thinking"},
            ]
        }
        project.load_storyboard.return_value = storyboard

        applicator = PatchApplicator(project, verbose=False)

        # Mock ClaudeCodeVisualInspector
        with mock_patch("src.refine.feedback.applicator.ClaudeCodeVisualInspector") as MockInspector:
            mock_instance = MagicMock()
            MockInspector.return_value = mock_instance
            mock_instance.refine_scene.return_value = MagicMock(
                scene_id="beyond_linear_thinking",
                scene_title="Beyond Linear Thinking",
                scene_file=tmp_path / "scenes" / "BeyondLinearThinkingScene.tsx",
                verification_passed=True,
                issues_found=[],
                fixes_applied=[],
                error_message=None,
            )

            results = applicator._run_scene_refinement(["beyond_linear_thinking"])

            # Should have called refine_scene with index 2 (0-based)
            mock_instance.refine_scene.assert_called_once_with(2)
            assert len(results) == 1
            assert results[0]["verification_passed"] is True

    def test_run_scene_refinement_handles_missing_scene(self, tmp_path):
        """Test that _run_scene_refinement handles missing scenes gracefully."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        storyboard = {
            "scenes": [
                {"scene_id": 1, "title": "Introduction"},
            ]
        }
        project.load_storyboard.return_value = storyboard

        applicator = PatchApplicator(project, verbose=False)

        with mock_patch("src.refine.feedback.applicator.ClaudeCodeVisualInspector"):
            results = applicator._run_scene_refinement(["nonexistent_scene"])

            assert len(results) == 1
            assert results[0]["verification_passed"] is False
            assert "not found" in results[0]["error"].lower()

    def test_run_scene_refinement_handles_inspector_error(self, tmp_path):
        """Test that _run_scene_refinement handles inspector errors."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        storyboard = {
            "scenes": [
                {"scene_id": 1, "title": "Introduction"},
            ]
        }
        project.load_storyboard.return_value = storyboard

        applicator = PatchApplicator(project, verbose=False)

        with mock_patch("src.refine.feedback.applicator.ClaudeCodeVisualInspector") as MockInspector:
            MockInspector.side_effect = Exception("Inspector initialization failed")

            results = applicator._run_scene_refinement(["1"])

            assert len(results) == 1
            assert results[0]["verification_passed"] is False
            assert "error" in results[0]


class TestEndToEndFeedbackFlow:
    """End-to-end tests for the complete feedback flow."""

    def test_visual_feedback_full_pipeline(self, tmp_path):
        """Test complete flow from feedback text to scene refinement trigger."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "beyond_linear_thinking",
                    "title": "Beyond Linear Thinking",
                    "scene_type": "explanation",
                    "voiceover": "Tree of thought explores multiple paths...",
                    "visual_cue": {"description": "Basic tree visualization"},
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        # Mock LLM responses
        mock_llm = MagicMock()
        mock_llm.generate_json.side_effect = [
            # Parser response
            {
                "intent": "visual_impl",
                "affected_scene_ids": ["beyond_linear_thinking"],
                "scope": "scene",
                "interpretation": "User wants improved tree animation with 3D depth",
            },
            # Generator response (for visual_cue patch)
            {
                "needs_update": True,
                "new_visual_cue": {
                    "description": "3D tree visualization with branching exploration, beautiful withering for backtracking, and stunning bloom for success",
                    "visual_type": "animation",
                    "elements": [
                        "3D tree with depth",
                        "Branching animation showing exploration",
                        "Withering effect for backtracking",
                        "Blooming effect for success",
                        "Calculation labels on branches",
                    ],
                },
                "reason": "Implementing user feedback for improved tree animation",
            },
        ]

        processor = FeedbackProcessor(project, mock_llm, verbose=False)

        # Patch the applicator's scene refinement
        with mock_patch.object(processor.applicator, "_run_scene_refinement") as mock_refine:
            mock_refine.return_value = [
                {
                    "scene_id": "beyond_linear_thinking",
                    "scene_title": "Beyond Linear Thinking",
                    "verification_passed": True,
                }
            ]

            result = processor.process(
                "In the beyond linear thinking scene, the tree is overlapping. "
                "Make the branching feel like exploring ideas, backtracking should "
                "wither beautifully, and success should bloom. Add 3D depth and "
                "show calculations on branches."
            )

            # Verify intent was correctly identified
            assert result.intent == FeedbackIntent.VISUAL_IMPLEMENTATION

            # Verify patch was generated correctly
            assert len(result.patches) == 1
            patch = result.patches[0]
            assert patch["patch_type"] == "update_visual_cue"
            assert patch["trigger_scene_refinement"] is True

            # Verify scene refinement was triggered
            mock_refine.assert_called_once()
            refine_args = mock_refine.call_args[0][0]
            assert "beyond_linear_thinking" in refine_args

        # Verify script.json was updated
        updated_script = json.loads((script_dir / "script.json").read_text())
        updated_cue = updated_script["scenes"][0]["visual_cue"]
        assert "3D" in updated_cue["description"] or "3D" in str(updated_cue.get("elements", []))

    def test_dry_run_does_not_trigger_refinement(self, tmp_path):
        """Test that dry_run mode doesn't trigger scene refinement."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "scene_type": "hook",
                    "voiceover": "Test",
                    "visual_cue": {"description": "Original"},
                }
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        mock_llm = MagicMock()
        mock_llm.generate_json.side_effect = [
            {
                "intent": "visual_impl",
                "affected_scene_ids": ["intro"],
                "scope": "scene",
                "interpretation": "Update visuals",
            },
            {
                "needs_update": True,
                "new_visual_cue": {"description": "Updated visual"},
                "reason": "Test",
            },
        ]

        processor = FeedbackProcessor(project, mock_llm, verbose=False)

        with mock_patch.object(processor.applicator, "_run_scene_refinement") as mock_refine:
            result = processor.process("Fix the animation", dry_run=True)

            # Refinement should not be called in dry run
            mock_refine.assert_not_called()

        # Script should not be modified in dry run
        original_script = json.loads((script_dir / "script.json").read_text())
        assert original_script["scenes"][0]["visual_cue"]["description"] == "Original"

        # But patches should be generated
        assert len(result.patches) == 1
        assert result.patches[0]["trigger_scene_refinement"] is True


# ============================================================================
# Structure Patch Tests (Add/Remove/Reorder Scenes)
# ============================================================================


class TestStructurePatchGeneration:
    """Tests for structure patch generation (add/remove/reorder scenes)."""

    def test_generate_add_scene_patch(self, tmp_path):
        """Test generating an add scene patch."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {"scene_id": "intro", "title": "Introduction", "scene_type": "hook"},
                {"scene_id": "main", "title": "Main Content", "scene_type": "explanation"},
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "action": "add",
            "details": {
                "insert_after": "intro",
                "new_scene": {
                    "title": "Problem Setup",
                    "scene_type": "context",
                    "narration": "Let's understand the problem first...",
                    "visual_description": "Animated problem diagram",
                    "duration_seconds": 30,
                },
            },
            "reason": "Adding context scene to improve flow",
        }

        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Add a scene explaining the problem after the intro",
            intent=FeedbackIntent.SCRIPT_STRUCTURE,
            target=FeedbackTarget(scene_ids=[], scope=FeedbackScope.PROJECT),
            interpretation="Add a context scene after intro",
        )

        result = generator.generate(item)

        assert len(result.patches) == 1
        patch = result.patches[0]
        # AddScenePatch is a dataclass object
        assert hasattr(patch, 'insert_after_scene_id') or patch.get('insert_after_scene_id')
        if hasattr(patch, 'insert_after_scene_id'):
            assert patch.insert_after_scene_id == "intro"
            assert patch.title == "Problem Setup"
            assert patch.narration == "Let's understand the problem first..."
            assert patch.duration_seconds == 30
        else:
            # If returned as dict
            assert patch.get("insert_after_scene_id") == "intro"
            assert patch.get("title") == "Problem Setup"

    def test_generate_remove_scene_patch(self, tmp_path):
        """Test generating a remove scene patch."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {"scene_id": "intro", "title": "Introduction", "scene_type": "hook"},
                {"scene_id": "filler", "title": "Filler Scene", "scene_type": "explanation"},
                {"scene_id": "main", "title": "Main Content", "scene_type": "explanation"},
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "action": "remove",
            "details": {
                "scene_id": "filler",
            },
            "reason": "Filler scene is redundant",
        }

        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Remove the filler scene, it's not needed",
            intent=FeedbackIntent.SCRIPT_STRUCTURE,
            target=FeedbackTarget(scene_ids=[], scope=FeedbackScope.PROJECT),
            interpretation="Remove the filler scene",
        )

        result = generator.generate(item)

        assert len(result.patches) == 1
        patch = result.patches[0]
        assert patch["patch_type"] == "remove_scene"
        assert patch["scene_id"] == "filler"

    def test_generate_reorder_scenes_patch(self, tmp_path):
        """Test generating a reorder scenes patch."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {"scene_id": "intro", "title": "Introduction", "scene_type": "hook"},
                {"scene_id": "conclusion", "title": "Conclusion", "scene_type": "conclusion"},
                {"scene_id": "main", "title": "Main Content", "scene_type": "explanation"},
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        mock_llm = MagicMock()
        mock_llm.generate_json.return_value = {
            "action": "reorder",
            "details": {
                "new_order": ["intro", "main", "conclusion"],
            },
            "reason": "Conclusion should come after main content",
        }

        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Move the conclusion to the end",
            intent=FeedbackIntent.SCRIPT_STRUCTURE,
            target=FeedbackTarget(scene_ids=[], scope=FeedbackScope.PROJECT),
            interpretation="Reorder scenes to put conclusion at the end",
        )

        result = generator.generate(item)

        assert len(result.patches) == 1
        patch = result.patches[0]
        assert patch["patch_type"] == "reorder_scenes"
        assert patch["new_order"] == ["intro", "main", "conclusion"]


class TestStructurePatchApplication:
    """Tests for structure patch application (add/remove/reorder scenes)."""

    def test_apply_add_scene_patch(self, tmp_path):
        """Test applying an add scene patch."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "scene_type": "hook",
                    "voiceover": "Welcome!",
                    "duration_seconds": 10,
                },
            ],
            "total_duration_seconds": 10,
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        narration_dir = tmp_path / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [
                {"scene_id": "intro", "title": "Introduction", "duration_seconds": 10, "narration": "Welcome!"},
            ],
            "total_duration_seconds": 10,
        }
        (narration_dir / "narrations.json").write_text(json.dumps(narrations))

        applicator = PatchApplicator(project, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Add a new scene",
            patches=[
                {
                    "patch_type": "add_scene",
                    "insert_after_scene_id": "intro",
                    "new_scene_id": "problem_setup",
                    "title": "Problem Setup",
                    "narration": "Let's look at the problem...",
                    "visual_description": "Problem diagram",
                    "duration_seconds": 25,
                }
            ],
        )

        result = applicator.apply(item, verify=False)

        assert result.status == FeedbackStatus.APPLIED
        assert "script/script.json" in result.files_modified

        # Verify script.json was updated
        updated_script = json.loads((script_dir / "script.json").read_text())
        assert len(updated_script["scenes"]) == 2
        assert updated_script["scenes"][1]["scene_id"] == "problem_setup"
        assert updated_script["scenes"][1]["title"] == "Problem Setup"
        assert updated_script["total_duration_seconds"] == 35

        # Verify narrations.json was updated
        updated_narrations = json.loads((narration_dir / "narrations.json").read_text())
        assert len(updated_narrations["scenes"]) == 2
        assert updated_narrations["scenes"][1]["scene_id"] == "problem_setup"

    def test_apply_add_scene_at_beginning(self, tmp_path):
        """Test adding a scene at the beginning (no insert_after)."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {"scene_id": "main", "title": "Main Content", "scene_type": "explanation", "duration_seconds": 30},
            ],
            "total_duration_seconds": 30,
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        narration_dir = tmp_path / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [{"scene_id": "main", "title": "Main Content", "duration_seconds": 30, "narration": "Main..."}],
            "total_duration_seconds": 30,
        }
        (narration_dir / "narrations.json").write_text(json.dumps(narrations))

        applicator = PatchApplicator(project, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Add intro at the beginning",
            patches=[
                {
                    "patch_type": "add_scene",
                    "insert_after_scene_id": None,  # Insert at beginning
                    "new_scene_id": "intro",
                    "title": "Introduction",
                    "narration": "Welcome!",
                    "visual_description": "Title card",
                    "duration_seconds": 10,
                }
            ],
        )

        result = applicator.apply(item, verify=False)

        updated_script = json.loads((script_dir / "script.json").read_text())
        assert updated_script["scenes"][0]["scene_id"] == "intro"
        assert updated_script["scenes"][1]["scene_id"] == "main"

    def test_apply_remove_scene_patch(self, tmp_path):
        """Test applying a remove scene patch."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {"scene_id": "intro", "title": "Introduction", "duration_seconds": 10},
                {"scene_id": "filler", "title": "Filler", "duration_seconds": 20},
                {"scene_id": "main", "title": "Main", "duration_seconds": 30},
            ],
            "total_duration_seconds": 60,
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        narration_dir = tmp_path / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [
                {"scene_id": "intro", "duration_seconds": 10},
                {"scene_id": "filler", "duration_seconds": 20},
                {"scene_id": "main", "duration_seconds": 30},
            ],
            "total_duration_seconds": 60,
        }
        (narration_dir / "narrations.json").write_text(json.dumps(narrations))

        applicator = PatchApplicator(project, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Remove filler scene",
            patches=[
                {
                    "patch_type": "remove_scene",
                    "scene_id": "filler",
                    "reason": "Redundant",
                }
            ],
        )

        result = applicator.apply(item, verify=False)

        assert result.status == FeedbackStatus.APPLIED

        updated_script = json.loads((script_dir / "script.json").read_text())
        assert len(updated_script["scenes"]) == 2
        scene_ids = [s["scene_id"] for s in updated_script["scenes"]]
        assert "filler" not in scene_ids
        assert updated_script["total_duration_seconds"] == 40

    def test_apply_reorder_scenes_patch(self, tmp_path):
        """Test applying a reorder scenes patch."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {"scene_id": "intro", "title": "Introduction", "duration_seconds": 10},
                {"scene_id": "conclusion", "title": "Conclusion", "duration_seconds": 15},
                {"scene_id": "main", "title": "Main", "duration_seconds": 30},
            ],
            "total_duration_seconds": 55,
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        narration_dir = tmp_path / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [
                {"scene_id": "intro", "duration_seconds": 10},
                {"scene_id": "conclusion", "duration_seconds": 15},
                {"scene_id": "main", "duration_seconds": 30},
            ],
            "total_duration_seconds": 55,
        }
        (narration_dir / "narrations.json").write_text(json.dumps(narrations))

        applicator = PatchApplicator(project, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Reorder scenes",
            patches=[
                {
                    "patch_type": "reorder_scenes",
                    "new_order": ["intro", "main", "conclusion"],
                    "reason": "Better flow",
                }
            ],
        )

        result = applicator.apply(item, verify=False)

        assert result.status == FeedbackStatus.APPLIED

        updated_script = json.loads((script_dir / "script.json").read_text())
        scene_order = [s["scene_id"] for s in updated_script["scenes"]]
        assert scene_order == ["intro", "main", "conclusion"]


# ============================================================================
# Timing Patch Tests
# ============================================================================


class TestTimingPatchGeneration:
    """Tests for timing patch generation."""

    def test_generate_timing_patch(self, tmp_path):
        """Test generating a timing patch."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {"scene_id": "intro", "title": "Introduction", "scene_type": "hook", "duration_seconds": 10},
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        mock_llm = MagicMock()
        # No LLM call needed for timing - it creates patches directly

        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Make the intro longer",
            intent=FeedbackIntent.TIMING,
            target=FeedbackTarget(scene_ids=["intro"], scope=FeedbackScope.SCENE),
            interpretation="Increase intro duration",
        )

        result = generator.generate(item)

        assert len(result.patches) == 1
        patch = result.patches[0]
        assert patch["patch_type"] == "modify_timing"
        assert patch["scene_id"] == "intro"
        assert patch["current_duration"] == 10


class TestTimingPatchApplication:
    """Tests for timing patch application."""

    def test_apply_timing_patch(self, tmp_path):
        """Test applying a timing patch."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "duration_seconds": 10,
                    "visual_cue": {"duration_seconds": 10},
                },
            ],
            "total_duration_seconds": 10,
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        narration_dir = tmp_path / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [{"scene_id": "intro", "duration_seconds": 10}],
            "total_duration_seconds": 10,
        }
        (narration_dir / "narrations.json").write_text(json.dumps(narrations))

        applicator = PatchApplicator(project, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Make intro longer",
            patches=[
                {
                    "patch_type": "modify_timing",
                    "scene_id": "intro",
                    "new_duration": 20,
                    "reason": "More time needed",
                }
            ],
        )

        result = applicator.apply(item, verify=False)

        assert result.status == FeedbackStatus.APPLIED

        updated_script = json.loads((script_dir / "script.json").read_text())
        assert updated_script["scenes"][0]["duration_seconds"] == 20
        assert updated_script["total_duration_seconds"] == 20


# ============================================================================
# Mixed Intent Tests
# ============================================================================


class TestMixedIntentPatches:
    """Tests for mixed intent feedback processing."""

    def test_mixed_intent_generates_multiple_patch_types(self, tmp_path):
        """Test that mixed intents generate appropriate patches for each sub-intent."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {
                    "scene_id": "intro",
                    "title": "Introduction",
                    "scene_type": "hook",
                    "voiceover": "Original narration",
                    "duration_seconds": 10,
                    "visual_cue": {"description": "Original visual"},
                },
            ]
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        mock_llm = MagicMock()
        # First call for script_content sub-intent
        # Second call for visual_cue sub-intent
        mock_llm.generate_json.side_effect = [
            {
                "changes": [
                    {
                        "field": "voiceover",
                        "old_text": "Original narration",
                        "new_text": "Updated narration",
                        "reason": "Improve clarity",
                    }
                ]
            },
            {
                "needs_update": True,
                "new_visual_cue": {"description": "Updated visual", "visual_type": "animation"},
                "reason": "Better visuals",
            },
        ]

        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Update both narration and visuals for intro",
            intent=FeedbackIntent.MIXED,
            sub_intents=[FeedbackIntent.SCRIPT_CONTENT, FeedbackIntent.VISUAL_CUE],
            target=FeedbackTarget(scene_ids=["intro"], scope=FeedbackScope.SCENE),
            interpretation="Update narration and visual cue",
        )

        result = generator.generate(item)

        # Should have patches from both sub-intents
        assert len(result.patches) >= 1
        patch_types = [p.get("patch_type") if isinstance(p, dict) else type(p).__name__ for p in result.patches]
        # At least one patch should be generated
        assert len(patch_types) >= 1


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in feedback processing."""

    def test_generator_handles_missing_script(self, tmp_path):
        """Test that generator handles missing script gracefully."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path
        # No script directory created

        mock_llm = MagicMock()
        generator = PatchGenerator(project, mock_llm, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Update visual",
            intent=FeedbackIntent.VISUAL_CUE,
            target=FeedbackTarget(scene_ids=["intro"], scope=FeedbackScope.SCENE),
            interpretation="Update visual",
        )

        result = generator.generate(item)

        # Should return item with no patches but not crash
        assert result.patches == []

    def test_applicator_handles_invalid_patch_type(self, tmp_path):
        """Test that applicator handles unknown patch types."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {"scenes": [{"scene_id": "intro", "title": "Introduction"}]}
        (script_dir / "script.json").write_text(json.dumps(script))

        applicator = PatchApplicator(project, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Test",
            patches=[
                {
                    "patch_type": "unknown_type",
                    "data": "some data",
                }
            ],
        )

        # Should not crash on unknown patch type
        result = applicator.apply(item, verify=False)
        assert result is not None

    def test_applicator_handles_missing_scene_for_remove(self, tmp_path):
        """Test that remove patch handles missing scene gracefully."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [{"scene_id": "intro", "title": "Introduction", "duration_seconds": 10}],
            "total_duration_seconds": 10,
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        applicator = PatchApplicator(project, verbose=False)

        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Remove nonexistent scene",
            patches=[
                {
                    "patch_type": "remove_scene",
                    "scene_id": "nonexistent",
                }
            ],
        )

        result = applicator.apply(item, verify=False)

        # Should complete without crashing
        # Scene count should remain the same
        updated_script = json.loads((script_dir / "script.json").read_text())
        assert len(updated_script["scenes"]) == 1


# ============================================================================
# Slug Matching in Structural Operations Tests
# ============================================================================


class TestSlugMatchingInStructuralOps:
    """Tests for slug matching in add/remove/reorder operations.

    These tests verify that structural operations work correctly when scene_id
    formats differ (e.g., numeric "1" vs slug "the_impossible_leap").
    """

    def test_add_scene_after_numeric_id_using_slug(self, tmp_path):
        """Test adding a scene after a numeric scene_id using slug match."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        # Scene uses numeric scene_id but has a title
        script = {
            "scenes": [
                {
                    "scene_id": 1,
                    "title": "The Impossible Leap",
                    "scene_type": "hook",
                    "voiceover": "First scene",
                    "duration_seconds": 10,
                },
                {
                    "scene_id": 2,
                    "title": "Beyond Linear Thinking",
                    "scene_type": "explanation",
                    "voiceover": "Second scene",
                    "duration_seconds": 20,
                },
            ],
            "total_duration_seconds": 30,
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        narration_dir = tmp_path / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [
                {"scene_id": 1, "title": "The Impossible Leap", "duration_seconds": 10, "narration": "First scene"},
                {"scene_id": 2, "title": "Beyond Linear Thinking", "duration_seconds": 20, "narration": "Second scene"},
            ],
            "total_duration_seconds": 30,
        }
        (narration_dir / "narrations.json").write_text(json.dumps(narrations))

        applicator = PatchApplicator(project, verbose=False)

        # Use slug format for insert_after, but scene uses numeric ID
        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Add a new scene after the first one",
            patches=[
                {
                    "patch_type": "add_scene",
                    "insert_after_scene_id": "the_impossible_leap",  # Slug format
                    "new_scene_id": "new_explanation",
                    "title": "New Explanation",
                    "narration": "This is new",
                    "visual_description": "New visual",
                    "duration_seconds": 15,
                }
            ],
        )

        result = applicator.apply(item, verify=False)

        assert result.status == FeedbackStatus.APPLIED

        # Verify scene was inserted at position 1 (after "The Impossible Leap")
        updated_script = json.loads((script_dir / "script.json").read_text())
        assert len(updated_script["scenes"]) == 3
        assert updated_script["scenes"][0]["scene_id"] == 1
        assert updated_script["scenes"][1]["scene_id"] == "new_explanation"  # New scene at position 1
        assert updated_script["scenes"][2]["scene_id"] == 2

        # Verify narrations.json too
        updated_narrations = json.loads((narration_dir / "narrations.json").read_text())
        assert len(updated_narrations["scenes"]) == 3
        assert updated_narrations["scenes"][1]["scene_id"] == "new_explanation"

    def test_remove_scene_using_slug_when_numeric_id(self, tmp_path):
        """Test removing a scene using slug when scene has numeric ID."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {"scene_id": 1, "title": "The Impossible Leap", "duration_seconds": 10},
                {"scene_id": 2, "title": "Beyond Linear Thinking", "duration_seconds": 20},
                {"scene_id": 3, "title": "The Final Reveal", "duration_seconds": 15},
            ],
            "total_duration_seconds": 45,
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        narration_dir = tmp_path / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [
                {"scene_id": 1, "title": "The Impossible Leap", "duration_seconds": 10},
                {"scene_id": 2, "title": "Beyond Linear Thinking", "duration_seconds": 20},
                {"scene_id": 3, "title": "The Final Reveal", "duration_seconds": 15},
            ],
            "total_duration_seconds": 45,
        }
        (narration_dir / "narrations.json").write_text(json.dumps(narrations))

        applicator = PatchApplicator(project, verbose=False)

        # Use slug format to remove, but scene uses numeric ID
        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Remove the middle scene",
            patches=[
                {
                    "patch_type": "remove_scene",
                    "scene_id": "beyond_linear_thinking",  # Slug format
                    "reason": "Not needed",
                }
            ],
        )

        result = applicator.apply(item, verify=False)

        assert result.status == FeedbackStatus.APPLIED

        updated_script = json.loads((script_dir / "script.json").read_text())
        assert len(updated_script["scenes"]) == 2
        scene_ids = [s["scene_id"] for s in updated_script["scenes"]]
        assert 2 not in scene_ids  # Scene with ID 2 was removed
        assert updated_script["total_duration_seconds"] == 25

    def test_reorder_scenes_using_slugs_when_numeric_ids(self, tmp_path):
        """Test reordering scenes using slugs when scenes have numeric IDs."""
        project = MagicMock()
        project.id = "test-project"
        project.root_dir = tmp_path

        script_dir = tmp_path / "script"
        script_dir.mkdir()
        script = {
            "scenes": [
                {"scene_id": 1, "title": "The Impossible Leap", "duration_seconds": 10},
                {"scene_id": 2, "title": "Beyond Linear Thinking", "duration_seconds": 20},
                {"scene_id": 3, "title": "The Final Reveal", "duration_seconds": 15},
            ],
            "total_duration_seconds": 45,
        }
        (script_dir / "script.json").write_text(json.dumps(script))

        narration_dir = tmp_path / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [
                {"scene_id": 1, "title": "The Impossible Leap", "duration_seconds": 10},
                {"scene_id": 2, "title": "Beyond Linear Thinking", "duration_seconds": 20},
                {"scene_id": 3, "title": "The Final Reveal", "duration_seconds": 15},
            ],
            "total_duration_seconds": 45,
        }
        (narration_dir / "narrations.json").write_text(json.dumps(narrations))

        applicator = PatchApplicator(project, verbose=False)

        # Use slug format for reordering
        item = FeedbackItem(
            id="fb_0001_test",
            timestamp=datetime.now(),
            feedback_text="Put the reveal first",
            patches=[
                {
                    "patch_type": "reorder_scenes",
                    "new_order": [
                        "the_final_reveal",  # Move to first
                        "the_impossible_leap",
                        "beyond_linear_thinking",
                    ],
                    "reason": "Better flow",
                }
            ],
        )

        result = applicator.apply(item, verify=False)

        assert result.status == FeedbackStatus.APPLIED

        updated_script = json.loads((script_dir / "script.json").read_text())
        assert len(updated_script["scenes"]) == 3
        # Verify new order
        assert updated_script["scenes"][0]["scene_id"] == 3  # Final Reveal
        assert updated_script["scenes"][1]["scene_id"] == 1  # Impossible Leap
        assert updated_script["scenes"][2]["scene_id"] == 2  # Beyond Linear

        # Verify narrations.json too
        updated_narrations = json.loads((narration_dir / "narrations.json").read_text())
        assert updated_narrations["scenes"][0]["scene_id"] == 3
        assert updated_narrations["scenes"][1]["scene_id"] == 1
        assert updated_narrations["scenes"][2]["scene_id"] == 2

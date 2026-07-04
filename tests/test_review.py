"""Tests for review CLI module."""

import pytest

from src.models import Script, ScriptScene, VisualCue
from src.review import ReviewCLI, ReviewResult
from src.review.cli import ReviewDecision


@pytest.fixture
def sample_script() -> Script:
    """Create a sample script for testing."""
    return Script(
        title="Test Script",
        total_duration_seconds=60.0,
        scenes=[
            ScriptScene(
                scene_id="scene_1",
                scene_type="hook",
                title="The Hook",
                voiceover="This is the hook that grabs attention.",
                visual_cue=VisualCue(
                    description="Animated intro sequence",
                    visual_type="animation",
                    elements=["title", "logo"],
                    duration_seconds=10.0,
                ),
                duration_seconds=10.0,
                notes="Make it punchy",
            ),
            ScriptScene(
                scene_id="scene_2",
                scene_type="explanation",
                title="The Main Point",
                voiceover="Here is the main content of the video.",
                visual_cue=VisualCue(
                    description="Diagram showing the concept",
                    visual_type="diagram",
                    elements=["boxes", "arrows"],
                    duration_seconds=40.0,
                ),
                duration_seconds=40.0,
            ),
            ScriptScene(
                scene_id="scene_3",
                scene_type="conclusion",
                title="Wrap Up",
                voiceover="In conclusion, remember this key point.",
                visual_cue=VisualCue(
                    description="Summary screen with key takeaways",
                    visual_type="animation",
                    elements=["bullet_points"],
                    duration_seconds=10.0,
                ),
                duration_seconds=10.0,
            ),
        ],
        source_document="test.md",
    )


class TestReviewCLI:
    """Tests for the ReviewCLI class."""

    def test_cli_initializes(self):
        cli = ReviewCLI()
        assert cli.console is not None

    def test_display_summary(self, sample_script, capsys):
        cli = ReviewCLI()
        cli.display_summary(
            "Test Summary",
            {
                "Title": sample_script.title,
                "Duration": f"{sample_script.total_duration_seconds}s",
                "Scenes": len(sample_script.scenes),
            },
        )
        # Rich output goes to console, so we just verify no exceptions

    def test_display_error(self, capsys):
        cli = ReviewCLI()
        cli.display_error("Something went wrong")
        # Verify no exceptions

    def test_display_success(self, capsys):
        cli = ReviewCLI()
        cli.display_success("Operation completed")
        # Verify no exceptions

    def test_display_info(self, capsys):
        cli = ReviewCLI()
        cli.display_info("Just letting you know")
        # Verify no exceptions


class TestReviewResult:
    """Tests for ReviewResult."""

    def test_approve_result(self, sample_script):
        result = ReviewResult(
            decision=ReviewDecision.APPROVE,
            content=sample_script,
            feedback="Looks good!",
        )
        assert result.decision == ReviewDecision.APPROVE
        assert result.content == sample_script

    def test_reject_result(self, sample_script):
        result = ReviewResult(
            decision=ReviewDecision.REJECT,
            content=sample_script,
            feedback="Needs more detail in scene 2",
        )
        assert result.decision == ReviewDecision.REJECT
        assert "more detail" in result.feedback

    def test_edit_result_with_changes(self, sample_script):
        result = ReviewResult(
            decision=ReviewDecision.EDIT,
            content=sample_script,
            feedback="Made some edits",
            changes_made=["Updated voiceover in scene 1", "Fixed timing"],
        )
        assert result.decision == ReviewDecision.EDIT
        assert len(result.changes_made) == 2


class TestReviewDecision:
    """Tests for ReviewDecision enum."""

    def test_decision_values(self):
        assert ReviewDecision.APPROVE.value == "approve"
        assert ReviewDecision.EDIT.value == "edit"
        assert ReviewDecision.REJECT.value == "reject"

    def test_decision_from_string(self):
        assert ReviewDecision("approve") == ReviewDecision.APPROVE
        assert ReviewDecision("edit") == ReviewDecision.EDIT
        assert ReviewDecision("reject") == ReviewDecision.REJECT

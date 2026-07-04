"""Tests for visual inspector."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.refine.models import (
    Beat,
    Issue,
    IssueType,
    Fix,
    FixStatus,
    SceneRefinementResult,
)
from src.refine.visual.inspector import (
    VisualInspector,
    MockVisualInspector,
    ClaudeCodeVisualInspector,
    CLAUDE_CODE_VISUAL_INSPECTION_PROMPT,
)
from src.refine.visual.beat_parser import MockBeatParser
from src.refine.visual.screenshot import MockScreenshotCapture


class TestVisualInspector:
    """Tests for VisualInspector class."""

    def test_inspector_initialization(self, project_with_files, mock_llm_provider):
        """Test VisualInspector initialization."""
        inspector = VisualInspector(
            project=project_with_files,
            llm_provider=mock_llm_provider,
        )
        assert inspector.project == project_with_files
        assert inspector.llm == mock_llm_provider

    def test_inspector_creates_screenshots_dir(self, project_with_files, mock_llm_provider):
        """Test that inspector creates screenshots directory."""
        screenshots_dir = project_with_files.root_dir / "test_screenshots"
        inspector = VisualInspector(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            screenshots_dir=screenshots_dir,
        )
        assert inspector.screenshots_dir.exists()

    def test_inspector_verbose_mode(self, project_with_files, mock_llm_provider, capsys):
        """Test verbose mode prints messages."""
        inspector = VisualInspector(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=True,
        )
        inspector._log("Test message")
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_inspector_quiet_mode(self, project_with_files, mock_llm_provider, capsys):
        """Test quiet mode suppresses messages."""
        inspector = VisualInspector(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )
        inspector._log("Test message")
        captured = capsys.readouterr()
        assert captured.out == ""


class TestMockVisualInspector:
    """Tests for MockVisualInspector."""

    def test_mock_inspector_initialization(self, project_with_files):
        """Test MockVisualInspector initialization."""
        inspector = MockVisualInspector(project_with_files, verbose=False)
        assert inspector.project == project_with_files
        assert isinstance(inspector.beat_parser, MockBeatParser)

    def test_mock_inspector_refine_scene(self, project_with_files):
        """Test MockVisualInspector refine_scene."""
        inspector = MockVisualInspector(project_with_files, verbose=False)

        result = inspector.refine_scene(0)

        assert result is not None
        assert isinstance(result, SceneRefinementResult)
        assert result.scene_id == "scene1_hook"

    def test_mock_inspector_returns_mock_issues(self, project_with_files):
        """Test that mock inspector returns mock issues."""
        inspector = MockVisualInspector(project_with_files, verbose=False)

        result = inspector.refine_scene(0)

        # Mock inspector returns one mock issue
        assert len(result.issues_found) >= 1
        assert result.issues_found[0].principle_violated == IssueType.VISUAL_HIERARCHY

    def test_mock_inspector_applies_mock_fixes(self, project_with_files):
        """Test that mock inspector applies mock fixes."""
        inspector = MockVisualInspector(project_with_files, verbose=False)

        result = inspector.refine_scene(0)

        # Mock inspector applies fixes for issues
        assert len(result.fixes_applied) >= 1
        assert result.fixes_applied[0].status == FixStatus.APPLIED

    def test_mock_inspector_verification_passes(self, project_with_files):
        """Test that mock verification always passes."""
        inspector = MockVisualInspector(project_with_files, verbose=False)

        result = inspector.refine_scene(0)

        assert result.verification_passed is True


class TestSceneRefinement:
    """Tests for scene refinement process."""

    def test_refine_scene_invalid_index(self, project_with_files):
        """Test refinement with invalid scene index."""
        inspector = MockVisualInspector(project_with_files, verbose=False)

        result = inspector.refine_scene(999)

        assert result.error_message is not None
        assert "scene" in result.error_message.lower() or "index" in result.error_message.lower()

    def test_refine_scene_returns_result(self, project_with_files):
        """Test that refine_scene returns a SceneRefinementResult."""
        inspector = MockVisualInspector(project_with_files, verbose=False)

        result = inspector.refine_scene(0)

        assert isinstance(result, SceneRefinementResult)
        assert result.scene_id is not None
        assert result.scene_title is not None

    def test_refine_scene_captures_beats(self, project_with_files):
        """Test that refine_scene captures beats."""
        inspector = MockVisualInspector(project_with_files, verbose=False)

        result = inspector.refine_scene(0)

        # Should have parsed beats
        assert result.beats is not None
        assert len(result.beats) > 0


class TestIssueDetection:
    """Tests for issue detection in visual inspection."""

    def test_parse_issues_from_analysis(self, project_with_files, mock_llm_provider):
        """Test parsing issues from analysis response."""
        inspector = VisualInspector(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )

        analysis_data = {
            "issues": [
                {
                    "beat_index": 0,
                    "principle_violated": "show_dont_tell",
                    "description": "Not showing the concept visually",
                    "severity": "high",
                },
                {
                    "beat_index": 1,
                    "principle_violated": "breathing_room",
                    "description": "Too cluttered",
                    "severity": "medium",
                },
            ]
        }

        issues = inspector._parse_issues(analysis_data, [])

        assert len(issues) == 2
        assert issues[0].principle_violated == IssueType.SHOW_DONT_TELL
        assert issues[1].principle_violated == IssueType.BREATHING_ROOM

    def test_parse_issues_empty(self, project_with_files, mock_llm_provider):
        """Test parsing empty issues list."""
        inspector = VisualInspector(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )

        analysis_data = {"issues": [], "passes_quality_bar": True}

        issues = inspector._parse_issues(analysis_data, [])

        assert len(issues) == 0

    def test_parse_issues_unknown_principle(self, project_with_files, mock_llm_provider):
        """Test parsing issues with unknown principle code."""
        inspector = VisualInspector(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )

        analysis_data = {
            "issues": [
                {
                    "beat_index": 0,
                    "principle_violated": "unknown_principle",
                    "description": "Some issue",
                    "severity": "low",
                },
            ]
        }

        issues = inspector._parse_issues(analysis_data, [])

        assert len(issues) == 1
        assert issues[0].principle_violated == IssueType.OTHER


class TestJSONParsing:
    """Tests for JSON parsing from LLM responses."""

    def test_parse_json_from_clean_response(self, project_with_files, mock_llm_provider):
        """Test parsing clean JSON response."""
        inspector = VisualInspector(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )

        response = '{"issues": [], "passes_quality_bar": true}'
        result = inspector._parse_json_from_response(response)

        assert result == {"issues": [], "passes_quality_bar": True}

    def test_parse_json_from_mixed_response(self, project_with_files, mock_llm_provider):
        """Test parsing JSON embedded in text."""
        inspector = VisualInspector(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )

        response = 'Here is my analysis:\n\n{"issues": [], "summary": "Good scene"}\n\nThat looks fine.'
        result = inspector._parse_json_from_response(response)

        assert "issues" in result
        assert "summary" in result

    def test_parse_json_from_invalid_response(self, project_with_files, mock_llm_provider):
        """Test parsing invalid JSON returns empty dict."""
        inspector = VisualInspector(
            project=project_with_files,
            llm_provider=mock_llm_provider,
            verbose=False,
        )

        response = "This response has no JSON in it."
        result = inspector._parse_json_from_response(response)

        assert result == {}


class TestSceneFileFinding:
    """Tests for finding scene files."""

    def test_find_scene_file_exists(self, project_with_files):
        """Test finding an existing scene file."""
        inspector = MockVisualInspector(project_with_files, verbose=False)

        scene_info = {
            "id": "scene1_hook",
            "title": "The Impossible Leap",
            "type": "test-project/impossible_leap",
        }

        scene_file = inspector._find_scene_file(scene_info)

        # The fixture creates TheImpossibleLeapScene.tsx
        assert scene_file is not None
        assert scene_file.exists()

    def test_find_scene_file_not_found(self, project_with_files):
        """Test finding a non-existent scene file."""
        inspector = MockVisualInspector(project_with_files, verbose=False)

        scene_info = {
            "id": "nonexistent",
            "title": "Nonexistent Scene",
            "type": "test-project/nonexistent_scene_type",
        }

        scene_file = inspector._find_scene_file(scene_info)

        # Should return None for non-existent scene
        assert scene_file is None


class TestBeatParsing:
    """Tests for beat parsing in inspector."""

    def test_parse_beats_from_narration(self, project_with_files):
        """Test parsing beats from narration."""
        inspector = MockVisualInspector(project_with_files, verbose=False)

        scene_info = {
            "narration": "Test narration with content.",
            "duration_seconds": 10.0,
        }

        beats = inspector._parse_beats(scene_info)

        assert len(beats) > 0
        assert all(isinstance(b, Beat) for b in beats)

    def test_parse_beats_empty_narration(self, project_with_files):
        """Test parsing beats from empty narration."""
        inspector = MockVisualInspector(project_with_files, verbose=False)

        scene_info = {
            "narration": "",
            "duration_seconds": 10.0,
        }

        beats = inspector._parse_beats(scene_info)

        # Should return a single beat for the whole scene
        assert len(beats) == 1
        assert beats[0].start_seconds == 0
        assert beats[0].end_seconds == 10.0


class TestClaudeCodeVisualInspector:
    """Tests for ClaudeCodeVisualInspector class."""

    def test_inspector_initialization(self, project_with_files):
        """Test ClaudeCodeVisualInspector initialization."""
        inspector = ClaudeCodeVisualInspector(
            project=project_with_files,
            verbose=False,
        )
        assert inspector.project == project_with_files
        assert inspector.timeout == 900  # Default 15 minutes

    def test_inspector_custom_timeout(self, project_with_files):
        """Test inspector with custom timeout."""
        inspector = ClaudeCodeVisualInspector(
            project=project_with_files,
            verbose=False,
            timeout=1800,  # 30 minutes
        )
        assert inspector.timeout == 1800

    def test_parse_claude_code_output_with_json_block(self, project_with_files):
        """Test parsing JSON from Claude Code output with markdown code block."""
        inspector = ClaudeCodeVisualInspector(project_with_files, verbose=False)

        output = '''Here is my analysis:

```json
{
  "issues_found": [
    {"beat_index": 0, "description": "Test issue", "principle_violated": "show_dont_tell"}
  ],
  "fixes_applied": [],
  "verification_passed": true
}
```

That's the summary.'''

        result = inspector._parse_claude_code_output(output)

        assert result["verification_passed"] is True
        assert len(result["issues_found"]) == 1
        assert result["issues_found"][0]["beat_index"] == 0

    def test_parse_claude_code_output_no_json(self, project_with_files):
        """Test parsing output with no JSON returns empty result."""
        inspector = ClaudeCodeVisualInspector(project_with_files, verbose=False)

        output = "I completed the inspection but forgot to output JSON."

        result = inspector._parse_claude_code_output(output)

        assert result["issues_found"] == []
        assert result["fixes_applied"] == []
        assert result["verification_passed"] is False
        assert "raw_output" in result

    def test_parse_issues_from_result(self, project_with_files):
        """Test parsing issues from Claude Code result."""
        inspector = ClaudeCodeVisualInspector(project_with_files, verbose=False)

        result = {
            "issues_found": [
                {
                    "beat_index": 0,
                    "principle_violated": "show_dont_tell",
                    "description": "Not showing visually",
                    "severity": "high",
                },
                {
                    "beat_index": 1,
                    "principle_violated": "breathing_room",
                    "description": "Too cluttered",
                    "severity": "medium",
                },
            ]
        }

        issues = inspector._parse_issues_from_result(result)

        assert len(issues) == 2
        assert issues[0].principle_violated == IssueType.SHOW_DONT_TELL
        assert issues[1].principle_violated == IssueType.BREATHING_ROOM

    def test_parse_fixes_from_result(self, project_with_files):
        """Test parsing fixes from Claude Code result."""
        inspector = ClaudeCodeVisualInspector(project_with_files, verbose=False)
        scene_file = Path("/test/scene.tsx")

        result = {
            "fixes_applied": [
                {
                    "beat_index": 0,
                    "description": "Added opacity animation",
                    "lines_changed": "10-25",
                },
            ]
        }

        fixes = inspector._parse_fixes_from_result(result, scene_file)

        assert len(fixes) == 1
        assert fixes[0].description == "Added opacity animation"
        assert fixes[0].status == FixStatus.APPLIED

    def test_ensure_remotion_running_already_running(self, project_with_files):
        """Test _ensure_remotion_running when Remotion is already running."""
        inspector = ClaudeCodeVisualInspector(project_with_files, verbose=False)

        with patch("src.refine.visual.inspector.check_remotion_running", return_value=True):
            result = inspector._ensure_remotion_running()

        assert result is True

    def test_ensure_remotion_running_starts_successfully(self, project_with_files):
        """Test _ensure_remotion_running starts Remotion when not running."""
        inspector = ClaudeCodeVisualInspector(project_with_files, verbose=False)

        # First call returns False (not running), subsequent calls return True (started)
        call_count = [0]
        def mock_check(*args):
            call_count[0] += 1
            return call_count[0] > 1  # False on first call, True after

        # Mock Path.exists to return True for remotion dir and package.json
        original_exists = Path.exists
        def mock_exists(self):
            if "remotion" in str(self) or "package.json" in str(self):
                return True
            return original_exists(self)

        with patch("src.refine.visual.inspector.check_remotion_running", side_effect=mock_check):
            with patch("subprocess.Popen") as mock_popen:
                mock_popen.return_value = MagicMock()
                with patch.object(Path, "exists", mock_exists):
                    result = inspector._ensure_remotion_running()

        assert result is True
        mock_popen.assert_called_once()

    def test_ensure_remotion_running_fails_to_start(self, project_with_files):
        """Test _ensure_remotion_running returns False when Remotion fails to start."""
        inspector = ClaudeCodeVisualInspector(project_with_files, verbose=False)

        # Mock Path.exists to return True for remotion dir and package.json
        original_exists = Path.exists
        def mock_exists(self):
            if "remotion" in str(self) or "package.json" in str(self):
                return True
            return original_exists(self)

        with patch("src.refine.visual.inspector.check_remotion_running", return_value=False):
            with patch("subprocess.Popen") as mock_popen:
                mock_popen.return_value = MagicMock()
                # Patch time.sleep to avoid long waits
                with patch("time.sleep"):
                    with patch.object(Path, "exists", mock_exists):
                        result = inspector._ensure_remotion_running()

        assert result is False


class TestClaudeCodePromptTemplate:
    """Tests for Claude Code visual inspection prompt template."""

    def test_prompt_template_has_placeholders(self):
        """Test that the prompt template has required placeholders."""
        required_placeholders = [
            "{remotion_url}",
            "{scene_title}",
            "{scene_file}",
            "{narration_text}",
            "{beats_info}",
            "{beat_frames_list}",
            "{first_beat_frame}",
            "{scene_number}",
            "{total_frames}",
            "{num_beats}",
            "{principles}",
        ]

        for placeholder in required_placeholders:
            assert placeholder in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT, \
                f"Missing placeholder: {placeholder}"

        # duration_seconds uses format specifier
        assert "duration_seconds" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

    def test_prompt_template_includes_do_not_read_instruction(self):
        """Test that prompt tells agent NOT to read files (we pre-calculate everything)."""
        assert "DO NOT" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "storyboard" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT.lower()
        assert "{remotion_url}" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

    def test_prompt_template_indicates_scene_starts_at_frame_zero(self):
        """Test that prompt indicates scene starts at frame 0 (SingleScenePlayer)."""
        assert "frame 0" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "no navigation math needed" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

    def test_prompt_template_includes_json_output_format(self):
        """Test that prompt includes expected JSON output format."""
        assert "issues_found" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "fixes_applied" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT
        assert "verification_passed" in CLAUDE_CODE_VISUAL_INSPECTION_PROMPT

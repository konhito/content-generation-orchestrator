"""Comprehensive tests for fact checking module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.factcheck import (
    FactChecker,
    FactCheckError,
    FactCheckIssue,
    FactCheckReport,
    FactCheckSummary,
    IssueCategory,
    IssueSeverity,
    run_fact_check,
)
from src.factcheck.prompts import FACT_CHECK_MOCK_RESPONSE


class TestIssueSeverity:
    """Tests for IssueSeverity enum."""

    def test_all_severity_levels(self):
        """Should have all expected severity levels."""
        assert IssueSeverity.CRITICAL.value == "critical"
        assert IssueSeverity.HIGH.value == "high"
        assert IssueSeverity.MEDIUM.value == "medium"
        assert IssueSeverity.LOW.value == "low"
        assert IssueSeverity.INFO.value == "info"

    def test_severity_from_string(self):
        """Should create severity from string value."""
        assert IssueSeverity("critical") == IssueSeverity.CRITICAL
        assert IssueSeverity("high") == IssueSeverity.HIGH


class TestIssueCategory:
    """Tests for IssueCategory enum."""

    def test_all_categories(self):
        """Should have all expected categories."""
        expected = [
            "factual_error",
            "outdated_info",
            "missing_context",
            "oversimplification",
            "misleading",
            "unsupported_claim",
            "terminology",
            "attribution",
            "numerical",
            "logical",
            "improvement",
        ]
        for cat in expected:
            assert IssueCategory(cat) is not None

    def test_category_from_string(self):
        """Should create category from string value."""
        assert IssueCategory("factual_error") == IssueCategory.FACTUAL_ERROR
        assert IssueCategory("terminology") == IssueCategory.TERMINOLOGY


class TestFactCheckIssue:
    """Tests for FactCheckIssue dataclass."""

    @pytest.fixture
    def sample_issue(self):
        """Create a sample issue for testing."""
        return FactCheckIssue(
            id="issue_1",
            severity=IssueSeverity.MEDIUM,
            category=IssueCategory.TERMINOLOGY,
            location="scene1_hook",
            original_text="The example text",
            issue_description="This term is imprecise",
            correction="Use the correct term",
            source_reference="Source document section 1.2",
            confidence=0.85,
            verified_via_web=True,
        )

    def test_issue_to_dict(self, sample_issue):
        """Should convert issue to dictionary."""
        d = sample_issue.to_dict()
        assert d["id"] == "issue_1"
        assert d["severity"] == "medium"
        assert d["category"] == "terminology"
        assert d["location"] == "scene1_hook"
        assert d["original_text"] == "The example text"
        assert d["confidence"] == 0.85
        assert d["verified_via_web"] is True

    def test_issue_from_dict(self):
        """Should create issue from dictionary."""
        data = {
            "id": "issue_2",
            "severity": "high",
            "category": "factual_error",
            "location": "scene2_main",
            "original_text": "Wrong fact",
            "issue_description": "This is incorrect",
            "correction": "Correct fact",
            "source_reference": "Web source",
            "confidence": 0.95,
            "verified_via_web": False,
        }
        issue = FactCheckIssue.from_dict(data)
        assert issue.id == "issue_2"
        assert issue.severity == IssueSeverity.HIGH
        assert issue.category == IssueCategory.FACTUAL_ERROR
        assert issue.confidence == 0.95

    def test_issue_roundtrip(self, sample_issue):
        """Should roundtrip through dict conversion."""
        d = sample_issue.to_dict()
        restored = FactCheckIssue.from_dict(d)
        assert restored.id == sample_issue.id
        assert restored.severity == sample_issue.severity
        assert restored.category == sample_issue.category


class TestFactCheckSummary:
    """Tests for FactCheckSummary dataclass."""

    @pytest.fixture
    def sample_summary(self):
        """Create a sample summary for testing."""
        return FactCheckSummary(
            total_issues=10,
            critical_count=1,
            high_count=2,
            medium_count=3,
            low_count=3,
            info_count=1,
            scenes_with_issues=["scene1", "scene2", "scene3"],
            overall_accuracy_score=0.85,
            web_verified_count=5,
        )

    def test_summary_to_dict(self, sample_summary):
        """Should convert summary to dictionary."""
        d = sample_summary.to_dict()
        assert d["total_issues"] == 10
        assert d["critical_count"] == 1
        assert d["overall_accuracy_score"] == 0.85
        assert len(d["scenes_with_issues"]) == 3

    def test_summary_from_dict(self):
        """Should create summary from dictionary."""
        data = {
            "total_issues": 5,
            "critical_count": 0,
            "high_count": 1,
            "medium_count": 2,
            "low_count": 1,
            "info_count": 1,
            "scenes_with_issues": ["scene1"],
            "overall_accuracy_score": 0.92,
            "web_verified_count": 2,
        }
        summary = FactCheckSummary.from_dict(data)
        assert summary.total_issues == 5
        assert summary.overall_accuracy_score == 0.92

    def test_summary_defaults(self):
        """Should have sensible defaults."""
        summary = FactCheckSummary()
        assert summary.total_issues == 0
        assert summary.overall_accuracy_score == 1.0
        assert summary.scenes_with_issues == []


class TestFactCheckReport:
    """Tests for FactCheckReport dataclass."""

    @pytest.fixture
    def sample_report(self):
        """Create a sample report for testing."""
        issues = [
            FactCheckIssue(
                id="issue_1",
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.FACTUAL_ERROR,
                location="scene1_hook",
                original_text="Wrong fact",
                issue_description="This is incorrect",
                correction="Correct fact",
                source_reference="Source",
                confidence=0.95,
            ),
            FactCheckIssue(
                id="issue_2",
                severity=IssueSeverity.LOW,
                category=IssueCategory.IMPROVEMENT,
                location="scene2_main",
                original_text="Could be better",
                issue_description="Suggestion",
                correction="Improved version",
                source_reference="Best practices",
                confidence=0.7,
            ),
        ]
        summary = FactCheckSummary(
            total_issues=2,
            critical_count=1,
            high_count=0,
            medium_count=0,
            low_count=1,
            info_count=0,
            scenes_with_issues=["scene1_hook", "scene2_main"],
            overall_accuracy_score=0.8,
        )
        return FactCheckReport(
            project_id="test-project",
            script_title="Test Script",
            issues=issues,
            summary=summary,
            source_documents=["doc1.md", "doc2.pdf"],
            recommendations=["Fix critical error", "Consider improvements"],
        )

    def test_report_to_dict(self, sample_report):
        """Should convert report to dictionary."""
        d = sample_report.to_dict()
        assert d["project_id"] == "test-project"
        assert d["script_title"] == "Test Script"
        assert len(d["issues"]) == 2
        assert d["summary"]["total_issues"] == 2
        assert len(d["source_documents"]) == 2
        assert len(d["recommendations"]) == 2

    def test_report_from_dict(self, sample_report):
        """Should create report from dictionary."""
        d = sample_report.to_dict()
        restored = FactCheckReport.from_dict(d)
        assert restored.project_id == sample_report.project_id
        assert len(restored.issues) == 2
        assert restored.summary.total_issues == 2

    def test_get_issues_by_severity(self, sample_report):
        """Should filter issues by severity."""
        critical = sample_report.get_issues_by_severity(IssueSeverity.CRITICAL)
        assert len(critical) == 1
        assert critical[0].id == "issue_1"

        low = sample_report.get_issues_by_severity(IssueSeverity.LOW)
        assert len(low) == 1
        assert low[0].id == "issue_2"

        high = sample_report.get_issues_by_severity(IssueSeverity.HIGH)
        assert len(high) == 0

    def test_get_issues_by_category(self, sample_report):
        """Should filter issues by category."""
        factual = sample_report.get_issues_by_category(IssueCategory.FACTUAL_ERROR)
        assert len(factual) == 1
        assert factual[0].id == "issue_1"

    def test_get_issues_for_scene(self, sample_report):
        """Should filter issues by scene."""
        scene1_issues = sample_report.get_issues_for_scene("scene1_hook")
        assert len(scene1_issues) == 1
        assert scene1_issues[0].id == "issue_1"

    def test_has_critical_issues(self, sample_report):
        """Should detect critical issues."""
        assert sample_report.has_critical_issues() is True

    def test_has_no_critical_issues(self):
        """Should detect when no critical issues."""
        report = FactCheckReport(
            project_id="test",
            script_title="Test",
            summary=FactCheckSummary(critical_count=0),
        )
        assert report.has_critical_issues() is False

    def test_is_accurate(self, sample_report):
        """Should check accuracy threshold."""
        assert sample_report.is_accurate(threshold=0.7) is True
        assert sample_report.is_accurate(threshold=0.9) is False


class TestFactChecker:
    """Tests for FactChecker class."""

    @pytest.fixture
    def mock_project(self, tmp_path):
        """Create a mock project with required files."""
        # Create project structure
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Create config
        config = {
            "id": "test-project",
            "title": "Test Project",
        }
        with open(project_dir / "config.json", "w") as f:
            json.dump(config, f)

        # Create input directory with source
        input_dir = project_dir / "input"
        input_dir.mkdir()
        source_md = input_dir / "source.md"
        source_md.write_text("""# Test Source

This is test source content for fact checking.

## Section 1

Some factual content here about the topic.

## Section 2

More detailed information about the subject.
""")

        # Create script
        script_dir = project_dir / "script"
        script_dir.mkdir()
        script = {
            "title": "Test Video Script",
            "total_duration_seconds": 120,
            "scenes": [
                {
                    "scene_id": "scene1_hook",
                    "scene_type": "hook",
                    "title": "The Hook",
                    "voiceover": "Welcome to our video about the topic.",
                    "visual_cue": {"description": "Title card"},
                },
                {
                    "scene_id": "scene2_main",
                    "scene_type": "explanation",
                    "title": "Main Content",
                    "voiceover": "Here is the main explanation of the topic.",
                    "visual_cue": {"description": "Diagram"},
                },
            ],
        }
        with open(script_dir / "script.json", "w") as f:
            json.dump(script, f)

        # Create narrations
        narration_dir = project_dir / "narration"
        narration_dir.mkdir()
        narrations = {
            "scenes": [
                {
                    "scene_id": "scene1_hook",
                    "title": "The Hook",
                    "narration": "Welcome to our video about the topic.",
                },
                {
                    "scene_id": "scene2_main",
                    "title": "Main Content",
                    "narration": "Here is the main explanation of the topic.",
                },
            ],
        }
        with open(narration_dir / "narrations.json", "w") as f:
            json.dump(narrations, f)

        # Create mock project object
        project = MagicMock()
        project.id = "test-project"
        project.title = "Test Project"
        project.root_dir = project_dir
        project.input_dir = input_dir

        return project

    def test_init_with_mock(self, mock_project):
        """Should initialize with mock provider."""
        checker = FactChecker(mock_project, use_mock=True)
        assert checker.use_mock is True
        assert checker.project == mock_project

    def test_init_sets_timeout(self, mock_project):
        """Should set custom timeout."""
        checker = FactChecker(mock_project, use_mock=True, timeout=300)
        assert checker.timeout == 300

    def test_load_script(self, mock_project):
        """Should load script from project."""
        checker = FactChecker(mock_project, use_mock=True)
        script = checker._load_script()
        assert script["title"] == "Test Video Script"
        assert len(script["scenes"]) == 2

    def test_load_script_not_found(self, mock_project):
        """Should raise error when script not found."""
        # Remove script file
        script_path = mock_project.root_dir / "script" / "script.json"
        script_path.unlink()

        checker = FactChecker(mock_project, use_mock=True)
        with pytest.raises(FactCheckError, match="Script not found"):
            checker._load_script()

    def test_load_narrations(self, mock_project):
        """Should load narrations from project."""
        checker = FactChecker(mock_project, use_mock=True)
        narrations = checker._load_narrations()
        assert len(narrations["scenes"]) == 2

    def test_load_narrations_not_found(self, mock_project):
        """Should raise error when narrations not found."""
        narration_path = mock_project.root_dir / "narration" / "narrations.json"
        narration_path.unlink()

        checker = FactChecker(mock_project, use_mock=True)
        with pytest.raises(FactCheckError, match="Narrations not found"):
            checker._load_narrations()

    def test_load_source_material(self, mock_project):
        """Should load source material from input directory."""
        checker = FactChecker(mock_project, use_mock=True)
        content, names = checker._load_source_material()
        assert "source.md" in names
        assert "Test Source" in content

    def test_load_source_material_no_input_dir(self, mock_project):
        """Should raise error when input directory doesn't exist."""
        import shutil

        shutil.rmtree(mock_project.root_dir / "input")

        checker = FactChecker(mock_project, use_mock=True)
        with pytest.raises(FactCheckError, match="Input directory not found"):
            checker._load_source_material()

    def test_load_source_material_empty_dir(self, mock_project):
        """Should raise error when no source documents found."""
        # Remove source file
        (mock_project.root_dir / "input" / "source.md").unlink()

        checker = FactChecker(mock_project, use_mock=True)
        with pytest.raises(FactCheckError, match="No source documents found"):
            checker._load_source_material()

    def test_format_script_content(self, mock_project):
        """Should format script for prompt."""
        checker = FactChecker(mock_project, use_mock=True)
        script = checker._load_script()
        formatted = checker._format_script_content(script)

        assert "Test Video Script" in formatted
        assert "scene1_hook" in formatted
        assert "scene2_main" in formatted
        assert "hook" in formatted

    def test_format_narration_content(self, mock_project):
        """Should format narrations for prompt."""
        checker = FactChecker(mock_project, use_mock=True)
        narrations = checker._load_narrations()
        formatted = checker._format_narration_content(narrations)

        assert "scene1_hook" in formatted
        assert "The Hook" in formatted
        assert "Welcome to our video" in formatted

    def test_run_fact_check_mock(self, mock_project):
        """Should run fact check with mock provider."""
        checker = FactChecker(mock_project, use_mock=True, verbose=False)
        report = checker.run_fact_check()

        assert report.project_id == "test-project"
        assert report.script_title == "Test Video Script"
        assert len(report.issues) == 2  # From mock response
        assert report.summary.total_issues == 2

    def test_run_fact_check_returns_report(self, mock_project):
        """Should return a valid FactCheckReport."""
        checker = FactChecker(mock_project, use_mock=True)
        report = checker.run_fact_check()

        assert isinstance(report, FactCheckReport)
        assert report.source_documents == ["source.md"]

    def test_save_report(self, mock_project):
        """Should save report to file."""
        checker = FactChecker(mock_project, use_mock=True)
        report = checker.run_fact_check()

        output_path = checker.save_report(report)
        assert output_path.exists()
        assert output_path.name == "report.json"

        # Verify content
        with open(output_path) as f:
            saved = json.load(f)
        assert saved["project_id"] == "test-project"

    def test_save_report_custom_path(self, mock_project, tmp_path):
        """Should save report to custom path."""
        checker = FactChecker(mock_project, use_mock=True)
        report = checker.run_fact_check()

        custom_path = tmp_path / "custom_report.json"
        output_path = checker.save_report(report, output_path=custom_path)
        assert output_path == custom_path
        assert custom_path.exists()

    def test_parse_json_from_response_plain(self, mock_project):
        """Should parse plain JSON response."""
        checker = FactChecker(mock_project, use_mock=True)
        response = '{"issues": [], "summary": {"total_issues": 0}}'
        result = checker._parse_json_from_response(response)
        assert result["summary"]["total_issues"] == 0

    def test_parse_json_from_response_markdown(self, mock_project):
        """Should parse JSON from markdown code block."""
        checker = FactChecker(mock_project, use_mock=True)
        response = """Here is the analysis:

```json
{"issues": [], "summary": {"total_issues": 0}}
```

End of analysis."""
        result = checker._parse_json_from_response(response)
        assert result["summary"]["total_issues"] == 0

    def test_parse_json_from_response_invalid(self, mock_project):
        """Should raise error for invalid JSON."""
        checker = FactChecker(mock_project, use_mock=True)
        with pytest.raises(FactCheckError, match="Failed to parse"):
            checker._parse_json_from_response("not valid json")

    def test_verbose_logging(self, mock_project, capsys):
        """Should log progress when verbose."""
        checker = FactChecker(mock_project, use_mock=True, verbose=True)
        checker.run_fact_check()

        captured = capsys.readouterr()
        assert "Starting fact check" in captured.out
        assert "Loading script" in captured.out
        assert "Loading narrations" in captured.out


class TestRunFactCheckFunction:
    """Tests for the run_fact_check convenience function."""

    @pytest.fixture
    def mock_project(self, tmp_path):
        """Create a minimal mock project."""
        project_dir = tmp_path / "test-project"
        project_dir.mkdir()

        # Config
        with open(project_dir / "config.json", "w") as f:
            json.dump({"id": "test-project", "title": "Test"}, f)

        # Input
        input_dir = project_dir / "input"
        input_dir.mkdir()
        (input_dir / "source.md").write_text("# Source\n\nContent here.")

        # Script
        script_dir = project_dir / "script"
        script_dir.mkdir()
        with open(script_dir / "script.json", "w") as f:
            json.dump({"title": "Test", "scenes": []}, f)

        # Narrations
        narration_dir = project_dir / "narration"
        narration_dir.mkdir()
        with open(narration_dir / "narrations.json", "w") as f:
            json.dump({"scenes": []}, f)

        project = MagicMock()
        project.id = "test-project"
        project.title = "Test"
        project.root_dir = project_dir
        project.input_dir = input_dir

        return project

    def test_run_fact_check_convenience(self, mock_project):
        """Should run fact check via convenience function."""
        report = run_fact_check(mock_project, use_mock=True)
        assert isinstance(report, FactCheckReport)
        assert report.project_id == "test-project"


class TestFactCheckCLI:
    """Tests for fact check CLI command."""

    @pytest.fixture
    def cli_project(self, tmp_path):
        """Create a project for CLI testing."""
        project_dir = tmp_path / "cli-project"
        project_dir.mkdir()

        # Config
        with open(project_dir / "config.json", "w") as f:
            json.dump({"id": "cli-project", "title": "CLI Test"}, f)

        # Input
        input_dir = project_dir / "input"
        input_dir.mkdir()
        (input_dir / "source.md").write_text("# Source\n\nTest content.")

        # Script
        script_dir = project_dir / "script"
        script_dir.mkdir()
        with open(script_dir / "script.json", "w") as f:
            json.dump({
                "title": "CLI Test Script",
                "scenes": [{"scene_id": "s1", "voiceover": "Test"}],
            }, f)

        # Narrations
        narration_dir = project_dir / "narration"
        narration_dir.mkdir()
        with open(narration_dir / "narrations.json", "w") as f:
            json.dump({
                "scenes": [{"scene_id": "s1", "title": "Scene 1", "narration": "Test"}],
            }, f)

        return tmp_path

    def test_cmd_factcheck_mock(self, cli_project, capsys):
        """Should run fact check via CLI."""
        from src.cli.main import cmd_factcheck

        args = MagicMock()
        args.projects_dir = str(cli_project)
        args.project = "cli-project"
        args.mock = True
        args.verbose = False
        args.timeout = 60
        args.no_save = True

        result = cmd_factcheck(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "FACT CHECK REPORT" in captured.out
        assert "cli-project" in captured.out

    def test_cmd_factcheck_saves_report(self, cli_project):
        """Should save report when --no-save not specified."""
        from src.cli.main import cmd_factcheck

        args = MagicMock()
        args.projects_dir = str(cli_project)
        args.project = "cli-project"
        args.mock = True
        args.verbose = False
        args.timeout = 60
        args.no_save = False

        result = cmd_factcheck(args)
        assert result == 0

        # Check report was saved
        report_path = cli_project / "cli-project" / "factcheck" / "report.json"
        assert report_path.exists()

    def test_cmd_factcheck_nonexistent_project(self, tmp_path, capsys):
        """Should fail for nonexistent project."""
        from src.cli.main import cmd_factcheck

        args = MagicMock()
        args.projects_dir = str(tmp_path)
        args.project = "nonexistent"
        args.mock = True
        args.verbose = False
        args.timeout = 60
        args.no_save = True

        result = cmd_factcheck(args)
        assert result == 1

        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_cmd_factcheck_missing_script(self, cli_project, capsys):
        """Should fail when script is missing."""
        from src.cli.main import cmd_factcheck

        # Remove script
        (cli_project / "cli-project" / "script" / "script.json").unlink()

        args = MagicMock()
        args.projects_dir = str(cli_project)
        args.project = "cli-project"
        args.mock = True
        args.verbose = False
        args.timeout = 60
        args.no_save = True

        result = cmd_factcheck(args)
        assert result == 1

        captured = capsys.readouterr()
        assert "Error" in captured.err
        assert "Script not found" in captured.err

    def test_cmd_factcheck_verbose(self, cli_project, capsys):
        """Should show verbose output when --verbose."""
        from src.cli.main import cmd_factcheck

        args = MagicMock()
        args.projects_dir = str(cli_project)
        args.project = "cli-project"
        args.mock = True
        args.verbose = True
        args.timeout = 60
        args.no_save = True

        result = cmd_factcheck(args)
        assert result == 0

        captured = capsys.readouterr()
        assert "Loading script" in captured.out


class TestFactCheckWithPDF:
    """Tests for fact checking with PDF source material."""

    @pytest.fixture
    def project_with_pdf(self, tmp_path):
        """Create a project with PDF source."""
        import fitz  # PyMuPDF

        project_dir = tmp_path / "pdf-project"
        project_dir.mkdir()

        # Config
        with open(project_dir / "config.json", "w") as f:
            json.dump({"id": "pdf-project", "title": "PDF Test"}, f)

        # Create PDF source
        input_dir = project_dir / "input"
        input_dir.mkdir()

        pdf_path = input_dir / "source.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "PDF Source Document\n\nThis is content from a PDF.")
        doc.set_metadata({"title": "PDF Source"})
        doc.save(str(pdf_path))
        doc.close()

        # Script
        script_dir = project_dir / "script"
        script_dir.mkdir()
        with open(script_dir / "script.json", "w") as f:
            json.dump({"title": "PDF Test", "scenes": []}, f)

        # Narrations
        narration_dir = project_dir / "narration"
        narration_dir.mkdir()
        with open(narration_dir / "narrations.json", "w") as f:
            json.dump({"scenes": []}, f)

        project = MagicMock()
        project.id = "pdf-project"
        project.title = "PDF Test"
        project.root_dir = project_dir
        project.input_dir = input_dir

        return project

    def test_load_pdf_source(self, project_with_pdf):
        """Should load PDF as source material."""
        checker = FactChecker(project_with_pdf, use_mock=True)
        content, names = checker._load_source_material()

        assert "source.pdf" in names
        assert "PDF Source Document" in content

    def test_fact_check_with_pdf(self, project_with_pdf):
        """Should run fact check with PDF source."""
        checker = FactChecker(project_with_pdf, use_mock=True)
        report = checker.run_fact_check()

        assert "source.pdf" in report.source_documents
        assert isinstance(report, FactCheckReport)

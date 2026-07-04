"""Tests for ClaudeCodeLLMProvider."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config import LLMConfig
from src.understanding.llm_provider import (
    ClaudeCodeError,
    ClaudeCodeLLMProvider,
    ClaudeCodeResult,
    get_llm_provider,
)


@pytest.fixture
def llm_config():
    """Create a test LLM config."""
    return LLMConfig(provider="claude-code", model="claude-sonnet-4-20250514")


@pytest.fixture
def provider(llm_config, tmp_path):
    """Create a ClaudeCodeLLMProvider for testing."""
    return ClaudeCodeLLMProvider(llm_config, working_dir=tmp_path, timeout=30)


class TestClaudeCodeLLMProviderInit:
    """Tests for provider initialization."""

    def test_init_with_defaults(self, llm_config):
        """Test initialization with default values."""
        provider = ClaudeCodeLLMProvider(llm_config)
        assert provider.config == llm_config
        assert provider.working_dir == Path.cwd()
        assert provider.timeout == 300

    def test_init_with_custom_working_dir(self, llm_config, tmp_path):
        """Test initialization with custom working directory."""
        provider = ClaudeCodeLLMProvider(llm_config, working_dir=tmp_path)
        assert provider.working_dir == tmp_path

    def test_init_with_custom_timeout(self, llm_config):
        """Test initialization with custom timeout."""
        provider = ClaudeCodeLLMProvider(llm_config, timeout=60)
        assert provider.timeout == 60


class TestBuildCommand:
    """Tests for _build_command method."""

    def test_basic_command(self, provider):
        """Test basic command without system prompt or tools."""
        cmd = provider._build_command("Hello world", tools=[])
        assert cmd == [
            "claude", "--print", "-p", "Hello world",
            "--model", "claude-sonnet-4-20250514",
        ]

    def test_command_with_system_prompt(self, provider):
        """Test command with system prompt."""
        cmd = provider._build_command(
            "Hello world",
            system_prompt="You are helpful.",
            tools=[],
        )
        assert cmd == [
            "claude", "--print", "-p", "Hello world",
            "--model", "claude-sonnet-4-20250514",
            "--system-prompt", "You are helpful.",
        ]

    def test_command_with_tools(self, provider):
        """Test command with tools enabled."""
        cmd = provider._build_command(
            "Read file.txt",
            tools=["Read", "Glob"],
        )
        assert "--allowedTools" in cmd
        assert "Read,Glob" in cmd
        assert "--dangerously-skip-permissions" in cmd

    def test_command_with_empty_tools_list(self, provider):
        """Test command with empty tools list (no tools)."""
        cmd = provider._build_command("Hello", tools=[])
        assert "--allowedTools" not in cmd
        assert "--dangerously-skip-permissions" not in cmd

    def test_command_with_all_default_tools(self, provider):
        """Test command with all default tools."""
        cmd = provider._build_command(
            "Modify files",
            tools=provider.DEFAULT_TOOLS,
        )
        expected_tools = "Read,Write,Edit,Bash,Glob,Grep"
        assert expected_tools in cmd


class TestParseJsonResponse:
    """Tests for _parse_json_response method."""

    def test_parse_plain_json(self, provider):
        """Test parsing plain JSON response."""
        response = '{"key": "value", "number": 42}'
        result = provider._parse_json_response(response)
        assert result == {"key": "value", "number": 42}

    def test_parse_json_with_markdown_block(self, provider):
        """Test parsing JSON from markdown code block."""
        response = """Here's the result:
```json
{"status": "success", "data": [1, 2, 3]}
```
"""
        result = provider._parse_json_response(response)
        assert result == {"status": "success", "data": [1, 2, 3]}

    def test_parse_json_with_plain_code_block(self, provider):
        """Test parsing JSON from plain code block (no language)."""
        response = """```
{"items": ["a", "b", "c"]}
```"""
        result = provider._parse_json_response(response)
        assert result == {"items": ["a", "b", "c"]}

    def test_parse_json_with_text_before_and_after(self, provider):
        """Test parsing JSON with surrounding text."""
        response = """I analyzed the content and here's the result:
{"analysis": "complete"}
Hope this helps!"""
        result = provider._parse_json_response(response)
        assert result == {"analysis": "complete"}

    def test_parse_json_array(self, provider):
        """Test parsing JSON array response."""
        response = '[{"id": 1}, {"id": 2}]'
        result = provider._parse_json_response(response)
        assert result == [{"id": 1}, {"id": 2}]

    def test_parse_invalid_json_raises_error(self, provider):
        """Test that invalid JSON raises ClaudeCodeError."""
        response = "This is not valid JSON at all"
        with pytest.raises(ClaudeCodeError) as exc_info:
            provider._parse_json_response(response)
        assert "Failed to parse JSON" in str(exc_info.value)


class TestExtractModifiedFiles:
    """Tests for _extract_modified_files method."""

    def test_extract_wrote_pattern(self, provider):
        """Test extracting files from 'Wrote' messages."""
        output = "Wrote src/file.py successfully"
        files = provider._extract_modified_files(output)
        assert "src/file.py" in files

    def test_extract_created_pattern(self, provider):
        """Test extracting files from 'Created' messages."""
        output = "Created models.py"
        files = provider._extract_modified_files(output)
        assert "models.py" in files

    def test_extract_multiple_files(self, provider):
        """Test extracting multiple modified files."""
        output = """
Modified src/module.py
Updated tests/test_module.py
Wrote config.json
"""
        files = provider._extract_modified_files(output)
        assert "src/module.py" in files
        assert "tests/test_module.py" in files
        assert "config.json" in files

    def test_extract_no_files(self, provider):
        """Test when no files were modified."""
        output = "Analysis complete. No changes needed."
        files = provider._extract_modified_files(output)
        assert files == []

    def test_extract_deduplicates(self, provider):
        """Test that duplicate file entries are removed."""
        output = """
Wrote file.py
Modified file.py
Updated file.py
"""
        files = provider._extract_modified_files(output)
        assert files.count("file.py") == 1


class TestGenerate:
    """Tests for generate method."""

    @patch("subprocess.run")
    def test_generate_success(self, mock_run, provider):
        """Test successful text generation."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="This is the response",
            stderr="",
        )

        result = provider.generate("Hello")

        assert result == "This is the response"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_generate_with_system_prompt(self, mock_run, provider):
        """Test generation with system prompt."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Helpful response",
            stderr="",
        )

        provider.generate("Hello", system_prompt="Be helpful")

        call_args = mock_run.call_args[0][0]
        assert "--system-prompt" in call_args
        assert "Be helpful" in call_args

    @patch("subprocess.run")
    def test_generate_failure_raises_error(self, mock_run, provider):
        """Test that CLI failure raises ClaudeCodeError."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Command failed",
        )

        with pytest.raises(ClaudeCodeError) as exc_info:
            provider.generate("Hello")
        assert "Command failed" in str(exc_info.value)

    @patch("subprocess.run")
    def test_generate_uses_correct_working_dir(self, mock_run, provider, tmp_path):
        """Test that generate uses the configured working directory."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        provider.generate("Hello")

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == str(tmp_path)


class TestGenerateJson:
    """Tests for generate_json method."""

    @patch("subprocess.run")
    def test_generate_json_success(self, mock_run, provider):
        """Test successful JSON generation."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"result": "success"}',
            stderr="",
        )

        result = provider.generate_json("Return JSON")

        assert result == {"result": "success"}

    @patch("subprocess.run")
    def test_generate_json_with_markdown(self, mock_run, provider):
        """Test JSON generation when response has markdown."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='```json\n{"data": [1,2,3]}\n```',
            stderr="",
        )

        result = provider.generate_json("Return JSON")

        assert result == {"data": [1, 2, 3]}

    @patch("subprocess.run")
    def test_generate_json_modifies_prompt(self, mock_run, provider):
        """Test that JSON instruction is added to prompt."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="{}",
            stderr="",
        )

        provider.generate_json("Get data")

        call_args = mock_run.call_args[0][0]
        prompt_arg_idx = call_args.index("-p") + 1
        prompt = call_args[prompt_arg_idx]
        assert "JSON" in prompt


class TestGenerateWithFileAccess:
    """Tests for generate_with_file_access method."""

    @patch("subprocess.run")
    def test_read_only_access(self, mock_run, provider):
        """Test file access with read-only mode."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="File contents analyzed",
            stderr="",
        )

        result = provider.generate_with_file_access(
            "Analyze files",
            allow_writes=False,
        )

        assert result.success
        assert result.response == "File contents analyzed"

        call_args = mock_run.call_args[0][0]
        tools_idx = call_args.index("--allowedTools") + 1
        tools = call_args[tools_idx]
        assert "Write" not in tools
        assert "Edit" not in tools
        assert "Read" in tools

    @patch("subprocess.run")
    def test_write_access(self, mock_run, provider):
        """Test file access with write mode."""
        # Mock returns different results for different commands
        def mock_subprocess(cmd, *args, **kwargs):
            if cmd[0] == "git":
                # Git diff returns modified file
                return MagicMock(
                    returncode=0,
                    stdout="src/file.py\n",
                    stderr="",
                )
            else:
                # Claude command response
                return MagicMock(
                    returncode=0,
                    stdout="Wrote src/file.py successfully",
                    stderr="",
                )
        mock_run.side_effect = mock_subprocess

        result = provider.generate_with_file_access(
            "Modify files",
            allow_writes=True,
        )

        assert result.success
        assert "src/file.py" in result.modified_files

        # Find the claude call (not the git call)
        claude_calls = [c for c in mock_run.call_args_list if c[0][0][0] == "claude"]
        assert len(claude_calls) > 0
        call_args = claude_calls[0][0][0]
        tools_idx = call_args.index("--allowedTools") + 1
        tools = call_args[tools_idx]
        assert "Write" in tools
        assert "Edit" in tools

    @patch("subprocess.run")
    def test_failure_returns_error_result(self, mock_run, provider):
        """Test that CLI failure returns error result."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error occurred",
        )

        result = provider.generate_with_file_access("Do something")

        assert not result.success
        assert "Error occurred" in result.error_message

    @patch("subprocess.run")
    def test_timeout_returns_error_result(self, mock_run, provider):
        """Test that timeout returns error result."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=30)

        result = provider.generate_with_file_access("Long task")

        assert not result.success
        assert "timed out" in result.error_message


class TestClaudeCodeResult:
    """Tests for ClaudeCodeResult dataclass."""

    def test_default_values(self):
        """Test default values for ClaudeCodeResult."""
        result = ClaudeCodeResult(response="test")
        assert result.response == "test"
        assert result.modified_files == []
        assert result.success is True
        assert result.error_message is None

    def test_with_modified_files(self):
        """Test ClaudeCodeResult with modified files."""
        result = ClaudeCodeResult(
            response="Done",
            modified_files=["a.py", "b.py"],
        )
        assert result.modified_files == ["a.py", "b.py"]

    def test_error_result(self):
        """Test ClaudeCodeResult for error case."""
        result = ClaudeCodeResult(
            response="",
            success=False,
            error_message="Something went wrong",
        )
        assert not result.success
        assert result.error_message == "Something went wrong"


class TestFactoryFunction:
    """Tests for get_llm_provider factory function."""

    def test_factory_creates_claude_code_provider(self):
        """Test that factory creates ClaudeCodeLLMProvider for 'claude-code'."""
        from src.config import Config, LLMConfig, TTSConfig, VideoConfig

        config = Config(
            llm=LLMConfig(provider="claude-code", model="test"),
            tts=TTSConfig(provider="mock"),
            video=VideoConfig(),
        )

        provider = get_llm_provider(config)

        assert isinstance(provider, ClaudeCodeLLMProvider)

    def test_factory_case_insensitive(self):
        """Test that factory handles case variations."""
        from src.config import Config, LLMConfig, TTSConfig, VideoConfig

        config = Config(
            llm=LLMConfig(provider="Claude-Code", model="test"),
            tts=TTSConfig(provider="mock"),
            video=VideoConfig(),
        )

        provider = get_llm_provider(config)

        assert isinstance(provider, ClaudeCodeLLMProvider)

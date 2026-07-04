"""Tests for delivery tags module."""

import pytest
from unittest.mock import MagicMock

from src.voiceover.delivery_tags import (
    add_delivery_tags,
    format_narration_for_recording,
    DELIVERY_TAGS,
    SYSTEM_PROMPT,
)


class MockLLMProvider:
    """Mock LLM provider for testing delivery tags."""

    def __init__(self, response: str = ""):
        self.response = response
        self.calls = []

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Record call and return mock response."""
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        return self.response


class TestDeliveryTags:
    """Tests for delivery tag functionality."""

    def test_available_tags(self):
        """Verify all expected tags are available."""
        expected_tags = [
            # Core emotional tones
            "thoughtful",
            "puzzled",
            "excited",
            "serious",
            "wonder",
            "matter-of-fact",
            "dramatic",
            "warm",
            # Additional emotional tones
            "curious",
            "confident",
            "playful",
            "reverent",
            "urgent",
            "satisfied",
            "intrigued",
        ]
        assert DELIVERY_TAGS == expected_tags

    def test_system_prompt_contains_all_tags(self):
        """Verify system prompt documents all tags."""
        for tag in DELIVERY_TAGS:
            assert f"[{tag}]" in SYSTEM_PROMPT, f"Tag [{tag}] not in system prompt"

    def test_add_delivery_tags_with_mock_llm(self):
        """Test adding tags with a mock LLM provider."""
        mock_response = "[thoughtful] You type a question. [puzzled] What happens next?"
        mock_llm = MockLLMProvider(response=mock_response)

        narration = "You type a question. What happens next?"
        result = add_delivery_tags(narration, llm=mock_llm)

        assert result == mock_response
        assert len(mock_llm.calls) == 1
        assert narration in mock_llm.calls[0]["prompt"]
        assert mock_llm.calls[0]["system_prompt"] == SYSTEM_PROMPT

    def test_add_delivery_tags_empty_narration(self):
        """Test handling empty narration."""
        mock_llm = MockLLMProvider(response="")

        result = add_delivery_tags("", llm=mock_llm)
        assert result == ""
        assert len(mock_llm.calls) == 0  # Should not call LLM for empty input

    def test_add_delivery_tags_whitespace_only(self):
        """Test handling whitespace-only narration."""
        mock_llm = MockLLMProvider(response="")

        result = add_delivery_tags("   \n\t   ", llm=mock_llm)
        assert result == "   \n\t   "
        assert len(mock_llm.calls) == 0

    def test_add_delivery_tags_strips_markdown(self):
        """Test that markdown code blocks are stripped from response."""
        mock_response = "```\n[thoughtful] Test narration.\n```"
        mock_llm = MockLLMProvider(response=mock_response)

        result = add_delivery_tags("Test narration.", llm=mock_llm)
        assert result == "[thoughtful] Test narration."

    def test_add_delivery_tags_handles_llm_error(self):
        """Test graceful handling of LLM errors."""
        mock_llm = MagicMock()
        mock_llm.generate.side_effect = Exception("LLM error")

        narration = "Test narration."
        result = add_delivery_tags(narration, llm=mock_llm)

        # Should return original narration on error
        assert result == narration

    def test_format_narration_with_tags(self):
        """Test format_narration_for_recording with tags enabled."""
        mock_response = "[excited] Amazing facts here!"
        mock_llm = MockLLMProvider(response=mock_response)

        result = format_narration_for_recording(
            "Amazing facts here!",
            include_tags=True,
            llm=mock_llm,
        )

        assert result == mock_response

    def test_format_narration_without_tags(self):
        """Test format_narration_for_recording with tags disabled."""
        mock_llm = MockLLMProvider(response="should not be called")

        narration = "Original narration text."
        result = format_narration_for_recording(
            narration,
            include_tags=False,
            llm=mock_llm,
        )

        assert result == narration
        assert len(mock_llm.calls) == 0  # LLM should not be called

    def test_multiple_narrations(self):
        """Test tagging multiple narrations independently."""
        mock_llm = MockLLMProvider()

        narrations = [
            "First scene narration.",
            "Second scene with a question?",
            "Third scene with exciting numbers: 1 billion!",
        ]

        for i, narration in enumerate(narrations):
            mock_llm.response = f"[tag{i}] {narration}"
            result = add_delivery_tags(narration, llm=mock_llm)
            assert f"[tag{i}]" in result

        assert len(mock_llm.calls) == 3


class TestDeliveryTagsIntegration:
    """Integration tests that verify tag format consistency."""

    def test_tagged_output_format(self):
        """Verify tagged output follows expected format."""
        # Simulate realistic LLM response
        mock_response = (
            "[thoughtful] You type a question. A quarter second later: an answer. "
            "[puzzled] What happens in that quarter second?"
        )
        mock_llm = MockLLMProvider(response=mock_response)

        result = add_delivery_tags(
            "You type a question. A quarter second later: an answer. What happens in that quarter second?",
            llm=mock_llm,
        )

        # Verify format: tags in square brackets at start of phrases
        assert "[thoughtful]" in result
        assert "[puzzled]" in result
        # Original text should be preserved
        assert "quarter second" in result

    def test_complex_narration_tagging(self):
        """Test tagging a longer, more complex narration."""
        complex_narration = """
        You press Enter. The character vanishes into the machine. But it doesn't just
        disappear. Every keystroke triggers a cascade of events. Thousands of operations
        in milliseconds. What happens inside that black box?
        """

        mock_response = """[warm] You press Enter. The character vanishes into the machine. [dramatic] But it doesn't just disappear. [serious] Every keystroke triggers a cascade of events. [excited] Thousands of operations in milliseconds. [puzzled] What happens inside that black box?"""

        mock_llm = MockLLMProvider(response=mock_response)

        result = add_delivery_tags(complex_narration.strip(), llm=mock_llm)

        # Verify multiple tags present
        assert "[warm]" in result
        assert "[dramatic]" in result
        assert "[serious]" in result
        assert "[excited]" in result
        assert "[puzzled]" in result

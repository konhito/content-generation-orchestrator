"""Tests for content understanding module."""

from pathlib import Path

import pytest

from src.config import Config, LLMConfig
from src.ingestion import parse_document
from src.models import ContentAnalysis, ParsedDocument, SourceType
from src.understanding import ContentAnalyzer, LLMProvider, get_llm_provider
from src.understanding.llm_provider import ClaudeCodeLLMProvider, MockLLMProvider


class TestMockLLMProvider:
    """Tests for the mock LLM provider."""

    @pytest.fixture
    def mock_llm(self):
        config = LLMConfig(provider="mock")
        return MockLLMProvider(config)

    def test_generate_returns_string(self, mock_llm):
        result = mock_llm.generate("Hello, world!")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_json_content_analysis(self, mock_llm):
        result = mock_llm.generate_json("Please analyze this document content")
        assert "core_thesis" in result
        assert "key_concepts" in result
        assert len(result["key_concepts"]) > 0

    def test_generate_json_script_generation(self, mock_llm):
        result = mock_llm.generate_json("Generate a script for this video")
        assert "title" in result
        assert "scenes" in result
        assert len(result["scenes"]) > 0

    def test_generate_json_unknown_prompt(self, mock_llm):
        result = mock_llm.generate_json("Some random unrecognized prompt")
        assert result == {}

    def test_content_analysis_has_expected_concepts(self, mock_llm):
        result = mock_llm.generate_json("Analyze this content")
        concepts = result["key_concepts"]

        # Mock provider returns generic concepts
        concept_names = [c["name"] for c in concepts]
        assert len(concept_names) >= 3
        assert any("Concept" in name for name in concept_names)

    def test_script_has_expected_scenes(self, mock_llm):
        result = mock_llm.generate_json("Create a script for this video")
        scenes = result["scenes"]

        # Should have hook, explanation, and conclusion scenes
        scene_types = [s["scene_type"] for s in scenes]
        assert "hook" in scene_types
        assert "conclusion" in scene_types

        # Should have visual cues
        for scene in scenes:
            assert "visual_cue" in scene
            assert "description" in scene["visual_cue"]


class TestGetLLMProvider:
    """Tests for provider factory function."""

    def test_returns_openai_provider_by_default(self):
        from src.understanding.llm_provider import OpenAILLMProvider

        config = Config()
        provider = get_llm_provider(config)
        assert isinstance(provider, OpenAILLMProvider)

    def test_raises_for_unknown_provider(self):
        config = Config()
        config.llm.provider = "unknown_provider"
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_provider(config)


class TestContentAnalyzer:
    """Tests for the content analyzer."""

    @pytest.fixture
    def analyzer(self):
        config = Config()
        config.llm.provider = "mock"  # Use mock to avoid real LLM calls
        return ContentAnalyzer(config)

    @pytest.fixture
    def sample_document(self, sample_markdown) -> ParsedDocument:
        return parse_document(sample_markdown)

    def test_analyze_returns_content_analysis(self, analyzer, sample_document):
        result = analyzer.analyze(sample_document)
        assert isinstance(result, ContentAnalysis)

    def test_analysis_has_core_thesis(self, analyzer, sample_document):
        result = analyzer.analyze(sample_document)
        assert result.core_thesis
        assert len(result.core_thesis) > 10

    def test_analysis_has_key_concepts(self, analyzer, sample_document):
        result = analyzer.analyze(sample_document)
        assert len(result.key_concepts) > 0
        for concept in result.key_concepts:
            assert concept.name
            assert concept.explanation
            assert 1 <= concept.complexity <= 10

    def test_analysis_has_duration(self, analyzer, sample_document):
        result = analyzer.analyze(sample_document)
        assert result.suggested_duration_seconds > 0

    def test_analysis_has_complexity_score(self, analyzer, sample_document):
        result = analyzer.analyze(sample_document)
        assert 1 <= result.complexity_score <= 10


class TestAnalyzeRealDocument:
    """Test analyzing the actual LLM inference document."""

    @pytest.fixture
    def inference_doc_path(self):
        path = Path("/Users/prajwal/Desktop/Learning/inference/website/post.md")
        if not path.exists():
            pytest.skip("Inference document not found")
        return path

    @pytest.fixture
    def analyzer(self):
        config = Config()
        config.llm.provider = "mock"  # Use mock to avoid real LLM calls
        return ContentAnalyzer(config)

    def test_analyze_inference_document(self, analyzer, inference_doc_path):
        doc = parse_document(inference_doc_path)
        result = analyzer.analyze(doc)

        # Mock provider returns generic concepts
        assert len(result.key_concepts) >= 3
        assert result.core_thesis

    def test_analyze_specific_sections(self, analyzer, inference_doc_path):
        doc = parse_document(inference_doc_path)

        # Analyze just the two phases section
        result = analyzer.analyze_sections(
            doc,
            start_heading="Two Phases",
            end_heading="Naive Inference",
        )

        assert isinstance(result, ContentAnalysis)
        assert result.core_thesis  # Should still produce a thesis

    def test_concepts_have_visual_potential(self, analyzer, inference_doc_path):
        doc = parse_document(inference_doc_path)
        result = analyzer.analyze(doc)

        for concept in result.key_concepts:
            assert concept.visual_potential in ["high", "medium", "low"]

    def test_concepts_have_analogies(self, analyzer, inference_doc_path):
        doc = parse_document(inference_doc_path)
        result = analyzer.analyze(doc)

        # At least some concepts should have analogies
        concepts_with_analogies = [c for c in result.key_concepts if c.analogies]
        assert len(concepts_with_analogies) > 0

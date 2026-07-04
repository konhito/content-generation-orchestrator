"""Content analyzer - extracts key concepts and structure from documents."""

from ..config import Config, load_config
from ..models import Concept, ContentAnalysis, ParsedDocument
from .llm_provider import LLMProvider, get_llm_provider


ANALYSIS_SYSTEM_PROMPT = """You are an expert at analyzing technical content and extracting
the key concepts, relationships, and teachable insights. Your goal is to identify what
makes content understandable and what visual representations would help explain it.

Always respond with valid JSON matching the requested schema."""


ANALYSIS_USER_PROMPT_TEMPLATE = """Analyze the following technical document and extract:

1. The core thesis (one sentence summary)
2. Key concepts with:
   - Name
   - Clear explanation
   - Complexity score (1-10)
   - Prerequisites (what the reader needs to know)
   - Analogies (real-world comparisons)
   - Visual potential (high/medium/low - how well can this be animated)
3. Target audience
4. Suggested video duration in seconds
5. Overall complexity score (1-10)

Document Title: {title}

Document Content:
{content}

Respond with a JSON object matching this schema:
{{
  "core_thesis": "string",
  "key_concepts": [
    {{
      "name": "string",
      "explanation": "string",
      "complexity": number,
      "prerequisites": ["string"],
      "analogies": ["string"],
      "visual_potential": "high|medium|low"
    }}
  ],
  "target_audience": "string",
  "suggested_duration_seconds": number,
  "complexity_score": number
}}"""


class ContentAnalyzer:
    """Analyzes documents to extract key concepts and structure."""

    def __init__(self, config: Config | None = None, llm: LLMProvider | None = None):
        """Initialize the analyzer.

        Args:
            config: Configuration object. If None, loads default.
            llm: LLM provider. If None, creates one from config.
        """
        self.config = config or load_config()
        self.llm = llm or get_llm_provider(self.config)

    def analyze(self, document: ParsedDocument) -> ContentAnalysis:
        """Analyze a parsed document and extract key concepts.

        Args:
            document: The parsed document to analyze

        Returns:
            ContentAnalysis with extracted concepts and metadata
        """
        # Build content string from sections
        content_parts = []
        for section in document.sections:
            content_parts.append(f"## {section.heading}\n\n{section.content}")

        content = "\n\n".join(content_parts)

        # Generate the analysis prompt
        prompt = ANALYSIS_USER_PROMPT_TEMPLATE.format(
            title=document.title,
            content=content[:15000],  # Limit content length for context window
        )

        # Get LLM analysis
        result = self.llm.generate_json(prompt, ANALYSIS_SYSTEM_PROMPT)

        # Parse into ContentAnalysis model
        return ContentAnalysis(
            core_thesis=result.get("core_thesis", ""),
            key_concepts=[
                Concept(
                    name=c.get("name", ""),
                    explanation=c.get("explanation", ""),
                    complexity=c.get("complexity", 5),
                    prerequisites=c.get("prerequisites", []),
                    analogies=c.get("analogies", []),
                    visual_potential=c.get("visual_potential", "medium"),
                )
                for c in result.get("key_concepts", [])
            ],
            target_audience=result.get("target_audience", ""),
            suggested_duration_seconds=result.get("suggested_duration_seconds", 180),
            complexity_score=result.get("complexity_score", 5),
        )

    def analyze_sections(
        self,
        document: ParsedDocument,
        start_heading: str | None = None,
        end_heading: str | None = None,
    ) -> ContentAnalysis:
        """Analyze specific sections of a document.

        Args:
            document: The parsed document
            start_heading: Heading to start from (inclusive)
            end_heading: Heading to end at (inclusive)

        Returns:
            ContentAnalysis for the specified sections
        """
        from ..ingestion.parser import extract_sections_by_range

        sections = extract_sections_by_range(document, start_heading, end_heading)

        # Create a temporary document with just these sections
        subset_doc = ParsedDocument(
            title=document.title,
            source_type=document.source_type,
            source_path=document.source_path,
            sections=sections,
            raw_content="",  # Not needed for analysis
            metadata=document.metadata,
        )

        return self.analyze(subset_doc)

"""Prompts for fact checking workflow."""

FACT_CHECK_SYSTEM_PROMPT = """You are an expert fact-checker with deep knowledge across technical, scientific, and educational domains. Your role is to thoroughly verify the accuracy of video script content against source materials and current factual information.

You have access to web search to verify any claims that cannot be verified from the source material alone. Use web search liberally to ensure accuracy.

Be extremely thorough and meticulous. Check:
1. All factual claims and statements
2. Technical terminology and definitions
3. Numerical data, statistics, and calculations
4. Cause-and-effect relationships
5. Historical claims and timelines
6. Attribution and citations
7. Logical consistency throughout the script
8. Whether simplifications maintain accuracy
9. Whether important context or caveats are missing
10. Whether the information is current and not outdated

Your fact check should be comprehensive and leave no stone unturned. It's better to flag a potential issue that turns out to be fine than to miss an actual error."""

FACT_CHECK_PROMPT = """Please perform a thorough fact-check of the following video script and narration.

## Source Material

The script was generated from the following source documents:

{source_content}

## Script to Fact-Check

Title: {script_title}

{script_content}

## Narration to Fact-Check

{narration_content}

---

## Instructions

Perform an extremely thorough fact-check of this content:

1. **Compare Against Source Material**: Verify that all claims in the script accurately reflect the source material. Flag any misrepresentations, oversimplifications that distort meaning, or unsupported claims.

2. **Verify External Facts**: For any claims that go beyond the source material or reference general knowledge, USE WEB SEARCH to verify accuracy. This includes:
   - Technical concepts and definitions
   - Historical facts and dates
   - Statistics and numerical claims
   - Current best practices and standards
   - Recent developments that might make information outdated

3. **Check Technical Accuracy**: Verify that all technical terminology is used correctly and that explanations are accurate.

4. **Identify Missing Context**: Flag any places where important caveats, exceptions, or context has been omitted in a way that could mislead viewers.

5. **Assess Logical Consistency**: Check that the narrative is internally consistent and doesn't contradict itself.

6. **Evaluate Simplifications**: When complex topics are simplified for the video format, ensure the simplification doesn't introduce inaccuracies.

For each issue found, provide:
- The exact text that's problematic
- Which scene it appears in
- What's wrong with it
- The correct information with source
- Severity level (critical/high/medium/low/info)
- Category of issue
- Your confidence level (0-1)

## Output Format

Respond with a JSON object in this exact format:
{{
    "issues": [
        {{
            "id": "issue_1",
            "severity": "critical|high|medium|low|info",
            "category": "factual_error|outdated_info|missing_context|oversimplification|misleading|unsupported_claim|terminology|attribution|numerical|logical|improvement",
            "location": "scene_id or section name",
            "original_text": "the exact problematic text",
            "issue_description": "detailed description of what's wrong",
            "correction": "the correct information or suggested fix",
            "source_reference": "source material section or web URL that confirms the correction",
            "confidence": 0.95,
            "verified_via_web": true
        }}
    ],
    "summary": {{
        "total_issues": 5,
        "critical_count": 1,
        "high_count": 2,
        "medium_count": 1,
        "low_count": 0,
        "info_count": 1,
        "scenes_with_issues": ["scene1_hook", "scene3_explanation"],
        "overall_accuracy_score": 0.85,
        "web_verified_count": 3
    }},
    "recommendations": [
        "Top priority: Fix the critical error in scene 1...",
        "Consider adding context about...",
        "Review the terminology used for..."
    ]
}}

Be thorough and check EVERYTHING. Use web search to verify any claims you're not 100% certain about from the source material."""

FACT_CHECK_MOCK_RESPONSE = {
    "issues": [
        {
            "id": "issue_1",
            "severity": "medium",
            "category": "terminology",
            "location": "scene1_hook",
            "original_text": "Example text from the script",
            "issue_description": "This is a mock issue for testing purposes. In a real fact-check, this would describe an actual problem found.",
            "correction": "The corrected version of the text",
            "source_reference": "Source document section 1.2",
            "confidence": 0.85,
            "verified_via_web": False,
        },
        {
            "id": "issue_2",
            "severity": "low",
            "category": "improvement",
            "location": "scene3_explanation",
            "original_text": "Another example text",
            "issue_description": "This is a suggestion for improvement.",
            "correction": "Consider rephrasing to be more precise",
            "source_reference": "General best practices",
            "confidence": 0.75,
            "verified_via_web": False,
        },
    ],
    "summary": {
        "total_issues": 2,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 1,
        "low_count": 1,
        "info_count": 0,
        "scenes_with_issues": ["scene1_hook", "scene3_explanation"],
        "overall_accuracy_score": 0.92,
        "web_verified_count": 0,
    },
    "recommendations": [
        "Review terminology in scene 1 for precision",
        "Consider adding more context in the explanation section",
    ],
}

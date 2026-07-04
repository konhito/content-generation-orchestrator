"""Narration generator - creates narrations from scripts and source documents."""

import json
from pathlib import Path
from typing import Any

from ..config import Config, load_config
from ..models import Script, ParsedDocument
from ..understanding.llm_provider import LLMProvider, get_llm_provider


NARRATION_SYSTEM_PROMPT = """You are creating narrations for a technical explainer video.

Your job is to write narration text that:
1. Follows the script's scene structure exactly (same scenes, same order)
2. Makes each concept genuinely understandable
3. Uses specific numbers and details from the source material
4. Creates narrations a technical viewer would actually understand

Do not add, remove, or reorder scenes. The script defines the structure."""


NARRATION_USER_PROMPT_TEMPLATE = """# Task: Generate Narrations for Video Script

You are an elite technical video scriptwriter creating narrations for a video about: **{topic}**

{script_context}
{source_context}

---

## CRITICAL: Content Prioritization

**YOUR PRIMARY SOURCE IS THE SCRIPT**. The script defines:
- The exact scene structure (do NOT add or remove scenes)
- The narrative flow and progression
- The key concepts to cover in each scene

**THE SOURCE DOCUMENT IS SUPPLEMENTARY**. Use it ONLY to:
- Ensure technical accuracy (correct terminology, accurate numbers)
- Add specific details, statistics, or examples from the original paper
- Enrich explanations where the script is thin
- Verify facts and claims

**NEVER**:
- Change the scene structure defined in the script
- Add concepts not mentioned in the script
- Change the narrative arc or progression
- Deviate from the script's framing of the topic

## Your Role

The script defines the structure and concepts. Your job is to write narrations that:
1. **Follow the script's scene structure exactly** (same number of scenes, same order, same concepts)
2. Make each concept genuinely understandable, not just mentioned
3. Pull specific numbers and details from the source document
4. Create narrations a technical viewer would actually understand

**IMPORTANT**: Do not add, remove, or reorder scenes. The script is your structure—you're writing the narration for it.

---

## Your Writing Style

**Voice**: Punchy, direct, confident. Short sentences that hit hard. No filler words, no hedging, no "basically" or "essentially." Every word earns its place.

**Tone**: Like a brilliant friend explaining something they're genuinely excited about. Technical but never dry. Respect the audience's intelligence while making complex ideas accessible.

**Structure**: Problem → Tension → Solution → Insight. Build curiosity, create stakes, deliver satisfying explanations.

## Core Principles

1. **Lead with contrast or surprise**: Start with a striking comparison, counterintuitive fact, or provocative question.
   - BAD: "Let's learn about vision transformers."
   - GOOD: "One hundred fifty thousand pixels. That's what a single 224×224 image contains. Transformers were built for sequences of 2,000 tokens. How do we bridge that gap?"

2. **Use concrete numbers**: Specific numbers create credibility and memorability.
   - BAD: "This processes many patches"
   - GOOD: "196 patches. Each one a 16×16 window into the image."

3. **Show the problem before the solution**: Create tension. Make the viewer feel the pain before revealing the elegant fix.

4. **Explain through mechanism**: Don't just say what something does—show HOW it works.
   - BAD: "Patch embeddings convert images to tokens."
   - GOOD: "Take a 16×16 patch. Flatten it to 768 values. Multiply by a learned projection matrix. Now you have a token—just like text."

5. **End scenes with forward momentum**: Each scene should create anticipation for the next.

## What Good Narration Looks Like

Here's an example of effective technical narration:

"Your journey begins in the browser. The moment you type, JavaScript captures a keydown event. This event propagates through the DOM—a tree structure representing every element on the page. Then the browser's rendering pipeline kicks in. Recalculate styles—which CSS rules apply? Compute layout—where does everything go? Paint pixels to layers. Composite those layers to the screen. All of this happens sixty times per second. Sixteen milliseconds per frame. Miss that window and you see stutter."

Notice what makes this work:
- Explains the mechanism step by step (event → DOM → styles → layout → paint → composite)
- Uses specific numbers (60 times/second, 16ms per frame)
- Shows HOW things work, not just THAT they happen

Another example:

"Here's the problem: a single bad gradient update can collapse your policy, and you might never recover. PPO's solution: compute a ratio between new and old policy probabilities. If this ratio exceeds 1.2 or drops below 0.8, the gradient is clipped—no incentive to push further. This prevents catastrophic updates."

This works because:
- Creates an information gap ("Here's the problem...")
- Explains the mechanism (ratio, clipping at 1.2/0.8)
- Shows WHY it works (prevents catastrophic updates)

---

## Important things to keep in mind

### Use Specific Numbers

Pull exact figures from the source:
- "150,528 pixels in a 224×224 image"
- "Eighty gigabytes of HBM3 memory at 3.35 terabytes per second"
- "Accuracy improved from 15.6% to 71.0%"

### Explain Mechanisms

Don't just say what something does—show HOW:

WEAK: "Patch embedding converts images to tokens."

STRONG: "Take your image. Slice it into 16×16 pixel squares—196 patches total. Flatten each patch into a vector: 16 times 16 times 3 equals 768 raw pixel values. Pass this through a learned linear projection. You've just tokenized an image."

### Create Information Gaps

"You need to share a secret with a server you've never met. But everything you send crosses public networks—anyone could listen. How do you share a secret in public?"

Then explain.

### Connect Causally

"But there's a problem: vanilla policy gradients have high variance. Gradient estimates fluctuate wildly. Therefore, we need advantage functions..."

---

## Output Format

Return JSON with this structure:
{{
  "scenes": [
    {{
      "scene_id": "scene1_hook",
      "title": "Scene title from script",
      "duration_seconds": <estimated based on word count, ~2.5 words/second>,
      "narration": "The narration text..."
    }}
  ],
  "total_duration_seconds": <sum of all scene durations>
}}

Match the script's scene structure exactly. Remember: Every sentence should either teach something, create curiosity, or move the narrative forward. Cut everything else."""


class NarrationGenerator:
    """Generates narrations from scripts and source documents."""

    def __init__(self, config: Config | None = None, llm: LLMProvider | None = None):
        """Initialize the generator.

        Args:
            config: Configuration object. If None, loads default.
            llm: LLM provider. If None, creates one from config.
        """
        self.config = config or load_config()
        self.llm = llm or get_llm_provider(self.config)

    def generate(
        self,
        script: Script,
        source_documents: list[ParsedDocument] | None = None,
        topic: str | None = None,
    ) -> dict[str, Any]:
        """Generate narrations from a script.

        Args:
            script: The script to generate narrations for.
            source_documents: Optional source documents for context.
            topic: Topic name for the video.

        Returns:
            Dictionary with narration data matching the expected format.
        """
        # Build script context
        script_data = script.model_dump()
        script_context = f"\n## Existing Script Structure\n```json\n{json.dumps(script_data, indent=2)}\n```"

        # Build source context
        source_context = ""
        if source_documents:
            all_content = []
            for doc in source_documents:
                title = doc.title or "Source Document"
                all_content.append(f"### {title}\n{doc.raw_content}")

            if all_content:
                combined_content = "\n\n---\n\n".join(all_content)
                # Truncate if too long
                if len(combined_content) > 50000:
                    combined_content = combined_content[:50000] + "\n... [truncated]"
                source_context = f"\n## Source Document (Reference Only)\n{combined_content}"

        # Determine topic
        video_topic = topic or script.title or "Technical Topic"

        # Build prompt
        prompt = NARRATION_USER_PROMPT_TEMPLATE.format(
            topic=video_topic,
            script_context=script_context,
            source_context=source_context,
        )

        # Generate via LLM
        result = self.llm.generate_json(prompt, NARRATION_SYSTEM_PROMPT)

        return result

    def generate_mock(self, topic: str) -> dict[str, Any]:
        """Generate mock narrations for testing.

        Args:
            topic: Topic name for the mock narrations.

        Returns:
            Dictionary with mock narration data.
        """
        return {
            "scenes": [
                {
                    "scene_id": "scene1_hook",
                    "title": "The Hook",
                    "duration_seconds": 15,
                    "narration": f"What if I told you that {topic} could change everything you know about technology?",
                },
                {
                    "scene_id": "scene2_context",
                    "title": "Setting the Context",
                    "duration_seconds": 20,
                    "narration": f"To understand {topic}, we need to first look at the bigger picture.",
                },
                {
                    "scene_id": "scene3_explanation",
                    "title": "How It Works",
                    "duration_seconds": 30,
                    "narration": f"At its core, {topic} works by processing information in a fundamentally different way.",
                },
                {
                    "scene_id": "scene4_conclusion",
                    "title": "Conclusion",
                    "duration_seconds": 15,
                    "narration": f"And that's how {topic} is reshaping our understanding of what's possible.",
                },
            ],
            "total_duration_seconds": 80,
        }

    def save_narrations(self, narrations: dict[str, Any], path: str | Path) -> None:
        """Save narrations to a file.

        Args:
            narrations: Narration data to save.
            path: Path to save the narrations.
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(narrations, f, indent=2)

    @staticmethod
    def load_narrations(path: str | Path) -> dict[str, Any]:
        """Load narrations from a file.

        Args:
            path: Path to the narrations file.

        Returns:
            Loaded narration data.
        """
        with open(Path(path)) as f:
            return json.load(f)

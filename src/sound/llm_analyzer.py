"""LLM-based semantic analyzer for sound moment detection.

This module uses an LLM to analyze scene context and identify moments
that should have sound effects based on semantic understanding of:
- Scene narrative and purpose
- Visual element descriptions
- Emotional beats and pacing
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .models import SoundMoment


# Prompt template for LLM analysis
ANALYSIS_PROMPT = '''Analyze this video scene for sound design opportunities.

Scene ID: {scene_id}
Scene Type: {scene_type}
Narration: {narration}
Visual Elements: {elements}
Scene Duration: {duration_seconds:.1f} seconds

Identify 3-8 moments that would benefit from subtle sound effects. For each moment:
- timestamp_seconds: When in the scene (0 to {duration_seconds:.1f})
- type: One of [element_appear, reveal, transition, counter, warning, success, highlight, data_flow]
- intensity: 0.3 (very subtle) to 1.0 (emphatic)
- context: Brief description of what's happening

Guidelines:
- Keep sounds subtle and non-distracting (max 3 per 10 seconds)
- Prioritize key narrative moments over minor visual changes
- Match sound type to the emotional tone (warning for problems, success for solutions)
- Space sounds at least 0.5 seconds apart

Return as JSON array only:
[
  {{"timestamp_seconds": 2.5, "type": "element_appear", "intensity": 0.6, "context": "Main diagram appears"}},
  ...
]'''


@dataclass
class LLMAnalysisConfig:
    """Configuration for LLM analysis."""
    max_moments: int = 8
    min_moments: int = 2
    min_gap_seconds: float = 0.5
    max_per_10_seconds: int = 3


class LLMAnalyzer:
    """Uses LLM to identify sound moments based on scene context."""

    def __init__(
        self,
        config: Optional[LLMAnalysisConfig] = None,
        fps: int = 30,
    ):
        """Initialize the LLM analyzer.

        Args:
            config: Analysis configuration
            fps: Frames per second (default 30)
        """
        self.config = config or LLMAnalysisConfig()
        self.fps = fps

    def analyze(
        self,
        scene_id: str,
        scene_type: str,
        narration: str,
        duration_seconds: float,
        elements: Optional[list[str]] = None,
        llm_client=None,
    ) -> list[SoundMoment]:
        """Analyze a scene using LLM to identify sound moments.

        Args:
            scene_id: Scene identifier
            scene_type: Scene type path
            narration: Scene narration text
            duration_seconds: Scene duration in seconds
            elements: Optional list of visual element descriptions
            llm_client: LLM client for making requests (optional)

        Returns:
            List of detected SoundMoment objects
        """
        # Build prompt
        prompt = ANALYSIS_PROMPT.format(
            scene_id=scene_id,
            scene_type=scene_type,
            narration=narration,
            duration_seconds=duration_seconds,
            elements=", ".join(elements) if elements else "Not specified",
        )

        # Get LLM response
        if llm_client is None:
            # Return empty list if no client provided
            return []

        try:
            response = self._call_llm(llm_client, prompt)
            moments = self._parse_response(response, duration_seconds)
            return moments
        except Exception as e:
            # Log error and return empty list
            print(f"LLM analysis error: {e}")
            return []

    def _call_llm(self, client, prompt: str) -> str:
        """Call the LLM with the analysis prompt.

        Args:
            client: LLM client
            prompt: Analysis prompt

        Returns:
            LLM response text
        """
        # Try different client interfaces
        if hasattr(client, "chat"):
            # OpenAI-style client
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.choices[0].message.content
        elif hasattr(client, "messages"):
            # Anthropic-style client
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        elif hasattr(client, "generate"):
            # Generic generate method
            return client.generate(prompt)
        else:
            raise ValueError("Unknown LLM client type")

    def _parse_response(
        self,
        response: str,
        duration_seconds: float,
    ) -> list[SoundMoment]:
        """Parse LLM response into SoundMoment objects.

        Args:
            response: LLM response text
            duration_seconds: Scene duration for validation

        Returns:
            List of SoundMoment objects
        """
        # Extract JSON from response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if not json_match:
            return []

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            return []

        moments = []
        for item in data:
            if not isinstance(item, dict):
                continue

            timestamp = item.get("timestamp_seconds", 0)
            moment_type = item.get("type", "element_appear")
            intensity = item.get("intensity", 0.7)
            context = item.get("context", "")

            # Validate
            if not 0 <= timestamp <= duration_seconds:
                continue
            if moment_type not in [
                "element_appear", "reveal", "transition", "counter",
                "warning", "success", "highlight", "data_flow",
                "text_reveal", "lock", "connection",
            ]:
                moment_type = "element_appear"
            intensity = max(0.3, min(1.0, intensity))

            frame = int(timestamp * self.fps)

            moments.append(SoundMoment(
                type=moment_type,
                frame=frame,
                confidence=0.7,  # LLM analysis has moderate confidence
                context=context,
                intensity=intensity,
                source="llm",
            ))

        # Apply constraints
        moments = self._apply_constraints(moments, duration_seconds)

        return moments

    def _apply_constraints(
        self,
        moments: list[SoundMoment],
        duration_seconds: float,
    ) -> list[SoundMoment]:
        """Apply configuration constraints to moments.

        Args:
            moments: Raw moments from parsing
            duration_seconds: Scene duration

        Returns:
            Constrained list of moments
        """
        if not moments:
            return []

        # Sort by frame
        moments.sort(key=lambda m: m.frame)

        # Enforce minimum gap
        min_gap_frames = int(self.config.min_gap_seconds * self.fps)
        filtered = [moments[0]]
        for moment in moments[1:]:
            if moment.frame - filtered[-1].frame >= min_gap_frames:
                filtered.append(moment)

        # Enforce max moments
        if len(filtered) > self.config.max_moments:
            # Keep highest intensity moments
            filtered.sort(key=lambda m: m.intensity, reverse=True)
            filtered = filtered[:self.config.max_moments]
            filtered.sort(key=lambda m: m.frame)

        return filtered


def analyze_scene_with_llm(
    scene_id: str,
    scene_type: str,
    narration: str,
    duration_seconds: float,
    elements: Optional[list[str]] = None,
    llm_client=None,
    fps: int = 30,
) -> list[SoundMoment]:
    """Analyze a scene using LLM for sound moment detection.

    Convenience function that creates an analyzer and runs analysis.

    Args:
        scene_id: Scene identifier
        scene_type: Scene type path
        narration: Scene narration text
        duration_seconds: Scene duration in seconds
        elements: Optional list of visual element descriptions
        llm_client: LLM client for making requests
        fps: Frames per second

    Returns:
        List of SoundMoment objects
    """
    analyzer = LLMAnalyzer(fps=fps)
    return analyzer.analyze(
        scene_id=scene_id,
        scene_type=scene_type,
        narration=narration,
        duration_seconds=duration_seconds,
        elements=elements,
        llm_client=llm_client,
    )


def mock_llm_analysis(
    scene_id: str,
    scene_type: str,
    narration: str,
    duration_seconds: float,
    fps: int = 30,
) -> list[SoundMoment]:
    """Generate mock LLM analysis for testing.

    Creates plausible sound moments based on simple heuristics.

    Args:
        scene_id: Scene identifier
        scene_type: Scene type path
        narration: Scene narration text
        duration_seconds: Scene duration in seconds
        fps: Frames per second

    Returns:
        List of mock SoundMoment objects
    """
    moments = []

    # Add moment at start
    moments.append(SoundMoment(
        type="element_appear",
        frame=int(0.5 * fps),
        confidence=0.7,
        context="Scene opening",
        intensity=0.7,
        source="llm",
    ))

    # Add moment in middle based on scene type
    mid_frame = int(duration_seconds * fps / 2)
    if "problem" in scene_type.lower() or "bottleneck" in scene_type.lower():
        moments.append(SoundMoment(
            type="warning",
            frame=mid_frame,
            confidence=0.7,
            context="Problem visualization",
            intensity=0.8,
            source="llm",
        ))
    elif "solution" in scene_type.lower() or "result" in scene_type.lower():
        moments.append(SoundMoment(
            type="success",
            frame=mid_frame,
            confidence=0.7,
            context="Solution reveal",
            intensity=0.8,
            source="llm",
        ))
    else:
        moments.append(SoundMoment(
            type="transition",
            frame=mid_frame,
            confidence=0.7,
            context="Key moment",
            intensity=0.7,
            source="llm",
        ))

    # Add moment near end if duration allows
    if duration_seconds > 5:
        end_frame = int((duration_seconds - 1) * fps)
        moments.append(SoundMoment(
            type="reveal",
            frame=end_frame,
            confidence=0.7,
            context="Scene conclusion",
            intensity=0.75,
            source="llm",
        ))

    return moments

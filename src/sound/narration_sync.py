"""Narration sync analyzer for detecting sound moments from word timestamps.

This module analyzes narration text and word-level timestamps to identify
moments that should have sound effects based on the spoken content.

Patterns detected:
- Numbers and statistics ("87x", "3500", "10 billion")
- Problem words ("bottleneck", "problem", "issue", "challenge")
- Solution words ("solution", "key", "insight", "answer")
- Action words ("watch", "see", "look", "notice")
- Emphasis words ("important", "crucial", "critical")
"""

import re
from dataclasses import dataclass
from typing import Optional

from .models import SoundMoment, WordTimestamp


@dataclass
class NarrationPattern:
    """A pattern to detect in narration text."""
    name: str
    pattern: re.Pattern
    moment_type: str
    intensity: float
    confidence: float


# Word patterns that trigger sound effects
WORD_PATTERNS = [
    # Numbers and statistics
    NarrationPattern(
        name="large_number",
        pattern=re.compile(r"\b(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?[xX%]|\d+\s*(?:billion|million|thousand|hundred))\b", re.IGNORECASE),
        moment_type="counter",
        intensity=0.8,
        confidence=0.85,
    ),
    NarrationPattern(
        name="multiplier",
        pattern=re.compile(r"\b(\d+)[xX]\b"),
        moment_type="reveal",
        intensity=0.9,
        confidence=0.9,
    ),

    # Problem indicators
    NarrationPattern(
        name="problem_word",
        pattern=re.compile(r"\b(bottleneck|problem|issue|challenge|difficult|slow|inefficient|waste|fail|error)\b", re.IGNORECASE),
        moment_type="warning",
        intensity=0.7,
        confidence=0.75,
    ),

    # Solution indicators
    NarrationPattern(
        name="solution_word",
        pattern=re.compile(r"\b(solution|solve|key|insight|answer|fix|optimize|improve|faster|better|efficient)\b", re.IGNORECASE),
        moment_type="success",
        intensity=0.8,
        confidence=0.8,
    ),

    # Revelation/insight moments
    NarrationPattern(
        name="revelation_word",
        pattern=re.compile(r"\b(secret|trick|magic|amazing|incredible|powerful|breakthrough|discover|realize|reveal)\b", re.IGNORECASE),
        moment_type="reveal",
        intensity=0.85,
        confidence=0.8,
    ),

    # Attention grabbers
    NarrationPattern(
        name="attention_word",
        pattern=re.compile(r"\b(watch|look|see|notice|observe|here|now|this)\b", re.IGNORECASE),
        moment_type="highlight",
        intensity=0.6,
        confidence=0.6,
    ),

    # Emphasis words
    NarrationPattern(
        name="emphasis_word",
        pattern=re.compile(r"\b(important|crucial|critical|essential|key|main|primary)\b", re.IGNORECASE),
        moment_type="highlight",
        intensity=0.7,
        confidence=0.7,
    ),

    # Transition words
    NarrationPattern(
        name="transition_word",
        pattern=re.compile(r"\b(but|however|instead|actually|surprisingly|interestingly)\b", re.IGNORECASE),
        moment_type="transition",
        intensity=0.6,
        confidence=0.65,
    ),
]


class NarrationSyncAnalyzer:
    """Analyzes narration to detect sound moments based on word content."""

    def __init__(self, fps: int = 30):
        """Initialize the analyzer.

        Args:
            fps: Frames per second (default 30)
        """
        self.fps = fps
        self.patterns = WORD_PATTERNS

    def analyze(
        self,
        narration: str,
        word_timestamps: list[WordTimestamp],
        scene_type: Optional[str] = None,
    ) -> list[SoundMoment]:
        """Analyze narration and word timestamps to find sound moments.

        Args:
            narration: Full narration text
            word_timestamps: List of word timestamps from TTS
            scene_type: Optional scene type for context-aware detection

        Returns:
            List of detected SoundMoment objects
        """
        moments = []

        # Create word lookup for timestamp matching
        word_lookup = self._build_word_lookup(word_timestamps)

        # Apply each pattern
        for pattern in self.patterns:
            for match in pattern.pattern.finditer(narration):
                matched_text = match.group(0)
                start_pos = match.start()

                # Find the word timestamp for this position
                timestamp = self._find_timestamp_for_position(
                    start_pos, narration, word_lookup
                )

                if timestamp:
                    frame = timestamp.start_frame

                    moment = SoundMoment(
                        type=pattern.moment_type,
                        frame=frame,
                        confidence=pattern.confidence,
                        context=f"Narration: '{matched_text}' ({pattern.name})",
                        intensity=pattern.intensity,
                        source="narration",
                    )
                    moments.append(moment)

        # Sort by frame and deduplicate nearby moments
        moments = self._deduplicate_nearby(moments)

        return moments

    def _build_word_lookup(
        self,
        timestamps: list[WordTimestamp],
    ) -> dict[str, list[WordTimestamp]]:
        """Build a lookup table for word timestamps.

        Args:
            timestamps: List of word timestamps

        Returns:
            Dict mapping lowercase words to their timestamps
        """
        lookup: dict[str, list[WordTimestamp]] = {}

        for ts in timestamps:
            word_lower = ts.word.lower().strip(".,!?;:'\"")
            if word_lower not in lookup:
                lookup[word_lower] = []
            lookup[word_lower].append(ts)

        return lookup

    def _find_timestamp_for_position(
        self,
        char_position: int,
        text: str,
        word_lookup: dict[str, list[WordTimestamp]],
    ) -> Optional[WordTimestamp]:
        """Find the word timestamp for a character position in text.

        Args:
            char_position: Character position in text
            text: Full narration text
            word_lookup: Word timestamp lookup table

        Returns:
            WordTimestamp if found, None otherwise
        """
        # Extract the word at this position
        word_start = char_position
        word_end = char_position

        # Find word boundaries
        while word_start > 0 and text[word_start - 1].isalnum():
            word_start -= 1
        while word_end < len(text) and text[word_end].isalnum():
            word_end += 1

        word = text[word_start:word_end].lower()

        # Look up timestamp
        if word in word_lookup and word_lookup[word]:
            # Return the first available timestamp for this word
            return word_lookup[word].pop(0)

        return None

    def _deduplicate_nearby(
        self,
        moments: list[SoundMoment],
        min_gap_frames: int = 15,
    ) -> list[SoundMoment]:
        """Remove moments that are too close together.

        Args:
            moments: List of moments
            min_gap_frames: Minimum frames between moments

        Returns:
            Deduplicated list
        """
        if not moments:
            return []

        sorted_moments = sorted(moments, key=lambda m: m.frame)
        result = [sorted_moments[0]]

        for moment in sorted_moments[1:]:
            if moment.frame - result[-1].frame >= min_gap_frames:
                result.append(moment)
            elif moment.confidence > result[-1].confidence:
                # Replace if this one has higher confidence
                result[-1] = moment

        return result


def sync_to_narration(
    narration: str,
    word_timestamps: list[WordTimestamp],
    scene_type: Optional[str] = None,
    fps: int = 30,
) -> list[SoundMoment]:
    """Sync sounds to narration based on word content and timing.

    Convenience function that creates an analyzer and runs analysis.

    Args:
        narration: Full narration text
        word_timestamps: List of word timestamps from TTS
        scene_type: Optional scene type for context
        fps: Frames per second (default 30)

    Returns:
        List of SoundMoment objects
    """
    analyzer = NarrationSyncAnalyzer(fps=fps)
    return analyzer.analyze(narration, word_timestamps, scene_type)


def parse_word_timestamps_from_json(data: list[dict]) -> list[WordTimestamp]:
    """Parse word timestamps from JSON format.

    Expected format: [{"word": "hello", "start": 0.5, "end": 0.8}, ...]

    Args:
        data: List of word timing dicts

    Returns:
        List of WordTimestamp objects
    """
    return [
        WordTimestamp(
            word=item.get("word", ""),
            start_seconds=item.get("start", 0.0),
            end_seconds=item.get("end", 0.0),
            confidence=item.get("confidence", 1.0),
        )
        for item in data
    ]


def analyze_narration_text(
    narration: str,
    fps: int = 30,
    avg_word_duration: float = 0.3,
) -> list[SoundMoment]:
    """Analyze narration text without explicit timestamps.

    Estimates word positions based on average word duration.
    Less accurate than using real timestamps, but useful for testing.

    Args:
        narration: Full narration text
        fps: Frames per second
        avg_word_duration: Average word duration in seconds

    Returns:
        List of SoundMoment objects
    """
    # Split into words and estimate timestamps
    words = narration.split()
    timestamps = []

    current_time = 0.0
    for word in words:
        # Clean word
        clean_word = word.strip(".,!?;:'\"")
        if clean_word:
            timestamps.append(WordTimestamp(
                word=clean_word,
                start_seconds=current_time,
                end_seconds=current_time + avg_word_duration,
            ))
            current_time += avg_word_duration

    return sync_to_narration(narration, timestamps, fps=fps)

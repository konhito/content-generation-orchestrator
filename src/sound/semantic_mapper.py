"""Semantic Sound Mapper for context-aware sound selection.

This module provides intelligent sound selection based on animation context,
component hints, and scene narrative phase. It replaces the simple
moment_type -> sound mapping with a more nuanced approach that considers:

1. Component context (what visual element is animating)
2. Property being animated (opacity, width, scale, etc.)
3. Value ranges (small vs dramatic changes)
4. Scene position (intro, buildup, climax, outro)
5. Nearby text hints from the source code
"""

from dataclasses import dataclass
from typing import Optional

from .models import SoundMoment, MOMENT_TO_SOUND


@dataclass
class SoundSelection:
    """Result of sound selection with explanation."""

    sound: str
    confidence: float
    reason: str


# Context patterns mapped to appropriate sounds
# Format: (context_pattern, property_pattern) -> sound_name
# Use "*" as wildcard for any match
CONTEXT_SOUND_MAP: dict[tuple[str, str], str] = {
    # Typing/Code patterns - keyboard sounds
    ("prompt", "opacity"): "keyboard_type",
    ("code", "opacity"): "keyboard_type",
    ("typing", "*"): "keyboard_type",
    ("cursor", "*"): "text_tick",

    # Token/Text streaming patterns
    ("token", "opacity"): "text_tick",
    ("token", "*"): "text_tick",
    ("text", "opacity"): "text_tick",
    ("response", "opacity"): "text_tick",
    ("stream", "*"): "digital_stream",

    # Counter/Number patterns - sweeping sounds
    ("speed", "counter"): "counter_sweep",
    ("speed", "*"): "counter_sweep",
    ("count", "counter"): "counter_sweep",
    ("count", "*"): "counter_sweep",
    ("counter", "*"): "counter_sweep",
    ("number", "*"): "counter_sweep",

    # Chart/Bar patterns - growth sounds
    ("bar", "width"): "bar_grow",
    ("bar", "*"): "bar_grow",
    ("chart", "width"): "bar_grow",
    ("chart", "*"): "bar_grow",
    ("progress", "width"): "progress_tick",
    ("progress", "*"): "progress_tick",
    ("slow", "width"): "bar_grow",
    ("fast", "width"): "bar_grow",

    # Reveal/Badge/Emphasis patterns - impact sounds
    ("reveal", "opacity"): "reveal_hit",
    ("reveal", "scale"): "reveal_hit",
    ("reveal", "*"): "reveal_hit",
    ("badge", "opacity"): "reveal_hit",
    ("badge", "scale"): "reveal_hit",
    ("badge", "*"): "reveal_hit",
    ("87x", "*"): "reveal_hit",
    ("faster", "*"): "reveal_hit",

    # Burst/Particle effects - transition sounds
    ("burst", "*"): "transition_whoosh",
    ("particle", "*"): "transition_whoosh",
    ("sparkle", "*"): "ui_pop",
    ("glow", "*"): "ui_pop",

    # Flow/Stream patterns
    ("flow", "opacity"): "data_flow",
    ("flow", "*"): "data_flow",
    ("data", "*"): "data_flow",

    # Phase/Transition patterns
    ("phase", "*"): "transition_whoosh",
    ("transition", "*"): "transition_whoosh",

    # Problem/Solution patterns
    ("slow", "opacity"): "warning_tone",
    ("naive", "*"): "warning_tone",
    ("problem", "*"): "warning_tone",
    ("optimized", "*"): "success_tone",
    ("solution", "*"): "success_tone",
    ("success", "*"): "success_tone",

    # Lock/Click patterns
    ("lock", "*"): "lock_click",
    ("click", "*"): "lock_click",
    ("cache", "*"): "cache_click",

    # Generic property-based fallbacks
    ("*", "opacity"): "ui_pop",
    ("*", "scale"): "ui_pop",
    ("*", "width"): "counter_sweep",
    ("*", "height"): "counter_sweep",
    ("*", "spring"): "ui_pop",
}


class SemanticSoundMapper:
    """Maps animation moments to appropriate sounds based on context.

    This mapper uses multiple signals to select the most appropriate
    sound for each animation moment:
    - Context hints from variable names and component structure
    - Animation property being changed
    - Value ranges indicating scale of change
    - Scene position for narrative arc
    """

    def __init__(self, custom_mappings: Optional[dict[tuple[str, str], str]] = None):
        """Initialize the mapper.

        Args:
            custom_mappings: Optional additional context->sound mappings
        """
        self.mappings = dict(CONTEXT_SOUND_MAP)
        if custom_mappings:
            self.mappings.update(custom_mappings)

    def select_sound(
        self,
        moment: SoundMoment,
        scene_duration: int = 300,
    ) -> SoundSelection:
        """Select the most appropriate sound for a moment.

        Args:
            moment: The sound moment with context
            scene_duration: Total scene duration for position calculations

        Returns:
            SoundSelection with sound name and explanation
        """
        # Extract context hints from moment
        context_lower = moment.context.lower() if moment.context else ""
        moment_type = moment.type.lower()

        # Try to find matching patterns
        sound, reason = self._find_best_match(context_lower, moment_type)

        # If no specific match, use moment type mapping
        if sound is None:
            sound = MOMENT_TO_SOUND.get(moment.type, "ui_pop")
            reason = f"Default mapping for {moment.type}"

        # Apply scene position adjustments
        sound, reason = self._adjust_for_position(
            sound, reason, moment.frame, scene_duration
        )

        # Apply intensity adjustments
        sound, reason = self._adjust_for_intensity(sound, reason, moment.intensity)

        return SoundSelection(
            sound=sound,
            confidence=moment.confidence,
            reason=reason,
        )

    def _find_best_match(
        self,
        context: str,
        moment_type: str,
    ) -> tuple[Optional[str], str]:
        """Find the best matching sound pattern.

        Args:
            context: Lowercase context string from moment
            moment_type: Type of moment

        Returns:
            Tuple of (sound_name or None, reason_string)
        """
        # Extract property hint from moment type
        property_hint = self._extract_property_hint(moment_type)

        # Score each pattern
        best_sound = None
        best_score = 0
        best_reason = ""

        for (ctx_pattern, prop_pattern), sound in self.mappings.items():
            score = self._score_pattern(context, property_hint, ctx_pattern, prop_pattern)
            if score > best_score:
                best_score = score
                best_sound = sound
                best_reason = f"Matched pattern ({ctx_pattern}, {prop_pattern})"

        if best_score > 0:
            return best_sound, best_reason

        return None, ""

    def _extract_property_hint(self, moment_type: str) -> str:
        """Extract property hint from moment type."""
        type_to_property = {
            "element_appear": "opacity",
            "element_disappear": "opacity",
            "text_reveal": "opacity",
            "reveal": "scale",
            "counter": "counter",
            "chart_grow": "width",
            "transition": "transition",
            "highlight": "glow",
            "pulse": "scale",
            "data_flow": "flow",
            "lock": "lock",
            "connection": "connection",
            "warning": "warning",
            "success": "success",
        }
        return type_to_property.get(moment_type, "unknown")

    def _score_pattern(
        self,
        context: str,
        property_hint: str,
        ctx_pattern: str,
        prop_pattern: str,
    ) -> int:
        """Score how well a pattern matches the context.

        Higher scores indicate better matches. Wildcard (*) matches
        are scored lower than specific matches.
        """
        score = 0

        # Context matching
        if ctx_pattern == "*":
            score += 1  # Wildcard match
        elif ctx_pattern in context:
            score += 10  # Specific context match

        # Property matching
        if prop_pattern == "*":
            score += 1  # Wildcard match
        elif prop_pattern == property_hint:
            score += 5  # Specific property match
        elif prop_pattern in property_hint:
            score += 3  # Partial property match

        # Both patterns must match for a valid score
        ctx_matches = ctx_pattern == "*" or ctx_pattern in context
        prop_matches = prop_pattern == "*" or prop_pattern in property_hint

        if not (ctx_matches and prop_matches):
            return 0

        return score

    def _adjust_for_position(
        self,
        sound: str,
        reason: str,
        frame: int,
        scene_duration: int,
    ) -> tuple[str, str]:
        """Adjust sound selection based on scene position.

        Args:
            sound: Currently selected sound
            reason: Current reason string
            frame: Frame position of moment
            scene_duration: Total scene duration

        Returns:
            Potentially adjusted sound and reason
        """
        if scene_duration <= 0:
            return sound, reason

        position = frame / scene_duration

        # Late reveals should use more impactful sounds
        if position > 0.7 and sound == "ui_pop":
            # Check if this might be a reveal moment
            return "reveal_hit", f"{reason} (climax position adjustment)"

        # Early elements might be more subtle
        if position < 0.15 and sound == "reveal_hit":
            return "ui_pop", f"{reason} (intro position adjustment)"

        return sound, reason

    def _adjust_for_intensity(
        self,
        sound: str,
        reason: str,
        intensity: float,
    ) -> tuple[str, str]:
        """Adjust sound selection based on intensity.

        Args:
            sound: Currently selected sound
            reason: Current reason string
            intensity: Moment intensity (0-1)

        Returns:
            Potentially adjusted sound and reason
        """
        # High intensity moments should use impactful sounds
        if intensity > 0.85 and sound in ("ui_pop", "text_tick"):
            return "reveal_hit", f"{reason} (high intensity adjustment)"

        # Very low intensity moments should use subtle sounds
        if intensity < 0.4 and sound == "reveal_hit":
            return "ui_pop", f"{reason} (low intensity adjustment)"

        return sound, reason

    def get_available_sounds(self) -> list[str]:
        """Get list of all sounds used in mappings."""
        return sorted(set(self.mappings.values()))


def map_moment_to_sound(
    moment: SoundMoment,
    scene_duration: int = 300,
) -> str:
    """Map a moment to an appropriate sound.

    Convenience function for simple usage.

    Args:
        moment: The sound moment
        scene_duration: Total scene duration in frames

    Returns:
        Sound name string
    """
    mapper = SemanticSoundMapper()
    selection = mapper.select_sound(moment, scene_duration)
    return selection.sound


def map_moments_to_sounds(
    moments: list[SoundMoment],
    scene_duration: int = 300,
) -> list[tuple[SoundMoment, str]]:
    """Map multiple moments to sounds.

    Args:
        moments: List of sound moments
        scene_duration: Total scene duration in frames

    Returns:
        List of (moment, sound_name) tuples
    """
    mapper = SemanticSoundMapper()
    return [
        (moment, mapper.select_sound(moment, scene_duration).sound)
        for moment in moments
    ]

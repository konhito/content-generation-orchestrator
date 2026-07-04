"""Data models for the SFX system.

This module defines the core data structures used throughout the
sound effects generation pipeline.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MomentType(Enum):
    """Types of sound moments detected in scenes."""

    ELEMENT_APPEAR = "element_appear"      # Element fading/popping in
    ELEMENT_DISAPPEAR = "element_disappear" # Element fading out
    TEXT_REVEAL = "text_reveal"            # Text appearing
    REVEAL = "reveal"                      # Big "aha" moment
    COUNTER = "counter"                    # Number animation
    TRANSITION = "transition"              # Scene/phase change
    WARNING = "warning"                    # Problem highlight
    SUCCESS = "success"                    # Solution/positive
    LOCK = "lock"                          # Snapping into place
    DATA_FLOW = "data_flow"               # Information streaming
    CONNECTION = "connection"             # Two things connecting
    HIGHLIGHT = "highlight"               # Visual emphasis
    CHART_GROW = "chart_grow"             # Growing bar/chart
    PULSE = "pulse"                       # Rhythmic emphasis


@dataclass
class SoundMoment:
    """A detected moment that should have sound.

    Represents a single point in time where an animation event
    occurs that would benefit from sound design.

    Attributes:
        type: The category of sound event
        frame: Frame number relative to scene start
        confidence: Detection confidence (0-1)
        context: Description of what's happening
        intensity: Suggested volume/prominence (0-1)
        source: Where this moment was detected from
        duration_frames: Optional duration for looping sounds
    """
    type: str
    frame: int
    confidence: float
    context: str
    intensity: float = 0.7
    source: str = "code"  # "code", "narration", "llm"
    duration_frames: Optional[int] = None

    def __post_init__(self):
        """Validate field values."""
        self.confidence = max(0.0, min(1.0, self.confidence))
        self.intensity = max(0.0, min(1.0, self.intensity))
        self.frame = max(0, self.frame)


@dataclass
class SFXCue:
    """Frame-accurate cue for storyboard.json.

    This is the output format that gets written to the storyboard
    and is consumed by the Remotion player.

    Attributes:
        sound: Sound file name (without extension)
        frame: Frame offset from scene start
        volume: Volume level (0-1), typically 0.05-0.15
        duration_frames: Optional duration for looping sounds
    """
    sound: str
    frame: int
    volume: float = 0.1
    duration_frames: Optional[int] = None

    def __post_init__(self):
        """Validate field values."""
        self.volume = max(0.0, min(1.0, self.volume))
        self.frame = max(0, self.frame)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "sound": self.sound,
            "frame": self.frame,
            "volume": self.volume,
        }
        if self.duration_frames is not None:
            result["duration_frames"] = self.duration_frames
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "SFXCue":
        """Create from dictionary."""
        return cls(
            sound=data["sound"],
            frame=data["frame"],
            volume=data.get("volume", 0.1),
            duration_frames=data.get("duration_frames"),
        )


@dataclass
class WordTimestamp:
    """A word with its timing information.

    Used for syncing sounds to narration.

    Attributes:
        word: The spoken word
        start_seconds: Start time in seconds
        end_seconds: End time in seconds
        confidence: Recognition confidence (0-1)
    """
    word: str
    start_seconds: float
    end_seconds: float
    confidence: float = 1.0

    @property
    def start_frame(self) -> int:
        """Get start time as frame number at 30fps."""
        return int(self.start_seconds * 30)

    @property
    def end_frame(self) -> int:
        """Get end time as frame number at 30fps."""
        return int(self.end_seconds * 30)

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        return self.end_seconds - self.start_seconds


@dataclass
class SceneAnalysisResult:
    """Result of analyzing a scene for sound moments.

    Attributes:
        scene_id: Scene identifier
        scene_type: Scene type path (e.g., "llm-inference/hook")
        duration_frames: Total scene duration in frames
        moments: Detected sound moments
        source_file: Path to the analyzed TSX file
        analysis_notes: Any notes from the analysis
    """
    scene_id: str
    scene_type: str
    duration_frames: int
    moments: list[SoundMoment] = field(default_factory=list)
    source_file: Optional[str] = None
    analysis_notes: list[str] = field(default_factory=list)

    def add_moment(self, moment: SoundMoment) -> None:
        """Add a sound moment to the result."""
        self.moments.append(moment)

    def get_moments_by_type(self, moment_type: str) -> list[SoundMoment]:
        """Get all moments of a specific type."""
        return [m for m in self.moments if m.type == moment_type]

    def get_moments_in_range(self, start_frame: int, end_frame: int) -> list[SoundMoment]:
        """Get moments within a frame range."""
        return [m for m in self.moments if start_frame <= m.frame <= end_frame]


# Volume guidelines by moment type
VOLUME_BY_TYPE = {
    "element_appear": 0.08,
    "element_disappear": 0.06,
    "text_reveal": 0.05,
    "reveal": 0.12,
    "counter": 0.10,
    "transition": 0.08,
    "warning": 0.10,
    "success": 0.10,
    "lock": 0.08,
    "data_flow": 0.08,
    "connection": 0.08,
    "highlight": 0.07,
    "chart_grow": 0.08,
    "pulse": 0.07,
}

# Mapping from moment type to sound library name
# Note: For more context-aware mapping, use semantic_mapper.py
MOMENT_TO_SOUND = {
    "element_appear": "ui_pop",
    "element_disappear": "ui_pop",
    "text_reveal": "text_tick",
    "reveal": "reveal_hit",
    "counter": "counter_sweep",
    "transition": "transition_whoosh",
    "warning": "warning_tone",
    "success": "success_tone",
    "lock": "lock_click",
    "data_flow": "data_flow",
    "connection": "lock_click",
    "highlight": "ui_pop",
    "chart_grow": "bar_grow",
    "pulse": "ui_pop",
    # Extended mappings for semantic analysis
    "typing": "keyboard_type",
    "typing_rapid": "keyboard_rapid",
    "bar_growth": "bar_grow",
    "progress": "progress_tick",
    "streaming": "digital_stream",
    "soft_reveal": "impact_soft",
    "hard_reveal": "impact_hard",
}


def calculate_volume(moment: SoundMoment) -> float:
    """Calculate appropriate volume for a sound moment.

    Uses the base volume for the moment type, scaled by intensity.

    Args:
        moment: The sound moment

    Returns:
        Volume value between 0 and 0.15
    """
    base = VOLUME_BY_TYPE.get(moment.type, 0.08)
    # Scale by intensity (0-1) - minimum 70% of base, maximum 130%
    volume = base * (0.7 + 0.3 * moment.intensity)
    # Cap at 0.15 to avoid overpowering narration
    return min(volume, 0.15)


def get_sound_for_moment(moment_type: str) -> str:
    """Get the appropriate sound name for a moment type.

    Args:
        moment_type: The type of sound moment

    Returns:
        Sound name from the library
    """
    return MOMENT_TO_SOUND.get(moment_type, "ui_pop")

"""Pydantic models for storyboard structure.

These models mirror the JSON schema in storyboards/schema/storyboard.schema.json
and provide validation and type safety in Python.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


class Position(BaseModel):
    """Position on screen."""

    x: int | Literal["left", "center", "right"] = "center"
    y: int | Literal["top", "center", "bottom"] = "center"
    anchor: Literal[
        "top-left",
        "top-center",
        "top-right",
        "center-left",
        "center",
        "center-right",
        "bottom-left",
        "bottom-center",
        "bottom-right",
    ] = "center"


class Transition(BaseModel):
    """Element enter/exit transition."""

    type: Literal["fade", "slide", "scale", "none"] = "fade"
    direction: Literal["up", "down", "left", "right"] | None = None
    duration_seconds: float = 0.3
    delay_seconds: float = 0


class Animation(BaseModel):
    """An animation to apply to an element."""

    action: str
    at_seconds: float
    duration_seconds: float = 0.3
    easing: Literal["linear", "ease-in", "ease-out", "ease-in-out", "spring"] = (
        "ease-out"
    )
    params: dict[str, Any] | None = None


class Element(BaseModel):
    """A visual component instance."""

    id: str
    component: str
    props: dict[str, Any] | None = None
    position: Position | None = None
    animations: list[Animation] | None = None
    enter: Transition | None = None
    exit: Transition | None = None


class SyncPoint(BaseModel):
    """Trigger an action when a word/phrase is spoken."""

    trigger_word: str | None = None
    trigger_seconds: float
    target: str
    action: str
    params: dict[str, Any] | None = None


class Beat(BaseModel):
    """A time-based segment of the scene."""

    id: str
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    voiceover: str | None = None
    elements: list[Element] | None = None
    sync_points: list[SyncPoint] | None = None

    @property
    def duration_seconds(self) -> float:
        """Calculate beat duration."""
        return self.end_seconds - self.start_seconds


class WordTimestamp(BaseModel):
    """Word-level timing from TTS."""

    word: str
    start: float
    end: float


class AudioConfig(BaseModel):
    """Audio file reference and timing metadata."""

    file: str
    duration_seconds: float
    word_timestamps: list[WordTimestamp] | None = None


class StyleConfig(BaseModel):
    """Visual style overrides for the scene."""

    background_color: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    font_family: str | None = None


class Storyboard(BaseModel):
    """Complete storyboard definition."""

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str
    description: str | None = None
    duration_seconds: float = Field(gt=0)
    audio: AudioConfig | None = None
    style: StyleConfig | None = None
    beats: list[Beat] = Field(min_length=1)

    @property
    def total_frames(self) -> int:
        """Calculate total frames at 30fps."""
        return int(self.duration_seconds * 30)

    def get_beat_at_time(self, time_seconds: float) -> Beat | None:
        """Get the beat that contains the given time."""
        for beat in self.beats:
            if beat.start_seconds <= time_seconds < beat.end_seconds:
                return beat
        return None

    def get_all_elements(self) -> list[Element]:
        """Get all elements across all beats."""
        elements = []
        for beat in self.beats:
            if beat.elements:
                elements.extend(beat.elements)
        return elements

    def get_used_components(self) -> set[str]:
        """Get all unique component types used."""
        components = set()
        for element in self.get_all_elements():
            components.add(element.component)
        return components

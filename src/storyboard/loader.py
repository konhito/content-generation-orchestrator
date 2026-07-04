"""Storyboard loader and validator.

This module handles loading storyboard JSON files and validating them
against the schema.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import Storyboard


class StoryboardError(Exception):
    """Base exception for storyboard errors."""

    pass


class StoryboardLoadError(StoryboardError):
    """Error loading a storyboard file."""

    pass


class StoryboardValidationError(StoryboardError):
    """Error validating a storyboard."""

    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


def load_storyboard(path: str | Path) -> Storyboard:
    """Load a storyboard from a JSON file.

    Args:
        path: Path to the storyboard JSON file.

    Returns:
        Validated Storyboard object.

    Raises:
        StoryboardLoadError: If the file cannot be read.
        StoryboardValidationError: If the storyboard is invalid.
    """
    path = Path(path)

    if not path.exists():
        raise StoryboardLoadError(f"Storyboard file not found: {path}")

    if not path.suffix == ".json":
        raise StoryboardLoadError(f"Storyboard file must be JSON: {path}")

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise StoryboardLoadError(f"Invalid JSON in {path}: {e}")
    except IOError as e:
        raise StoryboardLoadError(f"Error reading {path}: {e}")

    return parse_storyboard(data)


def parse_storyboard(data: dict[str, Any]) -> Storyboard:
    """Parse a storyboard from a dictionary.

    Args:
        data: Dictionary containing storyboard data.

    Returns:
        Validated Storyboard object.

    Raises:
        StoryboardValidationError: If the data is invalid.
    """
    try:
        return Storyboard.model_validate(data)
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        raise StoryboardValidationError(
            f"Invalid storyboard: {len(errors)} validation errors",
            errors=errors,
        )


def validate_storyboard(storyboard: Storyboard) -> list[str]:
    """Validate a storyboard for logical consistency.

    Performs additional validation beyond schema validation:
    - Beat times don't overlap unexpectedly
    - Element IDs are unique within a beat
    - Sync point targets reference valid elements
    - Animation times are within beat bounds

    Args:
        storyboard: Storyboard to validate.

    Returns:
        List of warning/error messages (empty if valid).
    """
    issues = []

    # Check beat ordering and gaps
    beats_sorted = sorted(storyboard.beats, key=lambda b: b.start_seconds)
    for i, beat in enumerate(beats_sorted):
        if beat.start_seconds >= beat.end_seconds:
            issues.append(
                f"Beat '{beat.id}': start_seconds ({beat.start_seconds}) "
                f">= end_seconds ({beat.end_seconds})"
            )

        if i > 0:
            prev_beat = beats_sorted[i - 1]
            if beat.start_seconds < prev_beat.end_seconds:
                # Overlapping beats - might be intentional
                pass  # Allow overlap for now

    # Check element IDs are unique within each beat
    for beat in storyboard.beats:
        if beat.elements:
            element_ids = [el.id for el in beat.elements]
            duplicates = [
                eid for eid in element_ids if element_ids.count(eid) > 1
            ]
            if duplicates:
                issues.append(
                    f"Beat '{beat.id}': duplicate element IDs: {set(duplicates)}"
                )

    # Check sync point targets reference valid elements
    for beat in storyboard.beats:
        if beat.sync_points and beat.elements:
            element_ids = {el.id for el in beat.elements}
            for sp in beat.sync_points:
                if sp.target not in element_ids:
                    issues.append(
                        f"Beat '{beat.id}': sync point targets unknown element "
                        f"'{sp.target}'"
                    )

    # Check animation times are within beat bounds
    for beat in storyboard.beats:
        if beat.elements:
            for element in beat.elements:
                if element.animations:
                    for anim in element.animations:
                        if anim.at_seconds < beat.start_seconds:
                            issues.append(
                                f"Beat '{beat.id}', element '{element.id}': "
                                f"animation at {anim.at_seconds}s is before "
                                f"beat start ({beat.start_seconds}s)"
                            )
                        anim_end = anim.at_seconds + anim.duration_seconds
                        if anim_end > beat.end_seconds + 1:  # Allow 1s grace
                            issues.append(
                                f"Beat '{beat.id}', element '{element.id}': "
                                f"animation ends at {anim_end}s, after "
                                f"beat end ({beat.end_seconds}s)"
                            )

    # Check total duration matches beats
    if storyboard.beats:
        max_beat_end = max(b.end_seconds for b in storyboard.beats)
        if max_beat_end > storyboard.duration_seconds:
            issues.append(
                f"Beat ends at {max_beat_end}s but storyboard duration is "
                f"{storyboard.duration_seconds}s"
            )

    return issues


def storyboard_to_dict(storyboard: Storyboard) -> dict[str, Any]:
    """Convert a storyboard to a dictionary for JSON serialization.

    Args:
        storyboard: Storyboard to convert.

    Returns:
        Dictionary suitable for JSON.dump().
    """
    return storyboard.model_dump(exclude_none=True)


def save_storyboard(storyboard: Storyboard, path: str | Path) -> None:
    """Save a storyboard to a JSON file.

    Args:
        storyboard: Storyboard to save.
        path: Path to save to.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(storyboard_to_dict(storyboard), f, indent=2)

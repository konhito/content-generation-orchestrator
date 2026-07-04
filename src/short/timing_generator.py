"""Timing generator for YouTube Shorts scene synchronization.

This module generates timing.ts files from storyboard word timestamps,
allowing scene components to automatically sync their animations with
voiceover timing changes.
"""

import json
import re
from pathlib import Path
from typing import Any

from .models import ShortsStoryboard, ShortsBeat, PhaseMarker


def find_word_frame(
    word_timestamps: list[dict[str, Any]],
    target_word: str,
    fps: int = 30,
    match_mode: str = "contains",
    use_start: bool = False,
    offset_frames: int = 0,
) -> int | None:
    """Find the frame number when a specific word is spoken.

    Args:
        word_timestamps: List of word timestamp dicts with 'word', 'start_seconds', 'end_seconds'.
        target_word: The word to find (case-insensitive).
        fps: Frames per second for conversion.
        match_mode: How to match words:
            - "exact": Word must match exactly (after stripping punctuation)
            - "contains": Word contains the target (default)
            - "starts_with": Word starts with target
        use_start: If True, return frame at word START. If False, return frame at word END.
        offset_frames: Number of frames to add to the result (negative = earlier).

    Returns:
        Frame number when the word starts/ends (plus offset), or None if not found.
    """
    target_lower = target_word.lower().strip()
    # Also strip punctuation from target for matching
    target_clean = re.sub(r"[.,!?;:'\"]+$", "", target_lower)

    for ts in word_timestamps:
        word = ts.get("word", "")
        # Strip common punctuation for matching
        word_clean = re.sub(r"[.,!?;:'\"]+$", "", word.lower().strip())

        matched = False
        if match_mode == "exact":
            matched = word_clean == target_clean
        elif match_mode == "contains":
            matched = target_clean in word_clean or word_clean in target_clean
        elif match_mode == "starts_with":
            matched = word_clean.startswith(target_clean)

        if matched:
            # Return frame at start or end of word
            if use_start:
                time_seconds = ts.get("start_seconds", 0)
            else:
                time_seconds = ts.get("end_seconds", 0)
            return int(time_seconds * fps) + offset_frames

    return None


def find_word_frame_fuzzy(
    word_timestamps: list[dict[str, Any]],
    target_word: str,
    fps: int = 30,
    use_start: bool = False,
    offset_frames: int = 0,
) -> int | None:
    """Find word frame with fuzzy matching, trying multiple strategies.

    Args:
        word_timestamps: List of word timestamp dicts.
        target_word: The word to find.
        fps: Frames per second.
        use_start: If True, return frame at word START.
        offset_frames: Number of frames to add to the result.

    Returns:
        Frame number or None if not found.
    """
    # Try exact match first
    frame = find_word_frame(word_timestamps, target_word, fps, "exact", use_start, offset_frames)
    if frame is not None:
        return frame

    # Try contains match
    frame = find_word_frame(word_timestamps, target_word, fps, "contains", use_start, offset_frames)
    if frame is not None:
        return frame

    # Try starts_with match
    frame = find_word_frame(word_timestamps, target_word, fps, "starts_with", use_start, offset_frames)
    if frame is not None:
        return frame

    return None


def calculate_beat_timing(
    beat: ShortsBeat,
    fps: int = 30,
    animation_lead_frames: int = -3,
) -> dict[str, int]:
    """Calculate timing values for a beat based on its phase markers.

    Args:
        beat: The beat containing word_timestamps and phase_markers.
        fps: Frames per second.
        animation_lead_frames: Offset to apply to animation start times.
            Negative values make animations start before the word is spoken,
            which typically looks more natural.

    Returns:
        Dict mapping marker IDs to frame numbers.
    """
    timing: dict[str, int] = {}

    # Add beat duration in frames
    duration_seconds = beat.end_seconds - beat.start_seconds
    timing["duration"] = int(duration_seconds * fps)

    # Process each phase marker
    # Use word START time with a lead offset so animations begin just before the word
    for marker in beat.phase_markers:
        frame = find_word_frame_fuzzy(
            beat.word_timestamps,
            marker.end_word,
            fps,
            use_start=True,  # Use word start time
            offset_frames=animation_lead_frames,  # Start animation slightly early
        )
        if frame is not None:
            # Ensure frame is not negative
            timing[marker.id] = max(0, frame)
        else:
            # Log warning but don't fail - use a default
            print(f"  Warning: Could not find word '{marker.end_word}' for marker '{marker.id}' in beat {beat.id}")
            # Default to middle of beat if word not found
            timing[marker.id] = timing["duration"] // 2

    return timing


def generate_timing_data(
    storyboard: ShortsStoryboard,
    fps: int = 30,
) -> dict[str, dict[str, int]]:
    """Generate timing data for all beats in a storyboard.

    Args:
        storyboard: The storyboard with beats containing phase markers.
        fps: Frames per second.

    Returns:
        Dict mapping beat IDs to their timing values.
    """
    timing_data: dict[str, dict[str, int]] = {}

    for beat in storyboard.beats:
        if beat.phase_markers:
            timing_data[beat.id] = calculate_beat_timing(beat, fps)

    return timing_data


def generate_timing_typescript(
    timing_data: dict[str, dict[str, int]],
) -> str:
    """Generate TypeScript source code for timing constants.

    Args:
        timing_data: Dict mapping beat IDs to their timing values.

    Returns:
        TypeScript source code as a string.
    """
    lines = [
        "/**",
        " * Auto-generated timing constants for scene synchronization.",
        " * DO NOT EDIT MANUALLY - regenerate with: python -m src.cli short timing <project>",
        " *",
        " * This file is generated from storyboard word timestamps and phase markers.",
        " * When the voiceover changes, regenerate this file to update all scene timings.",
        " */",
        "",
        "export const TIMING = {",
    ]

    for beat_id, timing in timing_data.items():
        lines.append(f"  {beat_id}: {{")
        for key, value in timing.items():
            lines.append(f"    {key}: {value},")
        lines.append("  },")

    lines.append("} as const;")
    lines.append("")
    lines.append("// Type helper for beat timing")
    lines.append("export type BeatTiming = typeof TIMING;")
    lines.append("")

    return "\n".join(lines)


def generate_timing_file(
    storyboard: ShortsStoryboard,
    output_path: Path,
    fps: int = 30,
) -> dict[str, dict[str, int]]:
    """Generate timing.ts file from storyboard.

    Args:
        storyboard: The storyboard with beats containing phase markers.
        output_path: Path to write the timing.ts file.
        fps: Frames per second.

    Returns:
        The generated timing data.
    """
    timing_data = generate_timing_data(storyboard, fps)

    if timing_data:
        typescript_code = generate_timing_typescript(timing_data)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(typescript_code)
        print(f"  Generated timing file: {output_path}")

    return timing_data


def load_storyboard_and_generate_timing(
    storyboard_path: Path,
    scenes_dir: Path,
    fps: int = 30,
) -> dict[str, dict[str, int]]:
    """Load storyboard from file and generate timing.ts.

    Args:
        storyboard_path: Path to the storyboard JSON file.
        scenes_dir: Directory containing scene files where timing.ts will be written.
        fps: Frames per second.

    Returns:
        The generated timing data.
    """
    from .generator import ShortGenerator

    storyboard = ShortGenerator.load_shorts_storyboard(storyboard_path)
    timing_path = scenes_dir / "timing.ts"
    return generate_timing_file(storyboard, timing_path, fps)


def add_phase_markers_to_beat(
    beat: ShortsBeat,
    markers: list[dict[str, str]],
) -> ShortsBeat:
    """Add phase markers to a beat.

    Args:
        beat: The beat to update.
        markers: List of marker dicts with 'id', 'end_word', and optionally 'description'.

    Returns:
        The updated beat.
    """
    beat.phase_markers = [
        PhaseMarker(
            id=m["id"],
            end_word=m["end_word"],
            description=m.get("description", ""),
        )
        for m in markers
    ]
    return beat


def update_storyboard_with_markers(
    storyboard: ShortsStoryboard,
    beat_markers: dict[str, list[dict[str, str]]],
) -> ShortsStoryboard:
    """Update storyboard beats with phase markers.

    Args:
        storyboard: The storyboard to update.
        beat_markers: Dict mapping beat IDs to lists of marker dicts.

    Returns:
        The updated storyboard.
    """
    for beat in storyboard.beats:
        if beat.id in beat_markers:
            add_phase_markers_to_beat(beat, beat_markers[beat.id])

    return storyboard

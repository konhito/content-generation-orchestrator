"""Sound moment aggregator - combines and filters moments from multiple sources.

This module handles:
- Merging moments from code analysis, narration sync, and LLM analysis
- Deduplication of nearby moments
- Enforcing density constraints
- Prioritizing higher-confidence sources
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from .models import SoundMoment


@dataclass
class AggregationConfig:
    """Configuration for moment aggregation."""

    # Density constraints
    max_per_second: float = 3.0  # Maximum sounds per second
    min_gap_frames: int = 10    # Minimum frames between sounds

    # Merge settings
    merge_window_frames: int = 10  # Merge moments within this window

    # Edge avoidance (don't place sounds too close to scene edges)
    edge_buffer_frames: int = 15  # ~0.5 seconds at 30fps

    # Source priority (higher = more trusted)
    source_priority: dict[str, float] = None

    def __post_init__(self):
        if self.source_priority is None:
            self.source_priority = {
                "code": 0.9,      # Code analysis is very reliable
                "narration": 0.8, # Narration sync is good
                "llm": 0.7,      # LLM analysis is contextual but less precise
            }


def aggregate_moments(
    code_moments: list[SoundMoment],
    narration_moments: list[SoundMoment],
    llm_moments: list[SoundMoment],
    max_per_second: float = 3.0,
    min_gap_frames: int = 10,
    merge_window_frames: int = 10,
    edge_buffer_frames: int = 15,
    fps: int = 30,
    scene_duration_frames: Optional[int] = None,
) -> list[SoundMoment]:
    """Aggregate moments from multiple sources with deduplication.

    Combines moments from code analysis, narration sync, and LLM analysis.
    Applies deduplication, density constraints, and edge avoidance.

    Args:
        code_moments: Moments from code analysis
        narration_moments: Moments from narration word sync
        llm_moments: Moments from LLM semantic analysis
        max_per_second: Maximum sound density
        min_gap_frames: Minimum frames between sounds
        merge_window_frames: Window for merging nearby moments
        edge_buffer_frames: Buffer from scene edges
        fps: Frames per second
        scene_duration_frames: Total scene duration (for edge avoidance)

    Returns:
        Filtered and deduplicated list of SoundMoment
    """
    # Combine all moments
    all_moments = code_moments + narration_moments + llm_moments

    if not all_moments:
        return []

    # Sort by frame
    all_moments.sort(key=lambda m: m.frame)

    # Step 1: Merge nearby moments
    merged = _merge_nearby_moments(all_moments, merge_window_frames)

    # Step 2: Apply edge buffer
    if scene_duration_frames:
        merged = _apply_edge_buffer(merged, edge_buffer_frames, scene_duration_frames)

    # Step 3: Enforce density constraints
    filtered = _enforce_density(merged, max_per_second, min_gap_frames, fps)

    return filtered


def _merge_nearby_moments(
    moments: list[SoundMoment],
    window_frames: int,
) -> list[SoundMoment]:
    """Merge moments that are very close together.

    When moments are within the merge window, keep the one with
    higher confidence and better source priority.

    Args:
        moments: Sorted list of moments
        window_frames: Merge window in frames

    Returns:
        Merged list of moments
    """
    if not moments:
        return []

    # Source priority for tiebreaking
    source_priority = {"code": 0.9, "narration": 0.8, "llm": 0.7}

    merged = []
    current_group: list[SoundMoment] = [moments[0]]

    for moment in moments[1:]:
        # Check if this moment is within the merge window of the group
        if moment.frame - current_group[0].frame <= window_frames:
            current_group.append(moment)
        else:
            # Process current group and start new one
            best = _select_best_moment(current_group, source_priority)
            merged.append(best)
            current_group = [moment]

    # Process final group
    if current_group:
        best = _select_best_moment(current_group, source_priority)
        merged.append(best)

    return merged


def _select_best_moment(
    moments: list[SoundMoment],
    source_priority: dict[str, float],
) -> SoundMoment:
    """Select the best moment from a group of nearby moments.

    Prioritizes by:
    1. Confidence score
    2. Source priority
    3. Intensity (for tiebreaking)

    Args:
        moments: Group of nearby moments
        source_priority: Dict mapping source names to priority scores

    Returns:
        The best moment from the group
    """
    if len(moments) == 1:
        return moments[0]

    def score(m: SoundMoment) -> tuple:
        return (
            m.confidence,
            source_priority.get(m.source, 0.5),
            m.intensity,
        )

    return max(moments, key=score)


def _apply_edge_buffer(
    moments: list[SoundMoment],
    buffer_frames: int,
    scene_duration: int,
) -> list[SoundMoment]:
    """Remove moments that are too close to scene edges.

    Args:
        moments: List of moments
        buffer_frames: Buffer distance in frames
        scene_duration: Total scene duration in frames

    Returns:
        Filtered list
    """
    return [
        m for m in moments
        if buffer_frames <= m.frame <= scene_duration - buffer_frames
    ]


def _enforce_density(
    moments: list[SoundMoment],
    max_per_second: float,
    min_gap_frames: int,
    fps: int,
) -> list[SoundMoment]:
    """Enforce density constraints on moments.

    Ensures:
    - No more than max_per_second sounds per second
    - At least min_gap_frames between consecutive sounds

    Prioritizes moments by confidence.

    Args:
        moments: List of moments
        max_per_second: Maximum sounds per second
        min_gap_frames: Minimum gap between sounds
        fps: Frames per second

    Returns:
        Filtered list respecting density constraints
    """
    if not moments:
        return []

    # Sort by confidence (descending) to prioritize high-confidence moments
    by_confidence = sorted(moments, key=lambda m: m.confidence, reverse=True)

    selected: list[SoundMoment] = []
    selected_frames: set[int] = set()

    # Window for density checking (1 second)
    window_frames = fps

    for moment in by_confidence:
        # Check minimum gap constraint
        if any(abs(moment.frame - f) < min_gap_frames for f in selected_frames):
            continue

        # Check density constraint
        window_start = moment.frame - window_frames // 2
        window_end = moment.frame + window_frames // 2
        count_in_window = sum(
            1 for f in selected_frames
            if window_start <= f <= window_end
        )

        if count_in_window >= max_per_second:
            continue

        # Add this moment
        selected.append(moment)
        selected_frames.add(moment.frame)

    # Sort back by frame for output
    return sorted(selected, key=lambda m: m.frame)


def deduplicate_cues_by_type(moments: list[SoundMoment]) -> list[SoundMoment]:
    """Remove consecutive moments of the same type that are too close.

    Useful for avoiding rapid repetition of the same sound type.

    Args:
        moments: List of moments (should be sorted by frame)

    Returns:
        Deduplicated list
    """
    if not moments:
        return []

    result = [moments[0]]

    for moment in moments[1:]:
        prev = result[-1]

        # If same type and within 20 frames, skip
        if moment.type == prev.type and moment.frame - prev.frame < 20:
            continue

        result.append(moment)

    return result


def group_moments_by_second(
    moments: list[SoundMoment],
    fps: int = 30,
) -> dict[int, list[SoundMoment]]:
    """Group moments by their second in the scene.

    Useful for analyzing density distribution.

    Args:
        moments: List of moments
        fps: Frames per second

    Returns:
        Dict mapping second number to moments in that second
    """
    groups: dict[int, list[SoundMoment]] = defaultdict(list)

    for moment in moments:
        second = moment.frame // fps
        groups[second].append(moment)

    return dict(groups)


def get_density_report(
    moments: list[SoundMoment],
    fps: int = 30,
) -> dict:
    """Generate a density report for a list of moments.

    Args:
        moments: List of moments
        fps: Frames per second

    Returns:
        Dict with density statistics
    """
    if not moments:
        return {
            "total_moments": 0,
            "avg_per_second": 0.0,
            "max_per_second": 0,
            "min_gap_frames": None,
            "type_distribution": {},
        }

    by_second = group_moments_by_second(moments, fps)

    # Calculate gaps
    sorted_frames = sorted(m.frame for m in moments)
    gaps = [
        sorted_frames[i+1] - sorted_frames[i]
        for i in range(len(sorted_frames) - 1)
    ]

    # Type distribution
    type_counts: dict[str, int] = defaultdict(int)
    for m in moments:
        type_counts[m.type] += 1

    return {
        "total_moments": len(moments),
        "avg_per_second": len(moments) / max(1, max(by_second.keys()) + 1),
        "max_per_second": max(len(v) for v in by_second.values()),
        "min_gap_frames": min(gaps) if gaps else None,
        "type_distribution": dict(type_counts),
    }

"""
Visual refinement module.

Handles Phase 3 of the refinement process: inspecting and refining scene visuals.
"""

from .beat_parser import BeatParser, parse_narration_to_beats
from .screenshot import ScreenshotCapture
from .inspector import VisualInspector, ClaudeCodeVisualInspector

__all__ = [
    "BeatParser",
    "parse_narration_to_beats",
    "ScreenshotCapture",
    "VisualInspector",
    "ClaudeCodeVisualInspector",
]

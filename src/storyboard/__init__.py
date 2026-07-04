"""Storyboard module for video explainer system.

This module handles loading, validating, generating, and rendering storyboards.
"""

from .generator import StoryboardGenerator
from .loader import (
    load_storyboard,
    validate_storyboard,
    StoryboardError,
)
from .models import (
    Storyboard,
    Beat,
    Element,
    Animation,
    Position,
    Transition,
    SyncPoint,
    AudioConfig,
    StyleConfig,
)
from .renderer import StoryboardRenderer

__all__ = [
    # Generator
    "StoryboardGenerator",
    # Loader
    "load_storyboard",
    "validate_storyboard",
    "StoryboardError",
    # Models
    "Storyboard",
    "Beat",
    "Element",
    "Animation",
    "Position",
    "Transition",
    "SyncPoint",
    "AudioConfig",
    "StyleConfig",
    # Renderer
    "StoryboardRenderer",
]

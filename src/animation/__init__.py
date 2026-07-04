"""Animation rendering module with pluggable backends."""

from .renderer import (
    AnimationRenderer,
    MockRenderer,
    RemotionRenderer,
    RenderResult,
    get_renderer,
)

__all__ = [
    "AnimationRenderer",
    "MockRenderer",
    "RemotionRenderer",
    "RenderResult",
    "get_renderer",
]

"""
Visual Cue Refiner - Analyzes and improves visual_cue specifications in script.json.

This module ensures visual_cues follow established patterns:
- Dark glass panels with 3D depth (multi-layer shadows, bezels, inner shadows)
- Specific element descriptions for each scene
- Consistency with the actual scene implementation
"""

from .refiner import VisualCueRefiner, VisualCueRefinerResult

__all__ = ["VisualCueRefiner", "VisualCueRefinerResult"]

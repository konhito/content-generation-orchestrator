"""Feedback processing module for video explainer refinement.

This module provides a pipeline for processing user feedback:
1. Parse feedback to determine intent and targets
2. Generate patches based on intent
3. Apply patches with verification

Example usage:
    from src.refine.feedback import FeedbackProcessor
    from src.project import Project

    project = Project.load("my-project")
    processor = FeedbackProcessor(project)
    result = processor.process("Make the intro scene more energetic")
"""

from .models import (
    FeedbackIntent,
    FeedbackItem,
    FeedbackScope,
    FeedbackStatus,
    FeedbackTarget,
    FeedbackHistory,
    generate_feedback_id,
)
from .parser import FeedbackParser
from .generator import PatchGenerator
from .applicator import PatchApplicator
from .store import FeedbackStore
from .processor import FeedbackProcessor

__all__ = [
    # Models
    "FeedbackIntent",
    "FeedbackItem",
    "FeedbackScope",
    "FeedbackStatus",
    "FeedbackTarget",
    "FeedbackHistory",
    "generate_feedback_id",
    # Components
    "FeedbackParser",
    "PatchGenerator",
    "PatchApplicator",
    "FeedbackStore",
    # Main processor
    "FeedbackProcessor",
]

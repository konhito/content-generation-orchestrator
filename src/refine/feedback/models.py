"""Data models for the feedback system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class FeedbackStatus(str, Enum):
    """Status of a feedback item."""

    PENDING = "pending"  # Created, not yet processed
    ANALYZING = "analyzing"  # Being analyzed to determine intent
    GENERATING = "generating"  # Generating patches
    APPLYING = "applying"  # Applying patches
    VERIFYING = "verifying"  # Verifying changes
    APPLIED = "applied"  # Successfully applied
    FAILED = "failed"  # Processing failed


class FeedbackIntent(str, Enum):
    """What kind of change the feedback requests."""

    SCRIPT_CONTENT = "script_content"  # Change narration text
    SCRIPT_STRUCTURE = "script_structure"  # Add/remove/reorder scenes
    VISUAL_CUE = "visual_cue"  # Change visual specification in script.json
    VISUAL_IMPLEMENTATION = "visual_impl"  # Change scene component code (.tsx)
    TIMING = "timing"  # Adjust scene durations
    STYLE = "style"  # Change visual styling patterns
    MIXED = "mixed"  # Multiple types of changes


class FeedbackScope(str, Enum):
    """Scope of the feedback impact."""

    SCENE = "scene"  # Affects a single scene
    MULTI_SCENE = "multi_scene"  # Affects multiple specific scenes
    PROJECT = "project"  # Affects the entire project


@dataclass
class FeedbackTarget:
    """Where the feedback should be applied."""

    scene_ids: list[str] = field(default_factory=list)  # Which scenes (slug IDs)
    scope: FeedbackScope = FeedbackScope.SCENE

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_ids": self.scene_ids,
            "scope": self.scope.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackTarget":
        return cls(
            scene_ids=data.get("scene_ids", []),
            scope=FeedbackScope(data.get("scope", "scene")),
        )


@dataclass
class FeedbackItem:
    """A single feedback item with its processing state."""

    id: str  # Unique ID (fb_XXXX_timestamp)
    timestamp: datetime
    feedback_text: str  # Original user input
    status: FeedbackStatus = FeedbackStatus.PENDING

    # Analysis results (populated after parsing)
    intent: FeedbackIntent | None = None
    sub_intents: list[FeedbackIntent] = field(default_factory=list)  # For MIXED
    target: FeedbackTarget | None = None
    interpretation: str = ""  # What the LLM understood

    # Generated patches (populated after generation)
    patches: list[dict[str, Any]] = field(default_factory=list)

    # Application results
    files_modified: list[str] = field(default_factory=list)
    verification_passed: bool | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "feedback_text": self.feedback_text,
            "status": self.status.value,
            "intent": self.intent.value if self.intent else None,
            "sub_intents": [i.value for i in self.sub_intents],
            "target": self.target.to_dict() if self.target else None,
            "interpretation": self.interpretation,
            "patches": self.patches,
            "files_modified": self.files_modified,
            "verification_passed": self.verification_passed,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackItem":
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            feedback_text=data["feedback_text"],
            status=FeedbackStatus(data.get("status", "pending")),
            intent=FeedbackIntent(data["intent"]) if data.get("intent") else None,
            sub_intents=[FeedbackIntent(i) for i in data.get("sub_intents", [])],
            target=FeedbackTarget.from_dict(data["target"]) if data.get("target") else None,
            interpretation=data.get("interpretation", ""),
            patches=data.get("patches", []),
            files_modified=data.get("files_modified", []),
            verification_passed=data.get("verification_passed"),
            error_message=data.get("error_message"),
        )


@dataclass
class FeedbackHistory:
    """Collection of feedback items for a project."""

    project_id: str
    items: list[FeedbackItem] = field(default_factory=list)

    def add(self, item: FeedbackItem) -> None:
        """Add a feedback item to the history."""
        self.items.append(item)

    def get_by_id(self, item_id: str) -> FeedbackItem | None:
        """Get a feedback item by ID."""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def get_by_status(self, status: FeedbackStatus) -> list[FeedbackItem]:
        """Get all items with a specific status."""
        return [item for item in self.items if item.status == status]

    def get_pending(self) -> list[FeedbackItem]:
        """Get all pending items."""
        return self.get_by_status(FeedbackStatus.PENDING)

    def get_applied(self) -> list[FeedbackItem]:
        """Get all applied items."""
        return self.get_by_status(FeedbackStatus.APPLIED)

    def get_failed(self) -> list[FeedbackItem]:
        """Get all failed items."""
        return self.get_by_status(FeedbackStatus.FAILED)

    def update_item(self, item: FeedbackItem) -> None:
        """Update an existing item in the history."""
        for i, existing in enumerate(self.items):
            if existing.id == item.id:
                self.items[i] = item
                return
        # If not found, add it
        self.items.append(item)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackHistory":
        return cls(
            project_id=data["project_id"],
            items=[FeedbackItem.from_dict(item) for item in data.get("items", [])],
        )


def generate_feedback_id(count: int = 0) -> str:
    """Generate a unique feedback ID.

    Args:
        count: Optional count for sequential numbering.

    Returns:
        ID in format 'fb_XXXX_timestamp'.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"fb_{count:04d}_{timestamp}"

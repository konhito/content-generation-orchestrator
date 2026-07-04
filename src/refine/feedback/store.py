"""Feedback history storage."""

import json
from datetime import datetime
from pathlib import Path

from ...project import Project
from .models import (
    FeedbackHistory,
    FeedbackItem,
    FeedbackStatus,
    generate_feedback_id,
)


class FeedbackStore:
    """Stores feedback history for a project.

    Location: projects/{project-id}/refinement/feedback.json
    """

    def __init__(self, project: Project):
        """Initialize the feedback store.

        Args:
            project: The project to store feedback for.
        """
        self.project = project
        self.storage_path = project.root_dir / "refinement" / "feedback.json"

    def _ensure_directory(self) -> None:
        """Ensure the refinement directory exists."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> FeedbackHistory:
        """Load feedback history from disk.

        Returns:
            FeedbackHistory object (empty if file doesn't exist).
        """
        if not self.storage_path.exists():
            return FeedbackHistory(project_id=self.project.id)

        try:
            with open(self.storage_path) as f:
                data = json.load(f)
            return FeedbackHistory.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            # If file is corrupted, return empty history
            return FeedbackHistory(project_id=self.project.id)

    def save(self, history: FeedbackHistory) -> None:
        """Save feedback history to disk.

        Args:
            history: The feedback history to save.
        """
        self._ensure_directory()
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(history.to_dict(), f, indent=2, ensure_ascii=False)

    def add_feedback(self, feedback_text: str) -> FeedbackItem:
        """Create and save a new feedback item.

        Args:
            feedback_text: The user's feedback text.

        Returns:
            The created FeedbackItem.
        """
        history = self.load()

        # Generate ID with count
        count = len(history.items) + 1
        item = FeedbackItem(
            id=generate_feedback_id(count),
            timestamp=datetime.now(),
            feedback_text=feedback_text,
            status=FeedbackStatus.PENDING,
        )

        history.add(item)
        self.save(history)
        return item

    def update_item(self, item: FeedbackItem) -> None:
        """Update an existing feedback item.

        Args:
            item: The updated feedback item.
        """
        history = self.load()
        history.update_item(item)
        self.save(history)

    def get_item(self, item_id: str) -> FeedbackItem | None:
        """Get a feedback item by ID.

        Args:
            item_id: The feedback item ID.

        Returns:
            The FeedbackItem or None if not found.
        """
        history = self.load()
        return history.get_by_id(item_id)

    def list_all(self) -> list[FeedbackItem]:
        """List all feedback items.

        Returns:
            List of all feedback items.
        """
        history = self.load()
        return history.items

    def list_by_status(self, status: FeedbackStatus) -> list[FeedbackItem]:
        """List feedback items by status.

        Args:
            status: The status to filter by.

        Returns:
            List of matching feedback items.
        """
        history = self.load()
        return history.get_by_status(status)

    def exists(self) -> bool:
        """Check if feedback history file exists.

        Returns:
            True if the file exists.
        """
        return self.storage_path.exists()

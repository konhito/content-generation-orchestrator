"""Feedback processor - orchestrates the feedback processing pipeline."""

from typing import Any

from ...project import Project
from ...understanding.llm_provider import LLMProvider
from .models import FeedbackItem, FeedbackStatus
from .parser import FeedbackParser
from .generator import PatchGenerator
from .applicator import PatchApplicator
from .store import FeedbackStore


class FeedbackProcessor:
    """Orchestrates the feedback processing pipeline.

    Pipeline stages:
    1. Store feedback in history
    2. Parse feedback to determine intent and targets
    3. Generate patches based on intent
    4. Apply patches with verification
    5. For visual changes (VISUAL_CUE, VISUAL_IMPLEMENTATION, STYLE):
       - Update visual_cue in script.json
       - Trigger ClaudeCodeVisualInspector for scene refinement
       - Uses /remotion skill, visual verification, and 13 principles

    Example:
        project = Project.load("my-project")
        processor = FeedbackProcessor(project)
        result = processor.process("Make the intro more energetic")
    """

    def __init__(
        self,
        project: Project,
        llm_provider: LLMProvider | None = None,
        verbose: bool = True,
        verify: bool = True,
        live_output: bool = False,
    ):
        """Initialize the feedback processor.

        Args:
            project: The project to process feedback for.
            llm_provider: Optional LLM provider to share across components.
            verbose: Whether to print progress.
            verify: Whether to verify changes after applying.
            live_output: Whether to stream Claude Code output in real-time.
        """
        self.project = project
        self.verbose = verbose
        self.verify = verify
        self.live_output = live_output

        # Initialize components
        self.store = FeedbackStore(project)
        self.parser = FeedbackParser(project, llm_provider, verbose)
        self.generator = PatchGenerator(project, llm_provider, verbose)
        self.applicator = PatchApplicator(project, llm_provider, verbose, live_output)

    def _log(self, message: str) -> None:
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def process(
        self,
        feedback_text: str,
        dry_run: bool = False,
    ) -> FeedbackItem:
        """Process feedback through the full pipeline.

        Args:
            feedback_text: The user's feedback text.
            dry_run: If True, generate patches but don't apply them.

        Returns:
            FeedbackItem with processing results.
        """
        self._log(f"\n{'='*60}")
        self._log(f"Processing feedback: {feedback_text[:80]}...")
        self._log(f"{'='*60}")

        # Stage 1: Store feedback
        self._log("\n[1/4] Storing feedback...")
        item = self.store.add_feedback(feedback_text)
        self._log(f"  Created: {item.id}")

        # Stage 2: Parse feedback
        self._log("\n[2/4] Parsing feedback...")
        item = self.parser.parse(item)
        self.store.update_item(item)

        if item.status == FeedbackStatus.FAILED:
            self._log(f"  Failed: {item.error_message}")
            return item

        # Stage 3: Generate patches
        self._log("\n[3/4] Generating patches...")
        item = self.generator.generate(item)
        self.store.update_item(item)

        if item.status == FeedbackStatus.FAILED:
            self._log(f"  Failed: {item.error_message}")
            return item

        if not item.patches:
            self._log("  No patches generated")
            item.status = FeedbackStatus.FAILED
            item.error_message = "No patches could be generated from this feedback"
            self.store.update_item(item)
            return item

        # Stage 4: Apply patches (unless dry run)
        if dry_run:
            self._log("\n[4/4] Dry run - skipping application")
            self._log(f"  Would apply {len(item.patches)} patches:")
            for i, patch in enumerate(item.patches, 1):
                patch_type = patch.get("patch_type", "unknown") if isinstance(patch, dict) else "unknown"
                self._log(f"    {i}. {patch_type}")
            return item

        self._log("\n[4/4] Applying patches...")
        item = self.applicator.apply(item, verify=self.verify)
        self.store.update_item(item)

        # Summary
        self._log(f"\n{'='*60}")
        self._log(f"Processing complete: {item.status.value}")
        if item.files_modified:
            self._log(f"Modified files: {', '.join(item.files_modified)}")
        if item.verification_passed is not None:
            self._log(f"Verification: {'passed' if item.verification_passed else 'failed'}")
        self._log(f"{'='*60}\n")

        return item

    def process_item(
        self,
        item_id: str,
        dry_run: bool = False,
    ) -> FeedbackItem | None:
        """Re-process an existing feedback item.

        Useful for retrying failed items or re-applying after rollback.

        Args:
            item_id: The feedback item ID to process.
            dry_run: If True, generate patches but don't apply them.

        Returns:
            Updated FeedbackItem or None if not found.
        """
        item = self.store.get_item(item_id)
        if not item:
            self._log(f"Feedback item not found: {item_id}")
            return None

        # Reset status and continue from appropriate stage
        if item.intent is None:
            item.status = FeedbackStatus.PENDING
            item = self.parser.parse(item)
            self.store.update_item(item)

        if item.status == FeedbackStatus.FAILED:
            return item

        if not item.patches:
            item = self.generator.generate(item)
            self.store.update_item(item)

        if item.status == FeedbackStatus.FAILED:
            return item

        if not dry_run:
            item = self.applicator.apply(item, verify=self.verify)
            self.store.update_item(item)

        return item

    def list_feedback(self, status: FeedbackStatus | None = None) -> list[FeedbackItem]:
        """List feedback items, optionally filtered by status.

        Args:
            status: Optional status to filter by.

        Returns:
            List of feedback items.
        """
        if status:
            return self.store.list_by_status(status)
        return self.store.list_all()

    def get_history(self) -> dict[str, Any]:
        """Get feedback history summary.

        Returns:
            Dictionary with history statistics.
        """
        items = self.store.list_all()

        status_counts = {}
        for item in items:
            status = item.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        intent_counts = {}
        for item in items:
            if item.intent:
                intent = item.intent.value
                intent_counts[intent] = intent_counts.get(intent, 0) + 1

        return {
            "total_items": len(items),
            "status_counts": status_counts,
            "intent_counts": intent_counts,
            "recent_items": [
                {
                    "id": item.id,
                    "status": item.status.value,
                    "feedback": item.feedback_text[:50] + "..." if len(item.feedback_text) > 50 else item.feedback_text,
                }
                for item in items[-5:]
            ],
        }

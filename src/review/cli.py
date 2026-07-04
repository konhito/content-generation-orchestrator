"""CLI interface for reviewing generated content."""

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..models import Script, ScriptScene, Storyboard


class ReviewDecision(str, Enum):
    """Possible review decisions."""

    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


@dataclass
class ReviewResult:
    """Result of a review session."""

    decision: ReviewDecision
    content: Any  # The reviewed/edited content
    feedback: str = ""
    changes_made: list[str] = field(default_factory=list)


class ReviewCLI:
    """CLI interface for reviewing generated content."""

    def __init__(self):
        self.console = Console()

    def review_script(self, script: Script) -> ReviewResult:
        """Review a generated script.

        Args:
            script: The script to review

        Returns:
            ReviewResult with the decision and potentially modified script
        """
        self.console.clear()
        self._display_script_header(script)

        # Display scenes one by one or all at once
        view_mode = Prompt.ask(
            "View mode",
            choices=["all", "scene-by-scene"],
            default="all"
        )

        if view_mode == "all":
            self._display_full_script(script)
        else:
            script = self._review_scene_by_scene(script)

        # Get overall decision
        self.console.print()
        decision = self._get_decision()

        if decision == ReviewDecision.EDIT:
            script = self._edit_script_in_editor(script)
            return ReviewResult(
                decision=ReviewDecision.APPROVE,
                content=script,
                feedback="Edited in external editor",
                changes_made=["Manual edits applied"],
            )
        elif decision == ReviewDecision.REJECT:
            feedback = Prompt.ask("Rejection reason")
            return ReviewResult(
                decision=ReviewDecision.REJECT,
                content=script,
                feedback=feedback,
            )
        else:
            return ReviewResult(
                decision=ReviewDecision.APPROVE,
                content=script,
                feedback="Approved as-is",
            )

    def _display_script_header(self, script: Script) -> None:
        """Display script header information."""
        self.console.print()
        self.console.print(Panel(
            f"[bold blue]{script.title}[/bold blue]\n\n"
            f"Duration: {script.total_duration_seconds:.0f}s "
            f"({script.total_duration_seconds / 60:.1f} min)\n"
            f"Scenes: {len(script.scenes)}\n"
            f"Source: {script.source_document}",
            title="Script Review",
            border_style="blue",
        ))

    def _display_full_script(self, script: Script) -> None:
        """Display the entire script."""
        from ..script.generator import ScriptGenerator

        generator = ScriptGenerator()
        formatted = generator.format_script_for_review(script)
        self.console.print(Markdown(formatted))

    def _display_scene(self, scene: ScriptScene, timestamp: float) -> None:
        """Display a single scene."""
        minutes = int(timestamp // 60)
        seconds = int(timestamp % 60)

        # Scene header
        self.console.print()
        self.console.print(Panel(
            f"[bold]{scene.title}[/bold]\n"
            f"Type: {scene.scene_type} | Duration: {scene.duration_seconds:.0f}s | "
            f"Timestamp: {minutes:02d}:{seconds:02d}",
            title=f"Scene {scene.scene_id}",
            border_style="green" if scene.scene_type == "hook" else "cyan",
        ))

        # Voiceover
        self.console.print()
        self.console.print("[bold]Voiceover:[/bold]")
        self.console.print(Panel(scene.voiceover, border_style="yellow"))

        # Visual cue
        self.console.print()
        self.console.print("[bold]Visual:[/bold]")
        visual_table = Table(show_header=False, box=None)
        visual_table.add_column("Key", style="cyan")
        visual_table.add_column("Value")
        visual_table.add_row("Type", scene.visual_cue.visual_type)
        visual_table.add_row("Description", scene.visual_cue.description)
        if scene.visual_cue.elements:
            visual_table.add_row("Elements", ", ".join(scene.visual_cue.elements))
        self.console.print(visual_table)

        if scene.notes:
            self.console.print()
            self.console.print(f"[dim]Notes: {scene.notes}[/dim]")

    def _review_scene_by_scene(self, script: Script) -> Script:
        """Review script scene by scene, allowing edits."""
        modified_scenes = list(script.scenes)
        timestamp = 0.0

        for i, scene in enumerate(script.scenes):
            self._display_scene(scene, timestamp)
            timestamp += scene.duration_seconds

            self.console.print()
            action = Prompt.ask(
                f"Scene {scene.scene_id}",
                choices=["ok", "edit", "skip"],
                default="ok"
            )

            if action == "edit":
                modified_scene = self._edit_scene(scene)
                modified_scenes[i] = modified_scene

        # Reconstruct script with modified scenes
        return Script(
            title=script.title,
            total_duration_seconds=sum(s.duration_seconds for s in modified_scenes),
            scenes=modified_scenes,
            source_document=script.source_document,
        )

    def _edit_scene(self, scene: ScriptScene) -> ScriptScene:
        """Edit a single scene."""
        self.console.print()
        self.console.print("[bold]Editing scene...[/bold]")

        # Simple field-by-field editing
        new_voiceover = Prompt.ask(
            "Voiceover (Enter to keep)",
            default=scene.voiceover,
        )

        new_description = Prompt.ask(
            "Visual description (Enter to keep)",
            default=scene.visual_cue.description,
        )

        new_duration = Prompt.ask(
            "Duration in seconds (Enter to keep)",
            default=str(scene.duration_seconds),
        )

        from ..models import VisualCue

        new_visual_cue = VisualCue(
            description=new_description,
            visual_type=scene.visual_cue.visual_type,
            elements=scene.visual_cue.elements,
            duration_seconds=float(new_duration),
        )

        return ScriptScene(
            scene_id=scene.scene_id,
            scene_type=scene.scene_type,
            title=scene.title,
            voiceover=new_voiceover,
            visual_cue=new_visual_cue,
            duration_seconds=float(new_duration),
            notes=scene.notes,
        )

    def _edit_script_in_editor(self, script: Script) -> Script:
        """Open script in external editor for editing."""
        import os

        # Create temp file with script JSON
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(script.model_dump(), f, indent=2)
            temp_path = f.name

        # Get editor from environment
        editor = os.environ.get("EDITOR", "vim")

        self.console.print(f"[dim]Opening in {editor}...[/dim]")

        try:
            subprocess.run([editor, temp_path], check=True)

            # Read back the edited content
            with open(temp_path) as f:
                edited_data = json.load(f)

            return Script(**edited_data)
        except subprocess.CalledProcessError:
            self.console.print("[red]Editor closed with error, keeping original[/red]")
            return script
        except json.JSONDecodeError as e:
            self.console.print(f"[red]Invalid JSON after edit: {e}[/red]")
            return script
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def _get_decision(self) -> ReviewDecision:
        """Get the user's review decision."""
        self.console.print()
        choice = Prompt.ask(
            "[bold]Decision[/bold]",
            choices=["approve", "edit", "reject"],
            default="approve",
        )
        return ReviewDecision(choice)

    def confirm_proceed(self, message: str) -> bool:
        """Ask for confirmation to proceed.

        Args:
            message: The confirmation message

        Returns:
            True if user confirms, False otherwise
        """
        return Confirm.ask(message, default=True)

    def display_summary(self, title: str, items: dict[str, Any]) -> None:
        """Display a summary table.

        Args:
            title: Title for the summary
            items: Dictionary of key-value pairs to display
        """
        table = Table(title=title, show_header=False)
        table.add_column("Item", style="cyan")
        table.add_column("Value")

        for key, value in items.items():
            table.add_row(key, str(value))

        self.console.print(table)

    def display_error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def display_success(self, message: str) -> None:
        """Display a success message."""
        self.console.print(f"[bold green]Success:[/bold green] {message}")

    def display_info(self, message: str) -> None:
        """Display an info message."""
        self.console.print(f"[blue]Info:[/blue] {message}")

"""Storyboard updater for SFX cues.

This module handles reading, modifying, and writing storyboard.json
files with generated SFX cues.
"""

import json
from pathlib import Path
from typing import Literal, Optional

from .models import SFXCue


class StoryboardUpdater:
    """Updates storyboard.json with generated SFX cues."""

    def __init__(self, storyboard_path: Path):
        """Initialize with path to storyboard.json.

        Args:
            storyboard_path: Path to the storyboard.json file
        """
        self.storyboard_path = Path(storyboard_path)
        self._storyboard: Optional[dict] = None

    def load(self) -> dict:
        """Load the storyboard from disk.

        Returns:
            Storyboard data as dict

        Raises:
            FileNotFoundError: If storyboard doesn't exist
        """
        if not self.storyboard_path.exists():
            raise FileNotFoundError(f"Storyboard not found: {self.storyboard_path}")

        with open(self.storyboard_path) as f:
            self._storyboard = json.load(f)

        return self._storyboard

    def save(self, backup: bool = True) -> None:
        """Save the storyboard to disk.

        Args:
            backup: If True, create a backup before saving
        """
        if self._storyboard is None:
            raise ValueError("No storyboard loaded")

        if backup and self.storyboard_path.exists():
            backup_path = self.storyboard_path.with_suffix(".json.bak")
            backup_path.write_text(self.storyboard_path.read_text())

        with open(self.storyboard_path, "w") as f:
            json.dump(self._storyboard, f, indent=2)

    @property
    def storyboard(self) -> dict:
        """Get the loaded storyboard data."""
        if self._storyboard is None:
            self.load()
        return self._storyboard

    def get_scenes(self) -> list[dict]:
        """Get all scenes from the storyboard."""
        return self.storyboard.get("scenes", [])

    def get_scene_by_id(self, scene_id: str) -> Optional[dict]:
        """Get a scene by its ID.

        Args:
            scene_id: Scene identifier

        Returns:
            Scene dict or None if not found
        """
        for scene in self.get_scenes():
            if scene.get("id") == scene_id:
                return scene
        return None

    def get_scene_by_type(self, scene_type: str) -> Optional[dict]:
        """Get a scene by its type path.

        Args:
            scene_type: Scene type (e.g., "llm-inference/hook")

        Returns:
            Scene dict or None if not found
        """
        for scene in self.get_scenes():
            if scene.get("type") == scene_type:
                return scene
        return None

    def update_scene_cues(
        self,
        scene_id: str,
        cues: list[SFXCue],
        mode: Literal["replace", "merge"] = "replace",
    ) -> bool:
        """Update SFX cues for a scene.

        Args:
            scene_id: Scene identifier
            cues: New SFX cues
            mode: "replace" to overwrite, "merge" to combine

        Returns:
            True if scene was found and updated
        """
        scene = self.get_scene_by_id(scene_id)
        if scene is None:
            return False

        cue_dicts = [cue.to_dict() for cue in cues]

        if mode == "replace":
            scene["sfx_cues"] = cue_dicts
        else:  # merge
            existing = scene.get("sfx_cues", [])
            # Merge by frame - new cues override existing at same frame
            existing_by_frame = {c["frame"]: c for c in existing}
            for cue in cue_dicts:
                existing_by_frame[cue["frame"]] = cue
            # Sort by frame
            merged = sorted(existing_by_frame.values(), key=lambda c: c["frame"])
            scene["sfx_cues"] = merged

        return True

    def update_all_scenes(
        self,
        scene_cues: dict[str, list[SFXCue]],
        mode: Literal["replace", "merge"] = "replace",
    ) -> dict[str, bool]:
        """Update SFX cues for multiple scenes.

        Args:
            scene_cues: Dict mapping scene IDs to cue lists
            mode: "replace" to overwrite, "merge" to combine

        Returns:
            Dict mapping scene IDs to success status
        """
        results = {}
        for scene_id, cues in scene_cues.items():
            results[scene_id] = self.update_scene_cues(scene_id, cues, mode)
        return results

    def clear_scene_cues(self, scene_id: str) -> bool:
        """Remove all SFX cues from a scene.

        Args:
            scene_id: Scene identifier

        Returns:
            True if scene was found and cleared
        """
        scene = self.get_scene_by_id(scene_id)
        if scene is None:
            return False

        scene["sfx_cues"] = []
        return True

    def clear_all_cues(self) -> None:
        """Remove all SFX cues from all scenes."""
        for scene in self.get_scenes():
            scene["sfx_cues"] = []

    def get_scene_cues(self, scene_id: str) -> list[SFXCue]:
        """Get existing SFX cues for a scene.

        Args:
            scene_id: Scene identifier

        Returns:
            List of SFXCue objects
        """
        scene = self.get_scene_by_id(scene_id)
        if scene is None:
            return []

        cue_dicts = scene.get("sfx_cues", [])
        return [SFXCue.from_dict(c) for c in cue_dicts]

    def get_all_cues(self) -> dict[str, list[SFXCue]]:
        """Get all SFX cues organized by scene ID.

        Returns:
            Dict mapping scene IDs to cue lists
        """
        result = {}
        for scene in self.get_scenes():
            scene_id = scene.get("id", "unknown")
            cue_dicts = scene.get("sfx_cues", [])
            result[scene_id] = [SFXCue.from_dict(c) for c in cue_dicts]
        return result

    def get_scene_duration_frames(self, scene_id: str, fps: int = 30) -> int:
        """Get scene duration in frames.

        Args:
            scene_id: Scene identifier
            fps: Frames per second

        Returns:
            Duration in frames
        """
        scene = self.get_scene_by_id(scene_id)
        if scene is None:
            return 0

        audio_duration = scene.get("audio_duration_seconds", 0)
        visual_padding = scene.get("visual_padding_seconds", 0)
        buffer = self.storyboard.get("audio", {}).get(
            "buffer_between_scenes_seconds", 1.0
        )

        total_seconds = audio_duration + visual_padding + buffer
        return int(total_seconds * fps)

    def get_project_info(self) -> dict:
        """Get project info from storyboard.

        Returns:
            Dict with project, title, fps, etc.
        """
        return {
            "project": self.storyboard.get("project", "unknown"),
            "title": self.storyboard.get("title", ""),
            "fps": self.storyboard.get("video", {}).get("fps", 30),
            "scene_count": len(self.get_scenes()),
            "total_duration": self.storyboard.get("total_duration_seconds", 0),
        }


def update_storyboard(
    storyboard_path: Path,
    scene_cues: dict[str, list[SFXCue]],
    mode: Literal["replace", "merge"] = "replace",
    backup: bool = True,
) -> dict[str, bool]:
    """Convenience function to update a storyboard with SFX cues.

    Args:
        storyboard_path: Path to storyboard.json
        scene_cues: Dict mapping scene IDs to cue lists
        mode: "replace" to overwrite, "merge" to combine
        backup: Whether to create a backup before saving

    Returns:
        Dict mapping scene IDs to success status
    """
    updater = StoryboardUpdater(storyboard_path)
    updater.load()
    results = updater.update_all_scenes(scene_cues, mode)
    updater.save(backup=backup)
    return results


def load_storyboard(storyboard_path: Path) -> StoryboardUpdater:
    """Load a storyboard for reading/modification.

    Args:
        storyboard_path: Path to storyboard.json

    Returns:
        StoryboardUpdater instance with loaded data
    """
    updater = StoryboardUpdater(storyboard_path)
    updater.load()
    return updater

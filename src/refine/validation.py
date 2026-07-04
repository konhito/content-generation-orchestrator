"""
Project validation for the refinement process.

Ensures project files are in sync before refinement begins.
"""

import json
from pathlib import Path
from typing import Optional

from ..audio import get_audio_duration
from ..project import Project
from .models import ProjectSyncStatus, SyncIssue, SyncIssueType


class ProjectValidator:
    """Validates project file synchronization for refinement."""

    def __init__(self, project: Project):
        self.project = project

    def validate(self) -> ProjectSyncStatus:
        """
        Validate that all project files are in sync.

        Returns:
            ProjectSyncStatus with any issues found.
        """
        issues: list[SyncIssue] = []

        # Get counts from different sources
        storyboard_scenes = self._get_storyboard_scenes()
        narration_scenes = self._get_narration_scenes()
        voiceover_files = self._get_voiceover_files()
        scene_files = self._get_scene_files()

        storyboard_count = len(storyboard_scenes)
        narration_count = len(narration_scenes)
        voiceover_count = len(voiceover_files)
        scene_file_count = len(scene_files)

        # Check 1: Scene count consistency between storyboard and narrations
        if storyboard_count != narration_count:
            issues.append(
                SyncIssue(
                    issue_type=SyncIssueType.SCENE_COUNT_MISMATCH,
                    description=(
                        f"Storyboard has {storyboard_count} scenes but "
                        f"narrations.json has {narration_count} scenes"
                    ),
                    suggestion="Run 'storyboard' command to regenerate storyboard",
                )
            )

        # Check 2: Voiceover files exist for each scene in storyboard
        for scene in storyboard_scenes:
            audio_file = scene.get("audio_file", "")
            if audio_file:
                audio_path = self.project.voiceover_dir / audio_file
                if not audio_path.exists():
                    issues.append(
                        SyncIssue(
                            issue_type=SyncIssueType.MISSING_VOICEOVER,
                            description=f"Missing voiceover file: {audio_file}",
                            affected_scene=scene.get("id", "unknown"),
                            suggestion="Run 'voiceover' command to generate missing audio",
                        )
                    )

        # Check 3: Duration consistency between storyboard and actual audio
        for scene in storyboard_scenes:
            audio_file = scene.get("audio_file", "")
            if audio_file:
                audio_path = self.project.voiceover_dir / audio_file
                if audio_path.exists():
                    try:
                        actual_duration = get_audio_duration(audio_path)
                        storyboard_duration = scene.get("audio_duration_seconds", 0)

                        # Allow 0.5 second tolerance
                        if abs(actual_duration - storyboard_duration) > 0.5:
                            issues.append(
                                SyncIssue(
                                    issue_type=SyncIssueType.DURATION_MISMATCH,
                                    description=(
                                        f"Duration mismatch for {scene.get('id')}: "
                                        f"storyboard says {storyboard_duration:.1f}s, "
                                        f"actual audio is {actual_duration:.1f}s"
                                    ),
                                    affected_scene=scene.get("id", "unknown"),
                                    suggestion="Run 'storyboard' command to update durations",
                                )
                            )
                    except Exception as e:
                        issues.append(
                            SyncIssue(
                                issue_type=SyncIssueType.DURATION_MISMATCH,
                                description=f"Could not read audio duration for {audio_file}: {e}",
                                affected_scene=scene.get("id", "unknown"),
                            )
                        )

        # Check 4: Scene component files exist
        scenes_dir = self.project.root_dir / "scenes"
        if scenes_dir.exists():
            # Get scene types from storyboard
            for scene in storyboard_scenes:
                scene_type = scene.get("type", "")
                if scene_type:
                    # Extract scene name from type (e.g., "thinking-models/impossible_leap" -> "impossible_leap")
                    scene_name = scene_type.split("/")[-1] if "/" in scene_type else scene_type

                    # Check if any .tsx file might match this scene
                    # This is a loose check since scene names can vary
                    matching_files = list(scenes_dir.glob(f"*{scene_name}*.tsx")) + \
                                   list(scenes_dir.glob(f"*{scene_name.replace('_', '')}*.tsx"))

                    if not matching_files and scene_name not in ["", "unknown"]:
                        # Try to find by pattern matching
                        all_tsx_files = list(scenes_dir.glob("*.tsx"))
                        found = False
                        for tsx_file in all_tsx_files:
                            if scene_name.lower().replace("_", "") in tsx_file.stem.lower():
                                found = True
                                break

                        if not found:
                            issues.append(
                                SyncIssue(
                                    issue_type=SyncIssueType.MISSING_SCENE_FILE,
                                    description=f"No scene file found for type: {scene_type}",
                                    affected_scene=scene.get("id", "unknown"),
                                    suggestion="Run 'scenes' command to generate scene files",
                                )
                            )

        is_synced = len(issues) == 0

        return ProjectSyncStatus(
            is_synced=is_synced,
            issues=issues,
            storyboard_scene_count=storyboard_count,
            narration_scene_count=narration_count,
            voiceover_file_count=voiceover_count,
            scene_file_count=scene_file_count,
        )

    def _get_storyboard_scenes(self) -> list[dict]:
        """Get scenes from storyboard.json."""
        try:
            storyboard = self.project.load_storyboard()
            return storyboard.get("scenes", [])
        except FileNotFoundError:
            return []

    def _get_narration_scenes(self) -> list:
        """Get scenes from narrations.json."""
        try:
            return self.project.load_narrations()
        except FileNotFoundError:
            return []

    def _get_voiceover_files(self) -> list[Path]:
        """Get voiceover audio files."""
        return self.project.get_voiceover_files()

    def _get_scene_files(self) -> list[Path]:
        """Get scene component files (.tsx)."""
        scenes_dir = self.project.root_dir / "scenes"
        if not scenes_dir.exists():
            return []
        return list(scenes_dir.glob("*.tsx"))

    def get_scene_start_frame(self, scene_index: int) -> int:
        """
        Calculate the start frame for a scene based on storyboard.

        Args:
            scene_index: Zero-based index of the scene.

        Returns:
            Frame number where the scene starts.

        Raises:
            ValueError: If scene_index is out of range.
        """
        storyboard = self.project.load_storyboard()
        scenes = storyboard.get("scenes", [])
        fps = self.project.video.fps

        if scene_index < 0 or scene_index >= len(scenes):
            raise ValueError(f"Scene index {scene_index} out of range (0-{len(scenes)-1})")

        start_frame = 0
        for i, scene in enumerate(scenes):
            if i == scene_index:
                return start_frame
            duration = scene.get("audio_duration_seconds", 0)
            start_frame += int(duration * fps)

        return start_frame

    def get_scene_duration_frames(self, scene_index: int) -> int:
        """
        Get the duration of a scene in frames.

        Args:
            scene_index: Zero-based index of the scene.

        Returns:
            Number of frames in the scene.
        """
        storyboard = self.project.load_storyboard()
        scenes = storyboard.get("scenes", [])
        fps = self.project.video.fps

        if scene_index < 0 or scene_index >= len(scenes):
            raise ValueError(f"Scene index {scene_index} out of range (0-{len(scenes)-1})")

        duration = scenes[scene_index].get("audio_duration_seconds", 0)
        return int(duration * fps)

    def get_scene_info(self, scene_index: int) -> dict:
        """
        Get comprehensive information about a scene.

        Args:
            scene_index: Zero-based index of the scene.

        Returns:
            Dict with scene information including:
            - id: Scene ID
            - title: Scene title
            - type: Scene type
            - start_frame: Starting frame number
            - end_frame: Ending frame number
            - duration_seconds: Duration in seconds
            - duration_frames: Duration in frames
            - audio_file: Path to audio file
            - narration: Narration text (if available)
            - visual_cue: Visual specification from script.json (if available)
        """
        storyboard = self.project.load_storyboard()
        scenes = storyboard.get("scenes", [])
        fps = self.project.video.fps

        if scene_index < 0 or scene_index >= len(scenes):
            raise ValueError(f"Scene index {scene_index} out of range (0-{len(scenes)-1})")

        scene = scenes[scene_index]
        start_frame = self.get_scene_start_frame(scene_index)
        duration_seconds = scene.get("audio_duration_seconds", 0)
        duration_frames = int(duration_seconds * fps)

        # Try to get narration text
        narration_text = ""
        try:
            narrations = self.project.load_narrations()
            if scene_index < len(narrations):
                narration_text = narrations[scene_index].narration
        except (FileNotFoundError, IndexError):
            pass

        # Try to get visual_cue from script.json
        visual_cue = None
        try:
            script_path = self.project.root_dir / "script" / "script.json"
            if script_path.exists():
                with open(script_path) as f:
                    script_data = json.load(f)
                script_scenes = script_data.get("scenes", [])
                if scene_index < len(script_scenes):
                    visual_cue = script_scenes[scene_index].get("visual_cue")
        except (FileNotFoundError, json.JSONDecodeError, IndexError):
            pass

        return {
            "id": scene.get("id", f"scene{scene_index + 1}"),
            "title": scene.get("title", "Untitled"),
            "type": scene.get("type", ""),
            "start_frame": start_frame,
            "end_frame": start_frame + duration_frames,
            "duration_seconds": duration_seconds,
            "duration_frames": duration_frames,
            "audio_file": scene.get("audio_file", ""),
            "narration": narration_text,
            "visual_cue": visual_cue,
        }


def validate_project_sync(project: Project) -> ProjectSyncStatus:
    """
    Convenience function to validate project synchronization.

    Args:
        project: The project to validate.

    Returns:
        ProjectSyncStatus with any issues found.
    """
    validator = ProjectValidator(project)
    return validator.validate()

"""Narration scripts for video explainer projects.

This module provides utilities for loading narration scripts from project files.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SceneNarration:
    """Narration for a single scene."""

    scene_id: str
    title: str
    duration_seconds: int
    narration: str


def load_narrations_from_file(path: str | Path) -> list[SceneNarration]:
    """Load narrations from a JSON file.

    Args:
        path: Path to the narrations JSON file.

    Returns:
        List of SceneNarration objects.

    The JSON file should have this format:
    {
        "scenes": [
            {
                "scene_id": "scene1",
                "title": "Scene Title",
                "duration_seconds": 15,
                "narration": "The narration text..."
            },
            ...
        ]
    }
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Narration file not found: {path}")

    with open(path) as f:
        data = json.load(f)

    return [
        SceneNarration(
            scene_id=scene["scene_id"],
            title=scene["title"],
            duration_seconds=scene["duration_seconds"],
            narration=scene["narration"],
        )
        for scene in data.get("scenes", [])
    ]


def load_narrations_from_project(project_path: str | Path) -> list[SceneNarration]:
    """Load narrations from a project directory.

    Args:
        project_path: Path to the project directory.

    Returns:
        List of SceneNarration objects.
    """
    project_path = Path(project_path)
    narration_path = project_path / "narration" / "narrations.json"
    return load_narrations_from_file(narration_path)

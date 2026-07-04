#!/usr/bin/env python3
"""
Migration script to convert scene IDs from numbered format to slug-only format.

Old format: "scene1_the_impossible_leap" or numeric 1
New format: "the_impossible_leap" (slug only, no number prefix)

This script:
1. Updates script.json (scene_id: int -> str slug)
2. Updates narrations.json (scene_id: "scene1_X" -> "X")
3. Updates storyboard.json (id: "scene1_X" -> "X", audio_file)
4. Updates voiceover/manifest.json (scene_id, audio_path)
5. Renames audio files (scene1_X.mp3 -> X.mp3)
"""

import json
import re
import shutil
from pathlib import Path


def slugify(title: str) -> str:
    """Convert title to slug format."""
    slug = title.lower()
    slug = re.sub(r'[\s\-]+', '_', slug)
    slug = re.sub(r'[^a-z0-9_]', '', slug)
    slug = re.sub(r'_+', '_', slug)
    slug = slug.strip('_')
    return slug


def strip_scene_prefix(scene_id: str) -> str:
    """Strip 'sceneN_' prefix from scene ID if present."""
    if re.match(r'^scene\d+_', scene_id):
        return re.sub(r'^scene\d+_', '', scene_id)
    return scene_id


def migrate_script_json(project_dir: Path) -> None:
    """Migrate script.json - convert scene_id from int to slug."""
    script_path = project_dir / "script" / "script.json"
    if not script_path.exists():
        print(f"  Skipping script.json (not found)")
        return

    with open(script_path) as f:
        data = json.load(f)

    for scene in data.get("scenes", []):
        old_id = scene.get("scene_id")
        title = scene.get("title", "")

        if isinstance(old_id, int):
            # Convert from int to slug based on title
            new_id = slugify(title)
        elif isinstance(old_id, str):
            # Strip prefix if present
            new_id = strip_scene_prefix(old_id)
        else:
            new_id = slugify(title)

        print(f"    scene_id: {old_id} -> {new_id}")
        scene["scene_id"] = new_id

    with open(script_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Updated script.json")


def migrate_narrations_json(project_dir: Path) -> None:
    """Migrate narrations.json - convert scene_id from 'scene1_X' to 'X'."""
    narrations_path = project_dir / "narration" / "narrations.json"
    if not narrations_path.exists():
        print(f"  Skipping narrations.json (not found)")
        return

    with open(narrations_path) as f:
        data = json.load(f)

    for scene in data.get("scenes", []):
        old_id = scene.get("scene_id", "")
        title = scene.get("title", "")

        if old_id:
            new_id = strip_scene_prefix(old_id)
        else:
            new_id = slugify(title)

        print(f"    scene_id: {old_id} -> {new_id}")
        scene["scene_id"] = new_id

    with open(narrations_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Updated narrations.json")


def migrate_storyboard_json(project_dir: Path) -> dict[str, str]:
    """Migrate storyboard.json - convert id and audio_file.

    Returns:
        Mapping of old audio filename to new audio filename
    """
    storyboard_path = project_dir / "storyboard" / "storyboard.json"
    if not storyboard_path.exists():
        print(f"  Skipping storyboard.json (not found)")
        return {}

    with open(storyboard_path) as f:
        data = json.load(f)

    audio_renames = {}

    for scene in data.get("scenes", []):
        old_id = scene.get("id", "")
        old_audio = scene.get("audio_file", "")

        # Generate new ID from old ID
        new_id = strip_scene_prefix(old_id)

        # Generate new audio filename
        if old_audio:
            # Old format: scene1_the_impossible_leap.mp3
            # New format: the_impossible_leap.mp3
            new_audio = re.sub(r'^scene\d+_', '', old_audio)
            audio_renames[old_audio] = new_audio
        else:
            new_audio = f"{new_id}.mp3"

        print(f"    id: {old_id} -> {new_id}")
        print(f"    audio_file: {old_audio} -> {new_audio}")
        scene["id"] = new_id
        scene["audio_file"] = new_audio

    with open(storyboard_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Updated storyboard.json")

    return audio_renames


def migrate_voiceover_manifest(project_dir: Path, audio_renames: dict[str, str]) -> None:
    """Migrate voiceover/manifest.json."""
    manifest_path = project_dir / "voiceover" / "manifest.json"
    if not manifest_path.exists():
        print(f"  Skipping manifest.json (not found)")
        return

    with open(manifest_path) as f:
        data = json.load(f)

    for scene in data.get("scenes", []):
        old_id = scene.get("scene_id", "")
        old_path = scene.get("audio_path", "")

        # Update scene_id
        new_id = strip_scene_prefix(old_id)

        # Update audio_path
        if old_path:
            # Extract filename from path
            old_filename = Path(old_path).name
            new_filename = audio_renames.get(old_filename, old_filename)
            new_path = str(Path(old_path).parent / new_filename)
        else:
            new_path = ""

        print(f"    scene_id: {old_id} -> {new_id}")
        if old_path != new_path:
            print(f"    audio_path: {old_path} -> {new_path}")
        scene["scene_id"] = new_id
        scene["audio_path"] = new_path

    with open(manifest_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Updated manifest.json")


def rename_audio_files(project_dir: Path, audio_renames: dict[str, str]) -> None:
    """Rename audio files in voiceover directory."""
    voiceover_dir = project_dir / "voiceover"
    if not voiceover_dir.exists():
        print(f"  Skipping audio rename (voiceover dir not found)")
        return

    for old_name, new_name in audio_renames.items():
        old_path = voiceover_dir / old_name
        new_path = voiceover_dir / new_name

        if old_path.exists():
            if old_path != new_path:
                print(f"    Renaming: {old_name} -> {new_name}")
                shutil.move(old_path, new_path)
        else:
            print(f"    Skipping: {old_name} (not found)")


def migrate_project(project_dir: Path) -> None:
    """Migrate a single project to the new scene ID format."""
    print(f"\nMigrating project: {project_dir.name}")
    print("=" * 50)

    # Step 1: Migrate script.json
    print("\n1. Migrating script.json...")
    migrate_script_json(project_dir)

    # Step 2: Migrate narrations.json
    print("\n2. Migrating narrations.json...")
    migrate_narrations_json(project_dir)

    # Step 3: Migrate storyboard.json (get audio rename mapping)
    print("\n3. Migrating storyboard.json...")
    audio_renames = migrate_storyboard_json(project_dir)

    # Step 4: Migrate voiceover manifest
    print("\n4. Migrating voiceover/manifest.json...")
    migrate_voiceover_manifest(project_dir, audio_renames)

    # Step 5: Rename audio files
    print("\n5. Renaming audio files...")
    rename_audio_files(project_dir, audio_renames)

    print("\n" + "=" * 50)
    print(f"Migration complete for {project_dir.name}")


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python migrate_scene_ids.py <project_dir>")
        print("Example: python migrate_scene_ids.py projects/thinking-models")
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)

    migrate_project(project_dir)


if __name__ == "__main__":
    main()

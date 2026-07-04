"""Import the GPLv3 SyncToon character into Remotion's public asset tree."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

ASSET_GROUPS = ("body", "head", "eyes", "mouth", "background")


def _source_revision(source: Path) -> str:
    head = source / ".git/HEAD"
    if not head.exists():
        return "unknown"
    value = head.read_text(encoding="utf-8").strip()
    if value.startswith("ref: "):
        ref = source / ".git" / value[5:]
        return ref.read_text(encoding="utf-8").strip() if ref.exists() else value[5:]
    return value


def _asset_key(group: str, relative: Path, existing: dict[str, Any]) -> str:
    if group == "head":
        preferred = relative.parent.name
    else:
        preferred = relative.stem
    if preferred not in existing:
        return preferred
    return relative.with_suffix("").as_posix().replace("/", ":")


def import_character(source: Path, destination: Path) -> dict[str, Any]:
    """Copy character_1 and emit a safe semantic manifest."""

    source = source.resolve()
    destination = destination.resolve()
    character_source = source / "core/images/characters/character_1"
    if not character_source.is_dir():
        raise FileNotFoundError(f"SyncToon character not found: {character_source}")

    target = destination / "character_1"
    target.mkdir(parents=True, exist_ok=True)
    assets: dict[str, dict[str, dict[str, Any]]] = {group: {} for group in ASSET_GROUPS}

    for group in ASSET_GROUPS:
        group_source = character_source / group
        if not group_source.exists():
            continue
        group_target = target / group
        if group_target.exists():
            shutil.rmtree(group_target)
        shutil.copytree(group_source, group_target)
        for file_path in sorted(group_target.rglob("*.png")):
            relative = file_path.relative_to(group_target)
            key = _asset_key(group, relative, assets[group])
            assets[group][key] = {
                "path": f"characters/synctoon/character_1/{group}/{relative.as_posix()}"
            }

    metadata_source = source / "core/images/metadata/metadata.json"
    mouth_map_source = source / "core/utils/mouth_image.json"
    metadata = json.loads(metadata_source.read_text(encoding="utf-8")) if metadata_source.exists() else {}
    mouth_map = json.loads(mouth_map_source.read_text(encoding="utf-8")) if mouth_map_source.exists() else {}

    fallbacks = {
        "body": "body1",
        "head": "M",
        "eyes": "content_M",
        "mouth": "m_b_close_h",
        "background": next(iter(assets["background"]), ""),
    }
    for group in ("body", "head", "eyes", "mouth"):
        if fallbacks[group] not in assets[group]:
            raise ValueError(f"required fallback {group}:{fallbacks[group]} is missing")

    manifest = {
        "version": 1,
        "character_id": "character_1",
        "source_revision": _source_revision(source),
        "assets": assets,
        "fallbacks": fallbacks,
        "metadata": metadata.get("character_1", metadata),
        "mouth_map": mouth_map,
    }
    (target / "character-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    license_source = source / "LICENSE"
    if license_source.exists():
        shutil.copy2(license_source, destination / "LICENSE")
    provenance = (
        "# SyncToon asset provenance\n\n"
        f"- Source: `{source}`\n"
        f"- Revision: `{manifest['source_revision']}`\n"
        "- Imported: 2026-07-04\n"
        "- License: GPLv3 (the source README claims MIT, but its LICENSE file is GPLv3)\n"
        "- Modifications: files copied into a Remotion public asset layout and indexed by a generated manifest\n"
    )
    (target / "PROVENANCE.md").write_text(provenance, encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    manifest = import_character(args.source, args.destination)
    print(
        json.dumps(
            {
                "character_id": manifest["character_id"],
                "source_revision": manifest["source_revision"],
                "assets": {key: len(value) for key, value in manifest["assets"].items()},
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

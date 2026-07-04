import json
from pathlib import Path

from scripts.import_synctoon_character import import_character


def _png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"png")


def test_import_builds_resolvable_manifest(tmp_path):
    source = tmp_path / "synctoon"
    character = source / "core/images/characters/character_1"
    _png(character / "body/body1.png")
    _png(character / "head/M/M.png")
    _png(character / "eyes/content/content_M.png")
    _png(character / "eyes/content/content_blink/02.png")
    _png(character / "mouth/happy/m_b_close_h.png")
    (source / "core/images/metadata").mkdir(parents=True)
    (source / "core/images/metadata/metadata.json").write_text("{}", encoding="utf-8")
    (source / "core/utils").mkdir(parents=True)
    (source / "core/utils/mouth_image.json").write_text(
        json.dumps({"M": {"happy": "m_b_close_h"}}), encoding="utf-8"
    )
    (source / "LICENSE").write_text("GPLv3 fixture", encoding="utf-8")

    destination = tmp_path / "public/characters/synctoon"
    manifest = import_character(source, destination)

    assert manifest["character_id"] == "character_1"
    assert manifest["fallbacks"]["body"] in manifest["assets"]["body"]
    assert all(
        ".." not in item["path"]
        for group in manifest["assets"].values()
        for item in group.values()
    )
    assert (destination / "LICENSE").exists()
    assert (destination / "character_1/PROVENANCE.md").exists()

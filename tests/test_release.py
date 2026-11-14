"""Exercise release guards and the actual integration archive builder."""

import json
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts import prepare_release as release


@pytest.fixture
def release_repo(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1]
    root = tmp_path / "repository"
    root.mkdir()
    for name in (
        "pyproject.toml",
        "hacs.json",
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "uv.lock",
        "DEVELOPMENT.md",
        "RELEASING.md",
    ):
        shutil.copyfile(source / name, root / name)
    for name in ("scripts", "custom_components"):
        shutil.copytree(
            source / name, root / name, ignore=shutil.ignore_patterns("__pycache__")
        )
    monkeypatch.setattr(release, "ROOT", root)
    version = json.loads(
        (root / "custom_components/tado_overlay_metadata/manifest.json").read_text(
            encoding="utf-8"
        )
    )["version"]
    return root, version


def test_release_contains_matching_notes_and_component_files(release_repo):
    root, version = release_repo
    (root / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## Unreleased\n\n- Future work.\n\n"
        f"## {version} - 2026-11-15\n\n- Ready for users.\n\n"
        "## 0.0.1 - Initial implementation\n\n- Old work.\n",
        encoding="utf-8",
    )
    notes = root / "notes.md"

    asset = release.prepare_release(f"v{version}", notes)

    assert notes.read_text(encoding="utf-8") == "- Ready for users.\n"
    assert asset.name == f"tado_overlay_metadata-{version}.zip"
    with ZipFile(asset) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read("manifest.json"))["version"] == version
        assert "__init__.py" in archive.namelist()
        assert "brand/icon.svg" in archive.namelist()
        assert not any(
            name.startswith(("custom_components/", "tests/", "scripts/"))
            or "__pycache__" in name
            for name in archive.namelist()
        )


def test_mismatched_tag_cannot_build_release(release_repo):
    root, version = release_repo
    notes = root / "notes.md"

    with pytest.raises(ValueError, match="must match manifest version"):
        release.prepare_release(f"v{version}.1", notes)

    assert not (root / "dist").exists()
    assert not notes.exists()


@pytest.mark.parametrize("section", ["## Unreleased\n\n- Future work.\n", ""])
def test_missing_or_empty_notes_cannot_build_release(release_repo, section):
    root, version = release_repo
    changelog = section or f"## {version} - 2026-11-15\n\n"
    (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    notes = root / "notes.md"

    with pytest.raises(ValueError, match="Missing dated changelog notes"):
        release.prepare_release(f"v{version}", notes)

    assert not (root / "dist").exists()
    assert not notes.exists()

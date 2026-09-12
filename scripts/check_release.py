"""Local release checks, not a substitute for upstream HACS/hassfest validation."""

import json
import re
import struct
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/tado_overlay_metadata"


def check():
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert manifest["domain"] == COMPONENT.name
    assert manifest["version"] == project["project"]["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    for key in ("documentation", "issue_tracker"):
        assert manifest[key].startswith("https://github.com/jonalbr/ha-tado-overlay-metadata")
        assert "OWNER" not in manifest[key]
    assert manifest["codeowners"] == ["@jonalbr"]
    assert manifest["dependencies"] == ["tado"]
    assert manifest["config_flow"] is True
    assert json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))["homeassistant"]
    english = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    assert english == json.loads((COMPONENT / "translations/en.json").read_text(encoding="utf-8"))
    for filename, size in (("icon.png", 256), ("icon@2x.png", 512)):
        image = (COMPONENT / "brand" / filename).read_bytes()
        assert image[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", image[16:24]) == (size, size)
    assert (COMPONENT / "quality_scale.yaml").is_file()
    assert f"## {manifest['version']} - " in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for name in (
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "uv.lock",
        "DEVELOPMENT.md",
        "RELEASING.md",
    ):
        assert (ROOT / name).is_file(), name
    print("Local release structure and metadata checks passed")


if __name__ == "__main__":
    check()

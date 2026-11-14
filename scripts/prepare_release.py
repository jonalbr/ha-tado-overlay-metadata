"""Validate a stable release tag, build its ZIP and extract changelog notes."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare_release(tag: str, notes_file: Path) -> Path:
    manifest = ROOT / "custom_components/tado_overlay_metadata/manifest.json"
    version = json.loads(manifest.read_text(encoding="utf-8"))["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or tag != f"v{version}":
        raise ValueError(f"Release tag {tag!r} must match manifest version v{version}")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    section = re.search(
        rf"^## {re.escape(version)} - \d{{4}}-\d{{2}}-\d{{2}}[^\S\n]*\n"
        r"(.*?)(?=^## |\Z)",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    if section is None or not section[1].strip():
        raise ValueError(f"Missing dated changelog notes for {version}")

    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_release.py")],
        cwd=ROOT,
        check=True,
    )
    notes_file.write_text(section[1].strip() + "\n", encoding="utf-8")
    return ROOT / "dist" / f"tado_overlay_metadata-{version}.zip"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--notes-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        asset = prepare_release(args.tag, args.notes_file)
    except ValueError as err:
        parser.error(str(err))

    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write(f"asset_path={asset.resolve()}\n")
            stream.write(f"notes_path={args.notes_file.resolve()}\n")
    print(f"Release notes: {args.notes_file.resolve()}")


if __name__ == "__main__":
    main()

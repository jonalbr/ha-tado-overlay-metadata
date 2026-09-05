"""Build a deterministic integration ZIP without private or development files."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from check_release import check

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/tado_overlay_metadata"


def build():
    check()
    version = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))["version"]
    target = ROOT / "dist" / f"tado_overlay_metadata-{version}.zip"
    target.parent.mkdir(exist_ok=True)
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(COMPONENT.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            info = ZipInfo(path.relative_to(COMPONENT).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    with ZipFile(target) as archive:
        assert archive.testzip() is None
    print(target)


if __name__ == "__main__":
    build()

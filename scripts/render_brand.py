# /// script
# requires-python = ">=3.14.2"
# dependencies = ["CairoSVG==2.9.1"]
# ///
"""Export Home Assistant's required PNG brand images from the SVG master."""

from pathlib import Path

import cairosvg

BRAND = (
    Path(__file__).resolve().parents[1]
    / "custom_components/tado_overlay_metadata/brand"
)


def render():
    for filename, size in (("icon.png", 256), ("icon@2x.png", 512)):
        target = BRAND / filename
        cairosvg.svg2png(
            url=str(BRAND / "icon.svg"),
            write_to=str(target),
            output_width=size,
            output_height=size,
        )
        print(target)


if __name__ == "__main__":
    render()

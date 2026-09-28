# SPDX-License-Identifier: Apache-2.0
"""Render the geometric tracker icon as SVG and PNG assets."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components/triangles/brand"
SOURCE = ROOT / "docs/assets"
OUTLINE = "#123344"
FACES = [
    ([(128, 16), (24, 92), (128, 140)], "#49D7C5"),
    ([(128, 16), (128, 140), (232, 92)], "#A0EFE5"),
    ([(24, 92), (128, 240), (128, 140)], "#159D9B"),
    ([(232, 92), (128, 140), (128, 240)], "#2184B5"),
]


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    SOURCE.mkdir(parents=True, exist_ok=True)
    polygons = []
    image = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for points, color in FACES:
        coordinates = " ".join(f"{x},{y}" for x, y in points)
        polygons.append(f'  <polygon points="{coordinates}" fill="{color}"/>')
        scaled = [(x * 4, y * 4) for x, y in points]
        draw.polygon(scaled, fill=color)
        draw.line([*scaled, scaled[0]], fill=OUTLINE, width=20, joint="curve")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" '
        'width="256" height="256">\n'
        "  <title>Triangles scene controller: an eight-sided tracker</title>\n"
        f'<g stroke="{OUTLINE}" stroke-width="5" stroke-linejoin="round">\n'
        + "\n".join(polygons)
        + "\n</g>\n</svg>\n"
    )
    (SOURCE / "icon.svg").write_text(svg)
    for filename, size in (("icon.png", 256), ("icon@2x.png", 512)):
        image.resize((size, size), Image.Resampling.LANCZOS).save(BRAND / filename)
        print(BRAND / filename)


if __name__ == "__main__":
    main()

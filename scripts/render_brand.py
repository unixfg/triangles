# SPDX-License-Identifier: Apache-2.0
"""Render a Timeular tracker with its central control strip."""

from math import hypot
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components/triangles/brand"
SOURCE = ROOT / "docs/assets"
OUTLINE = "#8B9195"
VERTICES = {
    "top": (124, 18),
    "right": (237, 130),
    "bottom": (124, 241),
    "left": (20, 132),
    "front": (50, 131),
}
FACES = [
    (("top", "left", "front"), "#ADB2B5"),
    (("left", "bottom", "front"), "#BBC0C2"),
    (("top", "front", "right"), "#F5F5F3"),
    (("front", "bottom", "right"), "#E1E3E3"),
]
SCALE = 4


def rounded_outline(points, radius=8):
    """Describe rounded corners as SVG curves and sampled raster points."""
    commands = []
    raster = []
    for index, point in enumerate(points):
        previous = points[index - 1]
        following = points[(index + 1) % len(points)]
        ends = []
        for neighbor in (previous, following):
            dx, dy = neighbor[0] - point[0], neighbor[1] - point[1]
            ratio = min(radius / hypot(dx, dy), 0.5)
            ends.append((point[0] + dx * ratio, point[1] + dy * ratio))
        start, end = ends
        commands.append(f"{'M' if index == 0 else 'L'} {start[0]:.2f},{start[1]:.2f}")
        commands.append(f"Q {point[0]},{point[1]} {end[0]:.2f},{end[1]:.2f}")
        for step in range(13):
            t = step / 12
            raster.append(
                tuple(
                    (1 - t) ** 2 * start[axis]
                    + 2 * (1 - t) * t * point[axis]
                    + t**2 * end[axis]
                    for axis in (0, 1)
                )
            )
    return " ".join([*commands, "Z"]), raster


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    SOURCE.mkdir(parents=True, exist_ok=True)
    outline, boundary = rounded_outline(
        [VERTICES[key] for key in ("top", "right", "bottom", "left")], radius=14
    )
    polygons = []
    image = Image.new("RGBA", (256 * SCALE, 256 * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def polygon(points, color):
        coordinates = " ".join(f"{x},{y}" for x, y in points)
        polygons.append(f'  <polygon points="{coordinates}" fill="{color}"/>')
        scaled = [(x * SCALE, y * SCALE) for x, y in points]
        draw.polygon(scaled, fill=color)

    for names, color in FACES:
        polygon([VERTICES[name] for name in names], color)

    draw.line(
        [(20 * SCALE, 132 * SCALE), (237 * SCALE, 130 * SCALE)],
        fill="#8A8C8C",
        width=SCALE,
    )
    polygons.append('<path d="M20,132 L237,130" stroke="#8A8C8C" fill="none"/>')
    strip, strip_points = rounded_outline(
        [(101, 119), (193, 119), (205, 130), (194, 142), (101, 142), (93, 131)],
        radius=5,
    )
    scaled_strip = [(x * SCALE, y * SCALE) for x, y in strip_points]
    draw.polygon(scaled_strip, fill="#292C2D")
    draw.line(
        [*scaled_strip, scaled_strip[0]], fill="#16191A", width=SCALE, joint="curve"
    )
    polygons.append(f'<path d="{strip}" fill="#292C2D" stroke="#16191A"/>')
    draw.ellipse((106 * SCALE, 128 * SCALE, 110 * SCALE, 132 * SCALE), fill="#0C0F10")
    draw.arc(
        (116 * SCALE, 125 * SCALE, 126 * SCALE, 135 * SCALE),
        start=-60,
        end=240,
        fill="#8B9396",
        width=round(1.25 * SCALE),
    )
    draw.line(
        [(121 * SCALE, 123 * SCALE), (121 * SCALE, 130 * SCALE)],
        fill="#8B9396",
        width=round(1.25 * SCALE),
    )
    polygons.extend(
        [
            '<circle cx="108" cy="130" r="2" fill="#0C0F10"/>',
            '<path d="M123.5,125.67 A5,5 0 1,1 118.5,125.67 M121,123 L121,130" '
            'fill="none" stroke="#8B9396" stroke-width="1.25"/>',
        ]
    )

    mask = Image.new("L", image.size, 0)
    scaled_boundary = [(x * SCALE, y * SCALE) for x, y in boundary]
    ImageDraw.Draw(mask).polygon(scaled_boundary, fill=255)
    image.putalpha(mask)
    draw.line(
        [*scaled_boundary, scaled_boundary[0]],
        fill=OUTLINE,
        width=SCALE,
        joint="curve",
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" '
        'width="256" height="256">\n'
        "  <title>Timeular tracker with a horizontal black control strip</title>\n"
        f'  <defs><clipPath id="shell"><path d="{outline}"/></clipPath></defs>\n'
        '  <g clip-path="url(#shell)">\n'
        + "\n".join(polygons)
        + f'\n  </g>\n  <path d="{outline}" fill="none" stroke="{OUTLINE}" '
        'stroke-width="1" stroke-linejoin="round"/>\n</svg>\n'
    )
    (SOURCE / "icon.svg").write_text(svg)
    for filename, size in (("icon.png", 256), ("icon@2x.png", 512)):
        image.resize((size, size), Image.Resampling.LANCZOS).save(BRAND / filename)
        print(BRAND / filename)


if __name__ == "__main__":
    main()

# SPDX-License-Identifier: Apache-2.0
"""Render a rounded, eight-sided tracker with a rubber button cap."""

from math import hypot
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components/triangles/brand"
SOURCE = ROOT / "docs/assets"
OUTLINE = "#667680"
VERTICES = {
    "top": (81, 30),
    "back": (158, 64),
    "button": (217, 124),
    "bottom": (175, 232),
    "front": (98, 198),
    "left": (39, 138),
}
FACES = [
    (("button", "front", "bottom"), "#CBD3D9"),
    (("button", "back", "top"), "#DEE4E8"),
    (("left", "front", "top"), "#FAFCFD"),
    (("button", "front", "top"), "#EBF0F3"),
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
    outline, boundary = rounded_outline(list(VERTICES.values()))
    polygons = []
    image = Image.new("RGBA", (256 * SCALE, 256 * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def polygon(points, color, stroke="#B1BEC7", width=1.5):
        coordinates = " ".join(f"{x},{y}" for x, y in points)
        polygons.append(
            f'  <polygon points="{coordinates}" fill="{color}" '
            f'stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round"/>'
        )
        scaled = [(x * SCALE, y * SCALE) for x, y in points]
        draw.polygon(scaled, fill=color)
        draw.line(
            [*scaled, scaled[0]], fill=stroke, width=round(width * SCALE), joint="curve"
        )

    for names, color in FACES:
        polygon([VERTICES[name] for name in names], color)

    tip = VERTICES["button"]
    cap = {
        name: tuple(
            round(t + (v - t) * 0.25, 2) for t, v in zip(tip, vertex, strict=True)
        )
        for name, vertex in VERTICES.items()
        if name in {"top", "back", "front", "bottom"}
    }
    polygon([tip, cap["back"], cap["top"]], "#46515A", "#35414A")
    polygon([tip, cap["front"], cap["bottom"]], "#20292F", "#35414A")
    polygon([tip, cap["front"], cap["top"]], "#303B43", "#35414A")
    polygon([(194, 110), (207, 120), (198, 129), (186, 119)], "#1D262C", "#71808B", 1)
    draw.ellipse((190 * SCALE, 131 * SCALE, 195 * SCALE, 136 * SCALE), fill="#66CBB8")
    polygons.append('  <circle cx="192.5" cy="133.5" r="2.5" fill="#66CBB8"/>')

    mask = Image.new("L", image.size, 0)
    scaled_boundary = [(x * SCALE, y * SCALE) for x, y in boundary]
    ImageDraw.Draw(mask).polygon(scaled_boundary, fill=255)
    image.putalpha(mask)
    draw.line(
        [*scaled_boundary, scaled_boundary[0]],
        fill=OUTLINE,
        width=round(1.75 * SCALE),
        joint="curve",
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" '
        'width="256" height="256">\n'
        "  <title>Eight-sided white tracker with a black button cap</title>\n"
        f'  <defs><clipPath id="shell"><path d="{outline}"/></clipPath></defs>\n'
        '  <g clip-path="url(#shell)">\n'
        + "\n".join(polygons)
        + f'\n  </g>\n  <path d="{outline}" fill="none" stroke="{OUTLINE}" '
        'stroke-width="1.75" stroke-linejoin="round"/>\n</svg>\n'
    )
    (SOURCE / "icon.svg").write_text(svg)
    for filename, size in (("icon.png", 256), ("icon@2x.png", 512)):
        image.resize((size, size), Image.Resampling.LANCZOS).save(BRAND / filename)
        print(BRAND / filename)


if __name__ == "__main__":
    main()

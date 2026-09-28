# SPDX-License-Identifier: Apache-2.0
"""Package only the files that belong in Home Assistant's /config directory."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
component = root / "custom_components/triangles"
manifest = json.loads((component / "manifest.json").read_text())
for filename in ("LICENSE", "NOTICE"):
    if (root / filename).read_bytes() != (component / filename).read_bytes():
        raise SystemExit(f"Root and packaged {filename} must match before packaging")
for filename in (
    "CREDITS.md",
    "licenses/MIT-linux-client.txt",
    "licenses/MIT-node-client.txt",
    "brand/icon.png",
    "blueprints/eight_scenes.yaml",
):
    if not (component / filename).is_file():
        raise SystemExit(f"Missing distribution file: {filename}")
bundled_blueprint = component / "blueprints/eight_scenes.yaml"
import_blueprint = root / "blueprints/automation/triangles/eight_scenes.yaml"
if bundled_blueprint.read_bytes() != import_blueprint.read_bytes():
    raise SystemExit("Bundled and importable scene blueprints must match")
destination = root / "dist" / f"triangles-{manifest['version']}.zip"
destination.parent.mkdir(exist_ok=True)
with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
    for directory in ("custom_components/triangles", "blueprints/automation/triangles"):
        for path in sorted((root / directory).rglob("*")):
            if path.is_file() and (
                path.suffix in {".py", ".json", ".yaml", ".png", ".md", ".txt"}
                or path.name in {"LICENSE", "NOTICE"}
            ):
                archive.write(path, path.relative_to(root))
print(destination)

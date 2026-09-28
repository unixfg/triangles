# SPDX-License-Identifier: Apache-2.0
"""Validate a stable release tag against the integration manifest."""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STABLE_VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")


def release_metadata(version: str, ref_type: str, ref_name: str) -> dict[str, str]:
    """Require a version tag matching a stable major.minor.patch version."""
    if not isinstance(version, str) or not STABLE_VERSION.fullmatch(version):
        raise ValueError("Releases require a stable major.minor.patch manifest version")
    tag = f"v{version}"
    if ref_type != "tag" or ref_name != tag:
        raise ValueError(f"Releases require the manifest version tag {tag}")
    return {"version": version, "tag": tag, "asset": f"triangles-{version}.zip"}


def main() -> None:
    manifest = json.loads(
        (ROOT / "custom_components/triangles/manifest.json").read_text()
    )
    try:
        metadata = release_metadata(
            manifest["version"],
            os.environ["GITHUB_REF_TYPE"],
            os.environ["GITHUB_REF_NAME"],
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        for key, value in metadata.items():
            output.write(f"{key}={value}\n")


if __name__ == "__main__":
    main()

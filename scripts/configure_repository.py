# SPDX-License-Identifier: Apache-2.0
"""Configure the integration's GitHub repository URLs and code owner."""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GITHUB_LOGIN = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", help="GitHub owner/repository")
    parser.add_argument(
        "--maintainer",
        help="GitHub user to list as code owner (defaults to repo owner)",
    )
    args = parser.parse_args()
    if not re.fullmatch(rf"{GITHUB_LOGIN}/[A-Za-z0-9_.-]+", args.repository):
        parser.error("Use a GitHub owner/repository, without a URL or .git suffix")
    owner, name = args.repository.split("/")
    if name in {".", ".."} or name.endswith(".git"):
        parser.error("Use the repository name without a .git suffix")
    maintainer = (args.maintainer or owner).removeprefix("@")
    if not re.fullmatch(GITHUB_LOGIN, maintainer):
        parser.error("The maintainer must be a GitHub username")

    manifest_path = ROOT / "custom_components/triangles/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    repository_url = f"https://github.com/{args.repository}"
    manifest.update(
        codeowners=[f"@{maintainer}"],
        documentation=repository_url,
        issue_tracker=f"{repository_url}/issues",
    )
    # Hassfest requires domain, name, then the remaining keys alphabetically.
    ordered = {key: manifest[key] for key in ("domain", "name")}
    ordered.update(
        (key, manifest[key]) for key in sorted(manifest) if key not in ordered
    )
    manifest_path.write_text(json.dumps(ordered, indent=2) + "\n")
    print(f"Configured {repository_url} with maintainer @{maintainer}")


if __name__ == "__main__":
    main()

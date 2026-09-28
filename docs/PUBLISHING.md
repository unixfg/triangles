# Publishing and CI

Maintainer guide for CI, releases, and HACS distribution.

## Repository metadata

HACS validation requires a public GitHub repository with Issues enabled, a
description, and topics. Suggested metadata:

- Description: `Use an eight-sided Bluetooth tracker as a Home Assistant scene controller.`
- Topics: `home-assistant`, `hacs`, `custom-integration`, `bluetooth`, `triangles`.

If maintaining a fork, update the manifest's repository URLs and code owner:

```sh
python3 scripts/configure_repository.py OWNER/REPOSITORY --maintainer GITHUB_USER
```

Update the repository and blueprint links in the README to match the fork.
Retain the integration's `LICENSE`, `NOTICE`, `CREDITS.md`, and upstream license
files in all distributions.

## CI runners

All jobs target a Linux x86-64 self-hosted runner:

```yaml
runs-on: [self-hosted, Linux, X64, workstation-ci]
```

The custom label is declared in `.github/actionlint.yaml`. The runner must be
registered for the repository, provide Python 3 and GitHub CLI, and have access
to a Docker-compatible container engine for the Hassfest and HACS actions.
Jobs wait for an eligible runner; there is no GitHub-hosted fallback.
Fork maintainers can register a matching
runner or adjust the workflow labels and actionlint configuration.

Require workflow approval for **all external contributors**
(`approval_policy: all_external_contributors`) before running fork PRs on a
self-hosted runner. Review the entire change before approving a run: its code
executes with access to the runner account and reachable network services.

## Required checks

| Check | Purpose |
| --- | --- |
| Ruff | Python lint and formatting |
| pytest | Home Assistant config flows, entities, triggers, blueprint actions, and Bluetooth failure/reconnect behavior |
| Packaging | Builds the manual-install ZIP for CI artifacts and release assets |
| Hassfest | Home Assistant integration metadata and related files |
| HACS | Repository layout, metadata, icon, description, topics, and Issues |

The test job creates a fresh virtual environment using Linux, Python 3.14, and
the pinned dependencies in `requirements-dev.txt`, including Home Assistant
2026.9.4. Bluetooth I/O is simulated; the runner needs no tracker or Bluetooth
adapter. Local development commands are in the [README](../README.md#development).

Test and validation jobs use read-only repository permissions. Only the release
publication job has `contents: write`. Checkouts do not persist credentials,
HACS PR comments are disabled, and no HACS checks are ignored. Dependabot
proposes GitHub Actions updates; Home Assistant and Bluetooth test dependency
changes should be verified together.

HACS also validates repository settings, so local Python checks do not replace
the GitHub validation jobs. Workflows use GitHub's provided token and need no
additional personal access token. Validation also runs weekly to detect changes
in upstream requirements.

## Distribution

HACS downloads `custom_components/triangles`; users import the scene blueprint
separately. The manual-install ZIP contains both directory trees for Home
Assistant's `/config` directory, so `hacs.json` does not enable `zip_release`.
Versioned ZIPs are attached to [GitHub Releases](https://github.com/unixfg/triangles/releases).
Installation instructions are in the [README](../README.md#install-with-hacs).

## Publish a version

1. Update `version` in `custom_components/triangles/manifest.json` to a stable
   `major.minor.patch` version and commit it.
2. Push a matching version tag, for example:

   ```sh
   git tag v0.1.2
   git push origin v0.1.2
   ```

The **Release** workflow validates the tag against the manifest, then runs the
CI and validation workflows against that revision. After tests, lint,
packaging, Hassfest, and HACS pass, it publishes a GitHub Release with generated
release notes and the tested `triangles-<version>.zip` attached. No manual
release creation or asset upload is needed.

The publication job downloads the ZIP from the same workflow run and verifies
its integrity, manifest version, and blueprint. It also checks that the remote
tag still points to the validated commit before publishing.

Branch pushes and pull requests run checks without publishing. Prerelease tags
and tags that do not match the manifest fail release validation. To retry a
failed release, rerun its failed jobs or dispatch **Release** on the existing
tag. Manual dispatch on a branch is rejected. Existing releases are not
overwritten; publish changed code under a new version tag.

Complete the [hardware checks](../README.md#verify-operation) before tagging a
release and document tested hardware and known limitations in the repository.
Automated tests use simulated Bluetooth I/O and do not establish firmware
compatibility.

## Apply for the default HACS catalog

After verifying custom-repository installation, passing HACS without ignored
checks and Hassfest, and publishing a GitHub Release:

1. Fork [`hacs/default`](https://github.com/hacs/default) and branch from `master`.
2. Add `unixfg/triangles` to the `integration` list in alphabetical order.
3. Open a PR as the repository owner or a major contributor, complete its
   submission template, and allow maintainer edits.

The integration includes `brand/icon.png`. Check the current
[HACS inclusion guide](https://www.hacs.xyz/docs/publish/include/) and
[integration requirements](https://www.hacs.xyz/docs/publish/integration/)
before submission. Catalog inclusion requires review; users can use the custom
repository while it is pending. HACS distribution and Home Assistant Core
inclusion are separate processes.

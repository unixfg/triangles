# SPDX-License-Identifier: Apache-2.0
"""Validate release identity and reject refs that must not publish."""

import pytest

from scripts.release_metadata import release_metadata


def test_matching_stable_tag():
    assert release_metadata("0.1.2", "tag", "v0.1.2") == {
        "version": "0.1.2",
        "tag": "v0.1.2",
        "asset": "triangles-0.1.2.zip",
    }


@pytest.mark.parametrize(
    ("version", "ref_type", "ref_name"),
    [
        ("0.1.2", "branch", "main"),
        ("0.1.2", "branch", "v0.1.2"),
        ("0.1.2", "tag", "v0.1.3"),
        ("0.1.2", "tag", "0.1.2"),
        ("0.1.2", "tag", "v0.1.2-rc.1"),
        ("0.1.2-rc.1", "tag", "v0.1.2-rc.1"),
        ("01.2.3", "tag", "v01.2.3"),
        ("1.2", "tag", "v1.2"),
        ("1.2.3\nasset=another.zip", "tag", "v1.2.3\nasset=another.zip"),
        ("../../elsewhere", "tag", "v../../elsewhere"),
        (None, "tag", "v0.1.2"),
    ],
)
def test_invalid_release_identity(version, ref_type, ref_name):
    with pytest.raises(ValueError):
        release_metadata(version, ref_type, ref_name)

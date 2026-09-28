# SPDX-License-Identifier: Apache-2.0
"""Test orientation packet lengths and valid side values."""

import pytest

from custom_components.triangles.const import parse_side


@pytest.mark.parametrize("side", range(9))
def test_valid_sides(side):
    assert parse_side(bytes([side])) == side


@pytest.mark.parametrize("data", [b"", b"\x01\x02", b"\x09", b"\xff", b"1"])
def test_invalid_sides(data):
    with pytest.raises(ValueError):
        parse_side(data)

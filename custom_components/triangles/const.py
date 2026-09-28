# SPDX-License-Identifier: Apache-2.0
"""Constants for the local Triangles scene controller."""

DOMAIN = "triangles"
EVENT_SIDE_CHANGED = "triangles_side_changed"
ORIENTATION_SERVICE_UUID = "c7e70010-c847-11e6-8175-8c89a55d403c"
ORIENTATION_CHARACTERISTIC_UUID = "c7e70012-c847-11e6-8175-8c89a55d403c"
SIDE_TRIGGER_TYPES = tuple(f"side_{side}" for side in range(1, 9))
SETTLE_SECONDS = 0.3
CONNECT_TIMEOUT = 30
GATT_TIMEOUT = 15
RETRY_SECONDS = 5
MAX_RETRY_SECONDS = 60


def parse_side(data: bytes | bytearray) -> int:
    """Decode the single-byte orientation; zero means no active face."""
    if len(data) != 1 or data[0] > 8:
        raise ValueError(f"Invalid Triangles orientation: {bytes(data).hex()}")
    return data[0]

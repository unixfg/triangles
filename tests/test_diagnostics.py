# SPDX-License-Identifier: Apache-2.0
"""Check diagnostic connection state and identifier redaction."""

import json

from custom_components.triangles.diagnostics import async_get_config_entry_diagnostics

from .conftest import ADDRESS
from .test_integration import setup_tracker


async def test_connected_diagnostics(hass, entry, ble):
    await setup_tracker(hass, entry, ble)
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result == {
        "loaded": True,
        "connected": True,
        "current_side": 1,
        "worker_running": True,
        "connection_stage": "connected",
        "connection_cycles": 1,
        "last_error": None,
    }


async def test_diagnostics_redact_error_identifiers(hass, entry, ble):
    await setup_tracker(hass, entry, ble)
    title = f"Study tracker {ADDRESS}"
    hass.config_entries.async_update_entry(entry, title=title)
    error = {
        "stage": "connection establishment",
        "type": "BleakError",
        "message": (
            f"{title}: {ADDRESS} at /org/bluez/hci0/dev_{ADDRESS.replace(':', '_')}"
        ),
    }
    entry.runtime_data.last_error = error
    result = await async_get_config_entry_diagnostics(hass, entry)
    encoded = json.dumps(result)
    assert ADDRESS not in encoded
    assert ADDRESS.replace(":", "_") not in encoded
    assert "Study tracker" not in encoded
    assert result["last_error"]["stage"] == "connection establishment"
    assert entry.runtime_data.last_error == error


async def test_unloaded_diagnostics(hass, entry):
    assert await async_get_config_entry_diagnostics(hass, entry) == {"loaded": False}

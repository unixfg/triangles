# SPDX-License-Identifier: Apache-2.0
"""Export connection state and the most recent failure for troubleshooting."""

import re
from typing import Any

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant

from . import TrianglesConfigEntry

_BLUETOOTH_ADDRESS = re.compile(r"(?:[0-9a-f]{2}[:_-]){5}[0-9a-f]{2}", re.IGNORECASE)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TrianglesConfigEntry
) -> dict[str, Any]:
    """Return a connection snapshot without device addresses or custom names."""
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is None:
        return {"loaded": False}
    error = None
    if coordinator.last_error is not None:
        error = dict(coordinator.last_error)
        message = error["message"]
        if entry.title:
            message = message.replace(entry.title, REDACTED)
        error["message"] = _BLUETOOTH_ADDRESS.sub(REDACTED, message)
    return {
        "loaded": True,
        "connected": coordinator.data.connected,
        "current_side": coordinator.data.side,
        "worker_running": coordinator.worker_running,
        "connection_stage": coordinator.connection_stage,
        "connection_cycles": coordinator.connection_cycles,
        "last_error": error,
    }

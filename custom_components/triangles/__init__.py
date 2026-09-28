# SPDX-License-Identifier: Apache-2.0
"""Triangles: use a supported eight-sided tracker as a scene controller."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant

from .coordinator import TrianglesCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.EVENT]
type TrianglesConfigEntry = ConfigEntry[TrianglesCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: TrianglesConfigEntry) -> bool:
    """Create entities before starting the persistent Bluetooth connection."""
    coordinator = entry.runtime_data = TrianglesCoordinator(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, coordinator.async_stop)
    )
    coordinator.async_start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TrianglesConfigEntry) -> bool:
    """Release the connection and listeners when the integration is unloaded."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.async_stop()
    return True

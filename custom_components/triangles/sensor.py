# SPDX-License-Identifier: Apache-2.0
"""Show the tracker's current side for setup and diagnostics."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TrianglesConfigEntry
from .coordinator import TrianglesCoordinator
from .entity import TrianglesEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrianglesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([TrianglesSideSensor(entry.runtime_data)])


class TrianglesSideSensor(TrianglesEntity, SensorEntity):
    """Orientation 1–8, or 0 when the tracker reports no active face."""

    _attr_translation_key = "current_side"
    _attr_icon = "mdi:dice-d8-outline"

    def __init__(self, coordinator: TrianglesCoordinator) -> None:
        super().__init__(coordinator, "current_side")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.side

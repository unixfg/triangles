# SPDX-License-Identifier: Apache-2.0
"""Expose Bluetooth connection status."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TrianglesConfigEntry
from .coordinator import TrianglesCoordinator
from .entity import TrianglesEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrianglesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([TrianglesConnectionSensor(entry.runtime_data)])


class TrianglesConnectionSensor(TrianglesEntity, BinarySensorEntity):
    """A disconnected device is off, rather than unavailable."""

    _attr_translation_key = "connection"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: TrianglesCoordinator) -> None:
        super().__init__(coordinator, "connection")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.connected

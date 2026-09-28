# SPDX-License-Identifier: Apache-2.0
"""Shared device identity for Triangles entities."""

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TrianglesCoordinator


class TrianglesEntity(CoordinatorEntity[TrianglesCoordinator]):
    """All entities belong to the same physical tracker."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TrianglesCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
            name=coordinator.entry.title,
            manufacturer="Timeular",
            model="Tracker",
        )

    @property
    def available(self) -> bool:
        return self.coordinator.data.connected

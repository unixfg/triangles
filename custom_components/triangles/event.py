# SPDX-License-Identifier: Apache-2.0
"""Expose side changes as a Home Assistant event entity."""

from homeassistant.components.event import EventEntity
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TrianglesConfigEntry
from .const import EVENT_SIDE_CHANGED, SIDE_TRIGGER_TYPES
from .coordinator import TrianglesCoordinator
from .entity import TrianglesEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TrianglesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([TrianglesFlipEvent(entry.runtime_data)])


class TrianglesFlipEvent(TrianglesEntity, EventEntity):
    """The timestamp and side of the most recent settled orientation change."""

    _attr_translation_key = "side_changed"
    _attr_icon = "mdi:gesture-swipe"
    _attr_event_types = list(SIDE_TRIGGER_TYPES)

    def __init__(self, coordinator: TrianglesCoordinator) -> None:
        super().__init__(coordinator, "side_changed")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_SIDE_CHANGED, self._async_side_changed)
        )

    @callback
    def _async_side_changed(self, event: Event) -> None:
        if self.device_entry is None or event.data["device_id"] != self.device_entry.id:
            return
        self._trigger_event(
            event.data["type"],
            {"side": event.data["side"], "previous_side": event.data["previous_side"]},
        )
        self.async_write_ha_state()

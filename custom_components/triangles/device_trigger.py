# SPDX-License-Identifier: Apache-2.0
"""Offer one named automation trigger per face in the device UI.

Adapted from Home Assistant's BTHome device-trigger implementation
(Apache-2.0). Modified for Triangles' eight faces and orientation events.
See NOTICE and CREDITS.md for attribution.
"""

import voluptuous as vol
from homeassistant.components.device_automation import (
    DEVICE_TRIGGER_BASE_SCHEMA,
    InvalidDeviceAutomationConfig,
)
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, EVENT_SIDE_CHANGED, SIDE_TRIGGER_TYPES

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_DOMAIN): DOMAIN,
        vol.Required(CONF_TYPE): vol.In(SIDE_TRIGGER_TYPES),
    }
)


async def async_validate_trigger_config(
    hass: HomeAssistant, config: ConfigType
) -> ConfigType:
    """Reject automations that refer to another integration's device."""
    config = TRIGGER_SCHEMA(config)
    _, entry = dr.async_get_device_and_config_entry_for_domain(
        hass, config[CONF_DEVICE_ID], domain=DOMAIN
    )
    if entry is None:
        raise InvalidDeviceAutomationConfig("Device is not a Triangles tracker")
    return config


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> list[dict]:
    _, entry = dr.async_get_device_and_config_entry_for_domain(
        hass, device_id, domain=DOMAIN
    )
    if entry is None:
        return []
    return [
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: trigger_type,
        }
        for trigger_type in SIDE_TRIGGER_TYPES
    ]


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Subscribe to side-change events for this device and face."""
    return await event_trigger.async_attach_trigger(
        hass,
        event_trigger.TRIGGER_SCHEMA(
            {
                CONF_PLATFORM: "event",
                event_trigger.CONF_EVENT_TYPE: EVENT_SIDE_CHANGED,
                event_trigger.CONF_EVENT_DATA: {
                    CONF_DEVICE_ID: config[CONF_DEVICE_ID],
                    CONF_TYPE: config[CONF_TYPE],
                },
            }
        ),
        action,
        trigger_info,
        platform_type="device",
    )

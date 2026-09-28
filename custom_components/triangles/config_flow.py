# SPDX-License-Identifier: Apache-2.0
"""Discover supported trackers using Home Assistant's Bluetooth API.

Config-flow patterns adapted from Home Assistant's LED BLE integration
(Apache-2.0). Triangles adds hardware matching and manual address entry.
See NOTICE and CREDITS.md for attribution.
"""

import re
from typing import Any

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN, ORIENTATION_SERVICE_UUID, default_tracker_name


def is_supported_tracker(info: bluetooth.BluetoothServiceInfoBleak) -> bool:
    """Match the known orientation service or advertised tracker name."""
    name = (info.name or "").lower()
    return info.connectable and (
        name.startswith(("timeular", "zei"))
        or ORIENTATION_SERVICE_UUID in (uuid.lower() for uuid in info.service_uuids)
    )


class TrianglesConfigFlow(ConfigFlow, domain=DOMAIN):
    """One config entry per physical tracker, identified by Bluetooth address."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: bluetooth.BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: bluetooth.BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        if not is_supported_tracker(discovery_info):
            return self.async_abort(reason="not_supported")
        await self.async_set_unique_id(discovery_info.address.upper())
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self.context["title_placeholders"] = {
            "name": default_tracker_name(discovery_info.address)
        }
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        assert self._discovery is not None
        if user_input is not None:
            return self.async_create_entry(
                title=default_tracker_name(self._discovery.address),
                data={CONF_ADDRESS: self._discovery.address.upper()},
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "name": default_tracker_name(self._discovery.address)
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="user", menu_options=["discovered", "manual"]
        )

    async def async_step_discovered(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        devices = {
            info.address.upper(): info
            for info in bluetooth.async_discovered_service_info(
                self.hass, connectable=True
            )
            if is_supported_tracker(info)
        }
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            if address in devices:
                return self.async_create_entry(
                    title=default_tracker_name(address), data={CONF_ADDRESS: address}
                )
        configured = self._async_current_ids()
        devices = {
            address: info
            for address, info in devices.items()
            if address not in configured
        }
        if not devices:
            return self.async_abort(reason="no_devices_found")
        return self.async_show_form(
            step_id="discovered",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: f"Timeular tracker ({address})"
                            for address in devices
                        }
                    )
                }
            ),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", address):
                errors[CONF_ADDRESS] = "invalid_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=default_tracker_name(address), data={CONF_ADDRESS: address}
                )
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): str}),
            errors=errors,
        )

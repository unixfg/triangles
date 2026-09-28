# SPDX-License-Identifier: Apache-2.0
"""Exercise discovery and manual configuration using Home Assistant flows."""

from types import SimpleNamespace

import pytest
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.triangles.config_flow import is_supported_tracker
from custom_components.triangles.const import DOMAIN

from .conftest import ADDRESS


@pytest.mark.parametrize("name", ["Timeular", "Timeular Tracker", "ZEI"])
def test_supported_advertised_names(name):
    """Recognize supported trackers by their Bluetooth advertisements."""
    assert is_supported_tracker(
        SimpleNamespace(name=name, connectable=True, service_uuids=[])
    )


async def test_bluetooth_discovery(hass, ble, discovery_info):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=discovery_info
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert result["description_placeholders"] == {"name": "Timeular tracker · EE:FF"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Timeular tracker · EE:FF"
    assert result["data"] == {"address": ADDRESS}
    assert result["result"].unique_id == ADDRESS
    await hass.async_block_till_done()


async def test_duplicate_discovery(hass, ble, entry, discovery_info):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=discovery_info
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_select_discovered(hass, ble):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "discovered"}
    )
    assert result["step_id"] == "discovered"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": ADDRESS}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Timeular tracker · EE:FF"
    await hass.async_block_till_done()


async def test_manual_address_rejects_macos_uuid(hass, ble):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": "11111111-2222-3333-4444-555555555555"}
    )
    assert result["errors"] == {"address": "invalid_address"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"address": f"  {ADDRESS.lower()}  "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Timeular tracker · EE:FF"
    assert result["data"] == {"address": ADDRESS}
    await hass.async_block_till_done()


async def test_no_devices(hass, ble):
    ble.discovered.return_value = []
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "discovered"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"

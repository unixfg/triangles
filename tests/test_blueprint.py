# SPDX-License-Identifier: Apache-2.0
"""Validate and execute the supplied scene-mapping blueprint inside HA."""

from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.components.automation.helpers import async_get_blueprints
from homeassistant.components.blueprint.models import Blueprint
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.triangles.blueprints import BLUEPRINT_PATH
from custom_components.triangles.const import DOMAIN, EVENT_SIDE_CHANGED

from .conftest import ADDRESS
from .test_integration import settle, setup_tracker


@pytest.fixture
def edited_blueprint(hass_config_dir):
    destination = Path(hass_config_dir) / "blueprints/automation" / BLUEPRINT_PATH
    destination.parent.mkdir(parents=True)
    source = (
        Path(__file__).resolve().parents[1]
        / "custom_components/triangles/blueprints/eight_scenes.yaml"
    )
    customized = source.read_text().replace(
        "Triangles — eight scenes", "My custom scene controller"
    )
    destination.write_text(customized)
    return destination, customized


@pytest.mark.parametrize("automation_loaded", [False, True])
async def test_setup_installs_discoverable_blueprint(
    hass, entry, ble, automation_loaded
):
    if automation_loaded:
        assert await async_setup_component(hass, "automation", {"automation": []})
        await hass.async_block_till_done()
    await setup_tracker(hass, entry, ble)
    blueprints = await async_get_blueprints(hass).async_get_blueprints()
    assert isinstance(blueprints[BLUEPRINT_PATH], Blueprint)
    assert blueprints[BLUEPRINT_PATH].validate() is None
    assert any(path.startswith("homeassistant/") for path in blueprints)
    assert hass.states.async_entity_ids("automation") == []


async def test_existing_blueprint_survives_setup_reload_and_second_tracker(
    hass, entry, ble, edited_blueprint
):
    destination, customized = edited_blueprint
    await setup_tracker(hass, entry, ble)
    assert await hass.async_add_executor_job(destination.read_text) == customized
    assert await hass.config_entries.async_reload(entry.entry_id)
    second_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AA:BB:CC:DD:EE:00",
        title="Second tracker",
        data={"address": "AA:BB:CC:DD:EE:00"},
    )
    second_entry.add_to_hass(hass)
    await setup_tracker(hass, second_entry, ble)
    assert await hass.async_add_executor_job(destination.read_text) == customized
    assert await hass.async_add_executor_job(
        lambda: list(destination.parent.glob("*.yaml"))
    ) == [destination]
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert await hass.config_entries.async_unload(second_entry.entry_id)
    assert await hass.async_add_executor_job(destination.read_text) == customized


async def test_install_failure_keeps_tracker_working(hass, entry, ble, caplog):
    with patch(
        "homeassistant.components.blueprint.models.DomainBlueprints.async_add_blueprint",
        side_effect=PermissionError("Blueprint directory is read-only"),
    ):
        tracker = await setup_tracker(hass, entry, ble)
    assert "Unable to install the scene blueprint" in caplog.text
    tracker.notify(2)
    await settle(hass)
    assert hass.states.get("sensor.timeular_current_side").state == "2"


@pytest.mark.parametrize("side", range(1, 9))
async def test_blueprint_activates_selected_scene_only(hass, entry, ble, side):
    tracker = await setup_tracker(hass, entry, ble)
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, ADDRESS), entry.entry_id
    )
    automation = {
        "alias": "Eight-scene controller",
        "use_blueprint": {
            "path": BLUEPRINT_PATH,
            "input": {"tracker": device.id, f"side_{side}": ["scene.focus"]},
        },
    }
    calls = []
    hass.services.async_register("scene", "turn_on", calls.append)
    assert await async_setup_component(hass, "automation", {"automation": automation})
    await hass.async_block_till_done()
    assert calls == []

    # Another controller must not activate this tracker's assigned scenes.
    hass.bus.async_fire(
        EVENT_SIDE_CHANGED,
        {"device_id": "another_tracker", "type": f"side_{side}"},
    )
    await hass.async_block_till_done()
    assert calls == []

    tracker.notify(0)
    tracker.notify(side)
    await settle(hass)
    assert len(calls) == 1
    assert calls[0].data["entity_id"] == ["scene.focus"]

    # An unassigned side has an empty selection and invokes no service.
    tracker.notify((side % 8) + 1)
    await settle(hass)
    assert len(calls) == 1

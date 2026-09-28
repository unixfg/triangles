# SPDX-License-Identifier: Apache-2.0
"""Validate and execute the supplied scene-mapping blueprint inside HA."""

from pathlib import Path

import pytest
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component
from homeassistant.util import yaml as yaml_util

from custom_components.triangles.const import DOMAIN, EVENT_SIDE_CHANGED

from .conftest import ADDRESS
from .test_integration import settle, setup_tracker

BLUEPRINT_PATH = (
    Path(__file__).resolve().parents[1]
    / "blueprints/automation/triangles/eight_scenes.yaml"
)


@pytest.mark.parametrize("side", range(1, 9))
async def test_blueprint_activates_selected_scene_only(hass, entry, ble, side):
    tracker = await setup_tracker(hass, entry, ble)
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, ADDRESS), entry.entry_id
    )
    data = await hass.async_add_executor_job(yaml_util.load_yaml, str(BLUEPRINT_PATH))
    blueprint = Blueprint(
        data, expected_domain="automation", schema=AUTOMATION_BLUEPRINT_SCHEMA
    )
    assert blueprint.validate() is None
    inputs = BlueprintInputs(
        blueprint,
        {
            "alias": "Eight-scene controller",
            "use_blueprint": {
                "path": "triangles/eight_scenes.yaml",
                "input": {"tracker": device.id, f"side_{side}": ["scene.focus"]},
            },
        },
    )
    inputs.validate()
    calls = []
    hass.services.async_register("scene", "turn_on", calls.append)
    assert await async_setup_component(
        hass, "automation", {"automation": inputs.async_substitute()}
    )
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

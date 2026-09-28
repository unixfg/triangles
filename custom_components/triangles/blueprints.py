# SPDX-License-Identifier: Apache-2.0
"""Make the bundled scene blueprint available in Home Assistant."""

import logging
from pathlib import Path

from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.automation.helpers import async_get_blueprints
from homeassistant.components.blueprint.errors import FileAlreadyExists
from homeassistant.components.blueprint.models import Blueprint
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import yaml as yaml_util

_LOGGER = logging.getLogger(__name__)
BLUEPRINT_PATH = "triangles/eight_scenes.yaml"
_BUNDLED_BLUEPRINT = Path(__file__).parent / "blueprints/eight_scenes.yaml"


async def async_install_blueprint(hass: HomeAssistant) -> None:
    """Add the blueprint without replacing an existing, possibly edited copy."""
    blueprints = async_get_blueprints(hass)
    try:
        # Automation populates its examples during setup. If it is not configured,
        # preserve those examples before creating the Triangles directory.
        if "automation" not in hass.config.components:
            await blueprints.async_populate()
        data = await hass.async_add_executor_job(
            yaml_util.load_yaml, str(_BUNDLED_BLUEPRINT)
        )
        blueprint = Blueprint(
            data, expected_domain="automation", schema=AUTOMATION_BLUEPRINT_SCHEMA
        )
        await blueprints.async_add_blueprint(
            blueprint, BLUEPRINT_PATH, allow_override=False
        )
    except FileAlreadyExists:
        pass
    except (OSError, HomeAssistantError) as err:
        # A blueprint write failure must not prevent device-trigger automations
        # from connecting to their trackers.
        _LOGGER.error("Unable to install the scene blueprint: %s", err)

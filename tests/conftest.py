# SPDX-License-Identifier: Apache-2.0
"""Home Assistant fixtures with simulated Bluetooth discovery and GATT I/O."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from bleak.backends.device import BLEDevice
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.triangles.const import DOMAIN, ORIENTATION_SERVICE_UUID

pytest_plugins = ["pytest_homeassistant_custom_component"]

ADDRESS = "AA:BB:CC:DD:EE:FF"


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    """Enable loading Triangles in the test Home Assistant instance."""


@pytest.fixture
def entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        title="Timeular",
        data={"address": ADDRESS},
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def discovery_info():
    return BluetoothServiceInfoBleak(
        name="Timeular",
        address=ADDRESS,
        rssi=-60,
        manufacturer_data={},
        service_data={},
        service_uuids=[ORIENTATION_SERVICE_UUID],
        source="00:11:22:33:44:55",
        device=BLEDevice(ADDRESS, "Timeular", {}),
        advertisement=Mock(),
        connectable=True,
        time=0,
        tx_power=None,
    )


class FakeTracker:
    """A GATT peer that can send notifications and drop connections."""

    def __init__(self, device, disconnected_callback, **kwargs):
        self.is_connected = False
        self.is_retry_client = kwargs.get("_is_retry_client", False)
        self.on_disconnect = disconnected_callback
        self.on_notify = None
        self.side = 1
        self.characteristic = SimpleNamespace(properties=["read", "indicate"])
        self.services = Mock()
        self.services.get_characteristic.return_value = self.characteristic
        self.connect = AsyncMock(side_effect=self._connect)
        self.disconnect = AsyncMock(side_effect=self._disconnect)
        self.read_gatt_char = AsyncMock(side_effect=lambda _: bytearray([self.side]))
        self.start_notify = AsyncMock(side_effect=self._subscribe)

    async def _connect(self, **kwargs):
        self.is_connected = True

    async def _disconnect(self):
        self.is_connected = False

    async def _subscribe(self, characteristic, callback):
        self.on_notify = callback

    def notify(self, side):
        self.side = side
        self.on_notify(self.characteristic, bytearray([side]))

    def drop(self):
        self.is_connected = False
        self.on_disconnect(self)


@pytest.fixture
def ble(hass, discovery_info):
    """Replace Bluetooth discovery and GATT clients with in-process fakes."""
    hass.config.components.update({"bluetooth", "bluetooth_adapters"})
    clients = []

    def create_client(*args, **kwargs):
        client = FakeTracker(*args, **kwargs)
        clients.append(client)
        return client

    with (
        patch(
            "custom_components.triangles.coordinator.BleakClientWithServiceCache",
            side_effect=create_client,
        ) as factory,
        patch(
            "homeassistant.components.bluetooth.async_ble_device_from_address",
            return_value=discovery_info.device,
        ) as lookup,
        patch(
            "homeassistant.components.bluetooth.async_register_callback",
            return_value=Mock(),
        ) as register,
        patch(
            "homeassistant.components.bluetooth.async_discovered_service_info",
            return_value=[discovery_info],
        ) as discovered,
    ):
        yield SimpleNamespace(
            clients=clients,
            factory=factory,
            lookup=lookup,
            register=register,
            discovered=discovered,
        )

# SPDX-License-Identifier: Apache-2.0
"""Maintain a GATT connection and publish settled orientation changes."""

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from functools import partial

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.exc import BleakError
from bleak_retry_connector import (
    BLEAK_RETRY_EXCEPTIONS,
    BleakClientWithServiceCache,
    establish_connection,
)
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONNECT_TIMEOUT,
    DOMAIN,
    EVENT_SIDE_CHANGED,
    GATT_TIMEOUT,
    MAX_RETRY_SECONDS,
    ORIENTATION_CHARACTERISTIC_UUID,
    RETRY_SECONDS,
    SETTLE_SECONDS,
    parse_side,
)

_LOGGER = logging.getLogger(__name__)
# Transport shutdowns can surface as EOFError/AttributeError rather than
# BleakError. BlueZ service rediscovery can also temporarily raise KeyError.
_CONNECTION_ERRORS = (*BLEAK_RETRY_EXCEPTIONS, OSError, KeyError, ValueError)


@dataclass(frozen=True)
class TrianglesState:
    """The current connection and settled orientation."""

    connected: bool = False
    side: int | None = None


class TrianglesCoordinator(DataUpdateCoordinator[TrianglesState]):
    """Manage a tracker's Bluetooth connection and orientation updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, config_entry=entry, always_update=False
        )
        self.entry = entry
        self.address: str = entry.data[CONF_ADDRESS]
        self.data = TrianglesState()
        self._client: BleakClient | None = None
        self._task: asyncio.Task | None = None
        self._cancel_discovery: CALLBACK_TYPE | None = None
        self._settle_timer: asyncio.TimerHandle | None = None
        self._discovered = asyncio.Event()
        self._disconnected = asyncio.Event()
        self._stopping = False
        self._ready = False
        self._raw_side: int | None = None
        self._stable_side: int | None = None
        self.connection_stage = "not started"
        self.connection_cycles = 0
        self.last_error: dict[str, str] | None = None

    @property
    def worker_running(self) -> bool:
        """Return whether the reconnect task is still active."""
        return self._task is not None and not self._task.done()

    @callback
    def async_start(self) -> None:
        """Listen for the selected tracker and connect in the background."""
        self._cancel_discovery = bluetooth.async_register_callback(
            self.hass,
            self._async_discovered,
            {"address": self.address, "connectable": True},
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
        self._task = self.entry.async_create_background_task(
            self.hass, self._async_run(), f"Triangles {self.address}"
        )

    @callback
    def _async_discovered(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        self._discovered.set()

    async def async_stop(self, event: Event | None = None) -> None:
        """Cancel reconnection and release Bluetooth on unload or shutdown."""
        self._stopping = True
        if self._cancel_discovery:
            self._cancel_discovery()
            self._cancel_discovery = None
        self._async_reset()
        if task := self._task:
            self._task = None
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        self.connection_stage = "stopped"

    async def _async_run(self) -> None:
        """Reconnect using Home Assistant discovery and capped backoff."""
        retry_delay = RETRY_SECONDS
        reported_error = False
        while not self._stopping:
            self._discovered.clear()
            client: BleakClient | None = None
            self._disconnected.clear()
            self.connection_stage = "Bluetooth discovery"
            try:
                device = bluetooth.async_ble_device_from_address(
                    self.hass, self.address, connectable=True
                )
                if device is None:
                    self.connection_stage = "waiting for discovery"
                    with suppress(TimeoutError):
                        await asyncio.wait_for(
                            self._discovered.wait(), MAX_RETRY_SECONDS
                        )
                    continue
                self.connection_stage = "connection establishment"
                self.connection_cycles += 1
                # Each connector attempt has its own timeout. An outer timeout
                # would cut short retries after a slow or failed connection.
                client = self._client = await establish_connection(
                    BleakClientWithServiceCache,
                    device,
                    self.entry.title,
                    disconnected_callback=self._async_disconnected,
                    timeout=CONNECT_TIMEOUT,
                )
                self.connection_stage = "orientation characteristic discovery"
                characteristic = client.services.get_characteristic(
                    ORIENTATION_CHARACTERISTIC_UUID
                )
                if characteristic is None:
                    raise BleakError(
                        "Tracker does not expose orientation characteristic "
                        f"{ORIENTATION_CHARACTERISTIC_UUID}"
                    )
                if not {"notify", "indicate"}.intersection(characteristic.properties):
                    raise BleakError(
                        "Triangles side characteristic has no notifications"
                    )
                async with asyncio.timeout(GATT_TIMEOUT):
                    if "read" in characteristic.properties:
                        self.connection_stage = "initial orientation read"
                        self._prime(
                            parse_side(await client.read_gatt_char(characteristic))
                        )
                    self.connection_stage = "orientation subscription"
                    await client.start_notify(
                        characteristic,
                        partial(self._async_notification, client),
                    )
                if not client.is_connected or self._disconnected.is_set():
                    raise BleakError("Tracker disconnected during setup")
                self._ready = True
                self.connection_stage = "connected"
                self.async_set_updated_data(TrianglesState(True, self._stable_side))
                if reported_error:
                    _LOGGER.info("Reconnected to Triangles %s", self.address)
                reported_error = False
                retry_delay = RETRY_SECONDS
                # Some backends can lose a disconnect callback. Check their
                # connection flag too, without polling the tracker's side.
                while client.is_connected and not self._disconnected.is_set():
                    with suppress(TimeoutError):
                        await asyncio.wait_for(self._disconnected.wait(), 30)
            except _CONNECTION_ERRORS as err:
                error = " ".join(str(err).split()) or type(err).__name__
                self.last_error = {
                    "stage": self.connection_stage,
                    "type": type(err).__name__,
                    "message": error,
                }
                if not reported_error:
                    _LOGGER.warning(
                        "Cannot connect to Triangles %s during %s: %s; will retry",
                        self.address,
                        self.connection_stage,
                        error,
                    )
                    reported_error = True
                else:
                    _LOGGER.debug(
                        "Triangles %s failed during %s: %s",
                        self.address,
                        self.connection_stage,
                        error,
                        exc_info=True,
                    )
            finally:
                self._async_reset()
                # Ignore callbacks from this session as soon as cleanup begins.
                self._client = None
                if client is not None:
                    try:
                        async with asyncio.timeout(10):
                            await client.disconnect()
                    except _CONNECTION_ERRORS:
                        _LOGGER.debug(
                            "Error releasing Triangles connection", exc_info=True
                        )
            if not self._stopping:
                self.connection_stage = "waiting to retry"
                # A tracker may advertise only briefly after waking. A fresh
                # discovery should interrupt the delay before it sleeps again.
                with suppress(TimeoutError):
                    await asyncio.wait_for(self._discovered.wait(), retry_delay)
                retry_delay = min(retry_delay * 2, MAX_RETRY_SECONDS)

    @callback
    def _async_disconnected(self, client: BleakClient) -> None:
        """Mark disconnected and cancel any pending side-change event."""
        if client is self._client:
            self._async_reset()
            self._disconnected.set()

    @callback
    def _async_reset(self) -> None:
        self._cancel_settle()
        self._ready = False
        self._raw_side = self._stable_side = None
        self.async_set_updated_data(TrianglesState())

    @callback
    def _cancel_settle(self) -> None:
        if self._settle_timer:
            self._settle_timer.cancel()
            self._settle_timer = None

    @callback
    def _prime(self, side: int) -> None:
        """Set the initial orientation without emitting a side-change event."""
        self._raw_side = self._stable_side = side

    @callback
    def _async_notification(
        self,
        client: BleakClient,
        sender: BleakGATTCharacteristic,
        data: bytearray,
    ) -> None:
        """Ignore invalid/duplicate packets and settle the final orientation."""
        if self._stopping or client is not self._client or not client.is_connected:
            return
        try:
            side = parse_side(data)
        except ValueError:
            _LOGGER.debug("Ignoring invalid Triangles orientation: %s", data.hex())
            return
        if not self._ready or self._stable_side is None:
            self._prime(side)
            if self._ready:
                self.async_set_updated_data(TrianglesState(True, side))
            return
        if side == self._raw_side:
            return
        self._raw_side = side
        self._cancel_settle()
        if side == 0:
            self._stable_side = 0
            self.async_set_updated_data(TrianglesState(True, 0))
        elif side != self._stable_side:
            self._settle_timer = self.hass.loop.call_later(
                SETTLE_SECONDS, self._async_settled, client, side
            )

    @callback
    def _async_settled(self, client: BleakClient, side: int) -> None:
        """Publish exactly one event for a stable new face."""
        self._settle_timer = None
        if (
            self._stopping
            or not self._ready
            or client is not self._client
            or not client.is_connected
            or side != self._raw_side
        ):
            return
        previous_side = self._stable_side
        self._stable_side = side
        self.async_set_updated_data(TrianglesState(True, side))
        device = dr.async_get(self.hass).async_get_device_by_identifier(
            (DOMAIN, self.address), self.entry.entry_id
        )
        if device:
            self.hass.bus.async_fire(
                EVENT_SIDE_CHANGED,
                {
                    "device_id": device.id,
                    "type": f"side_{side}",
                    "side": side,
                    "previous_side": previous_side,
                },
            )

# SPDX-License-Identifier: Apache-2.0
"""Check HA entities, scene triggers, settling, and Bluetooth lifecycle."""

import asyncio
from unittest.mock import patch

import pytest
from bleak.exc import BleakError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from custom_components.triangles.const import DOMAIN, EVENT_SIDE_CHANGED
from custom_components.triangles.device_trigger import async_get_triggers

from .conftest import ADDRESS


async def setup_tracker(hass, entry, ble):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert ble.clients
    assert entry.runtime_data.data.connected
    return ble.clients[-1]


async def settle(hass):
    await asyncio.sleep(0.35)
    await hass.async_block_till_done()


async def test_device_entities_and_initial_read(hass, entry, ble):
    events = []
    hass.bus.async_listen(EVENT_SIDE_CHANGED, events.append)
    tracker = await setup_tracker(hass, entry, ble)
    assert hass.states.get("sensor.timeular_current_side").state == "1"
    assert hass.states.get("binary_sensor.timeular_bluetooth_connection").state == "on"
    assert hass.states.get("event.timeular_side_changed").state == "unknown"
    assert events == []
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, ADDRESS), entry.entry_id
    )
    assert device.manufacturer == "Timeular"
    assert len(await async_get_triggers(hass, device.id)) == 8
    assert await async_get_triggers(hass, "nonexistent") == []
    assert tracker.read_gatt_char.await_count == 1


async def test_default_name_update_preserves_device_and_entity_ids(hass, entry, ble):
    hass.config_entries.async_update_entry(entry, title="8-sided tracker · EE:FF")
    devices = dr.async_get(hass)
    original_device = devices.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, ADDRESS)},
        name=entry.title,
    )
    devices.async_update_device(original_device.id, name_by_user="Office controller")
    original_sensor = er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{ADDRESS}_current_side",
        config_entry=entry,
        suggested_object_id="desk_tracker_side",
    )
    await setup_tracker(hass, entry, ble)
    device = devices.async_get_device_by_identifier((DOMAIN, ADDRESS), entry.entry_id)
    assert entry.title == "Timeular tracker · EE:FF"
    assert device.id == original_device.id
    assert device.name_by_user == "Office controller"
    assert hass.states.get(original_sensor.entity_id).state == "1"


@pytest.mark.parametrize("title", ["Study scenes", "Timeular CR2032", "Timeular"])
async def test_custom_entry_names_are_preserved(hass, entry, ble, title):
    hass.config_entries.async_update_entry(entry, title=title)
    await setup_tracker(hass, entry, ble)
    assert entry.title == title


@pytest.mark.parametrize("side", range(1, 9))
async def test_each_face_works_with_device_automation(hass, entry, ble, side):
    tracker = await setup_tracker(hass, entry, ble)
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, ADDRESS), entry.entry_id
    )
    actions = []
    hass.bus.async_listen("test_scene_activated", actions.append)
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "alias": "Triangles scene test",
                "triggers": [
                    {
                        "trigger": "device",
                        "domain": DOMAIN,
                        "device_id": device.id,
                        "type": f"side_{side}",
                    }
                ],
                "actions": [{"event": "test_scene_activated"}],
            }
        },
    )
    await hass.async_block_till_done()
    # Neutral permits re-selecting side 1, which was the initial face.
    tracker.notify(0)
    tracker.notify(side)
    tracker.notify(side)
    await settle(hass)
    assert len(actions) == 1
    assert hass.states.get("sensor.timeular_current_side").state == str(side)
    assert (
        hass.states.get("event.timeular_side_changed").attributes["event_type"]
        == f"side_{side}"
    )
    # Duplicate notifications must not activate the scene again.
    tracker.notify(side)
    await settle(hass)
    assert len(actions) == 1


async def test_intermediate_faces_and_invalid_data(hass, entry, ble):
    events = []
    hass.bus.async_listen(EVENT_SIDE_CHANGED, events.append)
    tracker = await setup_tracker(hass, entry, ble)
    tracker.notify(2)
    tracker.notify(3)
    tracker.on_notify(tracker.characteristic, bytearray([255]))
    await settle(hass)
    assert [event.data["side"] for event in events] == [3]
    tracker.notify(4)
    tracker.notify(3)
    await settle(hass)
    assert len(events) == 1


async def test_disconnect_cancels_pending_scene_and_reconnect_primes(hass, entry, ble):
    events = []
    hass.bus.async_listen(EVENT_SIDE_CHANGED, events.append)
    with patch("custom_components.triangles.coordinator.RETRY_SECONDS", 0.01):
        tracker = await setup_tracker(hass, entry, ble)
        tracker.notify(2)
        tracker.drop()
        assert entry.runtime_data.data.connected is False
        assert hass.states.get("sensor.timeular_current_side").state == "unavailable"
        await settle(hass)
        assert len(ble.clients) == 2
        assert ble.clients[-1] is not tracker
        assert entry.runtime_data.data.connected
        assert events == []
        # Late packets from the old client must never affect the new session.
        tracker.is_connected = True
        tracker.notify(7)
        await settle(hass)
        assert events == []
        ble.clients[-1].notify(8)
        await settle(hass)
        assert [event.data["side"] for event in events] == [8]


async def test_unload_cancels_pending_scene_and_releases_connection(hass, entry, ble):
    events = []
    hass.bus.async_listen(EVENT_SIDE_CHANGED, events.append)
    tracker = await setup_tracker(hass, entry, ble)
    coordinator = entry.runtime_data
    tracker.notify(2)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await settle(hass)
    assert events == []
    tracker.disconnect.assert_awaited_once()
    ble.register.return_value.assert_called_once()
    assert coordinator._task is None


async def test_offline_setup_then_discovery(hass, entry, ble, discovery_info):
    ble.lookup.return_value = None
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert not ble.clients
    assert hass.states.get("binary_sensor.timeular_bluetooth_connection").state == "off"
    ble.lookup.return_value = discovery_info.device
    discovered_callback = ble.register.call_args.args[1]
    discovered_callback(discovery_info, None)
    await hass.async_block_till_done()
    assert entry.runtime_data.data.connected


@pytest.mark.parametrize("discovery_during_cleanup", [False, True])
async def test_discovery_interrupts_reconnect_backoff(
    hass, entry, ble, discovery_info, discovery_during_cleanup
):
    create_client = ble.factory.side_effect
    released = asyncio.Event()
    subscribed = asyncio.Event()

    def retry_client(*args, **kwargs):
        client = create_client(*args, **kwargs)
        if len(ble.clients) == 1:
            client.start_notify.side_effect = BleakError("not ready")

            async def disconnect():
                await client._disconnect()
                if discovery_during_cleanup:
                    ble.register.call_args.args[1](discovery_info, None)
                released.set()

            client.disconnect.side_effect = disconnect
        else:

            async def subscribe(characteristic, callback):
                await client._subscribe(characteristic, callback)
                subscribed.set()

            client.start_notify.side_effect = subscribe
        return client

    ble.factory.side_effect = retry_client
    with patch("custom_components.triangles.coordinator.RETRY_SECONDS", 60):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await asyncio.wait_for(released.wait(), 1)
        if not discovery_during_cleanup:
            assert entry.runtime_data.connection_stage == "waiting to retry"
            ble.register.call_args.args[1](discovery_info, None)
        await asyncio.wait_for(subscribed.wait(), 1)
        assert entry.runtime_data.data.connected
        assert entry.runtime_data.connection_cycles == 2


async def test_discovery_error_does_not_stop_reconnect_worker(
    hass, entry, ble, discovery_info
):
    ble.lookup.side_effect = [KeyError("adapter vanished"), discovery_info.device]
    with patch("custom_components.triangles.coordinator.RETRY_SECONDS", 0.01):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await settle(hass)
        assert entry.runtime_data.worker_running
        assert entry.runtime_data.data.connected
        assert entry.runtime_data.last_error == {
            "stage": "Bluetooth discovery",
            "type": "KeyError",
            "message": "'adapter vanished'",
        }


@pytest.mark.parametrize(
    "error", [BleakError("busy"), EOFError("transport closed"), TimeoutError()]
)
async def test_connector_recovers_transient_connection_failures(
    hass, entry, ble, error
):
    """Exercise the real retry connector with only the Bluetooth client faked."""
    create_client = ble.factory.side_effect
    subscribed = asyncio.Event()

    def transient_client(*args, **kwargs):
        client = create_client(*args, **kwargs)

        async def connect(**kwargs):
            if client.connect.await_count == 1:
                raise error
            await client._connect(**kwargs)

        async def subscribe(characteristic, callback):
            await client._subscribe(characteristic, callback)
            subscribed.set()

        client.connect.side_effect = connect
        client.start_notify.side_effect = subscribe
        return client

    ble.factory.side_effect = transient_client
    events = []
    hass.bus.async_listen(EVENT_SIDE_CHANGED, events.append)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await asyncio.wait_for(subscribed.wait(), 3)
    await hass.async_block_till_done()
    assert len(ble.clients) == 1
    assert ble.clients[0].is_retry_client
    assert ble.clients[0].connect.await_count == 2
    assert entry.runtime_data.data.connected
    assert events == []


async def test_exhausted_connector_retries_start_a_new_session(
    hass, entry, ble, caplog
):
    create_client = ble.factory.side_effect
    subscribed = asyncio.Event()

    def failing_client(*args, **kwargs):
        client = create_client(*args, **kwargs)
        if len(ble.clients) == 1:
            client.connect.side_effect = BleakError("busy")
        else:

            async def subscribe(characteristic, callback):
                await client._subscribe(characteristic, callback)
                subscribed.set()

            client.start_notify.side_effect = subscribe
        return client

    ble.factory.side_effect = failing_client
    with patch("custom_components.triangles.coordinator.RETRY_SECONDS", 0.01):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await asyncio.wait_for(subscribed.wait(), 3)
        assert len(ble.clients) == 2
        assert ble.clients[0].connect.await_count > 1
        assert entry.runtime_data.data.connected
        assert "during connection establishment" in caplog.text
        assert "busy" in caplog.text


async def test_gatt_timeout_reports_stage_and_exception(hass, entry, ble, caplog):
    create_client = ble.factory.side_effect

    def blocked_read_client(*args, **kwargs):
        client = create_client(*args, **kwargs)
        if len(ble.clients) == 1:

            async def blocked_read(characteristic):
                await asyncio.Event().wait()

            client.read_gatt_char.side_effect = blocked_read
        return client

    ble.factory.side_effect = blocked_read_client
    with (
        patch("custom_components.triangles.coordinator.GATT_TIMEOUT", 0.01),
        patch("custom_components.triangles.coordinator.RETRY_SECONDS", 0.01),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await settle(hass)
        assert (
            "during initial orientation read: TimeoutError; will retry" in caplog.text
        )
        assert entry.runtime_data.data.connected
        ble.clients[0].disconnect.assert_awaited_once()


@pytest.mark.parametrize("stage", ["read", "subscribe", "uuid"])
async def test_failed_connection_setup_releases_client_and_retries(
    hass, entry, ble, stage
):
    """Release a client after GATT setup fails and reconnect with a new client."""
    create_client = ble.factory.side_effect

    def fail_first_client(*args, **kwargs):
        client = create_client(*args, **kwargs)
        if len(ble.clients) == 1:
            if stage == "read":
                client.read_gatt_char.side_effect = BleakError("read failed")
            elif stage == "subscribe":
                client.start_notify.side_effect = BleakError("subscribe failed")
            else:
                client.services.get_characteristic.return_value = None
        return client

    ble.factory.side_effect = fail_first_client
    events = []
    hass.bus.async_listen(EVENT_SIDE_CHANGED, events.append)
    with patch("custom_components.triangles.coordinator.RETRY_SECONDS", 0.01):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await settle(hass)
        assert len(ble.clients) == 2
        ble.clients[0].disconnect.assert_awaited_once()
        assert entry.runtime_data.data.connected
        assert events == []


async def test_unload_during_connection(hass, entry, ble):
    create_client = ble.factory.side_effect
    connecting = asyncio.Event()
    cancelled = asyncio.Event()

    async def blocked_connect(**kwargs):
        connecting.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    def blocked_client(*args, **kwargs):
        client = create_client(*args, **kwargs)
        client.connect.side_effect = blocked_connect
        return client

    ble.factory.side_effect = blocked_client
    assert await hass.config_entries.async_setup(entry.entry_id)
    await asyncio.wait_for(connecting.wait(), 1)
    coordinator = entry.runtime_data
    assert not coordinator.data.connected
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert cancelled.is_set()
    assert coordinator._task is None
    assert coordinator._client is None
    assert len(ble.clients) == 1


async def test_notification_only_tracker_primes_without_scene(hass, entry, ble):
    create_client = ble.factory.side_effect

    def notification_only_client(*args, **kwargs):
        client = create_client(*args, **kwargs)
        client.characteristic.properties = ["indicate"]
        return client

    ble.factory.side_effect = notification_only_client
    events = []
    hass.bus.async_listen(EVENT_SIDE_CHANGED, events.append)
    tracker = await setup_tracker(hass, entry, ble)
    tracker.read_gatt_char.assert_not_awaited()
    tracker.notify(3)
    await settle(hass)
    assert events == []
    assert hass.states.get("sensor.timeular_current_side").state == "3"
    tracker.notify(4)
    await settle(hass)
    assert [event.data["side"] for event in events] == [4]

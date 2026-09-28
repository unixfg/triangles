# Triangles

Triangles turns your Timeular into a scene controller.
This custom Home Assistant integration connects to compatible Timeular/ZEI
trackers over Bluetooth LE and triggers scenes when you change the upward-facing
side.

Devices appear as **Timeular tracker · EE:FF**, using the Bluetooth address suffix
to distinguish multiple trackers. You can rename each device to match its room
or purpose.

Triangles runs locally through Home Assistant's Bluetooth integration. No
vendor account or companion app is required.

Requires **Home Assistant Core 2026.9.4 or newer** and a working Bluetooth adapter
or proxy that supports active connections. Trackers must expose the orientation
characteristic described in [Protocol references](#protocol-references).
Automated tests simulate Bluetooth hardware; compatibility across all tracker
models and firmware versions is not verified.

## Hardware

I've tested with the coin cell version, but
the newer USB-C rechargeable trackers have much better signal.

If entering an address manually, use the Bluetooth MAC address shown by
**Home Assistant**, in `AA:BB:CC:DD:EE:FF` form. Manual setup can be
completed while the tracker is offline; the connection retries in the background.

## Assign scenes

1. In **Settings → Automations & scenes → Blueprints**, find
   **Triangles — eight scenes** and create an automation from it.
2. Select your Timeular tracker.
3. Select the scene for each side you want to use. Empty sides do nothing.
4. Save the automation, then flip the tracker to test it.

If the blueprint does not appear, reload automations or restart Home Assistant
after copying it. View **Current side** while turning the tracker to identify
its internal side numbers, then label the faces to match. No face-to-number
mapping is assumed from how the tracker looks.

You can also use the normal automation editor: **Add trigger → Device →
your tracker → Side 1 facing up**, then **Add action → Activate a scene**.
Repeat for other sides, or use any action instead of a scene.

Example device automation (replace the device ID and scene):

```yaml
alias: Triangles - focus lighting
triggers:
  - trigger: device
    domain: triangles
    device_id: YOUR_TRIANGLES_DEVICE_ID
    type: side_1
actions:
  - action: scene.turn_on
    target:
      entity_id: scene.focus
mode: restart
```

## Behavior

- One Home Assistant device with **Current side**, **Bluetooth connection**, and
  **Side changed** entities, plus eight named device triggers.
- A new side must remain unchanged for **300 ms** before firing. Brief
  intermediate faces and duplicate notifications do not produce extra events.
- The initial orientation after startup or reconnect establishes a baseline.
  It **does not activate a scene**. Flips made while disconnected are not replayed.
- Side `0` represents no active face and does not activate a scene. If the
  tracker reports `0`, placing it back on a numbered face can trigger that face
  again. Stand/neutral reporting depends on the tracker's firmware.
- A lost connection immediately makes the current-side entity unavailable and
  cancels any pending scene event. Connections retry automatically, with up to
  60 seconds between failed connection cycles. A new Bluetooth discovery
  interrupts this delay so the integration can reconnect to a waking tracker.
- An active connection occupies a Bluetooth connection slot. Other applications
  connected to the tracker may prevent Home Assistant from connecting.
- Side events are also available as `triangles_side_changed`, with `device_id`,
  `type` (`side_1`–`side_8`), `side`, and `previous_side` fields. For automations,
  prefer the supplied blueprint or device triggers: ordinary sensor state
  triggers can also fire when a sensor recovers from `unavailable`.

## Troubleshooting

If a tracker is not discovered or stays disconnected, check its battery,
Bluetooth range, and whether another app is connected to it. The Bluetooth
adapter or proxy must support active connections.

**Side changed** shows the time of the last side-change event. Its state is
unknown until the first flip after setup; unavailable means the Bluetooth
connection is down.

Enable debug logging for **Triangles** and inspect **Settings → System → Logs**
for connection errors. Each error identifies the failed stage, such as
connection establishment or the initial orientation read. A missing orientation
characteristic may indicate incompatible firmware or incomplete service
discovery.

When reporting a problem, include the relevant log messages, Home Assistant
version, tracker model or battery type, and firmware version if known.
Use **Download diagnostics** from the Triangles integration entry's menu to
capture connection state, reconnect-worker status, and the most recent failure.
The diagnostic snapshot omits device names and Bluetooth addresses.

## Development

Python 3.14.2 or newer is required for the Home Assistant 2026.9.4 test harness.

```sh
uv venv --python 3.14
uv pip install -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/ruff check custom_components tests scripts
.venv/bin/ruff format --check custom_components tests scripts
python3 scripts/package.py
```

Tests run Home Assistant config flows, entity/device registration, device
automations, and blueprints with simulated Bluetooth I/O and scene actions.

`scripts/package.py` creates `dist/triangles-<version>.zip` for manual installation.
Generated archives and development environments are excluded from Git.

GitHub Actions run tests, lint/format checks, ZIP packaging, Hassfest, and HACS
validation. Version tags matching the manifest trigger an automatic GitHub
Release with the installation ZIP attached after all checks pass. Maintainer
instructions are in [Publishing and CI](docs/PUBLISHING.md).

## Protocol references

Triangles subscribes to characteristic
`c7e70012-c847-11e6-8175-8c89a55d403c` in service
`c7e70010-c847-11e6-8175-8c89a55d403c` and reads the initial value when supported.
Orientation packets contain one byte: `1`–`8` identify a face, and `0` means no
active face.

- [timeular-linux Bluetooth implementation](https://github.com/cschomburg/timeular-linux/blob/master/bluetooth_manager.go)
- [timeular-python Bluetooth implementation](https://github.com/lemariva/timeular-python/blob/master/classes/bluetooth_backend.py)
- [Home Assistant Bluetooth APIs](https://developers.home-assistant.io/docs/core/bluetooth/api/)
- [Home Assistant device triggers](https://developers.home-assistant.io/docs/device_automation_trigger/)

Full source credits, exact revisions, and the license notes are in
[CREDITS.md](custom_components/triangles/CREDITS.md). The integration includes its
license and third-party notices so they also travel with HACS downloads and ZIPs.

Triangles is released under the [Apache 2.0 license](LICENSE). It is an
independent community integration, unaffiliated with Timeular or EARLY.

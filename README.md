# Triangles

Triangles turns your Timeular into a scene controller.
This custom Home Assistant integration connects to compatible Timeular/ZEI
trackers over Bluetooth LE and triggers scenes when you change the upward-facing
side.

Devices appear as **8-sided tracker · EE:FF**, using the Bluetooth address suffix
to distinguish multiple trackers. You can rename each device to match its room
or purpose.

Triangles runs locally through Home Assistant's Bluetooth integration. No
vendor account or companion app is required.

Requires **Home Assistant Core 2026.9.4 or newer** and a working Bluetooth adapter
or proxy that supports active connections. Trackers must expose the orientation
characteristic described in [Protocol references](#protocol-references).
Automated tests simulate Bluetooth hardware; compatibility across all tracker
models and firmware versions is not verified.

## Install with HACS

1. Open **HACS → ⋮ → Custom repositories**.
2. Enter `https://github.com/unixfg/triangles` and choose **Integration**.
3. Add it, then find **Triangles** in HACS and download it.
4. Restart Home Assistant Core.
5. Go to **Settings → Devices & services** and configure the discovered tracker,
   or choose **Add integration → Triangles**.

**Import the blueprint separately.** HACS downloads `custom_components/triangles`;
it does not install this repository's `blueprints` directory. Open
**Settings → Automations & scenes → Blueprints → Import blueprint**, and paste
the GitHub file URL for
[`blueprints/automation/triangles/eight_scenes.yaml`](https://github.com/unixfg/triangles/blob/main/blueprints/automation/triangles/eight_scenes.yaml).
You can also copy that YAML file manually as described below.

## Install manually

1. Make sure Home Assistant's **Bluetooth** integration is working and the
   tracker is within range of its adapter or proxy. Close any other application
   connected to the tracker, then turn the tracker on.
2. Copy the `custom_components/triangles` directory to
   `/config/custom_components/triangles` on Home Assistant. Create
   `custom_components` if necessary. The resulting path must be
   `/config/custom_components/triangles/manifest.json`.
3. Copy `blueprints/automation/triangles/eight_scenes.yaml` to
   `/config/blueprints/automation/triangles/eight_scenes.yaml`.
4. Restart **Home Assistant Core** from its system controls. Copying files alone
   does not load a new custom integration.
5. Open **Settings → Devices & services**. Configure the discovered tracker,
   or choose **Add integration → Triangles → Choose a nearby tracker**.
6. Open the new device. Its **Bluetooth connection** should be connected and
   **Current side** should change as you flip it.

Download `triangles-<version>.zip` from
[GitHub Releases](https://github.com/unixfg/triangles/releases). The ZIP contains
both directory trees. Extract it into Home Assistant's configuration directory
(`/config`), preserving other integrations
and blueprints. Back up an existing `triangles` directory before replacing it.
Home Assistant supplies the Python dependencies.

If entering an address manually, use the Bluetooth MAC address shown by
**Home Assistant**, in `AA:BB:CC:DD:EE:FF` form. macOS normally reports a UUID
instead; that identifier cannot be used as a Bluetooth MAC address. Manual setup
can be completed while the tracker is offline; the connection retries in the
background.

## Assign scenes

1. In **Settings → Automations & scenes → Blueprints**, find
   **Triangles — eight scenes** and create an automation from it.
2. Select your 8-sided tracker device.
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
  60 seconds between failed connection cycles.
- An active connection occupies a Bluetooth connection slot. Other applications
  connected to the tracker may prevent Home Assistant from connecting.
- Side events are also available as `triangles_side_changed`, with `device_id`,
  `type` (`side_1`–`side_8`), `side`, and `previous_side` fields. For automations,
  prefer the supplied blueprint or device triggers: ordinary sensor state
  triggers can also fire when a sensor recovers from `unavailable`.

## Verify operation

1. Confirm the device connects and reports a side.
2. Flip slowly through all eight faces and record their numbers.
3. Assign one existing scene to one side and test a deliberate flip.
4. Turn the tracker off and on. It should reconnect without activating a scene;
   the next deliberate flip should work.
5. Restart Home Assistant and check the same behavior.

## Troubleshooting

If a tracker is not discovered or stays disconnected, check its battery,
Bluetooth range, and whether another app is connected to it. The Bluetooth
adapter or proxy must support active connections.

Enable debug logging for **Triangles** and inspect **Settings → System → Logs**
for connection errors. Each error identifies the failed stage, such as
connection establishment or the initial orientation read. A missing orientation
characteristic may indicate incompatible firmware or incomplete service
discovery.

When reporting a problem, include the relevant log messages, Home Assistant
version, tracker model or battery type, and firmware version if known.

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

# Sources, attribution, and licenses

Triangles is licensed under [Apache 2.0](LICENSE). The protocol references and
adapted Home Assistant code are credited below, with their source revisions and
license locations.

## Bluetooth protocol references

### Constantin Schomburg and Kris Buist — Linux tracker client

- Source: [`cschomburg/timeular-linux`](https://github.com/cschomburg/timeular-linux)
- Revision: `e0fe64052dd94acbf7130588535a8d6fd50b7e4c`
- Consulted file: [`bluetooth_manager.go`](https://github.com/cschomburg/timeular-linux/blob/e0fe64052dd94acbf7130588535a8d6fd50b7e4c/bluetooth_manager.go)
- License: MIT; the full upstream copyright notice and license are retained in
  [`licenses/MIT-linux-client.txt`](licenses/MIT-linux-client.txt).

Protocol reference for the orientation service and characteristic UUIDs,
single-byte side values, and subscriptions.

### LeMaRiva — Python tracker client

- Source: [`lemariva/timeular-python`](https://github.com/lemariva/timeular-python)
- Revision: `aab3438891e9093e8a0d2eca8c38fad111effd37`
- Consulted file: [`classes/bluetooth_backend.py`](https://github.com/lemariva/timeular-python/blob/aab3438891e9093e8a0d2eca8c38fad111effd37/classes/bluetooth_backend.py)
- License: [Apache 2.0](LICENSE).

Protocol reference for GATT UUIDs and indication-based updates.

### Zack Dawood — Node.js tracker client

- Source: [`zackria/timeularapi`](https://github.com/zackria/timeularapi)
- Revision: `fa79b11184cc0d355e973edfcb7453900ab73fc9`
- Consulted file: [`timeularapi.js`](https://github.com/zackria/timeularapi/blob/fa79b11184cc0d355e973edfcb7453900ab73fc9/timeularapi.js)
- License: MIT; the full upstream copyright notice and license are retained in
  [`licenses/MIT-node-client.txt`](licenses/MIT-node-client.txt).

Protocol reference for device discovery, initial orientation reads, and
indication subscriptions. These three reference clients are not bundled with
Triangles.

## Home Assistant integration patterns

The following modules adapt code from Home Assistant Core `2026.9.4`, licensed
under Apache 2.0:

- [`led_ble/config_flow.py`](https://github.com/home-assistant/core/blob/2026.9.4/homeassistant/components/led_ble/config_flow.py)
  provides the discovery-flow structure used in `config_flow.py`, modified for
  tracker matching, a setup menu, and manual Bluetooth-address entry.
- [`bthome/device_trigger.py`](https://github.com/home-assistant/core/blob/2026.9.4/homeassistant/components/bthome/device_trigger.py)
  provides the structure used in `device_trigger.py`, modified for eight face
  triggers, orientation events, and device-registry validation.

Both modules carry attribution and modification notices. Home Assistant also
supplies the Bluetooth, coordinator, entity, and event-platform APIs.

Documentation references:

- [Bluetooth APIs](https://developers.home-assistant.io/docs/core/bluetooth/api/)
- [Device triggers](https://developers.home-assistant.io/docs/device_automation_trigger/)
- [Event entities](https://developers.home-assistant.io/docs/core/entity/event/)
- [HACS integration requirements](https://www.hacs.xyz/docs/publish/integration/)
- [HACS validation action](https://www.hacs.xyz/docs/publish/action/)

## Dependencies and distribution

Home Assistant supplies Bleak and bleak-retry-connector through its Bluetooth
integration. Development dependencies are listed in `requirements-dev.txt` at
the repository root. These dependencies are not bundled with the integration.

The Triangles code and geometric icon are licensed under Apache 2.0. The MIT
notices retain the licenses and copyright statements of the credited sources.
`LICENSE`, `NOTICE`, this credits file, and the MIT license texts are included
in both HACS installations and manual-install ZIPs.

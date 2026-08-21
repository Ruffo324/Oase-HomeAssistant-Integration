# OASE FM-Master Local — Implementation Status

## Goal

Control the FM-Master's four local outlets through a Home Assistant custom
integration without cloud access.

## Confirmed local transport

- O-Net v2 frames over UDP port 5959.
- The FM-Master answers local discovery and accepts a TCP callback request.
- The callback is TLS 1.2. The integration generates a local self-signed
  callback identity using the EasyControl certificate common name.
- The device authenticates the callback with its separate device password.
- Socket state uses the current EasyControl live-scene commands.

## Completed implementation

- `custom_components/oase_fm/manifest.json`: HA integration metadata.
- `config_flow.py`: manual host/device-password flow.
- `transport.py`: UDP callback request, TLS session, packet framing,
  password authentication.
- `client.py`: short authenticated operation session for reads/writes.
- `coordinator.py`: serialized state refresh/write model.
- `switch.py`: four Home Assistant switch entities.
- `switch_model.py`: HA-independent entity behavior.

## Hardware validation

All four outlets were switched on individually, read back successfully, then
restored to their original state. This validates local control end-to-end.

## Remaining release work

1. Install the custom component in an actual Home Assistant configuration.
2. Complete HA config-flow/platform smoke testing inside a normal HA runtime.
3. Add a GitHub Actions test workflow and user-facing README.
4. Review naming, documentation, diagnostics redaction, then release.

## Security

- Device passwords belong in Home Assistant config-entry storage, not source.
- Runtime TLS identities are created under HA `.storage` and never committed.
- Private analysis, credentials, captures, and test scripts remain ignored.
- No cloud service is used for device discovery, authentication, reads, or
  switching.

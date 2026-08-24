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

## Release status

Complete for the stated local-control goal.

- HA lifecycle smoke test passed: integration setup created all four switch
  entities from the live FM-Master state.
- Unit/component suite passes.
- All four local outlets were validated with readback and restored to their
  original state.
- Home-network onboarding succeeded: FM-Master DHCP lease is reachable on LAN;
  the HA lifecycle smoke test created all four entities through the LAN address.
- UI config flow is tested for existing-LAN access plus AP-to-home-network onboarding.
- Fourth output is validated as a 0–255 brightness light; relay outputs 1–3 remain switches.
- Source review confirmed private credentials, TLS materials, captures, and
  reference analysis remain ignored.

## Security

- Device passwords belong in Home Assistant config-entry storage, not source.
- Runtime TLS identities are created under HA `.storage` and never committed.
- Private analysis, credentials, captures, and test scripts remain ignored.
- No cloud service is used for device discovery, authentication, reads, or
  switching.

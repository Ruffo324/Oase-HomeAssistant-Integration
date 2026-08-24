# OASE FM-Master Local

Local Home Assistant custom integration for the four FM-Master outlets.

## Status

Protocol, authentication, state reads, and four-outlet switching are verified
against a local FM-Master. All outlet tests were restored to the prior state.

## Install

1. Copy `custom_components/oase_fm` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add **OASE FM-Master Local** under Devices & services.
4. Enter the FM-Master address and its device password.

The factory access-point address is normally `192.168.1.1`. A host with Home
Assistant must be reachable by the FM-Master over the same local network.

## Entities

- `Outlet 1` — relay switch
- `Outlet 2` — relay switch
- `Outlet 3` — relay switch
- `Outlet 4 dimmer` — brightness light, 0–255

## UI onboarding

For an already reachable gateway, choose **Existing LAN gateway** and enter its
LAN address plus device password.

For a factory-reset gateway, first connect the Home Assistant host to the
FM-Master access point. Choose **Gateway AP onboarding**, enter the AP host,
device password, home Wi-Fi SSID, and home Wi-Fi password. The integration
submits DHCP router configuration. After the gateway joins the router, enter
its DHCP address from the router in the final UI step.

Home Assistant cannot itself switch an arbitrary host's Wi-Fi connection to a
gateway AP; that prerequisite remains platform/network configuration outside a
custom integration.

## Local operation

No OASE cloud endpoint is contacted. The integration uses O-Net v2 local UDP
control-channel setup plus a short TLS callback session for each operation.

## Security

The integration stores the device password in the Home Assistant config entry.
It generates a local TLS callback certificate beneath HA `.storage`. Neither
belongs in Git.

## Development verification

```bash
.venv/bin/python -m pytest -q
```

Private test utilities, traffic captures, credentials, and reference analysis
are intentionally gitignored.

## Verification

- 30 unit/component tests pass.
- Home Assistant lifecycle smoke test passed: setup created all four switch
  entities with current live-device state.
- Real FM-Master validation switched every outlet on, verified each readback,
  then restored the original state.
- Home-network onboarding succeeded: the FM-Master is reachable on the local
  LAN, and the same HA lifecycle smoke test created all four switch entities
  through its LAN address.

## Home Assistant UI setup

1. Copy `custom_components/oase_fm` into Home Assistant's `custom_components/`.
2. Restart Home Assistant.
3. **Settings → Devices & services → Add integration → OASE FM-Master Local**.
4. Enter the FM-Master's current LAN address and its device password.

The config flow stores the address/password in Home Assistant's encrypted
configuration storage. No OASE cloud account is used.

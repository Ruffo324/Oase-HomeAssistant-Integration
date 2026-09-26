# OASE FM-Master Onboarding App

Optional HA OS/Supervised companion App for reset-gateway AP access.

## What it does

1. Reads Supervisor network information.
2. Scans every spare wireless interface.
3. Lists only SSIDs beginning `OASE FM-Master`.
4. Connects the selected spare Wi-Fi interface through the Supervisor Network API.
5. Leaves Ethernet untouched and primary.
6. Starts the existing **OASE FM-Master Local** config flow through the
   authenticated HA Core proxy.
7. Provisions the FM-Master to destination home Wi-Fi, discovers its DHCP
   address, verifies it, and creates the integration entry.

The App runs the complete AP onboarding sequence after AP join. It sends device
and home-Wi-Fi credentials only to the HA Core config-flow request, does not
persist them, and clears browser form fields after use.

## Requirements

- Home Assistant OS or Supervised.
- A separate wireless adapter.
- Ethernet as the primary connection.
- The FM-Master AP password.

HA Container/Core lacks the Supervisor Network API, so cannot use this App.

## Install

Add this GitHub repository in **Settings → Apps → App store → Repositories**.
Install and open **OASE FM-Master Onboarding**. The App requires its declared
network privileges because it changes only the selected Wi-Fi interface.

The App intentionally does not store AP passwords.

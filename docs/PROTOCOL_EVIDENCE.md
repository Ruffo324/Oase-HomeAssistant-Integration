# Protocol Evidence Log

Public, clean-room record of independently observed or publicly documented
OASE FM-Master network/protocol behavior. See `docs/RESEARCH_METHOD.md` for
the evidence standard and confidence definitions that govern every entry
below.

Only entries that satisfy that standard may be added here. Nothing in this
file may be derived from, or cross-referenced against, private reference
material.

## How to add an entry

Append a row to the relevant table using this template:

```
| <short finding> | <live-device observation \| public documentation \| standard protocol> | <what it implies for the integration> | <confirmed \| likely \| unknown> |
```

Keep findings generic and reproducible — e.g. "device responds on UDP
broadcast" rather than a raw packet dump. Do not paste captures, logs, or
device-identifying data (IP/MAC/serial/SSID) into this file.

## Discovery

| Finding | Evidence source | Interpretation | Confidence |
|---|---|---|---|
| A one-shot standard mDNS/DNS-SD service query and SSDP `M-SEARCH ssdp:all` query, run for a 5s listen window each, did not surface any device identifying as OASE/FM-Master on the tested LAN | live-device observation | Inconclusive: standard multicast discovery alone did not confirm the device supports either protocol in this run; the device may not have been present/powered on the tested segment at test time. See `docs/DEVICE_DISCOVERY.md` for the full sanitized run report | unknown |

## Transport / application protocol

| Finding | Evidence source | Interpretation | Confidence |
|---|---|---|---|
| _No findings recorded yet._ | | | |

## Authentication / pairing

| Finding | Evidence source | Interpretation | Confidence |
|---|---|---|---|
| _No findings recorded yet._ | | | |

## Device identity / capabilities

| Finding | Evidence source | Interpretation | Confidence |
|---|---|---|---|
| _No findings recorded yet._ | | | |

## Open questions

Clean-room investigation questions to resolve in Phase 1 (live-device
discovery), derived only as high-level questions — not as conclusions or
excerpts from any private material:

- Does the FM-Master announce itself via mDNS/DNS-SD, SSDP, or neither on
  first boot / after factory reset?
- Does it request a DHCP lease with an identifiable hostname or vendor class,
  or fall back to a self-assigned/AP mode?
- What port(s), if any, respond to unsolicited local traffic, and over what
  transport (TCP/UDP)?
- Is there a local HTTP(S)/WebSocket/MQTT/CoAP endpoint reachable without
  cloud involvement, and does it require authentication to read state?
- Does onboarding require a companion mobile app pairing step that cannot be
  observed purely from the LAN side?

Each question above is to be answered with an entry in the tables above,
sourced strictly per `docs/RESEARCH_METHOD.md`, before being treated as
settled.

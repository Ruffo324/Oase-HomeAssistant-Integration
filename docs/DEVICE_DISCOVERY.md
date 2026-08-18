# Device Discovery — Phase 1 Findings

Sanitized results from a single run of `tools/discover_oase.py` on the
research LAN. Method, evidence hierarchy, and confidence definitions are per
`docs/RESEARCH_METHOD.md`. All IP addresses, MAC addresses, SSIDs, serials,
and third-party device identifiers observed during this run have been
redacted or generalized below, per the confidentiality review in that
document.

## Run parameters

- Script: `tools/discover_oase.py`
- Techniques used: local interface/route/neighbour-table inspection, one-shot
  mDNS/DNS-SD service query (RFC 6762/6763), one-shot SSDP `M-SEARCH`
  (`ssdp:all`, `MX: 2`).
- Listen window: 5 seconds per protocol.
- No port scanning, pairing, control, or repeated/aggressive probing was
  performed.

## Local network state

| Finding | Evidence source | Interpretation | Confidence |
|---|---|---|---|
| Host has one active wired interface on a private (RFC 1918) `/24` subnet, plus one inactive Wi-Fi interface | live-device observation | Research host is on a typical home LAN; a wireless-only device would need the Wi-Fi interface active to be observed | confirmed |
| Neighbour (ARP) table contained a small number of entries for other hosts already on the LAN | live-device observation | Some other LAN hosts were recently active; this table alone does not identify device type or vendor without further correlation | confirmed |

No OASE/FM-Master-specific identifiers were present in interface, route, or
neighbour-table data — this data is generic and vendor-agnostic.

## mDNS / DNS-SD

| Finding | Evidence source | Interpretation | Confidence |
|---|---|---|---|
| Sent standard DNS-SD service-enumeration and common-service-type queries over multicast; within the 5s window, only the host's own outgoing queries were observed (multicast loopback), no third-party mDNS responses were received | live-device observation | No device on this LAN answered standard mDNS/DNS-SD queries during this run. This does not prove the target device never uses mDNS — it may have been absent from the LAN, powered off, in a pre-onboarding state, or mDNS may be disabled/unsupported | unknown |

## SSDP / UPnP

| Finding | Evidence source | Interpretation | Confidence |
|---|---|---|---|
| Several distinct hosts responded to a standard SSDP `M-SEARCH ssdp:all` query | live-device observation | Multiple UPnP-capable devices are present on the LAN (consumer router/gateway and printer UPnP stacks were the only vendor patterns observed) | confirmed |
| None of the SSDP responses matched OASE, FM-Master, or any unrecognized/unidentified device pattern | live-device observation | No SSDP-advertising device on this LAN self-identified as an OASE product during this run | unknown (absence of evidence, not evidence of absence) |

## Overall assessment

No device matching the OASE FM-Master was observed via standard mDNS/DNS-SD
or SSDP discovery during this run. Possible explanations, none of which are
established by this run alone: the physical device was not present/powered
on the same LAN segment at test time, it does not implement either
discovery protocol, or it only announces itself in a specific onboarding
state (e.g. first-boot AP mode) not exercised here.

## Next steps (not yet performed)

- Repeat discovery with the physical device confirmed powered on and on the
  same LAN segment/VLAN as the research host.
- If still silent on mDNS/SSDP, consult public documentation (manual,
  datasheet, regulatory filing) for stated connectivity/discovery behavior
  before considering any further low-rate, targeted, single-device probing
  per `docs/RESEARCH_METHOD.md`.

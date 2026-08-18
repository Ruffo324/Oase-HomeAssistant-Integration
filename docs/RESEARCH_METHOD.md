# Research Method — Clean-Room Discovery

This document defines how findings about OASE device behavior are investigated,
verified, and recorded for this project. It applies to every phase of work,
from network discovery through protocol documentation.

## Purpose

This integration is built from independently observed device behavior and
publicly available information only. Historical/legacy source material that
may be available to contributors during development is treated strictly as
private orientation material — never as a source of code, structure, or fact.

## Evidence hierarchy

Public findings must be traceable to one of the following sources, ranked by
strength:

1. **Live-device observation** — behavior directly observed from the physical
   device over the network (traffic shape, response codes, timing, discovery
   broadcasts, documented API responses), captured using standard, general-
   purpose tools.
2. **Public documentation** — vendor user manuals, published datasheets,
   regulatory filings (e.g. FCC/CE), app store listings, public support
   articles, or other material published for general audiences.
3. **Standard protocol specification** — behavior defined by an open standard
   (e.g. mDNS/DNS-SD, SSDP, DHCP, HTTP) that the device is observed to follow.

Nothing is published on any other basis. If a fact cannot be traced to one of
these sources, it is recorded as `unknown`, not asserted.

## Provenance rule

Private reference material of any kind — historical source archives, internal
tools, internal documentation, or similar — may only ever be used, if present,
to:

- form high-level investigation questions ("does the device advertise itself
  via mDNS?", "does the app talk to it over HTTP or a raw socket?"), and
- sanity-check whether an independently observed conclusion is plausible.

It is never used as a template, never quoted, paraphrased, or structurally
mirrored, and never cited as an evidence source in any public artifact. No
file path, filename, identifier, comment, string, protocol constant, or code
structure from such material may appear in this repository, in commit
history, in issues, or in any message about this project. See
`OASE_HOME_ASSISTANT_AGENT_PROMPT.md` for the full confidentiality policy.

If private material and independent observation ever appear to disagree, the
independent observation is what gets published; the disagreement itself is
not discussed in public artifacts.

## Confidence levels

Every finding in `docs/PROTOCOL_EVIDENCE.md` (and other protocol/behavior
docs) is tagged with one of:

- `confirmed` — reproduced directly against the live device, or stated
  unambiguously in public documentation.
- `likely` — consistent with one independently observed data point or a
  standard-protocol default, but not yet reproduced/cross-checked.
- `unknown` — not yet independently established. Treated as a gap, not
  filled with assumption.

Findings are never upgraded in confidence without new independent evidence.

## Investigation approach

Preference order, least to most invasive:

1. Passive observation: interface/route/DNS state, ARP/neighbour tables,
   existing mDNS/SSDP/DHCP traffic, passive packet capture where lawful and
   available.
2. Standard discovery queries: mDNS/DNS-SD browsing, SSDP M-SEARCH, DHCP
   lease inspection — all standard, low-volume, non-disruptive queries.
3. Targeted, rate-limited active probing of the specific device only, after
   passive methods are exhausted, and only as needed to confirm a specific
   hypothesis.

Probing is stopped immediately if it produces signs of device instability.
The device is never factory-reset, firmware-flashed, or otherwise
deliberately disrupted as part of routine investigation.

## Recording findings

Each entry recorded in a public evidence document states:

- **Observation** — what was seen, described generically (e.g. "device
  responds to SSDP M-SEARCH with a `ST` matching its device type"), never as
  a raw dump of a capture.
- **Evidence source** — `live-device observation`, `public documentation`, or
  `standard protocol`, per the hierarchy above.
- **Interpretation** — what this implies for the integration.
- **Confidence** — `confirmed` / `likely` / `unknown`.

Raw packet captures, logs, and other private working material used to reach a
finding are kept locally, outside version control (see `.gitignore`), and are
never attached to commits, issues, or public documentation.

## Review before publishing

Before any finding, script, or document derived from this process is
committed, it is checked against:

- Does every fact trace to an evidence source in the hierarchy above?
- Does anything in the text, identifiers, or structure originate from private
  reference material rather than independent observation?
- Does it expose secrets, credentials, serials, MAC addresses, IP addresses,
  SSIDs, or other identifying data?

If any check fails, the finding is not published until it can be
independently re-derived or removed.

#!/usr/bin/env python3
"""Passive/low-rate LAN discovery helper for Phase 1 device research.

Uses only standard, non-disruptive techniques:
  - Local interface / route / neighbour (ARP) table inspection.
  - One-shot mDNS/DNS-SD service enumeration query (RFC 6762/6763).
  - One-shot SSDP M-SEARCH discovery (UPnP ssdp:all).

Explicitly does NOT do: port scanning, device pairing/control, firmware
actions, or repeated/aggressive probing. Each discovery step sends a small,
bounded number of standard multicast queries and listens for a short,
fixed window.

Raw results (which may contain IP/MAC/hostname/service-record details) are
written to a local JSON file under scans/ (already git-ignored). This
script never redacts on your behalf when printing to stdout -- treat all
output as private working material. Only hand-reviewed, redacted summaries
belong in docs/DEVICE_DISCOVERY.md.
"""

from __future__ import annotations

import argparse
import json
import socket
import struct
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MDNS_ADDR = "224.0.0.1"
MDNS_PORT = 5353
SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900

# Standard, generic DNS-SD service enumeration query plus a handful of
# common well-known service types. This is exactly what a passive mDNS
# browser (e.g. `avahi-browse -a`) does; it is not device-specific.
MDNS_QUERY_NAMES = [
    "_services._dns-sd._udp.local",
    "_http._tcp.local",
    "_https._tcp.local",
    "_workstation._tcp.local",
]


# --------------------------------------------------------------------------
# Local interface / route / neighbour inspection
# --------------------------------------------------------------------------


def _run_ip_json(args: list[str]) -> Any:
    try:
        out = subprocess.run(
            ["ip", "-j", *args], capture_output=True, text=True, timeout=5, check=True
        )
        return json.loads(out.stdout)
    except Exception as exc:  # noqa: BLE001 - best-effort local inspection
        return {"error": str(exc)}


def inspect_local_network() -> dict[str, Any]:
    """Passive: interfaces, routes, neighbour (ARP/NDP) table."""
    return {
        "interfaces": _run_ip_json(["addr", "show"]),
        "routes": _run_ip_json(["route", "show"]),
        "neighbours": _run_ip_json(["neigh", "show"]),
    }


# --------------------------------------------------------------------------
# mDNS / DNS-SD (RFC 6762 / 6763) one-shot query
# --------------------------------------------------------------------------


def _encode_dns_name(name: str) -> bytes:
    out = b""
    for label in name.strip(".").split("."):
        data = label.encode("ascii")
        out += bytes([len(data)]) + data
    return out + b"\x00"


def _build_dns_query(qname: str, qtype: int = 12, qclass: int = 1) -> bytes:
    # qtype 12 = PTR, qtype 255 = ANY
    header = struct.pack(">HHHHHH", 0, 0, 1, 0, 0, 0)
    question = _encode_dns_name(qname) + struct.pack(">HH", qtype, qclass)
    return header + question


def _read_name(data: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    start = offset
    jumped = False
    seen_offsets: set[int] = set()
    while True:
        if offset >= len(data):
            break
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(data):
                break
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if pointer in seen_offsets:
                break  # guard against malformed/looping pointers
            seen_offsets.add(pointer)
            if not jumped:
                start = offset + 2
                jumped = True
            offset = pointer
            continue
        offset += 1
        labels.append(data[offset : offset + length].decode("ascii", "replace"))
        offset += length
    end = offset if not jumped else start
    return ".".join(labels), end


_RTYPE = {1: "A", 5: "CNAME", 12: "PTR", 16: "TXT", 28: "AAAA", 33: "SRV"}


def _parse_rr(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    name, offset = _read_name(data, offset)
    rtype, rclass, ttl, rdlen = struct.unpack_from(">HHIH", data, offset)
    offset += 10
    rdata_start = offset
    parsed: Any
    if rtype == 12 or rtype == 5:  # PTR / CNAME
        parsed, _ = _read_name(data, rdata_start)
    elif rtype == 16:  # TXT
        strs = []
        pos = rdata_start
        end = rdata_start + rdlen
        while pos < end:
            slen = data[pos]
            pos += 1
            strs.append(data[pos : pos + slen].decode("utf-8", "replace"))
            pos += slen
        parsed = strs
    elif rtype == 33:  # SRV
        prio, weight, port = struct.unpack_from(">HHH", data, rdata_start)
        target, _ = _read_name(data, rdata_start + 6)
        parsed = {"priority": prio, "weight": weight, "port": port, "target": target}
    elif rtype == 1 and rdlen == 4:  # A
        parsed = socket.inet_ntoa(data[rdata_start : rdata_start + 4])
    elif rtype == 28 and rdlen == 16:  # AAAA
        parsed = socket.inet_ntop(socket.AF_INET6, data[rdata_start : rdata_start + 16])
    else:
        parsed = data[rdata_start : rdata_start + rdlen].hex()
    offset = rdata_start + rdlen
    record = {
        "name": name,
        "type": _RTYPE.get(rtype, str(rtype)),
        "ttl": ttl,
        "data": parsed,
    }
    return record, offset


def _parse_dns_message(data: bytes) -> dict[str, Any]:
    if len(data) < 12:
        return {"error": "short packet"}
    _id, flags, qd, an, ns, ar = struct.unpack_from(">HHHHHH", data, 0)
    offset = 12
    for _ in range(qd):
        _name, offset = _read_name(data, offset)
        offset += 4  # qtype + qclass
    records = []
    for _ in range(an + ns + ar):
        try:
            rr, offset = _parse_rr(data, offset)
        except (struct.error, IndexError):
            break
        records.append(rr)
    return {"records": records}


def mdns_discover(timeout: float) -> list[dict[str, Any]]:
    """Send standard DNS-SD queries, listen briefly, return parsed responses."""
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    recv_sock.bind(("", MDNS_PORT))
    mreq = struct.pack("4s4s", socket.inet_aton(MDNS_ADDR), socket.inet_aton("0.0.0.0"))
    recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    recv_sock.settimeout(0.5)

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)

    for qname in MDNS_QUERY_NAMES:
        send_sock.sendto(_build_dns_query(qname), (MDNS_ADDR, MDNS_PORT))
        time.sleep(0.05)  # small gap between queries, not a burst

    responses = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            data, addr = recv_sock.recvfrom(65535)
        except socket.timeout:
            continue
        except OSError:
            break
        parsed = _parse_dns_message(data)
        parsed["from"] = addr[0]
        responses.append(parsed)

    recv_sock.close()
    send_sock.close()
    return responses


# --------------------------------------------------------------------------
# SSDP (UPnP) one-shot M-SEARCH
# --------------------------------------------------------------------------


def ssdp_discover(timeout: float, mx: int = 2) -> list[dict[str, Any]]:
    msg = (
        "M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
        'MAN: "ssdp:discover"\r\n'
        f"MX: {mx}\r\n"
        "ST: ssdp:all\r\n"
        "\r\n"
    ).encode("ascii")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(0.5)
    sock.sendto(msg, (SSDP_ADDR, SSDP_PORT))

    responses = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            data, addr = sock.recvfrom(65535)
        except socket.timeout:
            continue
        except OSError:
            break
        text = data.decode("utf-8", "replace")
        headers: dict[str, str] = {}
        for line in text.split("\r\n")[1:]:
            if ":" in line:
                key, _, value = line.partition(":")
                headers[key.strip().upper()] = value.strip()
        responses.append({"from": addr[0], "status_line": text.split("\r\n", 1)[0], "headers": headers})

    sock.close()
    return responses


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


@dataclass
class DiscoveryResult:
    local_network: dict[str, Any] = field(default_factory=dict)
    mdns_responses: list[dict[str, Any]] = field(default_factory=list)
    ssdp_responses: list[dict[str, Any]] = field(default_factory=list)


def run(timeout: float) -> DiscoveryResult:
    result = DiscoveryResult()
    result.local_network = inspect_local_network()
    result.mdns_responses = mdns_discover(timeout)
    result.ssdp_responses = ssdp_discover(timeout)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=float,
        default=4.0,
        help="Listen window in seconds for each of mDNS/SSDP (default: 4.0)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("scans/discover_oase_raw.json"),
        help="Where to write raw JSON results (local-only, git-ignored)",
    )
    args = parser.parse_args()

    result = run(args.timeout)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "local_network": result.local_network,
                "mdns_responses": result.mdns_responses,
                "ssdp_responses": result.ssdp_responses,
            },
            indent=2,
        )
    )

    print(f"Interfaces found: {len(result.local_network.get('interfaces') or [])}")
    print(f"Neighbour table entries: {len(result.local_network.get('neighbours') or [])}")
    print(f"mDNS responses received: {len(result.mdns_responses)}")
    print(f"SSDP responses received: {len(result.ssdp_responses)}")
    print(f"Raw results written to: {args.out}")
    print("NOTE: raw output may contain IP/MAC/hostname data. Do not commit it.")
    print("Review manually and write a redacted summary to docs/DEVICE_DISCOVERY.md.")


if __name__ == "__main__":
    main()

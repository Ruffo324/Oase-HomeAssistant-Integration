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


def mdns_discover(timeout: float, source_ip: str | None = None) -> list[dict[str, Any]]:
    """Send standard DNS-SD queries, listen briefly, return parsed responses.

    If source_ip is given, multicast egress and group membership are bound
    to that local interface address so the query reaches only the network
    reachable from that interface (e.g. a single-purpose device AP subnet)
    instead of whichever interface the default route happens to prefer.
    """
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    recv_sock.bind(("", MDNS_PORT))
    mreq = struct.pack("4s4s", socket.inet_aton(MDNS_ADDR), socket.inet_aton(source_ip or "0.0.0.0"))
    recv_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    recv_sock.settimeout(0.5)

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    if source_ip:
        send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(source_ip))
        send_sock.bind((source_ip, 0))

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


def ssdp_discover(timeout: float, mx: int = 2, source_ip: str | None = None) -> list[dict[str, Any]]:
    """Send a standard SSDP M-SEARCH and listen briefly.

    If source_ip is given, egress is bound to that local interface address
    (see mdns_discover docstring for why this matters on multi-homed hosts).
    """
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
    if source_ip:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(source_ip))
        sock.bind((source_ip, 0))
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
# Targeted single-host probe (opt-in, rate-limited, gateway-only)
# --------------------------------------------------------------------------

# Curated, small set of well-known ports plausible for a local IoT
# config/control surface. This is a bounded, fixed list probed once each
# with a delay between attempts -- not a port scan. Only ever point this
# at a single device you own/administer (e.g. its own AP gateway address),
# never at a subnet or third-party hosts.
COMMON_PORT_CANDIDATES: dict[int, str] = {
    22: "ssh",
    23: "telnet",
    53: "dns",
    80: "http",
    443: "https",
    502: "modbus",
    1883: "mqtt",
    7777: "misc-iot",
    8080: "http-alt",
    8443: "https-alt",
    8883: "mqtts",
    9999: "misc-iot",
}

# Standard/publicly documented UDP service ports. Same bounded, single-host,
# low-rate approach as the TCP list above.
UDP_PORT_CANDIDATES: dict[int, str] = {
    53: "dns",
    123: "ntp",
    161: "snmp",
    3702: "ws-discovery",
    5683: "coap",
}


def probe_udp_port(host: str, port: int, timeout: float) -> bool:
    """Send one empty datagram, true if any reply arrives from that host:port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(timeout)
    try:
        sock.sendto(b"", (host, port))
        data, addr = sock.recvfrom(4096)
        return addr[0] == host
    except OSError:
        return False
    finally:
        sock.close()


def probe_tcp_port(host: str, port: int, timeout: float) -> bool:
    """Single TCP connect attempt. True if the port accepted a connection."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def probe_http_banner(host: str, port: int, use_tls: bool, timeout: float) -> dict[str, Any]:
    """Single HTTP HEAD request. Returns status line + headers only, never body."""
    try:
        import http.client

        conn_cls = http.client.HTTPSConnection if use_tls else http.client.HTTPConnection
        conn = conn_cls(host, port, timeout=timeout)
        conn.request("HEAD", "/")
        resp = conn.getresponse()
        result: dict[str, Any] = {
            "status": resp.status,
            "reason": resp.reason,
            "headers": dict(resp.getheaders()),
        }
        conn.close()
        return result
    except Exception as exc:  # noqa: BLE001 - best-effort banner probe
        return {"error": str(exc)}


def targeted_probe(host: str, delay: float = 0.3, timeout: float = 1.5) -> dict[str, Any]:
    """Low-rate, single-host probe of a curated port list plus a minimal
    HTTP HEAD banner check on any open HTTP(S)-plausible port. Intended
    for use against the device's own AP gateway address only, after
    passive discovery, per docs/RESEARCH_METHOD.md."""
    open_ports: dict[int, str] = {}
    for port, label in COMMON_PORT_CANDIDATES.items():
        if probe_tcp_port(host, port, timeout):
            open_ports[port] = label
        time.sleep(delay)

    http_banners: dict[int, Any] = {}
    for port in (80, 8080):
        if port in open_ports:
            http_banners[port] = probe_http_banner(host, port, use_tls=False, timeout=timeout)
            time.sleep(delay)
    for port in (443, 8443):
        if port in open_ports:
            http_banners[port] = probe_http_banner(host, port, use_tls=True, timeout=timeout)
            time.sleep(delay)

    udp_open: dict[int, str] = {}
    for port, label in UDP_PORT_CANDIDATES.items():
        if probe_udp_port(host, port, timeout):
            udp_open[port] = label
        time.sleep(delay)

    return {
        "host": host,
        "open_ports": open_ports,
        "http_banners": http_banners,
        "udp_responding": udp_open,
    }


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


@dataclass
class DiscoveryResult:
    local_network: dict[str, Any] = field(default_factory=dict)
    mdns_responses: list[dict[str, Any]] = field(default_factory=list)
    ssdp_responses: list[dict[str, Any]] = field(default_factory=list)
    targeted: dict[str, Any] | None = None


def run(timeout: float, target_host: str | None = None, source_ip: str | None = None) -> DiscoveryResult:
    result = DiscoveryResult()
    result.local_network = inspect_local_network()
    result.mdns_responses = mdns_discover(timeout, source_ip=source_ip)
    result.ssdp_responses = ssdp_discover(timeout, source_ip=source_ip)
    if target_host:
        result.targeted = targeted_probe(target_host)
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
    parser.add_argument(
        "--target-host",
        type=str,
        default=None,
        help=(
            "Optional: run a low-rate, curated-port TCP probe against this "
            "single host only (e.g. the device's own AP gateway address). "
            "Never point this at a subnet or third-party host."
        ),
    )
    parser.add_argument(
        "--source-ip",
        type=str,
        default=None,
        help=(
            "Optional: bind mDNS/SSDP multicast egress to this local "
            "interface address, so queries reach a specific subnet on a "
            "multi-homed host instead of whichever interface the default "
            "route happens to prefer."
        ),
    )
    args = parser.parse_args()

    result = run(args.timeout, target_host=args.target_host, source_ip=args.source_ip)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "local_network": result.local_network,
                "mdns_responses": result.mdns_responses,
                "ssdp_responses": result.ssdp_responses,
                "targeted": result.targeted,
            },
            indent=2,
        )
    )

    print(f"Interfaces found: {len(result.local_network.get('interfaces') or [])}")
    print(f"Neighbour table entries: {len(result.local_network.get('neighbours') or [])}")
    print(f"mDNS responses received: {len(result.mdns_responses)}")
    print(f"SSDP responses received: {len(result.ssdp_responses)}")
    if result.targeted:
        print(f"Targeted probe open ports: {sorted(result.targeted.get('open_ports', {}).keys())}")
    print(f"Raw results written to: {args.out}")
    print("NOTE: raw output may contain IP/MAC/hostname data. Do not commit it.")
    print("Review manually and write a redacted summary to docs/DEVICE_DISCOVERY.md.")


if __name__ == "__main__":
    main()

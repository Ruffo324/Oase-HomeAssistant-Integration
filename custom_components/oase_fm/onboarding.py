"""FM-Master home-network onboarding over its local AP or LAN endpoint."""

from __future__ import annotations

import asyncio
import datetime
import socket
from collections.abc import Awaitable, Callable

from .transport import ONetV2, parse_packet


def build_onboarding_handoff(
    device_password: str,
    wifi_ssid: str,
    wifi_password: str,
    *,
    gateway_host: str = "192.168.1.1",
) -> dict[str, str]:
    """Validate the transient data passed from the privileged HA OS App.

    The App only joins the spare Wi-Fi adapter. HA Core remains the sole
    O-Net/TLS transport owner and consumes this object without persistence.
    """
    if gateway_host != "192.168.1.1":
        raise ValueError("gateway host must be the FM-Master AP host")
    if not all((device_password, wifi_ssid, wifi_password)):
        raise ValueError("onboarding credentials must not be empty")
    if len(wifi_ssid.encode("utf-8")) > 32 or len(wifi_password.encode("utf-8")) > 64:
        raise ValueError("Wi-Fi credential exceeds FM-Master limits")
    return {
        "gateway_host": gateway_host,
        "device_password": device_password,
        "wifi_ssid": wifi_ssid,
        "wifi_password": wifi_password,
    }


def _fixed(value: str, length: int) -> bytes:
    encoded = value.encode("utf-8")
    if len(encoded) > length:
        raise ValueError(f"network field exceeds {length} bytes")
    return encoded.ljust(length, b"\0")


def build_router_initial_config(device_password: str, ssid: str, wifi_password: str) -> bytes:
    """Current EasyControl initial-config packet for router/DHCP mode.

    The AP host must already be connected to the FM-Master AP. The gateway then
    leaves its AP and joins ``ssid`` through DHCP.
    """
    now = datetime.datetime.now().astimezone()
    clock = bytes(
        (
            now.hour,
            now.minute,
            now.second,
            now.year - 2014,
            now.month,
            now.day,
            now.isoweekday() % 7,
            int(bool(now.dst())),
        )
    )
    payload = (
        bytes((2,))  # Router mode
        + bytes(32)  # no retained AP SSID in router-only onboarding
        + bytes(64)  # no retained AP password
        + bytes((1,))  # WPA2 PSK
        + _fixed(ssid, 32)
        + _fixed(wifi_password, 64)
        + bytes((0,))  # DHCP
        + bytes(20)
        + _fixed("FM-Master", 64)
        + _fixed(device_password, 64)
        + clock
        + _fixed("Europe/Berlin", 100)
        + bytes((0,))
    )
    if len(payload) != 452:
        raise AssertionError(len(payload))
    return payload


async def async_discover_gateway_host(
    probe: Callable[[], Awaitable[str | None]] | None = None,
    *,
    timeout: float = 4.0,
) -> str | None:
    """Discover a single O-Net v2 gateway on the LAN after AP provisioning.

    Uses one broadcast discovery datagram; no subnet or port scan. A caller may
    supply ``probe`` for tests or a platform-specific discovery implementation.
    """
    if probe is not None:
        return await probe()

    def discover() -> str | None:
        request = ONetV2.packet(1, 0x1000)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp.settimeout(timeout)
            udp.bind(("", 5959))
            udp.sendto(request, ("255.255.255.255", 5959))
            while True:
                raw, address = udp.recvfrom(2048)
                _transaction, packet_type, _payload = parse_packet(raw)
                if packet_type == 0x10FF:
                    return address[0]

    try:
        return await asyncio.to_thread(discover)
    except (OSError, TimeoutError, ValueError):
        return None


async def async_apply_router_initial_config(
    open_session: Callable[[], Awaitable[object]],
    device_password: str,
    ssid: str,
    wifi_password: str,
) -> None:
    """Submit router configuration and require the gateway's accepted status."""
    session = await open_session()
    try:
        packet_type, reply = await session.request(
            0xB400, build_router_initial_config(device_password, ssid, wifi_password)
        )
    finally:
        await session.close()
    if packet_type != 0xB4FF or reply != b"\x01":
        raise ConnectionError("FM-Master rejected home-network configuration")

"""FM-Master home-network onboarding over its local AP or LAN endpoint."""

from __future__ import annotations

import datetime
from collections.abc import Awaitable, Callable


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

import asyncio

from custom_components.oase_fm.onboarding import (
    async_apply_router_initial_config,
    build_router_initial_config,
)


def test_router_initial_config_is_current_fixed_length_packet() -> None:
    packet = build_router_initial_config("device-password", "home-wifi", "wifi-password")

    assert len(packet) == 452
    assert packet[0] == 2
    assert packet[97] == 1
    assert packet[98:130].split(b"\0")[0] == b"home-wifi"
    assert packet[130:194].split(b"\0")[0] == b"wifi-password"
    assert packet[194] == 0


def test_router_initial_config_rejects_overlength_credentials() -> None:
    try:
        build_router_initial_config("password", "x" * 33, "wifi-password")
    except ValueError:
        pass
    else:
        raise AssertionError("accepted long SSID")


class Session:
    async def request(self, packet_type: int, payload: bytes):
        assert packet_type == 0xB400
        assert len(payload) == 452
        return 0xB4FF, b"\x01"

    async def close(self) -> None:
        return None


async def session_factory():
    return Session()


def test_router_initial_config_requires_success_reply() -> None:
    asyncio.run(async_apply_router_initial_config(session_factory, "password", "ssid", "wifi-password"))


class RejectedSession(Session):
    async def request(self, packet_type: int, payload: bytes):
        return 0xB4FF, b"\x00"


async def rejected_session_factory():
    return RejectedSession()


def test_router_initial_config_rejection_is_reported() -> None:
    try:
        asyncio.run(async_apply_router_initial_config(rejected_session_factory, "password", "ssid", "wifi-password"))
    except ConnectionError:
        pass
    else:
        raise AssertionError("rejection was ignored")

import asyncio

import pytest

from custom_components.oase_fm.client import FmMasterClient


def test_packet_builder_uses_current_socket_scene() -> None:
    assert FmMasterClient.socket_scene(socket=2, on=False) == b"\x04" + b"\x00" * 8 + b"\x64\x02\x02\x00"


def test_parse_socket_state_returns_four_socket_states() -> None:
    # FM-Master reply: IdType=4, Id=0, Countdown=0, SceneType=101, len=5, outputs 255,0,255,0,0.
    payload = b"\x04" + b"\x00" * 8 + b"\x65\x05\xff\x00\xff\x00\x00"

    assert FmMasterClient.parse_socket_states(payload) == (True, False, True, False)


def test_parse_socket_state_rejects_non_socket_scene() -> None:
    with pytest.raises(ValueError, match="socket scene"):
        FmMasterClient.parse_socket_states(b"\x04" + b"\x00" * 8 + b"\x64\x02\x00\xff")


def test_read_and_switch_use_authenticated_tcp_session() -> None:
    class FakeSession:
        def __init__(self):
            self.requests = []

        async def request(self, packet_type, payload):
            self.requests.append((packet_type, payload))
            if packet_type == 0xC500:
                return 0xC5FF, b"\x04" + b"\x00" * 8 + b"\x65\x05\xff\x00\xff\x00\x00"
            return 0xC4FF, b"\x01"

    session = FakeSession()
    client = FmMasterClient("192.168.1.1", "secret", session_factory=lambda: session)

    assert asyncio.run(client.read_sockets()) == (True, False, True, False)
    asyncio.run(client.set_socket(3, True))

    assert session.requests[0][0] == 0xC500
    assert session.requests[1] == (0xC400, b"\x04" + b"\x00" * 8 + b"\x64\x02\x03\xff")

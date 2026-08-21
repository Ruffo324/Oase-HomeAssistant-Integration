import asyncio

from custom_components.oase_fm.client import LiveFmMasterClient


class FakeSession:
    async def request(self, packet_type, payload):
        if packet_type == 0xC500:
            return 0xC5FF, b"\x04" + b"\x00" * 8 + b"\x65\x05\xff\x00\xff\x00\x00"
        return 0xC4FF, b"\x01"

    async def close(self):
        pass


def test_live_client_opens_new_authenticated_session_per_operation() -> None:
    calls = []

    async def open_session():
        calls.append(True)
        return FakeSession()

    client = LiveFmMasterClient(open_session)

    assert asyncio.run(client.read_sockets()) == (True, False, True, False)
    asyncio.run(client.set_socket(1, True))
    assert len(calls) == 2


def test_live_client_raises_on_failed_set_reply() -> None:
    class RejectingSession(FakeSession):
        async def request(self, packet_type, payload):
            return 0xC4FF, b"\x00"

    async def open_session():
        return RejectingSession()

    import pytest

    with pytest.raises(ValueError, match="rejected"):
        asyncio.run(LiveFmMasterClient(open_session).set_socket(0, True))

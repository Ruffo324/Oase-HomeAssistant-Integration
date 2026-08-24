import asyncio

from custom_components.oase_fm.onboarding import async_scan_wifi_ssids, parse_wifi_scan_reply


def test_parse_wifi_scan_reply_returns_ssids_sorted_by_signal() -> None:
    # count, length/SSID/RSSI: weak then strong
    payload = b"\x02\x04weak\xd8\x06strong\xec"
    assert parse_wifi_scan_reply(payload) == ["strong", "weak"]


def test_parse_wifi_scan_reply_ignores_hidden_and_duplicate_ssids() -> None:
    payload = b"\x03\x00\xf0\x04home\xd8\x04home\xec"
    assert parse_wifi_scan_reply(payload) == ["home"]


class Session:
    async def request(self, packet_type: int, payload: bytes):
        assert packet_type == 0x9400
        assert payload == b""
        return 0x94FF, b"\x01\x04home\xec"

    async def close(self) -> None:
        return None


async def session_factory():
    return Session()


def test_wifi_scan_uses_gateway_radio() -> None:
    assert asyncio.run(async_scan_wifi_ssids(session_factory)) == ["home"]


def test_malformed_wifi_scan_reply_is_rejected() -> None:
    try:
        parse_wifi_scan_reply(b"\x01\x05bad")
    except ValueError:
        pass
    else:
        raise AssertionError("malformed reply was accepted")

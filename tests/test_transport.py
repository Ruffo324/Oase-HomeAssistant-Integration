import socket

from custom_components.oase_fm.transport import ONetV2, parse_packet


def test_request_tcp_callback_payload_is_unencrypted_port() -> None:
    assert ONetV2.request_tcp_callback(6014) == b"\x00" + (6014).to_bytes(2, "little")


def test_packet_round_trip_preserves_v2_header() -> None:
    raw = ONetV2.packet(7, 0xC500, b"abc")

    assert parse_packet(raw) == (7, 0xC500, b"abc")


def test_socket_scene_query_is_fm_master_appliance() -> None:
    assert ONetV2.socket_query() == b"\x04\x00\x00\x00\x00"


def test_password_payload_is_ascii_fixed_width() -> None:
    payload = ONetV2.password_payload("secret")

    assert len(payload) == 64
    assert payload[:6] == b"secret"
    assert payload[6:] == b"\0" * 58


def test_packet_parser_rejects_invalid_marker() -> None:
    import pytest

    with pytest.raises(ValueError, match="marker"):
        parse_packet(b"bad")

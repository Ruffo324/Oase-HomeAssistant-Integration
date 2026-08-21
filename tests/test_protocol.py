"""Tests for the locally observed FM-Master O-Net v2 framing."""

from __future__ import annotations

import struct

import pytest

from custom_components.oase_fm.protocol import (
    DISCOVERY,
    DISCOVERY_REPLY,
    GET_OUTPUT,
    ONetPacket,
    ProtocolError,
    SET_OUTPUT,
    build_set_output,
    parse_output_state,
)


def test_v2_packet_serializes_empty_discovery() -> None:
    packet = ONetPacket(transaction=7, packet_type=DISCOVERY).to_bytes()

    assert packet == b"\\#OA" + struct.pack("<IBBH", 0, 2, 7, DISCOVERY) + b"\x00\x00\x00\x00"


def test_v2_packet_round_trip() -> None:
    original = ONetPacket(transaction=9, packet_type=DISCOVERY_REPLY, data=b"abc")

    assert ONetPacket.from_bytes(original.to_bytes()) == original


def test_v2_packet_rejects_bad_marker() -> None:
    with pytest.raises(ProtocolError, match="marker"):
        ONetPacket.from_bytes(b"bad!")


def test_build_set_output_addresses_local_control_unit_channel() -> None:
    packet = build_set_output(transaction=3, channel=2, on=True)

    assert packet.packet_type == SET_OUTPUT
    assert packet.data == bytes((255, 2, 255))


def test_parse_output_state_maps_three_relays_and_dimmer() -> None:
    state = parse_output_state(bytes((0, 255, 1, 128, 42, 9)))

    assert state.relays == (False, True, False)
    assert state.dimmer_on is True
    assert state.dimmer_level == 42
    assert state.device_table_revision == 9


def test_parse_output_state_rejects_short_reply() -> None:
    with pytest.raises(ProtocolError, match="six"):
        parse_output_state(b"\x00")


def test_get_output_packet_has_no_payload() -> None:
    assert ONetPacket(transaction=1, packet_type=GET_OUTPUT).data == b""


def test_live_scene_request_for_fm_master_sockets() -> None:
    # IdType.FmMasterSockets=4, ID=0.
    payload = bytes((4,)) + struct.pack("<I", 0)
    assert payload == b"\x04\x00\x00\x00\x00"


def test_socket_scene_payload_for_socket_one_on() -> None:
    from custom_components.oase_fm.protocol import build_socket_scene

    assert build_socket_scene(socket=0, on=True) == b"\x04" + b"\x00" * 8 + b"\x64\x02\x00\xff"


def test_socket_scene_rejects_unsupported_socket() -> None:
    from custom_components.oase_fm.protocol import build_socket_scene

    with pytest.raises(ProtocolError):
        build_socket_scene(socket=4, on=True)

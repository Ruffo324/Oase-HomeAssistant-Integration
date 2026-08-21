"""Minimal local O-Net v2 packet codec for the FM-Master integration."""

from __future__ import annotations

from dataclasses import dataclass
import struct

MARKER = b"\\#OA"
PROTOCOL_VERSION = 2
DISCOVERY = 0x1000
DISCOVERY_REPLY = 0x10FF
SET_OUTPUT = 0x2000
SET_OUTPUT_REPLY = 0x20FF
GET_OUTPUT = 0x2100
GET_OUTPUT_REPLY = 0x21FF
LOCAL_CONTROL_UNIT_INDEX = 255


class ProtocolError(ValueError):
    """The remote datagram does not match the expected packet format."""


@dataclass(frozen=True)
class ONetPacket:
    """One O-Net v2 datagram."""

    transaction: int
    packet_type: int
    data: bytes = b""

    def to_bytes(self) -> bytes:
        if not 0 <= self.transaction <= 255:
            raise ProtocolError("transaction must fit in one byte")
        if not 0 <= self.packet_type <= 0xFFFF:
            raise ProtocolError("packet type must fit in two bytes")
        return MARKER + struct.pack(
            "<IBBH", len(self.data), PROTOCOL_VERSION, self.transaction, self.packet_type
        ) + b"\x00\x00\x00\x00" + self.data

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ONetPacket":
        if raw[:4] != MARKER:
            raise ProtocolError("invalid packet marker")
        if len(raw) < 16:
            raise ProtocolError("packet is shorter than the v2 header")
        data_length, version, transaction, packet_type = struct.unpack_from("<IBBH", raw, 4)
        if version != PROTOCOL_VERSION:
            raise ProtocolError(f"unsupported protocol version {version}")
        if len(raw) != 16 + data_length:
            raise ProtocolError("packet payload length does not match header")
        return cls(transaction=transaction, packet_type=packet_type, data=raw[16:])


@dataclass(frozen=True)
class OutputState:
    """State returned by an FM-Master output-status reply."""

    relays: tuple[bool, bool, bool]
    dimmer_on: bool
    dimmer_level: int
    device_table_revision: int


def build_set_output(*, transaction: int, channel: int, on: bool) -> ONetPacket:
    """Build a local control-unit relay/dimmer on-off request."""
    if not 0 <= channel <= 3:
        raise ProtocolError("channel must be in range 0 through 3")
    return ONetPacket(
        transaction=transaction,
        packet_type=SET_OUTPUT,
        data=bytes((LOCAL_CONTROL_UNIT_INDEX, channel, 255 if on else 0)),
    )


def build_socket_scene(*, socket: int, on: bool) -> bytes:
    """Build a current EasyControl FM-Master socket scene request payload."""
    if not 0 <= socket <= 3:
        raise ProtocolError("socket must be in range 0 through 3")
    # IdType.FmMasterSockets=4, ID=0, no countdown, SceneType=100, two scene bytes.
    return bytes((4,)) + struct.pack("<II", 0, 0) + bytes((100, 2, socket, 255 if on else 0))


def parse_output_state(data: bytes) -> OutputState:
    """Parse the six-byte output-status payload."""
    if len(data) < 6:
        raise ProtocolError("output state reply must contain at least six bytes")
    return OutputState(
        relays=tuple(value >= 128 for value in data[:3]),
        dimmer_on=data[3] >= 128,
        dimmer_level=data[4],
        device_table_revision=data[5],
    )

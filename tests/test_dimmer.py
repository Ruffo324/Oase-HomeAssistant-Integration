import struct

from custom_components.oase_fm.client import FmMasterClient


def test_dimmer_scene_uses_dimmer_value_socket() -> None:
    assert FmMasterClient.dimmer_scene(64) == bytes((4,)) + struct.pack("<II", 0, 0) + bytes((100, 2, 4, 64))


def test_dimmer_scene_rejects_out_of_range_level() -> None:
    for level in (-1, 256):
        try:
            FmMasterClient.dimmer_scene(level)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted {level}")


def test_live_scene_parser_exposes_dimmer_level() -> None:
    payload = b"\x04" + struct.pack("<II", 0, 0) + bytes((101, 5, 0, 255, 0, 128, 64))
    assert FmMasterClient.parse_dimmer_level(payload) == 64


def test_live_scene_parser_rejects_non_fm_master_scene() -> None:
    try:
        FmMasterClient.parse_dimmer_level(b"\0" * 16)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid scene was accepted")

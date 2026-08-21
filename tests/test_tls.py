from pathlib import Path

from custom_components.oase_fm.tls import create_server_context


def test_create_server_context_generates_easycontrol_certificate(tmp_path: Path) -> None:
    context = create_server_context(tmp_path)

    assert context.minimum_version.name == "TLSv1_2"
    assert context.maximum_version.name == "TLSv1_2"
    assert (tmp_path / "oase-easycontrol-cert.pem").is_file()
    assert (tmp_path / "oase-easycontrol-key.pem").is_file()


def test_create_server_context_reuses_certificate(tmp_path: Path) -> None:
    create_server_context(tmp_path)
    cert = tmp_path / "oase-easycontrol-cert.pem"
    first = cert.read_bytes()

    create_server_context(tmp_path)

    assert cert.read_bytes() == first

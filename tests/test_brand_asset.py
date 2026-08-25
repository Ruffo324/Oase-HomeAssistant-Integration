from pathlib import Path


def test_integration_includes_original_relay_mesh_icon() -> None:
    asset = Path("custom_components/oase_fm/icon.svg")
    text = asset.read_text(encoding="utf-8")

    assert asset.exists()
    assert "FM Relay Mesh" in text
    assert "<svg" in text
    assert "<text" not in text
    assert "font-family" not in text
    assert "OASE" not in text
    assert "#102a43" in text
    assert "#63d4b1" in text
    assert "#f7c873" in text
    assert "aria-label" in text
    assert "role=\"img\"" in text

from pathlib import Path


ASSET = Path("addons/oase_fm_onboard/run.py")


def test_onboarding_ui_explains_each_credential_field() -> None:
    text = ASSET.read_text(encoding="utf-8")

    assert "Select the FM-Master Wi-Fi" in text
    assert "FM-Master access-point Wi-Fi password" in text
    assert "not the device password" in text
    assert "Device/O-Net password" in text
    assert "Home Wi-Fi network name" in text
    assert "Home Wi-Fi password for that network" in text
    assert "Do not enter credentials in Home Assistant chat" in text


def test_onboarding_ui_says_ethernet_remains_primary() -> None:
    text = ASSET.read_text(encoding="utf-8")

    assert "Ethernet remains the primary connection" in text
    assert "spare Wi-Fi adapter" in text

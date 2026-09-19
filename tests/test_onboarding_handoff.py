from custom_components.oase_fm.onboarding import build_onboarding_handoff


def test_handoff_uses_only_gateway_endpoint_and_user_provided_credentials() -> None:
    handoff = build_onboarding_handoff("device-secret", "Home WiFi", "home-secret")

    assert handoff["gateway_host"] == "192.168.1.1"
    assert handoff["device_password"] == "device-secret"
    assert handoff["wifi_ssid"] == "Home WiFi"
    assert handoff["wifi_password"] == "home-secret"


def test_handoff_rejects_non_ap_host() -> None:
    try:
        build_onboarding_handoff("x", "wifi", "y", gateway_host="192.168.178.20")
    except ValueError as error:
        assert "AP host" in str(error)
    else:
        raise AssertionError("non-AP host accepted")


def test_handoff_rejects_empty_secrets() -> None:
    for values in (("", "ssid", "pass"), ("device", "", "pass"), ("device", "ssid", "")):
        try:
            build_onboarding_handoff(*values)
        except ValueError:
            pass
        else:
            raise AssertionError("empty field accepted")

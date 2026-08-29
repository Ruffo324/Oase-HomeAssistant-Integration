import asyncio

from custom_components.oase_fm.config_flow import MODE_AP_ONBOARD, MODE_EXISTING, OaseFmConfigFlow


def test_config_flow_shows_mode_picker() -> None:
    flow = OaseFmConfigFlow()
    result = asyncio.run(flow.async_step_user())
    assert result["type"] == "form"
    assert result["step_id"] == "user"


def test_existing_lan_path_shows_host_and_password_form() -> None:
    flow = OaseFmConfigFlow()
    result = asyncio.run(flow.async_step_user({"setup_mode": MODE_EXISTING}))
    assert result["type"] == "form"
    assert result["step_id"] == "existing"


def test_ap_onboarding_separates_ap_access_from_home_wifi_credentials() -> None:
    flow = OaseFmConfigFlow()
    result = asyncio.run(flow.async_step_user({"setup_mode": MODE_AP_ONBOARD}))
    assert result["type"] == "form"
    assert result["step_id"] == "ap_access"
    schema = str(result["data_schema"])
    assert "host" in schema
    assert "password" in schema
    assert "wifi_ssid" not in schema
    assert "wifi_password" not in schema


def test_ap_onboarding_home_wifi_is_a_later_step(monkeypatch) -> None:
    flow = OaseFmConfigFlow()
    flow._onboarding_data = {"host": "192.168.1.1", "password": "x"}
    result = asyncio.run(flow.async_step_home_wifi())
    assert result["type"] == "form"
    assert result["step_id"] == "home_wifi"
    assert "wifi_ssid" in str(result["data_schema"])


def test_ap_onboarding_home_host_auto_discovers_gateway(monkeypatch) -> None:
    flow = OaseFmConfigFlow()
    flow._onboarding_data = {"password": "x"}

    async def discover() -> str:
        return "192.168.178.102"

    async def create(host: str, password: str):
        return {"type": "create_entry", "data": {"host": host, "password": password}}

    monkeypatch.setattr("custom_components.oase_fm.config_flow.async_discover_gateway_host", discover)
    flow._async_create_gateway_entry = create
    result = asyncio.run(flow.async_step_home_host())
    assert result["type"] == "create_entry"
    assert result["data"]["host"] == "192.168.178.102"


def test_create_gateway_entry() -> None:
    flow = OaseFmConfigFlow()

    async def set_unique_id(unique_id: str) -> None:
        return None

    flow.async_set_unique_id = set_unique_id
    flow._abort_if_unique_id_configured = lambda: None
    result = asyncio.run(flow._async_create_gateway_entry("192.168.178.102", "x"))
    assert result["type"] == "create_entry"
    assert result["data"]["host"] == "192.168.178.102"

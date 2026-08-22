import asyncio

from custom_components.oase_fm.config_flow import OaseFmConfigFlow


def test_config_flow_shows_home_network_form() -> None:
    flow = OaseFmConfigFlow()
    result = asyncio.run(flow.async_step_user())

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert "host" in str(result["data_schema"])
    assert "password" in str(result["data_schema"])


def test_config_flow_creates_entry() -> None:
    flow = OaseFmConfigFlow()

    async def set_unique_id(unique_id: str) -> None:
        return None

    flow.async_set_unique_id = set_unique_id
    flow._abort_if_unique_id_configured = lambda: None

    result = asyncio.run(flow.async_step_user({"host": "192.168.178.102", "password": "x"}))

    assert result["type"] == "create_entry"
    assert result["data"]["host"] == "192.168.178.102"

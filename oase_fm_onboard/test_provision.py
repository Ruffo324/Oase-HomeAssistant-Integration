import asyncio
from unittest.mock import AsyncMock, patch

from aiohttp.test_utils import make_mocked_request

from addons.oase_fm_onboard import run


def test_provision_passes_credentials_once_to_core_flow() -> None:
    request = make_mocked_request("POST", "/api/provision")
    request.json = AsyncMock(return_value={"device_password": "device", "wifi_ssid": "home", "wifi_password": "secret"})
    with patch.object(run, "start_core_onboarding", AsyncMock(return_value={"entry_id": "entry-1"})) as onboarding:
        response = asyncio.run(run.provision_gateway(request))
    assert response.status == 200
    assert response.text == '{"entry_id": "entry-1"}'
    onboarding.assert_awaited_once_with("device", "home", "secret")


def test_provision_rejects_missing_credentials() -> None:
    request = make_mocked_request("POST", "/api/provision")
    request.json = AsyncMock(return_value={"device_password": "device"})
    try:
        asyncio.run(run.provision_gateway(request))
    except Exception as error:
        assert getattr(error, "status", None) == 400
    else:
        raise AssertionError("missing credentials accepted")

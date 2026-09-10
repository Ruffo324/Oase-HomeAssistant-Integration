import asyncio
import importlib.util
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.setdefault("SUPERVISOR_TOKEN", "test")
spec = importlib.util.spec_from_file_location("run", Path(__file__).with_name("run.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_scan_filters_oase_access_points() -> None:
    async def request(*args, **kwargs):
        if args[1] == "GET" and args[2] == "/network/info":
            return {"interfaces": [{"interface": "eth0", "type": "ethernet"}, {"interface": "wlan0", "type": "wireless"}]}
        return {"accesspoints": [{"ssid": "Other", "signal": 99}, {"ssid": "OASE FM-Master EGC Cloud 91", "signal": 42}]}

    with patch.object(module, "supervisor", request):
        from aiohttp.test_utils import make_mocked_request
        response = asyncio.run(module.get_access_points(make_mocked_request("GET", "/api/scan")))
    assert response.status == 200
    assert "OASE FM-Master EGC Cloud 91" in response.text
    assert '"Other"' not in response.text


def test_join_refuses_non_oase_ssid() -> None:
    from aiohttp.test_utils import make_mocked_request
    request = make_mocked_request("POST", "/api/join")
    request.json = AsyncMock(return_value={"interface": "wlan0", "ssid": "Other", "password": "secret"})
    try:
        asyncio.run(module.join_access_point(request))
    except Exception as error:
        assert getattr(error, "status", None) == 400
    else:
        raise AssertionError("non-OASE SSID accepted")

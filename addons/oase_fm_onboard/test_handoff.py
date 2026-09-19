import asyncio
import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SUPERVISOR_TOKEN", "test")
spec = importlib.util.spec_from_file_location("onboard_run", Path(__file__).with_name("run.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_config_flow_handoff_runs_ap_steps_in_order() -> None:
    calls = []

    async def core(method, path, payload=None):
        calls.append((method, path, payload))
        responses = [
            {"flow_id": "flow-1", "step_id": "user"},
            {"flow_id": "flow-1", "step_id": "ap_access"},
            {"flow_id": "flow-1", "step_id": "home_wifi"},
            {"type": "create_entry", "result": {"entry_id": "entry-1"}},
        ]
        return responses[len(calls) - 1]

    with patch.object(module, "core", core):
        result = asyncio.run(module.start_core_onboarding("device", "Home", "wifi-pass"))

    assert result["entry_id"] == "entry-1"
    assert calls[1][2] == {"setup_mode": "ap_onboard"}
    assert calls[2][2] == {"host": "192.168.1.1", "password": "device"}
    assert calls[3][2] == {"wifi_ssid": "Home", "wifi_password": "wifi-pass"}


def test_config_flow_handoff_rejects_unexpected_step() -> None:
    async def core(*_args, **_kwargs):
        return {"flow_id": "flow-1", "step_id": "wrong"}

    with patch.object(module, "core", core):
        try:
            asyncio.run(module.start_core_onboarding("device", "Home", "wifi-pass"))
        except RuntimeError as error:
            assert "Unexpected" in str(error)
        else:
            raise AssertionError("unexpected flow response accepted")

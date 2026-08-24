import asyncio

from custom_components.oase_fm.onboarding import async_discover_gateway_host


async def found_probe() -> str | None:
    return "192.168.178.102"


async def missing_probe() -> str | None:
    return None


def test_ap_onboarding_discovers_lan_gateway_address() -> None:
    assert asyncio.run(async_discover_gateway_host(found_probe)) == "192.168.178.102"


def test_ap_onboarding_returns_none_until_gateway_has_dhcp_lease() -> None:
    assert asyncio.run(async_discover_gateway_host(missing_probe)) is None

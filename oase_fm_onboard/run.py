"""Ingress companion App: supervisor-controlled spare Wi-Fi AP joining."""

from __future__ import annotations

import json
import os
from aiohttp import web, ClientSession

SUPERVISOR = "http://supervisor"
TOKEN = os.environ["SUPERVISOR_TOKEN"]
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


async def supervisor(session: ClientSession, method: str, path: str, payload: dict | None = None) -> dict:
    async with session.request(method, f"{SUPERVISOR}{path}", headers=HEADERS, json=payload) as response:
        response.raise_for_status()
        data = await response.json()
    if data.get("result") != "ok":
        raise web.HTTPBadGateway(text=data.get("message", "Supervisor request failed"))
    return data["data"]


async def core(method: str, path: str, payload: dict | None = None) -> dict:
    """Call HA Core via the authenticated Supervisor proxy."""
    async with ClientSession() as session:
        async with session.request(method, f"{SUPERVISOR}/core/api{path}", headers=HEADERS, json=payload) as response:
            response.raise_for_status()
            return await response.json()


async def start_core_onboarding(device_password: str, wifi_ssid: str, wifi_password: str) -> dict:
    """Drive the existing integration config flow after the App joined its AP."""
    if not all((device_password, wifi_ssid, wifi_password)):
        raise ValueError("device and home Wi-Fi credentials are required")
    flow = await core("POST", "/config/config_entries/flow", {"handler": "oase_fm"})
    if flow.get("step_id") != "user":
        raise RuntimeError("Unexpected integration start response")
    flow_id = flow["flow_id"]
    flow = await core("POST", f"/config/config_entries/flow/{flow_id}", {"setup_mode": "ap_onboard"})
    if flow.get("step_id") != "ap_access":
        raise RuntimeError("Unexpected AP access response")
    flow = await core("POST", f"/config/config_entries/flow/{flow_id}", {"host": "192.168.1.1", "password": device_password})
    if flow.get("step_id") != "home_wifi":
        raise RuntimeError("Unexpected home Wi-Fi response")
    result = await core("POST", f"/config/config_entries/flow/{flow_id}", {"wifi_ssid": wifi_ssid, "wifi_password": wifi_password})
    if result.get("type") != "create_entry":
        raise RuntimeError("Gateway provisioning did not complete")
    return result.get("result", {})


async def wireless_interfaces(session: ClientSession) -> list[dict]:
    data = await supervisor(session, "GET", "/network/info")
    return [item for item in data["interfaces"] if item.get("type") == "wireless"]


async def get_access_points(request: web.Request) -> web.Response:
    async with ClientSession() as session:
        interfaces = await wireless_interfaces(session)
        result = []
        for interface in interfaces:
            name = interface["interface"]
            scan = await supervisor(session, "GET", f"/network/interface/{name}/accesspoints")
            for ap in scan.get("accesspoints", []):
                if ap.get("ssid", "").lower().startswith("oase fm-master"):
                    result.append({"interface": name, "ssid": ap["ssid"], "signal": ap.get("signal", 0)})
    return web.json_response(sorted(result, key=lambda item: item["signal"], reverse=True))


async def join_access_point(request: web.Request) -> web.Response:
    body = await request.json()
    interface, ssid, password = (body.get(key, "") for key in ("interface", "ssid", "password"))
    if not interface or not ssid or not password or not ssid.lower().startswith("oase fm-master"):
        raise web.HTTPBadRequest(text="Select an OASE FM-Master AP and supply its password")
    async with ClientSession() as session:
        interfaces = await wireless_interfaces(session)
        if interface not in {item["interface"] for item in interfaces}:
            raise web.HTTPBadRequest(text="Unknown wireless interface")
        await supervisor(session, "POST", f"/network/interface/{interface}/update", {
            "enabled": True,
            "ipv4": {"method": "auto"},
            "ipv6": {"method": "disabled"},
            "wifi": {"mode": "infrastructure", "ssid": ssid, "psk": password},
        })
    return web.json_response({"joined": True, "gateway_host": "192.168.1.1"})


async def provision_gateway(request: web.Request) -> web.Response:
    body = await request.json()
    device_password = body.get("device_password", "")
    wifi_ssid = body.get("wifi_ssid", "")
    wifi_password = body.get("wifi_password", "")
    if not all(isinstance(value, str) and value for value in (device_password, wifi_ssid, wifi_password)):
        raise web.HTTPBadRequest(text="Device and home Wi-Fi credentials are required")
    try:
        result = await start_core_onboarding(device_password, wifi_ssid, wifi_password)
    except (ConnectionError, OSError, RuntimeError, ValueError) as error:
        raise web.HTTPBadGateway(text="Home Assistant onboarding did not complete") from error
    return web.json_response({"entry_id": result.get("entry_id")})


async def index(_: web.Request) -> web.Response:
    return web.Response(text="""<!doctype html><meta charset=utf-8><title>FM-Master Onboarding</title>
<style>body{font:16px/1.45 system-ui;margin:2rem;max-width:42rem}label,input,select,button{display:block;margin:.55rem 0;width:100%;box-sizing:border-box}input,select{padding:.55rem}button{padding:.7rem}small{display:block;color:#68768a;margin:-.25rem 0 .8rem}section{border:1px solid #7d8b9d;border-radius:.6rem;padding:1rem;margin:1rem 0}#status{white-space:pre-wrap}</style>
<h2>FM-Master AP onboarding</h2><p>Ethernet remains the primary connection. This App uses only a spare Wi-Fi adapter.</p>
<section><h3>Step 1 — Connect the HA spare Wi-Fi adapter to the reset gateway</h3><p>Tap scan, then select the FM-Master Wi-Fi whose name starts with <b>OASE FM-Master…</b>. Do not select your normal home Wi-Fi here.</p>
<button onclick='scan()'>Scan FM-Master gateways</button>
<label>Gateway AP<select id=ap required><option>Scan first</option></select></label><small>Select the FM-Master Wi-Fi found by this App.</small>
<label>Gateway AP password<input id=apPassword type=password required autocomplete=new-password></label><small>FM-Master access-point Wi-Fi password. This is not the device password and not your home Wi-Fi password.</small>
<button onclick='join()'>Join gateway AP</button></section>
<section><h3>Step 2 — Move the FM-Master itself onto your home Wi-Fi</h3><p>Complete this only after Step 1 says the gateway AP is joined. Credentials are sent once to Home Assistant and not stored by this App.</p>
<label>FM-Master device password<input id=devicePassword type=password autocomplete=new-password></label><small>Device/O-Net password used to authenticate to the FM-Master. This is not either Wi-Fi password.</small>
<label>Home Wi-Fi SSID<input id=homeSsid autocomplete=off></label><small>Home Wi-Fi network name: the SSID the FM-Master should join, for example <b>LoboMifi</b>.</small>
<label>Home Wi-Fi password<input id=homePassword type=password autocomplete=new-password></label><small>Home Wi-Fi password for that network.</small>
<button onclick='provision()'>Provision and add integration</button></section><p><b>Do not enter credentials in Home Assistant chat.</b></p><p id=status></p>
<script>
async function api(path,body){let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)throw Error(await r.text());return r.json()}
async function scan(){let s=document.querySelector('#status'),a=document.querySelector('#ap');s.textContent='Scanning…';try{let r=await fetch('api/scan');let x=await r.json();a.innerHTML=x.map(v=>`<option value="${v.interface}|${v.ssid}">${v.ssid} (${v.signal}%) — ${v.interface}</option>`).join('')||'<option>No FM-Master AP found</option>';s.textContent=x.length?'Select a gateway AP.':'No FM-Master AP found.'}catch(e){s.textContent='Scan failed: '+e}}
async function join(){let [i,...rest]=document.querySelector('#ap').value.split('|'),ssid=rest.join('|'),password=document.querySelector('#apPassword').value,s=document.querySelector('#status');if(!ssid||!password){s.textContent='Select an AP and enter its password.';return}s.textContent='Joining gateway AP…';try{await api('api/join',{interface:i,ssid,password});document.querySelector('#apPassword').value='';s.textContent='Gateway AP joined. Enter the device password and destination home Wi-Fi below.'}catch(e){s.textContent='Join failed: '+e}}
async function provision(){let s=document.querySelector('#status'),device_password=document.querySelector('#devicePassword').value,wifi_ssid=document.querySelector('#homeSsid').value,wifi_password=document.querySelector('#homePassword').value;if(!device_password||!wifi_ssid||!wifi_password){s.textContent='Enter all gateway and home Wi-Fi credentials.';return}s.textContent='Provisioning gateway and verifying home-network connection…';try{let x=await api('api/provision',{device_password,wifi_ssid,wifi_password});s.textContent='Complete. Integration entry: '+(x.entry_id||'created')}catch(e){s.textContent='Provisioning failed: '+e}finally{document.querySelector('#devicePassword').value='';document.querySelector('#homePassword').value=''}}
</script>""", content_type="text/html")

app = web.Application()
app.add_routes([
    web.get("/", index),
    web.get("/api/scan", get_access_points),
    web.post("/api/join", join_access_point),
    web.post("/api/provision", provision_gateway),
])

if __name__ == "__main__":
    web.run_app(app, port=8099)

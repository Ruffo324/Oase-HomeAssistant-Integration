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


async def index(_: web.Request) -> web.Response:
    return web.Response(text="""<!doctype html><meta charset=utf-8><title>FM-Master Onboarding</title>
<style>body{font:16px system-ui;margin:2rem;max-width:38rem}label,input,select,button{display:block;margin:.6rem 0;width:100%;box-sizing:border-box}button{padding:.6rem}#status{white-space:pre-wrap}</style>
<h2>FM-Master AP onboarding</h2><p>Ethernet remains the primary connection. This App uses only a spare Wi-Fi adapter.</p>
<button onclick='scan()'>Scan FM-Master gateways</button>
<label>Gateway AP<select id=ap required><option>Scan first</option></select></label>
<label>Gateway AP password<input id=p type=password required autocomplete=new-password></label>
<button onclick='join()'>Join gateway AP</button><p id=status></p>
<script>
async function scan(){let s=document.querySelector('#status'),a=document.querySelector('#ap');s.textContent='Scanning…';try{let r=await fetch('api/scan');let x=await r.json();a.innerHTML=x.map(v=>`<option value="${v.interface}|${v.ssid}">${v.ssid} (${v.signal}%) — ${v.interface}</option>`).join('')||'<option>No FM-Master AP found</option>';s.textContent=x.length?'Select a gateway AP.':'No FM-Master AP found.'}catch(e){s.textContent='Scan failed: '+e}}
async function join(){let [i,...rest]=document.querySelector('#ap').value.split('|'),ssid=rest.join('|'),password=document.querySelector('#p').value,s=document.querySelector('#status');if(!ssid||!password){s.textContent='Select an AP and enter its password.';return}s.textContent='Joining gateway AP…';try{let r=await fetch('api/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({interface:i,ssid,password})});if(!r.ok)throw Error(await r.text());s.textContent='Connected. Now open Settings → Devices & services → Add integration → OASE FM-Master Local, choose Gateway AP onboarding, and use 192.168.1.1.';password='';document.querySelector('#p').value=''}catch(e){s.textContent='Join failed: '+e}}
</script>""", content_type="text/html")

app = web.Application()
app.add_routes([web.get("/", index), web.get("/api/scan", get_access_points), web.post("/api/join", join_access_point)])

if __name__ == "__main__":
    web.run_app(app, port=8099)

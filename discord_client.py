"""
Cliente nativo de Discord para Antigravity en ambos PCs.
Lee automáticamente el token y guild_id desde config_discord.json (en OneDrive).
Zero-dependencias externas (usa urllib y json estándar de Python).
"""

import json
import os
import sys
import urllib.error
import urllib.request

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config_discord.json")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_headers():
    cfg = load_config()
    return {
        "Authorization": f"Bot {cfg['token']}",
        "Content-Type": "application/json",
        "User-Agent": "AntigravityDiscordClient/1.0"
    }

def request(endpoint, method="GET", data=None):
    url = f"https://discord.com/api/v10{endpoint}"
    headers = get_headers()
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code}: {error_msg}")

def get_channels():
    cfg = load_config()
    return request(f"/guilds/{cfg['guild_id']}/channels")

def get_messages(channel_id, limit=10):
    return request(f"/channels/{channel_id}/messages?limit={limit}")

def send_message(channel_id, content=None, embeds=None):
    payload = {}
    if content:
        payload["content"] = content
    if embeds:
        payload["embeds"] = embeds
    return request(f"/channels/{channel_id}/messages", method="POST", data=payload)

def get_roles():
    cfg = load_config()
    return request(f"/guilds/{cfg['guild_id']}/roles")

def create_role(name, color=0, hoist=False, mentionable=False):
    cfg = load_config()
    payload = {
        "name": name,
        "color": color,
        "hoist": hoist,
        "mentionable": mentionable
    }
    return request(f"/guilds/{cfg['guild_id']}/roles", method="POST", data=payload)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python discord_client.py [channels|messages <cid>|roles]")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "channels":
        for c in get_channels():
            print(f"[{c.get('type')}] {c.get('name')} -> {c.get('id')}")
    elif cmd == "roles":
        for r in get_roles():
            print(f"{r.get('name')} -> {r.get('id')}")
    elif cmd == "messages" and len(sys.argv) > 2:
        cid = sys.argv[2]
        for m in get_messages(cid):
            print(f"[{m.get('author', {}).get('username')}]: {m.get('content')}")

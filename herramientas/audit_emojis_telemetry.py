"""
Script de auditoría integral de telemetría y copia de seguridad de emojis para Discord.
Descarga los 124 emojis en alta calidad a datos_locales/emojis_backup/, genera manifest.json,
y escanea el historial de mensajes y reacciones de todos los canales de texto para compilar
las métricas de uso real antes de la expiración del Server Boost (2 de noviembre de 2026).
"""

import os
import sys
import json
import time
import re
import hashlib
import urllib.request
import urllib.error

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import discord_client as dc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(BASE_DIR, "datos_locales", "emojis_backup")
MANIFEST_PATH = os.path.join(BACKUP_DIR, "manifest.json")
TELEMETRY_DATA_PATH = os.path.join(BASE_DIR, "datos_locales", "telemetria_emojis.json")

HEADERS = {
    "User-Agent": "AntigravityEmojiAuditor/1.0 (Windows NT 10.0; Win64; x64)"
}

def request_with_retry(endpoint, method="GET", data=None, max_retries=6):
    """Petición a la API de Discord con control automático de rate limits (HTTP 429)."""
    cfg = dc.load_config()
    headers = {
        "Authorization": f"Bot {cfg['token']}",
        "Content-Type": "application/json",
        "User-Agent": "AntigravityDiscordClient/1.0"
    }
    url = f"https://discord.com/api/v10{endpoint}"
    body = json.dumps(data).encode("utf-8") if data else None

    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            time.sleep(0.12)  # Delay preventivo para no ahogar la API
            with urllib.request.urlopen(req) as resp:
                content = resp.read().decode("utf-8")
                return json.loads(content) if content.strip() else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            if e.code == 429:
                try:
                    retry_info = json.loads(err_body)
                    retry_after = float(retry_info.get("retry_after", 1.0))
                except Exception:
                    retry_after = 1.0
                print(f"⚠️ [Rate Limit 429] Esperando {retry_after:.2f}s antes de reintentar (intento {attempt + 1}/{max_retries})...")
                time.sleep(retry_after + 0.25)
                continue
            elif e.code in (500, 502, 503, 504):
                print(f"⚠️ [HTTP {e.code}] Error temporal de Discord. Esperando 2s...")
                time.sleep(2.0)
                continue
            else:
                raise RuntimeError(f"HTTP {e.code}: {err_body}")
    raise RuntimeError(f"Falló la petición a {endpoint} tras {max_retries} reintentos.")

def fetch_guild_emojis():
    cfg = dc.load_config()
    guild_id = cfg["guild_id"]
    return request_with_retry(f"/guilds/{guild_id}/emojis")

def backup_emojis(emojis):
    """Descarga los 124 emojis desde la CDN de Discord y genera manifest.json."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    print(f"📦 Iniciando descarga de respaldo de {len(emojis)} emojis en: {BACKUP_DIR}")
    
    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_emojis": len(emojis),
        "static_count": sum(1 for e in emojis if not e.get("animated")),
        "animated_count": sum(1 for e in emojis if e.get("animated")),
        "emojis": []
    }
    
    for idx, emoji in enumerate(emojis, 1):
        eid = str(emoji["id"])
        ename = emoji["name"]
        animated = bool(emoji.get("animated"))
        ext = "gif" if animated else "png"
        filename = f"{idx:03d}_{ename}_{eid}.{ext}"
        filepath = os.path.join(BACKUP_DIR, filename)
        
        cdn_url = f"https://cdn.discordapp.com/emojis/{eid}.{ext}?size=128"
        
        # Descargar archivo si no existe
        try:
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                with open(filepath, "rb") as f:
                    data = f.read()
            else:
                req = urllib.request.Request(cdn_url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                with open(filepath, "wb") as f:
                    f.write(data)
                
            sha256 = hashlib.sha256(data).hexdigest()
            size = len(data)
            
            manifest["emojis"].append({
                "slot_index": idx,
                "id": eid,
                "name": ename,
                "animated": animated,
                "filename": filename,
                "size_bytes": size,
                "sha256": sha256,
                "cdn_url": cdn_url
            })
            if idx % 20 == 0 or idx == len(emojis):
                print(f"  -> Descargados {idx}/{len(emojis)} emojis...")
        except Exception as ex:
            print(f"❌ Error descargando emoji {ename} ({eid}): {ex}")
            
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Copia de seguridad completada. Manifiesto guardado en: {MANIFEST_PATH}")
    return manifest

def scan_channel_history(channel_id, channel_name):
    """Escanea el historial completo de mensajes y reacciones de un canal."""
    messages = []
    last_id = None
    batch_count = 0
    
    while True:
        endpoint = f"/channels/{channel_id}/messages?limit=100"
        if last_id:
            endpoint += f"&before={last_id}"
            
        try:
            batch = request_with_retry(endpoint)
        except Exception as e:
            print(f"  ❌ Error escaneando #{channel_name}: {e}")
            break
            
        if not batch:
            break
            
        messages.extend(batch)
        last_id = batch[-1]["id"]
        batch_count += 1
        
        # Si ya hemos obtenido suficientes lotes o el canal es gigante, informar progreso
        if batch_count % 10 == 0:
            print(f"    ... {len(messages)} mensajes recopilados de #{channel_name}...")
            
    return messages

def analyze_telemetry(emojis):
    """Ejecuta el escaneo de telemetría en todos los canales de texto."""
    cfg = dc.load_config()
    channels = request_with_retry(f"/guilds/{cfg['guild_id']}/channels")
    text_channels = [c for c in channels if c.get("type") in (0, 5)]
    text_channels.sort(key=lambda x: x.get("position", 0))
    
    print(f"\n🔍 Canales de texto a auditar: {len(text_channels)}")
    
    # Mapeo de emojis para búsqueda rápida
    emoji_by_id = {str(e["id"]): e for e in emojis}
    emoji_by_name = {e["name"].lower(): e for e in emojis}
    
    # Contadores
    stats = {}
    for idx, e in enumerate(emojis, 1):
        eid = str(e["id"])
        stats[eid] = {
            "slot_index": idx,
            "id": eid,
            "name": e["name"],
            "animated": bool(e.get("animated")),
            "body_uses": 0,
            "reaction_uses": 0,
            "total_uses": 0,
            "channels": {},
            "users": {}
        }
        
    channel_summary = []
    total_messages_guild = 0
    total_reactions_guild = 0
    
    # Regex para capturar emojis custom: <:name:id> o <a:name:id>
    custom_emoji_regex = re.compile(r"<a?:([a-zA-Z0-9_]+):([0-9]+)>")
    # Regex para capturar emojis con formato :name: en texto plano (se aplica sobre texto sin menciones estructuradas)
    plain_emoji_regex = re.compile(r":([a-zA-Z0-9_]+):")
    
    start_time = time.time()
    
    for c in text_channels:
        cid = c["id"]
        cname = c.get("name", "sin-nombre")
        print(f"📖 Escaneando #{cname} (ID: {cid})...")
        
        msgs = scan_channel_history(cid, cname)
        msg_count = len(msgs)
        reaction_count_channel = 0
        emojis_used_in_channel = set()
        
        for m in msgs:
            content = m.get("content", "")
            author = m.get("author", {})
            author_tag = f"{author.get('username', 'desc')}"
            
            # 1. Emojis en cuerpo del mensaje
            # Buscar menciones estructuradas <:name:id> / <a:name:id>
            found_by_id = custom_emoji_regex.findall(content)
            for ename, eid in found_by_id:
                if eid in stats:
                    stats[eid]["body_uses"] += 1
                    stats[eid]["channels"][cname] = stats[eid]["channels"].get(cname, 0) + 1
                    stats[eid]["users"][author_tag] = stats[eid]["users"].get(author_tag, 0) + 1
                    emojis_used_in_channel.add(eid)
                    
            # Buscar menciones en texto plano :name: (solo si no fueron capturadas por custom_emoji_regex)
            # Primero retiramos los custom ya capturados para evitar doble conteo
            cleaned_content = custom_emoji_regex.sub(" ", content)
            plain_matches = plain_emoji_regex.findall(cleaned_content)
            for match in plain_matches:
                pname = match[0].lower()
                if pname in emoji_by_name:
                    target_emoji = emoji_by_name[pname]
                    target_id = str(target_emoji["id"])
                    stats[target_id]["body_uses"] += 1
                    stats[target_id]["channels"][cname] = stats[target_id]["channels"].get(cname, 0) + 1
                    stats[target_id]["users"][author_tag] = stats[target_id]["users"].get(author_tag, 0) + 1
                    emojis_used_in_channel.add(target_id)
            
            # 2. Reacciones en el mensaje
            reactions = m.get("reactions", [])
            for r in reactions:
                rcount = r.get("count", 0)
                reaction_count_channel += rcount
                remoji = r.get("emoji", {})
                reid = str(remoji.get("id")) if remoji.get("id") else None
                rname = remoji.get("name")
                
                matched_id = None
                if reid and reid in stats:
                    matched_id = reid
                elif rname and rname.lower() in emoji_by_name:
                    matched_id = str(emoji_by_name[rname.lower()]["id"])
                    
                if matched_id:
                    stats[matched_id]["reaction_uses"] += rcount
                    stats[matched_id]["channels"][cname] = stats[matched_id]["channels"].get(cname, 0) + rcount
                    emojis_used_in_channel.add(matched_id)
                    
        total_messages_guild += msg_count
        total_reactions_guild += reaction_count_channel
        
        channel_summary.append({
            "id": cid,
            "name": cname,
            "messages_count": msg_count,
            "reactions_count": reaction_count_channel,
            "unique_emojis_used": len(emojis_used_in_channel)
        })
        print(f"  -> #{cname}: {msg_count} mensajes, {reaction_count_channel} reacciones, {len(emojis_used_in_channel)} emojis del server detectados.")
        
    elapsed = time.time() - start_time
    print(f"\n✨ Escaneo completado en {elapsed:.1f}s.")
    print(f"📊 Totales del Servidor: {total_messages_guild} mensajes, {total_reactions_guild} reacciones en {len(text_channels)} canales.")
    
    # Calcular totales
    for eid, s in stats.items():
        s["total_uses"] = s["body_uses"] + s["reaction_uses"]
        
    telemetry_result = {
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_messages": total_messages_guild,
        "total_reactions": total_reactions_guild,
        "channel_summary": channel_summary,
        "emojis_stats": stats
    }
    
    with open(TELEMETRY_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(telemetry_result, f, indent=2, ensure_ascii=False)
        
    return telemetry_result

def main():
    print("=" * 60)
    print("🚀 AUDITORÍA DE TELEMETRÍA Y COPIA DE SEGURIDAD DE EMOJIS")
    print("=" * 60)
    
    emojis = fetch_guild_emojis()
    print(f"Encontrados {len(emojis)} emojis en el servidor.")
    
    # 1. Copia de seguridad
    manifest = backup_emojis(emojis)
    
    # 2. Análisis de telemetría
    telemetry = analyze_telemetry(emojis)
    
    print("\n✅ Proceso completado exitosamente.")

if __name__ == "__main__":
    main()

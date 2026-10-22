"""
Script de migración integral de Muro de la Fama:
1. Elimina los 7 mensajes antiguos y planos de Cakey Bot en #⭐muro-de-la-fama⭐ (1548043919827271740).
2. Renderiza para cada uno su portada vintage 'The Sanvi Daily' con Pillow (Ediciones 1 a 7).
3. Publica cada portada con Embed dorado y botón interactivo [🔗 Ir al Mensaje].
4. Registra las entradas en datos/starboard.json (dejando next_edition_number = 8).
"""

import os
import io
import sys
import json
import time
import requests
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modulos.starboard import render_sanvi_daily_cover, STARBOARD_CHANNEL_ID, STARBOARD_DATA_PATH

CONFIG_PATH = os.path.join(BASE_DIR, "config", "config_discord.json")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# Datos de los 7 mensajes históricos auditados
HISTORICAL_MESSAGES = [
    {
        "edition": 1,
        "cakey_msg_id": "1548800878432100514",
        "orig_channel_id": "1455700883378536559",  # #🎮gaming-general🎮
        "orig_msg_id": "1547697788379341051",
        "author_id": "999304511464149104",  # mpx56.
        "author_name": "mpx56.",
        "content": "Me la intente ligar",
        "date_str": "13/09/2026",
        "stars_count": 3,
        "has_attachment": False,
    },
    {
        "edition": 2,
        "cakey_msg_id": "1548981156433764404",
        "orig_channel_id": "1455700883378536559",  # #🎮gaming-general🎮
        "orig_msg_id": "1547697699695108140",
        "author_id": "999304511464149104",  # mpx56.
        "author_name": "mpx56.",
        "content": "[Captura de conversación]",
        "date_str": "14/09/2026",
        "stars_count": 2,
        "has_attachment": True,
        "attachment_url": "https://cdn.discordapp.com/attachments/1455700883378536559/1547697699573342289/rn_image_picker_lib_temp_2b8355eb-a07c-4c3f-8f16-638c85e6075c.jpg",
    },
    {
        "edition": 3,
        "cakey_msg_id": "1548981200000127089",
        "orig_channel_id": "1455700883378536559",  # #🎮gaming-general🎮
        "orig_msg_id": "1547697853671931944",
        "author_id": "999304511464149104",  # mpx56.
        "author_name": "mpx56.",
        "content": "Xd y al siguiente dia a su amiga",
        "date_str": "14/09/2026",
        "stars_count": 2,
        "has_attachment": False,
    },
    {
        "edition": 4,
        "cakey_msg_id": "1549123507491709042",
        "orig_channel_id": "1532002622461050931",  # #🤝juegos-cooperativos🤝
        "orig_msg_id": "1549086901338767584",
        "author_id": "794223776215990332",  # terreneiror
        "author_name": "terreneiror",
        "content": "Pero no muy tarde q si no me pegan",
        "date_str": "14/09/2026",
        "stars_count": 3,
        "has_attachment": False,
    },
    {
        "edition": 5,
        "cakey_msg_id": "1550087542940897291",
        "orig_channel_id": "1549458785485987890",  # #🎰casino-y-apuestas🎰
        "orig_msg_id": "1550087354079903857",
        "author_id": "857923274771136522",  # joselito3499
        "author_name": "Joselito",
        "content": "Your boyfriend finds out you been succing other dicc. You get dumped and he takes 389 Porros.",
        "date_str": "17/09/2026",
        "stars_count": 2,
        "has_attachment": False,
    },
    {
        "edition": 6,
        "cakey_msg_id": "1557732041490174014",
        "orig_channel_id": "1446143938044887052",  # #🗨️la-shit-de-todos-los-dias🗨️
        "orig_msg_id": "1557054822543532185",
        "author_id": "794223776215990332",  # terreneiror
        "author_name": "terreneiror",
        "content": "A spike",
        "date_str": "08/10/2026",
        "stars_count": 2,
        "has_attachment": False,
    },
    {
        "edition": 7,
        "cakey_msg_id": "1557883569031090237",
        "orig_channel_id": "1549458785485987890",  # #🎰casino-y-apuestas🎰
        "orig_msg_id": "1557883502630805600",
        "author_id": "794223776215990332",  # terreneiror
        "author_name": "terreneiror",
        "content": "No Win en la Tragaperras de 300.000 Porros. Payout: 0 Porros.",
        "date_str": "08/10/2026",
        "stars_count": 2,
        "has_attachment": False,
    },
]

def main():
    cfg = load_config()
    token = cfg["token"]
    guild_id = cfg["guild_id"]

    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "AntigravityDiscordClient/1.0",
    }

    print("🚀 Iniciando migración de The Sanvi Daily en #⭐muro-de-la-fama⭐...")

    # 1. Eliminar mensajes antiguos de Cakey Bot
    print("\n🗑️ Eliminando los 7 mensajes antiguos de Cakey Bot...")
    for item in HISTORICAL_MESSAGES:
        cid = item["cakey_msg_id"]
        del_url = f"https://discord.com/api/v10/channels/{STARBOARD_CHANNEL_ID}/messages/{cid}"
        try:
            r = requests.delete(del_url, headers=headers)
            if r.status_code in (204, 200):
                print(f"  ✅ Mensaje Cakey Bot {cid} eliminado.")
            elif r.status_code == 404:
                print(f"  ℹ️ Mensaje Cakey Bot {cid} ya no existía.")
            else:
                print(f"  ⚠️ Error eliminando {cid}: HTTP {r.status_code}")
        except Exception as e:
            print(f"  ❌ Error en DELETE {cid}: {e}")
        time.sleep(0.5)

    # 2. Descargar avatares en caché
    avatar_cache = {}
    for item in HISTORICAL_MESSAGES:
        uid = item["author_id"]
        if uid not in avatar_cache:
            try:
                r_u = requests.get(f"https://discord.com/api/v10/users/{uid}", headers=headers)
                if r_u.status_code == 200:
                    u_data = r_u.json()
                    item["author_name"] = u_data.get("global_name") or u_data.get("username", item["author_name"])
                    av_hash = u_data.get("avatar")
                    if av_hash:
                        av_url = f"https://cdn.discordapp.com/avatars/{uid}/{av_hash}.png?size=256"
                        r_av = requests.get(av_url)
                        if r_av.status_code == 200:
                            avatar_cache[uid] = r_av.content
                            print(f"  👤 Avatar descargado para {item['author_name']}")
            except Exception as e:
                print(f"  ⚠️ Error obteniendo avatar de {uid}: {e}")

    # 3. Renderizar y publicar portadas históricas en orden
    starboard_data = {
        "next_edition_number": 8,
        "entries": {},
    }

    print("\n🎨 Renderizando y publicando las 7 portadas históricas...")
    for item in HISTORICAL_MESSAGES:
        ed = item["edition"]
        uid = item["author_id"]
        aname = item["author_name"]
        content = item["content"]
        dstr = item["date_str"]
        scount = item["stars_count"]
        orig_cid = item["orig_channel_id"]
        orig_mid = item["orig_msg_id"]

        # Descargar adjunto si existe
        att_bytes = None
        if item.get("has_attachment") and item.get("attachment_url"):
            try:
                r_att = requests.get(item["attachment_url"])
                if r_att.status_code == 200:
                    att_bytes = r_att.content
                    print(f"  🖼️ Adjunto descargado para Edición #{ed} ({len(att_bytes)} bytes)")
            except Exception as e:
                print(f"  ⚠️ Error descargando adjunto #{ed}: {e}")

        # Renderizar portada
        img_bytes = render_sanvi_daily_cover(
            author_name=aname,
            author_avatar_bytes=avatar_cache.get(uid),
            content=content,
            created_at_str=dstr,
            edition_num=ed,
            stars_count=scount,
            attachment_bytes=att_bytes,
        )

        # Construir payload para Discord
        filename = f"sanvi_daily_edicion_{ed}.png"
        payload = {
            "embeds": [
                {
                    "title": f"⭐ #{ed} | The Sanvi Daily",
                    "description": f"📰 Inmortalizado desde <#{orig_cid}> • Declaración de <@{uid}>.",
                    "color": 0xF59E0B,  # Dorado
                    "image": {
                        "url": f"attachment://{filename}"
                    },
                    "footer": {
                        "text": f"The Sanvi Daily • Edición Nº {ed} • {scount} ⭐"
                    },
                }
            ],
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "style": 5,
                            "label": "Ir al Mensaje",
                            "url": f"https://discord.com/channels/{guild_id}/{orig_cid}/{orig_mid}",
                            "emoji": {"name": "🔗"},
                        }
                    ],
                }
            ],
        }

        # Enviar vía Multipart POST a #⭐muro-de-la-fama⭐
        post_url = f"https://discord.com/api/v10/channels/{STARBOARD_CHANNEL_ID}/messages"
        files = {
            "files[0]": (filename, io.BytesIO(img_bytes), "image/png"),
        }
        data = {
            "payload_json": json.dumps(payload),
        }

        res = requests.post(post_url, headers=headers, data=data, files=files)
        if res.status_code in (200, 201):
            sent_id = res.json().get("id")
            print(f"  🎉 Edición #{ed} publicada con éxito (Mensaje ID: {sent_id})")

            # Registrar en persistencia
            entry_key = f"{orig_cid}_{orig_mid}"
            starboard_data["entries"][entry_key] = {
                "edition_number": ed,
                "orig_channel_id": int(orig_cid),
                "orig_message_id": int(orig_mid),
                "starboard_message_id": int(sent_id),
                "author_id": int(uid),
                "author_name": aname,
                "stars_count": scount,
                "stargazers": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "has_image": bool(att_bytes),
            }
        else:
            print(f"  ❌ Error publicando Edición #{ed}: HTTP {res.status_code} - {res.text}")

        time.sleep(1.0)  # Rate limit cordial

    # 4. Guardar datos en datos/starboard.json
    os.makedirs(os.path.dirname(STARBOARD_DATA_PATH), exist_ok=True)
    with open(STARBOARD_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(starboard_data, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Persistencia actualizada en {STARBOARD_DATA_PATH} con 7 entradas registradas.")
    print("✅ ¡Migración de The Sanvi Daily completada al 100%!")

if __name__ == "__main__":
    main()

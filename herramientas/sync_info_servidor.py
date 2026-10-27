"""
Script de sincronización y auditoría bidireccional de docs/INFO_SERVIDOR.md contra Discord API v10.
Opera como sensor determinista de telemetría, detectando altas, bajas, renombrados y desfases de censo.

Uso:
  python herramientas/sync_info_servidor.py               -> Auditoría completa bidireccional
  python herramientas/sync_info_servidor.py --update      -> Sincroniza censos y fechas deterministas en docs/INFO_SERVIDOR.md
  python herramientas/sync_info_servidor.py --json        -> Emite reporte estructurado en JSON para agentes
"""

from datetime import datetime
import json
import os
import re
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Asegurar path para importar discord_client
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import discord_client as dc

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INFO_DOC_PATH = os.path.join(BASE_DIR, "docs", "INFO_SERVIDOR.md")

CHANNEL_TYPE_MAP = {
    0: "Texto",
    2: "Voz",
    4: "Categoría",
    5: "Anuncios",
    13: "Stage",
    15: "Foro"
}

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

def fetch_discord_data():
    cfg = dc.load_config()
    guild_id = cfg["guild_id"]
    
    channels = dc.get_channels()
    roles = dc.get_roles()
    members = dc.request(f"/guilds/{guild_id}/members?limit=1000")
    
    bots = [m for m in members if m.get("user", {}).get("bot")]
    humans = [m for m in members if not m.get("user", {}).get("bot")]
    
    role_counts = {r["id"]: 0 for r in roles}
    for m in members:
        for rid in m.get("roles", []):
            if rid in role_counts:
                role_counts[rid] += 1
                
    roles_sorted = sorted(roles, key=lambda x: x.get("position", 0), reverse=True)
    categories = {c["id"]: c.get("name") for c in channels if c.get("type") == 4}
    
    return {
        "guild_id": guild_id,
        "channels": channels,
        "roles": roles_sorted,
        "role_counts": role_counts,
        "categories": categories,
        "total_channels": len(channels),
        "total_roles": len(roles),
        "total_members": len(members),
        "humans_count": len(humans),
        "bots_count": len(bots)
    }

def parse_doc_data():
    if not os.path.exists(INFO_DOC_PATH):
        raise FileNotFoundError(f"No existe el archivo {INFO_DOC_PATH}")
        
    with open(INFO_DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 1. Censos declarados en cabecera
    m_humans = re.search(r"(\d+)\s+usuarios humanos", content)
    m_bots = re.search(r"(\d+)\s+bots integrados", content)
    m_members = re.search(r"\*\*Total Miembros\*\*:\s+\*\*(\d+)\s+miembros\*\*", content)
    m_channels = re.search(r"\*\*Total Canales\*\*:\s+\*\*(\d+)\s+canales\*\*", content)
    m_roles = re.search(r"\*\*Total Roles\*\*:\s+\*\*(\d+)\s+roles\s+configurados\*\*", content)
    m_chan_title = re.search(r"## 📁 Categorías y Canales del Servidor \(Censo Real de (\d+) Canales\)", content)
    
    # 2. Canales delimitados en la sección de canales
    doc_channel_ids = set()
    doc_channels = {}
    m_chans_sec = re.search(r"## 📁 Categorías y Canales del Servidor.*?(?=## 📜 Reglamento)", content, re.DOTALL)
    if m_chans_sec:
        sec_text = m_chans_sec.group(0)
        # IDs de canales individuales
        for m in re.finditer(r"-\s+`?([#\w\s\-\u2600-\u27bf\U0001f300-\U0001f9ff]+?)`?\s+\(`?(\d{17,20})`?\s*\|\s*([^)]+)\)", sec_text):
            name, cid, ctype = m.group(1).strip("`# "), m.group(2), m.group(3).strip()
            doc_channel_ids.add(cid)
            doc_channels[cid] = {"name": name, "type": ctype}
            
        # IDs de categorías
        for m in re.finditer(r"###\s+\d+\.\s+([^\n]+?)\s+\(`?(\d{17,20})`?\)", sec_text):
            name, cid = m.group(1).strip("` "), m.group(2)
            doc_channel_ids.add(cid)
            doc_channels[cid] = {"name": name, "type": "Categoría"}
            
        # Fallback para IDs sueltos en esa sección
        for cid in re.findall(r"\(`?(\d{17,20})`?", sec_text):
            doc_channel_ids.add(cid)

    # 3. Roles delimitados en la sección de roles
    doc_role_ids = set()
    doc_roles = {}
    m_roles_sec = re.search(r"### Estructura y Jerarquía Completa de Roles.*?(?=## ⚡ Tasas de Ganancia)", content, re.DOTALL)
    if m_roles_sec:
        sec_text = m_roles_sec.group(0)
        for m in re.finditer(r"(?:Pos\s+\d+[:\.]|\d+\.\s+\*\*Pos\s+\d+\*\*:)?[^\n]*?`([^`\n]+)`\s+\(`?(\d{17,20})`?", sec_text):
            rname, rid = m.group(1).strip(), m.group(2)
            doc_role_ids.add(rid)
            doc_roles[rid] = rname
            
        # Fallback para IDs sueltos en la sección de roles
        for rid in re.findall(r"\(`?(\d{17,20})`?", sec_text):
            doc_role_ids.add(rid)

    return {
        "content": content,
        "humans_count": int(m_humans.group(1)) if m_humans else None,
        "bots_count": int(m_bots.group(1)) if m_bots else None,
        "total_members": int(m_members.group(1)) if m_members else None,
        "total_channels": int(m_channels.group(1)) if m_channels else None,
        "total_roles": int(m_roles.group(1)) if m_roles else None,
        "channel_title_count": int(m_chan_title.group(1)) if m_chan_title else None,
        "doc_channel_ids": doc_channel_ids,
        "doc_channels": doc_channels,
        "doc_role_ids": doc_role_ids,
        "doc_roles": doc_roles
    }

def run_bidirectional_audit():
    disc = fetch_discord_data()
    doc = parse_doc_data()
    
    delta = {
        "census": [],
        "missing_channels": [],
        "removed_channels": [],
        "renamed_channels": [],
        "missing_roles": [],
        "removed_roles": []
    }
    
    # 1. Censos
    if doc["total_members"] != disc["total_members"]:
        delta["census"].append(f"Total Miembros: Doc={doc['total_members']} vs Discord={disc['total_members']}")
    if doc["humans_count"] != disc["humans_count"]:
        delta["census"].append(f"Humanos: Doc={doc['humans_count']} vs Discord={disc['humans_count']}")
    if doc["bots_count"] != disc["bots_count"]:
        delta["census"].append(f"Bots: Doc={doc['bots_count']} vs Discord={disc['bots_count']}")
    if doc["total_channels"] != disc["total_channels"]:
        delta["census"].append(f"Total Canales: Doc={doc['total_channels']} vs Discord={disc['total_channels']}")
    if doc["channel_title_count"] != disc["total_channels"]:
        delta["census"].append(f"Título Sección Canales: Doc={doc['channel_title_count']} vs Discord={disc['total_channels']}")
    if doc["total_roles"] != disc["total_roles"]:
        delta["census"].append(f"Total Roles: Doc={doc['total_roles']} vs Discord={disc['total_roles']}")
        
    # 2. Canales Discord -> Doc
    discord_channel_ids = set()
    for c in disc["channels"]:
        cid = c["id"]
        cname = c.get("name", "")
        ctype = c.get("type", 0)
        parent_id = c.get("parent_id")
        parent_name = disc["categories"].get(parent_id, "Sin Categoría") if parent_id else "Raíz"
        discord_channel_ids.add(cid)
        
        if cid not in doc["doc_channel_ids"]:
            delta["missing_channels"].append({
                "id": cid,
                "name": cname,
                "type": CHANNEL_TYPE_MAP.get(ctype, str(ctype)),
                "parent_id": parent_id,
                "parent_name": parent_name
            })
        else:
            if cid in doc["doc_channels"]:
                doc_name = doc["doc_channels"][cid]["name"]
                if doc_name != cname and doc_name.strip("#") != cname.strip("#"):
                    if cname.lower() not in doc_name.lower() and doc_name.lower() not in cname.lower():
                        delta["renamed_channels"].append({
                            "id": cid,
                            "doc_name": doc_name,
                            "discord_name": cname
                        })

    # 3. Canales Doc -> Discord (detectar eliminados)
    for cid, cinfo in doc["doc_channels"].items():
        if cid not in discord_channel_ids:
            delta["removed_channels"].append({
                "id": cid,
                "name": cinfo["name"],
                "type": cinfo["type"]
            })

    # 4. Roles Discord -> Doc
    discord_role_ids = set()
    for r in disc["roles"]:
        rid = r["id"]
        rname = r.get("name", "")
        discord_role_ids.add(rid)
        if rname == "@everyone":
            continue
            
        if rid not in doc["doc_role_ids"]:
            delta["missing_roles"].append({
                "id": rid,
                "name": rname,
                "position": r.get("position", 0),
                "managed": r.get("managed", False),
                "count": disc["role_counts"].get(rid, 0)
            })

    # 5. Roles Doc -> Discord (detectar eliminados)
    for rid, rname in doc["doc_roles"].items():
        if rid not in discord_role_ids and rid != disc["guild_id"]:
            delta["removed_roles"].append({
                "id": rid,
                "name": rname
            })

    return disc, doc, delta

def sync_censuses_only(disc, doc):
    """Actualiza deterministamente los censos numéricos, títulos y fecha sin alterar el contenido semántico."""
    content = doc["content"]
    now = datetime.now()
    fecha_str = f"{now.day} de {MESES_ES.get(now.month, 'Octubre')} de {now.year}"
    changes = []
    
    # 1. Fecha de auditoría
    audit_regex = r"> \*\*Última auditoría integral\*\*:.*?\n"
    new_audit_line = f"> **Última auditoría integral**: {fecha_str} (Auditoría bidireccional API v10).\n"
    if re.search(audit_regex, content):
        content = re.sub(audit_regex, new_audit_line, content, count=1)
        changes.append("Fecha de auditoría integral actualizada.")
        
    # 2. Conteo de canales por tipo
    chans = disc["channels"]
    cats = [c for c in chans if c.get("type") == 4]
    texts = [c for c in chans if c.get("type") in (0, 5, 15)]
    voices = [c for c in chans if c.get("type") in (2, 13)]
    
    # 3. Censo de Miembros
    old_m = r"- \*\*Total Miembros\*\*: \*\*\d+ miembros\*\* \(\d+ usuarios humanos \+ \d+ bots integrados\)"
    new_m = f"- **Total Miembros**: **{disc['total_members']} miembros** ({disc['humans_count']} usuarios humanos + {disc['bots_count']} bots integrados)"
    if re.search(old_m, content):
        content = re.sub(old_m, new_m, content, count=1)
        changes.append(f"Censo de miembros: {disc['total_members']} ({disc['humans_count']} humanos, {disc['bots_count']} bots).")
        
    # 4. Censo de Canales
    old_c = r"- \*\*Total Canales\*\*: \*\*\d+ canales\*\* \(\d+ categorías, \d+ canales de texto/anuncios, \d+ canales de voz\)"
    new_c = f"- **Total Canales**: **{disc['total_channels']} canales** ({len(cats)} categorías, {len(texts)} canales de texto/anuncios, {len(voices)} canales de voz)"
    if re.search(old_c, content):
        content = re.sub(old_c, new_c, content, count=1)
        changes.append(f"Censo de canales: {disc['total_channels']} ({len(cats)} cats, {len(texts)} texto, {len(voices)} voz).")
        
    # 5. Censo de Roles
    old_r = r"- \*\*Total Roles\*\*: \*\*\d+ roles configurados\*\*"
    new_r = f"- **Total Roles**: **{disc['total_roles']} roles configurados**"
    if re.search(old_r, content):
        content = re.sub(old_r, new_r, content, count=1)
        changes.append(f"Censo de roles: {disc['total_roles']} roles.")
        
    # 6. Título de Sección de Canales
    old_t = r"## 📁 Categorías y Canales del Servidor \(Censo Real de \d+ Canales\)"
    new_t = f"## 📁 Categorías y Canales del Servidor (Censo Real de {disc['total_channels']} Canales)"
    if re.search(old_t, content):
        content = re.sub(old_t, new_t, content, count=1)
        changes.append(f"Título de sección de canales: Censo Real de {disc['total_channels']} Canales.")
        
    with open(INFO_DOC_PATH, "w", encoding="utf-8") as f:
        f.write(content)
        
    return changes

def main():
    json_mode = "--json" in sys.argv
    update_mode = "--update" in sys.argv
    
    try:
        disc, doc, delta = run_bidirectional_audit()
    except Exception as e:
        if json_mode:
            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"Error durante la auditoría: {e}")
        sys.exit(1)
        
    if json_mode:
        output = {
            "timestamp": datetime.now().isoformat(),
            "discord": {
                "total_members": disc["total_members"],
                "humans": disc["humans_count"],
                "bots": disc["bots_count"],
                "total_channels": disc["total_channels"],
                "total_roles": disc["total_roles"]
            },
            "delta": delta
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    print("═══════════════════════════════════════════════════════════════════")
    print("📡 AUDITORÍA BIDIRECCIONAL: DISCORD API v10 vs docs/INFO_SERVIDOR.md")
    print("═══════════════════════════════════════════════════════════════════")
    print(f"Estado en vivo: {disc['total_members']} miembros ({disc['humans_count']} humanos, {disc['bots_count']} bots), {disc['total_channels']} canales, {disc['total_roles']} roles.\n")
    
    total_issues = (
        len(delta["census"]) +
        len(delta["missing_channels"]) +
        len(delta["removed_channels"]) +
        len(delta["renamed_channels"]) +
        len(delta["missing_roles"]) +
        len(delta["removed_roles"])
    )
    
    if total_issues == 0:
        print("✅ El documento docs/INFO_SERVIDOR.md está 100% sincronizado con Discord. Cero discrepancias.")
        return
        
    print(f"⚠️ Se han detectado {total_issues} discrepancias:")
    
    if delta["census"]:
        print("\n📊 Desfases en Censos Globales:")
        for d in delta["census"]:
            print(f"  • {d}")
            
    if delta["missing_channels"]:
        print(f"\n➕ Canales en Discord no registrados en doc ({len(delta['missing_channels'])}):")
        for c in delta["missing_channels"]:
            print(f"  • [{c['type']}] '{c['name']}' (ID: {c['id']}) en '{c['parent_name']}'")
            
    if delta["removed_channels"]:
        print(f"\n❌ Canales en doc eliminados en Discord ({len(delta['removed_channels'])}):")
        for c in delta["removed_channels"]:
            print(f"  • '{c['name']}' (ID: {c['id']}, Tipo: {c['type']})")
            
    if delta["renamed_channels"]:
        print(f"\n✏️ Canales con discrepancia de nombre ({len(delta['renamed_channels'])}):")
        for c in delta["renamed_channels"]:
            print(f"  • ID {c['id']}: Doc='{c['doc_name']}' vs Discord='{c['discord_name']}'")
            
    if delta["missing_roles"]:
        print(f"\n➕ Roles en Discord no registrados en doc ({len(delta['missing_roles'])}):")
        for r in delta["missing_roles"]:
            tag = "Bot" if r["managed"] else f"{r['count']} miembros"
            print(f"  • '{r['name']}' (ID: {r['id']}, Pos: {r['position']}, {tag})")
            
    if delta["removed_roles"]:
        print(f"\n❌ Roles en doc eliminados en Discord ({len(delta['removed_roles'])}):")
        for r in delta["removed_roles"]:
            print(f"  • '{r['name']}' (ID: {r['id']})")
            
    if update_mode:
        print("\n🔧 Sincronizando censos y cabeceras deterministas...")
        changes = sync_censuses_only(disc, doc)
        for ch in changes:
            print(f"  ✓ {ch}")
            
        remaining_structural = (
            len(delta["missing_channels"]) +
            len(delta["removed_channels"]) +
            len(delta["missing_roles"]) +
            len(delta["removed_roles"])
        )
        if remaining_structural > 0:
            print(f"\n💡 [ACCIÓN SEMÁNTICA REQUERIDA]: Quedan {remaining_structural} cambios estructurales.")
            print("   El agente de IA debe integrar los canales/roles con el lore y formato canónico.")
        else:
            print("\n✅ docs/INFO_SERVIDOR.md ha quedado 100% sincronizado.")

if __name__ == "__main__":
    main()

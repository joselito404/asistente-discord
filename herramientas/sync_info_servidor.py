"""
Script de sincronización y auditoría automática de docs/INFO_SERVIDOR.md contra Discord API.
Permite auditar discrepancias en segundos y actualizar las tablas de canales, roles y censos.
Uso:
  python herramientas/sync_info_servidor.py          -> Audita y muestra discrepancias
  python herramientas/sync_info_servidor.py --update -> Sincroniza y actualiza docs/INFO_SERVIDOR.md
"""

from datetime import datetime
import os
import re
import sys

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
    
    return channels, roles, members

def audit_server():
    channels, roles, members = fetch_discord_data()
    
    # Análisis de miembros
    bots = [m for m in members if m.get("user", {}).get("bot")]
    humans = [m for m in members if not m.get("user", {}).get("bot")]
    
    # Análisis de roles y conteo de miembros
    role_counts = {r["id"]: 0 for r in roles}
    for m in members:
        for rid in m.get("roles", []):
            if rid in role_counts:
                role_counts[rid] += 1
    
    roles_sorted = sorted(roles, key=lambda x: x.get("position", 0), reverse=True)
    
    # Mapeo de canales por categoría
    categories = {c["id"]: c.get("name") for c in channels if c.get("type") == 4}
    
    report = {
        "total_channels": len(channels),
        "total_roles": len(roles),
        "total_members": len(members),
        "humans_count": len(humans),
        "bots_count": len(bots),
        "channels": channels,
        "roles_sorted": roles_sorted,
        "role_counts": role_counts,
        "categories": categories
    }
    return report

def compare_with_doc(report):
    if not os.path.exists(INFO_DOC_PATH):
        return ["El archivo docs/INFO_SERVIDOR.md no existe."]
    
    with open(INFO_DOC_PATH, "r", encoding="utf-8") as f:
        doc_content = f.read()
    
    discrepancies = []
    
    # Verificar canales en el documento
    for c in report["channels"]:
        cid = c.get("id")
        cname = c.get("name")
        if cid not in doc_content:
            discrepancies.append(f"Canal faltante en doc: '{cname}' (ID: {cid}, Tipo: {CHANNEL_TYPE_MAP.get(c.get('type'), c.get('type'))})")
            
    # Verificar roles en el documento
    for r in report["roles_sorted"]:
        rid = r.get("id")
        rname = r.get("name")
        if rname == "@everyone":
            continue
        if rid not in doc_content:
            discrepancies.append(f"Rol faltante en doc: '{rname}' (ID: {rid})")
            
    # Verificar censo
    m_human = re.search(r"(\d+)\s+humanos", doc_content)
    if m_human and int(m_human.group(1)) != report["humans_count"]:
        discrepancies.append(f"Censo de humanos desfasado: Doc={m_human.group(1)}, Real={report['humans_count']}")
        
    m_bots = re.search(r"(\d+)\s+bots", doc_content)
    if m_bots and int(m_bots.group(1)) != report["bots_count"]:
        discrepancies.append(f"Censo de bots desfasado: Doc={m_bots.group(1)}, Real={report['bots_count']}")

    m_channels = re.search(r"\*\*Total Canales\*\*:\s+\*\*(\d+)\s+canales\*\*", doc_content)
    if m_channels and int(m_channels.group(1)) != report["total_channels"]:
        discrepancies.append(f"Censo de canales desfasado: Doc={m_channels.group(1)}, Real={report['total_channels']}")

    m_roles = re.search(r"\*\*Total Roles\*\*:\s+\*\*(\d+)\s+roles\s+configurados\*\*", doc_content)
    if m_roles and int(m_roles.group(1)) != report["total_roles"]:
        discrepancies.append(f"Censo de roles desfasado: Doc={m_roles.group(1)}, Real={report['total_roles']}")
        
    return discrepancies

def update_doc(report):
    """Actualiza deterministamente docs/INFO_SERVIDOR.md sincronizando censos, canales y roles faltantes."""
    if not os.path.exists(INFO_DOC_PATH):
        raise FileNotFoundError(f"No se encontró {INFO_DOC_PATH}")

    with open(INFO_DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    changes = []
    now = datetime.now()
    fecha_str = f"{now.day} de {MESES_ES.get(now.month, 'Octubre')} de {now.year}"

    # 1. Actualizar fecha de última auditoría
    audit_regex = r"> \*\*Última auditoría integral\*\*:.*?\n"
    new_audit_line = f"> **Última auditoría integral**: {fecha_str} (Sincronización determinista vía API v10 de Discord).\n"
    if re.search(audit_regex, content):
        content = re.sub(audit_regex, new_audit_line, content, count=1)
        changes.append("Fecha de última auditoría actualizada.")

    # 2. Conteo de canales por tipo
    chans = report["channels"]
    cats = [c for c in chans if c.get("type") == 4]
    texts = [c for c in chans if c.get("type") in (0, 5, 15)]
    voices = [c for c in chans if c.get("type") in (2, 13)]

    # 3. Actualizar Datos Generales
    old_members_regex = r"- \*\*Total Miembros\*\*: \*\*\d+ miembros\*\* \(\d+ usuarios humanos \+ \d+ bots integrados\)"
    new_members_line = f"- **Total Miembros**: **{report['total_members']} miembros** ({report['humans_count']} usuarios humanos + {report['bots_count']} bots integrados)"
    if re.search(old_members_regex, content):
        content = re.sub(old_members_regex, new_members_line, content, count=1)
        changes.append(f"Censo de miembros: {report['total_members']} ({report['humans_count']} humanos + {report['bots_count']} bots).")

    old_channels_regex = r"- \*\*Total Canales\*\*: \*\*\d+ canales\*\* \(\d+ categorías, \d+ canales de texto/anuncios, \d+ canales de voz\)"
    new_channels_line = f"- **Total Canales**: **{report['total_channels']} canales** ({len(cats)} categorías, {len(texts)} canales de texto/anuncios, {len(voices)} canales de voz)"
    if re.search(old_channels_regex, content):
        content = re.sub(old_channels_regex, new_channels_line, content, count=1)
        changes.append(f"Censo de canales: {report['total_channels']} ({len(cats)} cats, {len(texts)} texto/anuncios, {len(voices)} voz).")

    old_roles_regex = r"- \*\*Total Roles\*\*: \*\*\d+ roles configurados\*\*"
    new_roles_line = f"- **Total Roles**: **{report['total_roles']} roles configurados**"
    if re.search(old_roles_regex, content):
        content = re.sub(old_roles_regex, new_roles_line, content, count=1)
        changes.append(f"Censo de roles: {report['total_roles']} roles.")

    # 4. Insertar canales faltantes en su respectiva categoría
    for c in chans:
        cid = c.get("id")
        cname = c.get("name")
        ctype = c.get("type")
        if cid in content:
            continue

        parent_id = c.get("parent_id")
        type_str = CHANNEL_TYPE_MAP.get(ctype, str(ctype))
        prefix = "#" if ctype in (0, 5, 15) else ""
        chan_line = f"- `{prefix}{cname}` (`{cid}` | {type_str}): Canal sincronizado automáticamente vía API v10."

        if parent_id and parent_id in content:
            # Buscar el encabezado de la categoría que contiene parent_id
            cat_pattern = rf"(### \d+\..*?`{parent_id}`\).*?\n)"
            m_cat = re.search(cat_pattern, content)
            if m_cat:
                pos = m_cat.end()
                # Insertar justo después del encabezado de la categoría
                content = content[:pos] + chan_line + "\n" + content[pos:]
                changes.append(f"Canal '{cname}' ({cid}) insertado en categoría parent `{parent_id}`.")
            else:
                # Insertar antes de la siguiente sección si la categoría está en el doc
                parent_idx = content.find(parent_id)
                next_newline = content.find("\n", parent_idx)
                content = content[:next_newline+1] + chan_line + "\n" + content[next_newline+1:]
                changes.append(f"Canal '{cname}' ({cid}) añadido junto al ID parent `{parent_id}`.")
        else:
            # Si no tiene categoría o es una categoría nueva, agregar al final de la sección de canales
            target = "## 📜 Reglamento Oficial"
            if target in content:
                content = content.replace(target, f"{chan_line}\n\n{target}")
            else:
                content += f"\n{chan_line}\n"
            changes.append(f"Canal/Categoría '{cname}' ({cid}) añadido.")

    # 5. Insertar roles faltantes
    for r in report["roles_sorted"]:
        rid = r.get("id")
        rname = r.get("name")
        if rname == "@everyone" or rid in content:
            continue

        pos = r.get("position", 0)
        managed = r.get("managed", False)
        count = report["role_counts"].get(rid, 0)
        tag_managed = "Bot Gestionado" if managed else f"{count} miembros"
        role_line = f"- `Pos {pos}`: `{rname}` (`{rid}` | {tag_managed}) — Rol sincronizado vía API v10."

        target_role = "38. **Pos 0**: `@everyone`"
        if target_role in content:
            content = content.replace(target_role, f"{role_line}\n38. **Pos 0**: `@everyone`")
        else:
            content += f"\n{role_line}\n"
        changes.append(f"Rol '{rname}' ({rid}) insertado.")

    with open(INFO_DOC_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    return changes

def main():
    update_mode = "--update" in sys.argv
    print("Conectando con la API de Discord...")
    try:
        report = audit_server()
    except Exception as e:
        print(f"Error conectando a Discord: {e}")
        sys.exit(1)
        
    print(f"Estado en vivo: {report['total_members']} miembros ({report['humans_count']} humanos, {report['bots_count']} bots), {report['total_channels']} canales, {report['total_roles']} roles.")
    
    discrepancies = compare_with_doc(report)
    if not discrepancies:
        print("El documento docs/INFO_SERVIDOR.md está 100% sincronizado con Discord. Cero discrepancias.")
        return
        
    print(f"Se han detectado {len(discrepancies)} discrepancias:")
    for d in discrepancies[:15]:
        print(f"  - {d}")
    if len(discrepancies) > 15:
        print(f"  ... y {len(discrepancies) - 15} discrepancias más.")
        
    if update_mode:
        print("\nModo actualización (--update) activado. Sincronizando...")
        changes = update_doc(report)
        print(f"Sincronización completada. Cambios aplicados ({len(changes)}):")
        for ch in changes:
            print(f"  ✓ {ch}")
        
        # Re-auditar
        print("\nVerificando sincronización posterior...")
        discrepancies_post = compare_with_doc(report)
        if not discrepancies_post:
            print("docs/INFO_SERVIDOR.md ha quedado 100% sincronizado sin discrepancias.")
        else:
            print(f"Quedan {len(discrepancies_post)} discrepancias pendientes:")
            for d in discrepancies_post:
                print(f"  - {d}")

if __name__ == "__main__":
    main()

---
name: sync-info-servidor
description: >-
  [Confirmada · Jose · 27/10/2026] (Origen: Antigravity-discord / Chat 3)
  Audita en tiempo real la estructura completa de canales, categorías, roles y censos del servidor
  de Discord contra la API v10 y sincroniza deterministamente docs/INFO_SERVIDOR.md.
  Activar cuando el usuario pida 'audita el servidor', 'sincroniza info servidor', 'sync canales',
  'audita canales y roles', o tras realizar modificaciones manuales o automáticas en Discord.
---

# Skill: Sincronización y Auditoría del Servidor (`sync-info-servidor`)

Esta skill permite auditar y sincronizar la estructura completa del servidor de Discord contra la API v10 oficial en menos de 2 segundos, actualizando de forma determinista el documento maestro [docs/INFO_SERVIDOR.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/INFO_SERVIDOR.md).

---

## 🚀 Cuándo Usar Esta Skill
- Tras crear, renombrar, mover o eliminar canales o categorías en Discord.
- Tras crear o alterar roles de usuario o bots en el servidor.
- Al cerrar un hito funcional que haya tocado la infraestructura de Discord.
- Antes de cerrar sesión o relevo entre chats para garantizar 0 discrepancias documentales (Regla de Documentación del Proyecto).

---

## 🛠️ Procedimiento de Ejecución

### Paso 1: Ejecutar la Sincronización Automática
Para sincronizar y actualizar el documento directamente:
```powershell
python herramientas/sync_info_servidor.py --update
```

*(Si únicamente se desea inspeccionar discrepancias sin modificar el documento, omitir `--update`)*:
```powershell
python herramientas/sync_info_servidor.py
```

### Paso 2: Verificar la Auditoría Posterior
El script verificará automáticamente tras el `--update` que las discrepancias sean 0:
- ✅ Censos globales actualizados (miembros humanos, bots, canales de texto, canales de voz, categorías y roles).
- ✅ Canales nuevos insertados en su categoría correspondiente.
- ✅ Roles nuevos registrados en la jerarquía.
- ✅ Fecha de última auditoría actualizada.

### Paso 3: Sincronización Atómica y Commit (§11 y §14)
1. Si hubo cambios en el censo total de canales o categorías, reflejarlos en [docs/README.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/README.md).
2. Realizar commit atómico:
   ```powershell
   git add docs/INFO_SERVIDOR.md docs/README.md
   git commit -m "docs: sincronizar info_servidor con API v10 de Discord"
   git push origin main
   ```

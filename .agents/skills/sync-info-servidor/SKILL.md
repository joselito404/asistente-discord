---
name: sync-info-servidor
description: >-
  [Confirmada · Jose · 27/10/2026] (Origen: Antigravity-discord / Chat 3)
  Audita en tiempo real la estructura completa de canales, categorías, roles y censos del servidor
  de Discord contra la API v10 y sincroniza docs/INFO_SERVIDOR.md mediante el modelo híbrido (sensor + agente).
  Activar cuando el usuario pida 'audita el servidor', 'sincroniza info servidor', 'sync canales',
  'audita canales y roles', o tras realizar modificaciones manuales o automáticas en Discord.
---

# Skill: Sincronización y Auditoría Bidireccional del Servidor (`sync-info-servidor`)

Esta skill audita la estructura completa del servidor de Discord contra la API v10 oficial en menos de 2 segundos mediante un **modelo híbrido en 2 etapas**: un escáner determinista bidireccional (`herramientas/sync_info_servidor.py`) y la inteligencia editorial del agente para preservar el lore y maquetación de [docs/INFO_SERVIDOR.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/INFO_SERVIDOR.md).

---

## 🚀 Cuándo Usar Esta Skill
- Tras crear, renombrar, mover o eliminar canales o categorías en Discord.
- Tras crear, renombrar o retirar roles de usuario o bots en el servidor.
- Al cerrar cualquier hito funcional que altere la infraestructura o miembros de Discord.
- Antes de cerrar sesión o relevo entre chats para garantizar **0 discrepancias documentales** (Regla de Documentación del Proyecto).

---

## 🛠️ Procedimiento Operativo Oficial (Modelo Híbrido)

### Fase 1: Diagnóstico con el Sensor Determinista
Ejecuta el escáner bidireccional para comparar el estado en vivo de Discord contra el documento:
```powershell
python herramientas/sync_info_servidor.py
```
*(Para obtener el delta estructurado en JSON, añade `--json`)*.

El script reportará:
1. **Censos globales**: Miembros humanos, bots, total canales (categorías, texto/anuncios, voz) y roles.
2. **Canales**:
   - `➕ Canales en Discord no registrados`: Con su tipo y categoría parent.
   - `❌ Canales en doc eliminados en Discord`: Canales obsoletos a purgar.
   - `✏️ Canales con discrepancia de nombre`: Cambios de nombre o emojis.
3. **Roles**:
   - `➕ Roles nuevos en Discord`.
   - `❌ Roles en doc eliminados en Discord`.

### Fase 2: Sincronización Determinista de Censos
Ejecuta el modo `--update` para sincronizar de forma segura los números, el título de sección y la fecha de auditoría:
```powershell
python herramientas/sync_info_servidor.py --update
```

### Fase 3: Cirugía Editorial Asistida por IA (Si hay Altas/Bajas)
Si el reporte de la Fase 1 detectó canales o roles añadidos, eliminados o renombrados:
1. **Canales nuevos**: El agente los ubica en su categoría correspondiente dentro de `docs/INFO_SERVIDOR.md`, maquetando sus viñetas y redactando su *topic* con coherencia de lore y permisos.
2. **Canales/roles eliminados**: El agente retira las líneas obsoletas (ej. bots retirados como UnbelievaBoat).
3. **Renombrados**: El agente actualiza el nombre preservando la descripción.

### Fase 4: Verificación Final y Cierre Atómico (§11 y §14)
1. Ejecuta nuevamente `python herramientas/sync_info_servidor.py` para constatar:
   `✅ El documento docs/INFO_SERVIDOR.md está 100% sincronizado con Discord. Cero discrepancias.`
2. Actualiza [docs/README.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/README.md) si varió el número de canales o categorías.
3. Commit semántico y push:
   ```powershell
   git add docs/INFO_SERVIDOR.md docs/README.md
   git commit -m "docs: sincronizar info_servidor con API v10 de Discord"
   git push origin main
   ```

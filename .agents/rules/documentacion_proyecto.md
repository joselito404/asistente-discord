---
trigger: always_on
description: "Estándar de documentación del proyecto, ciclo de relevos y fuentes de verdad vivas."
---

# Estándar de Documentación del Proyecto

> **Ámbito:** Memoria operativa, relevos y fuentes de verdad del proyecto Antigravity-discord.

---

## 1. Estructura de Documentación y Memoria
- **Constitución Modular:** En [.agents/rules/](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/.agents/rules/) residen las directrices técnicas del proyecto.
- **Historial y Relevos:** [.agents/chats/resumen.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/.agents/chats/resumen.md) recoge la línea temporal única y los relevos actualizados.
- **Transcripciones RAW:** [.agents/chats/raw/](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/.agents/chats/raw/) mantiene transcripciones literales con un archivo por chat (`chat_01.md`, `chat_02.md`, etc.).
- **Ciclo de Actualización:** Registrar en `raw/` y resumir en `resumen.md` en **cada interacción** o al culminar hitos importantes. `[Confirmada · Jose · 19/10/2026]` [Chat 3]

---

## 2. Fuentes de Verdad Vivas del Proyecto
- [docs/INFO_SERVIDOR.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/INFO_SERVIDOR.md): Mapa en tiempo real del servidor (49 canales, 73 roles, bots y censos). Actualización obligatoria al alterar canales, roles o servicios.
- [docs/PERSONALIDAD_BOT.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/PERSONALIDAD_BOT.md): Directrices canónicas de tono, relaciones y lore del bot Asistente.
- [modulos/README.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/README.md): Catálogo y responsabilidades de cada submódulo de código.

---

## 3. Sincronización Determinista
- Para evitar desactualizaciones manuales en `docs/INFO_SERVIDOR.md`, es obligatorio ejecutar [herramientas/sync_info_servidor.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/herramientas/sync_info_servidor.py) antes de cerrar relevos para auditar y refrescar canales y roles vía Discord API en 2 segundos. `[Confirmada · Jose · 18/10/2026]` [Chat 3]

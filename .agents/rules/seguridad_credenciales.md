---
trigger: always_on
description: "Reglas de seguridad, credenciales de Discord y límites disciplinarios (veto absoluto a kick/ban y respuestas efímeras)."
---

# Reglas de Seguridad, Credenciales y Conducta del Bot

> **Ámbito:** Seguridad, protección de credenciales y límites disciplinarios del bot Asistente en Discord.

---

## 1. Credenciales y Configuración Segura
- Las credenciales y secretos residen estrictamente en [config/config_discord.json](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/config/config_discord.json) (sincronizado en OneDrive, protegido en `.gitignore`, jamás commiteado a Git).
- El script [herramientas/discord_client.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/herramientas/discord_client.py) permite a los asistentes en cualquiera de los dos PCs consultar canales, auditar estados y enviar mensajes vía API REST sin necesidad de levantar el bot localmente. `[Confirmada · Jose · 09/10/2026]` [Chat 2]

---

## 2. Prohibición Absoluta de Expulsión o Baneo
- Queda **terminantemente prohibido** que el bot `Asistente` o cualquier asistente/agente ejecute acciones de expulsión (*kick*), baneo (*ban*) o eliminación de miembros del servidor, ya sean usuarios humanos o aplicaciones/bots de terceros (ej. UnbelievaBoat, Carl-bot, Cakey Bot).
- La potestad disciplinaria y de expulsión reside de forma exclusiva e indelegable en Jose. `[Confirmada · Jose · 19/10/2026]` [Chat 1]

---

## 3. Interacciones Efímeras contra Spam
- Todas las respuestas de interacción personal (asignación/retirada de roles, consulta de inventario/balance, errores de ejecución o confirmaciones de comandos) deben enviarse estrictamente como interacción privada efímera (`ephemeral=True`).
- Los canales públicos se reservan para conversaciones abiertas, juegos colectivos y anuncios. `[Confirmada · Jose · 18/10/2026]` [Chat 1]

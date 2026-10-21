---
trigger: always_on
description: "Estructura física de carpetas del repositorio, blindaje de la raíz y control de archivos."
---

# Estructura de Carpetas y Blindaje de Raíz

> **Ámbito:** Organización física del repositorio, higiene de directorios y control de archivos en Git.

---

## 1. Blindaje de la Raíz del Repositorio
- En la raíz conviven únicamente los archivos estrictamente requeridos para el despliegue en Render, configuración de agentes y presentación del proyecto:
  `README.md`, `bot_service.py`, `Dockerfile`, `Procfile`, `requirements.txt`, `CLAUDE.md`.
- Queda terminantemente prohibido crear scripts o archivos sueltos en la raíz; cualquier archivo nuevo debe pertenecer a una de las subcarpetas designadas. `[Chat 2]`

---

## 2. Asignación y Responsabilidad por Carpeta
- `modulos/`: Submódulos de lógica funcional del bot (comandos, chat IA, juegos, economía, eventos, voz) orquestados desde `bot_service.py`. Todo submódulo se documenta en [modulos/README.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/README.md).
- `config/`: Configuración y secretos (`config_discord.json`, gitignored).
- `datos/`: Persistencia de datos versionados en formato JSON (`economia.json`, trivias, censos, memoria de usuarios).
- `docs/`: Biblioteca central de diseño, lore del servidor, especificaciones y recursos (`documentos_pdf/`, `imagenes_contexto/`).
- `herramientas/`: Scripts auxiliares locales de mantenimiento, sincronización y tests.
- `datos_locales/`: Grabaciones de audio, logs, temporales e instaladores (todo gitignored).
- `.agents/rules/`: Constitución modular nativa del proyecto en Antigravity y Claude Code.
- `.agents/agents/`: Subagentes declarativos nativos del proyecto (`.agents/agents/<nombre>/agent.md` y su catálogo [`.agents/agents/README.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/.agents/agents/README.md)). `[Confirmada · Jose · 20/10/2026]` [Chat 1]
- `.agents/skills.json`: Configuración declarativa nativa que enlaza las skills maestras (`Antigravity-general/skills/`). Los hooks deterministas del ciclo de vida (`Antigravity-general/hooks/`) se cargan desde `~/.gemini/config/hooks.json` de cada PC; el `.agents/hooks.json` local se retiró el 21/10/2026 porque llamaba a scripts que ya no existen (Antigravity-juego / Chat 4, «ok» de Jose). `[Confirmada · Jose · 20/10/2026; hooks · Jose · 21/10/2026]` [Chat 4]
- `.agents/chats/`: Memoria operativa de desarrollo (`resumen.md`, `raw/`, `archive/`).

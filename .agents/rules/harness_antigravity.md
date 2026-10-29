---
trigger: always_on
description: "Configuración y herramientas exclusivas del entorno Google Antigravity en el proyecto."
---

# Harness Antigravity — Configuración de Entorno

> **Ámbito:** Integración y herramientas exclusivas de Antigravity en Antigravity-discord (§7 y AGENTS_ANTIGRAVITY.md).

---

## A.1. Subagentes y Personalización Local
- `.agents/agents/`: Subagentes declarativos nativos del proyecto (`.agents/agents/<nombre>/agent.md`; sin `README.md`). `[Confirmada · Jose · 20/10/2026]`
- `.agents/skills/<nombre>/SKILL.md`: Puntero híbrido con transclusión `@` a las skills maestras (`Antigravity-general/skills/`), sustituyendo a `skills.json` (§20). `[Confirmada · Jose · 25/10/2026]`
- Hooks deterministas: Invocados a nivel de máquina desde `~/.gemini/config/hooks.json` apuntando al repositorio maestro `Antigravity-general/hooks/`. `[Confirmada · Jose · 21/10/2026]`

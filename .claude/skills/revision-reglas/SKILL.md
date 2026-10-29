---
name: revision-reglas
description: >-
  [Confirmada · Jose] Revisar, auditar o sanear las reglas del proyecto (.agents/rules/ y CLAUDE.md) con el procedimiento maestro de Jose. Úsala cuando pida «revisar reglas», «auditar normas», «sanear .agents/rules/», o al auditar el proyecto tras un hito mayor.
---

# revision-reglas (puente a la skill maestra)

Este fichero no contiene el procedimiento: solo hace que Claude Code encuentre la skill maestra, que vive en el repositorio central de skills (norma global §17 y C.3). Así no hay copia que se desfase. Creado el 29/10/2026 por orden de Jose.

1. Lee entera la skill maestra: `~/OneDrive/Antigravity-general/skills/revision-reglas/SKILL.md` (en Windows, `C:\Users\jose\OneDrive\Antigravity-general\skills\revision-reglas\SKILL.md`; la misma ruta en los dos PC).
2. Comprueba que su cabecera dice `status: confirmada`. Si no, no la sigas y avisa a Jose (§17).
3. Sigue sus pasos sobre este proyecto. Lo que en ella sea propio de Antigravity (`invoke_subagent`, `ask_question`, `search_web`, límites del inyector) se traduce aquí a los subagentes nativos de Claude Code (herramienta de subagentes, y los agentes de `.claude/agents/` si el proyecto los tiene) y a la herramienta de preguntas de Claude Code.

---
name: revision-multiangulo
description: >-
  [Confirmada · Jose] Panel de críticos: subagentes con ángulos distintos (finanzas, legal, web, publicidad…) revisan un modelo o plan ya apuntado y devuelven hallazgos con evidencia, que luego se debaten con Jose. Úsala SOLO si Jose lo pide de forma explícita («revisa esto desde todos los ángulos», «panel de críticos»).
---

# revision-multiangulo (puente a la skill maestra)

Este fichero no contiene el procedimiento: solo hace que Claude Code encuentre la skill maestra, que vive en el repositorio central de skills (norma global §17 y C.3). Así no hay copia que se desfase. Creado el 29/10/2026 por orden de Jose.

1. Lee entera la skill maestra: `~/OneDrive/Antigravity-general/skills/revision-multiangulo/SKILL.md` (en Windows, `C:\Users\jose\OneDrive\Antigravity-general\skills\revision-multiangulo\SKILL.md`; la misma ruta en los dos PC).
2. Comprueba que su cabecera dice `status: confirmada`. Si no, no la sigas y avisa a Jose (§17).
3. Sigue sus pasos sobre este proyecto. Lo que en ella sea propio de Antigravity (`invoke_subagent`, `ask_question`, `search_web`, límites del inyector) se traduce aquí a los subagentes nativos de Claude Code (herramienta de subagentes, y los agentes de `.claude/agents/` si el proyecto los tiene) y a la herramienta de preguntas de Claude Code.

4. En Claude Code los críticos usan Sonnet 5.5 en esfuerzo high (parámetro `model: sonnet` de la herramienta de subagentes; si el proyecto no tiene un agente propio, vale el agente general) y solo con herramientas de lectura y web (Read, Grep, Glob, WebSearch, WebFetch). Se lanzan todos en el mismo mensaje.

# Directorio `.agents/rules/` — Constitución Modular del Proyecto

> **Propósito (Regla Global §8):** Este directorio contiene las reglas operativas, de seguridad y arquitectura técnica de `Antigravity-discord`, organizadas bajo el estándar oficial de **Constitución Modular Pura** y descubiertas automáticamente por el motor nativo de Google Antigravity y Claude Code.
> **Quién puede escribir:** Solo agentes autorizados bajo orden o consentimiento explícito de Jose (`[Confirmada · Jose · fecha]`).

---

## 📂 Módulos de Reglas Activos

| Archivo | Trigger | Tipo | Ámbito y Responsabilidad |
| :--- | :---: | :---: | :--- |
| [`reglas_globales_core.md`](./reglas_globales_core.md) | `always_on` | Global Core | Perfil de Jose, hardware AM4/AM5, almacenamiento multi-PC y constitución modular (`AGENTS_CORE.md`). |
| [`reglas_globales_workflows.md`](./reglas_globales_workflows.md) | `always_on` | Global Workflows | Control de versiones Git, docs vivas, orquestación, co-worker mindset y skills (`AGENTS_WORKFLOWS.md`). |
| [`reglas_globales_antigravity.md`](./reglas_globales_antigravity.md) | `always_on` | Global Antigravity | Solo Antigravity: telemetría, inyector de reglas, subagentes declarativos (§18), hooks (§19) y `skills.json` (§20). Transcluye `AGENTS_ANTIGRAVITY.md`. |
| [`seguridad_credenciales.md`](./seguridad_credenciales.md) | `always_on` | Local Proyecto | Protección de `config_discord.json`, cliente API REST, veto absoluto a kick/ban y respuestas efímeras. |
| [`despliegue_render.md`](./despliegue_render.md) | `always_on` | Local Proyecto | Supervisor 24/7 en Render Cloud, keep-alive cada 5 min y despliegue manual obligatorio con script. |
| [`modelos_ia.md`](./modelos_ia.md) | `always_on` | Local Proyecto | Síntesis FLUX.1 libre con Re-roll, cascada lite, Circuit Breaker 60s y veto a modelos lite en juicios. |
| [`estructura_carpetas.md`](./estructura_carpetas.md) | `always_on` | Local Proyecto | Blindaje estricto de la raíz del repo y catálogo de carpetas autorizadas. |
| [`harness_antigravity.md`](./harness_antigravity.md) | `always_on` | Local Proyecto | Configuración exclusiva de Antigravity: subagentes declarativos, skills.json y hooks de máquina. |
| [`harness_claudecode.md`](./harness_claudecode.md) | `model_decision` | Local Proyecto | SOLO para Claude Code: subagentes en `.claude/agents/`, skills y hooks locales. |
| [`documentacion_proyecto.md`](./documentacion_proyecto.md) | `always_on` | Local Proyecto | Relevos y raw por interacción, fuentes de verdad vivas y sincronización determinista vía script. |

# Catálogo de Subagentes Nativos (`.agents/agents/`)

> **Propósito:** Subagentes declarativos persistentes del proyecto `Antigravity-discord` (Regla Global §18 y §8).
> **Estado actual:** Vigente (`[Aprobado · Jose · 20/10/2026]`).
> **Quién puede escribir aquí:** El asistente orquestador principal, bajo supervisión de Jose.

---

## Subagentes Vigentes

| Subagente (`TypeName`) | Estado | Modelo Recomendado | `inheritCustomizations` | `inheritMcp` | Herramientas | Propósito y Restricciones |
| :--- | :---: | :--- | :---: | :---: | :--- | :--- |
| [`especialista-codigo`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/.agents/agents/especialista-codigo/agent.md) | `[Aprobado · Jose · 20/10/2026]` | `flash` (*Gemini 3.8 Flash Medium*) | `true` | `true` | Lectura, búsqueda web (`search_web`, `read_url_content`), MCPs (`gemini-api-docs`, `chrome-devtools`), escritura (`write_file`, `edit_file`), consola (`run_command`), `send_message` | Subagente puro de código, gráficas, web y tests unitarios. **Sin permisos de `git commit/push` ni deploy a Render**; el Orquestador verifica el trabajo antes de commitear. |

---

## Cómo Invocarlo

- **Desde el Orquestador en Antigravity IDE / 2.0 (`invoke_subagent`):**
  ```json
  {
    "TypeName": "especialista-codigo",
    "Model": "flash",
    "Role": "Code Implementation Specialist",
    "Prompt": "Lee docs/<ESPECIFICACION>.md e implementa en modulos/<archivo>.py..."
  }
  ```
- **Desde Antigravity CLI (`agy`):**
  ```bash
  agy -p "<encargo>" --agent especialista-codigo --model gemini-3.8-flash-medium --mode accept-edits
  ```

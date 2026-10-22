# Catálogo de Subagentes Nativos (`.agents/agents/`)

> **Propósito:** Subagentes declarativos persistentes del proyecto `Antigravity-discord` (Regla Global §18 y §8).
> **Estado actual:** Vigente (`[Aprobado · Jose · 20/10/2026]`).
> **Quién puede escribir aquí:** El asistente orquestador principal, bajo supervisión de Jose.

---

## Subagentes Vigentes

| Subagente (`TypeName`) | Estado | Modelo Recomendado | `inheritCustomizations` | `inheritMcp` | Herramientas | Propósito y Restricciones |
| :--- | :---: | :--- | :---: | :---: | :--- | :--- |
| [`especialista-codigo`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/.agents/agents/especialista-codigo/agent.md) | `[Aprobado · Jose · 20/10/2026]` | `flash` (*Gemini 3.8 Flash Medium*) | `true` | `true` | Lectura, búsqueda web (`search_web`, `read_url_content`), MCPs (`gemini-api-docs`, `chrome-devtools`), escritura (`write_file`, `edit_file`), consola (`run_command`), `send_message` | Subagente puro de código, gráficas, web y tests unitarios estándar. Fijado estrictamente en tier `flash` para no consumir cuota de modelos superiores. **Sin permisos de `git commit/push` ni deploy a Render**. |
| [`especialista-codigo-argon`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/.agents/agents/especialista-codigo-argon/agent.md) | `[Aprobado · Jose · 23/10/2026]` | `pro` (*Gemini 4 Argon / Pro*) | `true` | `true` | Lectura, búsqueda web (`search_web`, `read_url_content`), MCPs (`gemini-api-docs`, `chrome-devtools`), escritura (`write_file`, `edit_file`), consola (`run_command`), `send_message` | Especialista senior para tareas complejas, algoritmos matemáticos densos, refactorizaciones críticas y depuración profunda con razonamiento extendido. **Sin permisos de `git commit/push` ni deploy a Render**. |

---

## Cómo Invocar cada Especialista

- **Para tareas de código estándar (Flash):**
  ```json
  {
    "TypeName": "especialista-codigo",
    "Model": "flash",
    "Role": "Code Implementation Specialist",
    "Prompt": "Lee docs/<ESPECIFICACION>.md e implementa en modulos/<archivo>.py..."
  }
  ```
- **Para tareas complejas de alta dificultad (Argon / Pro):**
  ```json
  {
    "TypeName": "especialista-codigo-argon",
    "Model": "pro",
    "Role": "Advanced Code Architect",
    "Prompt": "Analiza la arquitectura de <SISTEMA> y refactoriza..."
  }
  ```
- **Desde Antigravity CLI (`agy`):**
  ```bash
  agy -p "<encargo>" --agent especialista-codigo --model gemini-3.8-flash-medium --mode accept-edits
  agy -p "<encargo_complejo>" --agent especialista-codigo-argon --model gemini-4-argon --mode accept-edits
  ```

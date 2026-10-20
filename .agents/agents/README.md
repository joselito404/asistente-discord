# Catálogo de Subagentes Nativos (`.agents/agents/`)

> **Propósito:** Subagentes declarativos persistentes del proyecto `Antigravity-discord` (Regla Global §18 y §8).
> **Quién puede escribir aquí:** El asistente orquestador principal, bajo supervisión de Jose.

---

## Subagentes Disponibles

| Subagente (`TypeName`) | Modelo Recomendado | `inheritCustomizations` | `inheritMcp` | Herramientas | Propósito y Uso |
| :--- | :--- | :---: | :---: | :--- | :--- |
| [`especialista-codigo`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/.agents/agents/especialista-codigo/agent.md) | `flash` (*Gemini 3.8 Flash Medium*) | `false` (~600 tokens base) | `false` | Lectura, escritura (`write_file`, `edit_file`), ejecución (`run_command`), `send_message` | Implementación de módulos Python (`modulos/`), motores matemáticos, renderizado de gráficas (`Pillow`/`mplfinance`), persistencia JSON (`datos/`) y ejecución de suites de tests (`herramientas/`). Incluye protocolo *Fast-Escalation* (Regla Global §15). |

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

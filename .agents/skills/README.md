# Directorio `.agents/skills/` — Skills Nativas y Compartidas del Proyecto

> **Propósito (Regla Global §8 y §20):** Este directorio contiene las skills registradas para `Antigravity-discord`. Sigue el estándar de **Puntero Híbrido con Transclusión `@`** (§20), permitiendo que la interfaz gráfica de Google Antigravity indexe los comandos contextuales `/` sin duplicar la lógica central alojada en el repositorio maestro central (`C:\Users\jose\OneDrive\Antigravity-general\skills\`).
> **Quién puede escribir:** Agentes autorizados con visto bueno o instrucción explícita de Jose (`[Confirmada · Jose · fecha]`).

---

## 🛠️ Catálogo de Skills Registradas

| Skill | Versión | Tipo | Descripción |
| :--- | :---: | :---: | :--- |
| [`revision-reglas`](./revision-reglas/SKILL.md) | `1.2.0` | Puntero Híbrido `@` | Triaje técnico estandarizado para auditar, sanear y mantener reglas locales en cualquier proyecto. Enlace a la skill maestra de OneDrive. |

---

## 📐 Estructura de un Puntero Híbrido (§20)

Cada skill compartida en este directorio se compone exclusivamente de:
1. **Cabecera YAML canónica:** Frontmatter mínimo (`name`, `description`) para que el motor visual de Antigravity indexe el comando `/`.
2. **Cuerpo transcluido de una línea:** Transclusión directa vía `@[Skill Maestra - <Nombre>](<Ruta_Absoluta_OneDrive>)`, garantizando 0 duplicación física y sincronización instantánea multi-PC.

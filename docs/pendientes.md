# Lista Única de Pendientes (`docs/pendientes.md`)

> **Regla de origen (Regla Global §21):** Fuente de verdad única de trabajo por hacer, encargos en espera, ideas aparcadas y decisiones que esperan a Jose en `Antigravity-discord`.
> **Gobernanza:** Sincronización obligatoria atómica (§14). Toda tarea completada se retira de este archivo (el historial reside en Git y `.agents/chats/resumen.md`).

---

## 🏛️ Área 3: Dinámicas Sociales, Juicios y Entretenimiento

### 3.1. Juicios Comunitarios en Discord (Minijuego de Litigios y Disputas entre Usuarios)
- **Qué falta:** Diseñar con Jose mediante preguntas interactivas la mecánica completa del minijuego de juicio entre usuarios (acusar a otro miembro, jurado popular, deliberación, votación interactiva, consecuencias lúdicas y/o con Porros, roles temporales). **Completamente independiente y desvinculado de El Tribunal Gaming (web de videojuegos)**.
- **Por qué importa:** Dinámica social tensa, interactiva y muy divertida en Discord sin confundir ni mezclar la marca de la web de análisis de videojuegos de Jose e Iván.
- **Siguiente paso:** Jose responde a las preguntas interactivas para definir el nombre del comando, reglas de apuesta/fianza y duración.
- **Responsable:** Chat 3 / Jose.
- **Estado:** en espera de Jose.
- **Detalle:** docs/pendientes.md.

### 3.2. El Periódico Semanal / The Sanvi Weekly
- **Qué falta:** Crónica semanal automática publicada cada domingo a las 20:00 ES en `#📣anuncios📣` o `#🗨️la-shit-de-todos-los-dias🗨️`, resumiendo el post más votado de Starboard de la semana, el tiburón del casino/bolsa, el récord de horas de voz en Cakey y una columna de opinión satírica de Asistente.
- **Por qué importa:** Crea cultura y cohesión comunitaria semanal destacando los mejores momentos del servidor.
- **Siguiente paso:** Crear el generador y programador semanal del boletín.
- **Responsable:** Chat 3.
- **Estado:** `por hacer`.
- **Detalle:** [modulos/chat_ia.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/chat_ia.py) y [modulos/starboard.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/starboard.py).

### 3.3. Minijuego de Robo Interactivo (Hackeo / Ganzúa en `/robar`)
- **Qué falta:** Convertir `/robar @usuario` en un minijuego interactivo de reacción rápida con botones V2: el atacante tiene 5 segundos para pulsar la secuencia correcta (`[🔴] [🟢] [🔵]`); si la víctima está conectada, recibe alerta y tiene 5 segundos para pulsar `[🚨 Activar Alarma]` y atrapar al ladrón cobrándole fianza compensatoria.
- **Por qué importa:** Sustituye la fórmula matemática pasiva por una experiencia tensa, interactiva y justa para ambas partes.
- **Siguiente paso:** Diseñar la vista interactiva Discord V2 con timeouts concurrentes.
- **Responsable:** Chat 3 / Especialista de Código.
- **Estado:** `por hacer`.
- **Detalle:** [modulos/economia_core.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/economia_core.py) y [modulos/comandos_economia.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/comandos_economia.py).

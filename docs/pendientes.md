# Lista Única de Pendientes (`docs/pendientes.md`)

> **Regla de origen (Regla Global §21):** Fuente de verdad única de trabajo por hacer, encargos en espera, ideas aparcadas y decisiones que esperan a Jose en `Antigravity-discord`.
> **Gobernanza:** Sincronización obligatoria atómica (§14). Toda tarea completada se retira de este archivo (el historial reside en Git y `.agents/chats/resumen.md`).

---

## 📈 Área 1: Bolsa Sanvi & Aura

### 1.1. Calibración Local, Simulaciones y Validación de la Bolsa Sanvi y Aura
- **Qué falta:** Ejecutada con éxito la simulación de ciclo semanal y la **simulación real con datos vivos de la semana** en [herramientas/simular_economia_real.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/herramientas/simular_economia_real.py) (Joselito con 2.91M Porros adquiriendo 1.500 acciones bajo límite anti-ballenas, elasticidad $K=2000$, subida de $\$JOSE$ a 144,76 Porros, tramo 5 de sinergia con 132k Aura y absorción del 84,39% del Yield Pool dominical de 311k Porros). Pendiente decisión de Jose sobre cuándo retirar el paro de emergencia (`emergency_halt = False`) y desplegar en producción.
- **Por qué importa:** La simulación matemática y visual ha verificado al 100% que todos los sistemas cuadran a la perfección tanto en escenarios abstractos como con la distribución real de riqueza del servidor.
- **Siguiente paso:** Jose decide si desplegar y reabrir el mercado bursátil en Discord.
- **Responsable:** Jose / Chat 1.
- **Estado:** `en espera de Jose`.
- **Detalle:** [docs/DISENO_BOLSA_SANVI.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/DISENO_BOLSA_SANVI.md) y [modulos/bolsa_sanvi.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/bolsa_sanvi.py).



---

## 🏛️ Área 3: Dinámicas Sociales, Juicios y Entretenimiento

### 3.1. Juicios Comunitarios de El Tribunal en Discord (Diferenciado de la Web Oficial)
- **Qué falta:** Evolucionar el comando `/tribunal` en Discord a un juicio comunitario interactivo con votación de jurado popular (botones `[⚖️ Declarar Culpable]` y `[🕊️ Declarar Inocente]`) durante 5 minutos y sentencias automatizadas (multa en Porros de la cartera o rol temporal `"Culpable de Skill Issue"`). Claramente diferenciado de la web oficial de El Tribunal Gaming (`el-tribunal-gaming.vercel.app`).
- **Por qué importa:** Fomenta piques divertidos y debates comunitarios en `#⚖️el-tribunal-gaming⚖️` con consecuencias reales dentro del servidor.
- **Siguiente paso:** Diseñar el flujo de votación y las sanciones automáticas en Discord.
- **Responsable:** Chat 3 / Jose.
- **Estado:** `por hacer`.
- **Detalle:** [modulos/juegos.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/juegos.py).

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

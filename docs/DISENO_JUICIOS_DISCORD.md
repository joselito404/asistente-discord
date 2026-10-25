# ⚖️ Especificación Canónica de Diseño: Minijuego de Juicios Comunitarios en Discord

> **Ámbito:** Minijuego de litigios, acusaciones y resolución lúdica de disputas entre miembros en el servidor de Discord 'LOS MONGOLOS DEL SANVI'.
> **Regla de origen:** Regla Global §13 (Compuertas 1 a 5).
> **Estado:** `[Confirmada · Jose · 25/10/2026]`
> **Desvinculación:** Sistema 100% autónomo de Discord. **No tiene relación ni conexión con El Tribunal Gaming** (catálogo y web de análisis de videojuegos de Jose e Iván).

---

## 1. Visión General y Filosofía de Juego

El sistema de Juicios en Discord es un minijuego interactivo comunitario diseñado para piques amistosos, vaciladas y resolución teatral de acusaciones entre miembros (ej. *"Se quedó AFK en la última ronda"*, *"Prometió jugar y se fue a dormir"*, *"Dijo que invitaba a las pizzas y desapareció"*).

El Asistente actúa como **Juez Instructor Teatral y Portavoz del Jurado**, moderando el debate, gestionando la votación popular y dictando una sentencia satírica inapelable.

---

## 2. Mecánica Detallada y Parámetros Aprobados

### 2.1. Apertura del Proceso (`/juicio demandar`)
- **Comando:** `/juicio` con acciones `demandar` y `estado`.
- **Parámetros de demanda:**
  - `acusado` (`discord.Member`): Miembro demandado. No puede ser un bot ni el propio demandante.
  - `motivo` (`str`): Causa de la acusación (máximo 250 caracteres).
  - `fianza` (`int`, opcional, por defecto `300`):
    - **Modo Económico (`fianza >= 100` y `<= 2500`):** Se retiene la fianza a demandante y acusado. Tasa judicial de apertura de **50 Porros no reembolsables** transferida al `server_jackpot`.
    - **Modo Moral (`fianza == 0`):** Juicio puramente honorífico y lúdico. 0 Porros retenidos y 0 tasas judiciales.
- **Gestión de Concurrencia:** Solo puede haber **un juicio activo simultáneo por canal** (`ACTIVE_TRIALS`) protegido con candado asíncrono para evitar colisiones.

### 2.2. Fase de Jurado Popular y Deliberación (120 Segundos)
- **Duración:** **120 segundos (2 minutos)** exactos con cuenta regresiva.
- **Componentes interactivos (`discord.ui.View`):**
  - Botón `[⚖️ Declarar Culpable]` (`ButtonStyle.danger`).
  - Botón `[🕊️ Declarar Inocente]` (`ButtonStyle.success`).
  - Botón `[📜 Ver Cargos]` (`ButtonStyle.secondary`, modal/ephemeral con el expediente).
- **Reglas de Votación:**
  - Todos los miembros del servidor pueden emitir **1 voto**.
  - Si un usuario pulsa el botón opuesto, su voto se conmuta limpiamente.
  - **Incompatibilidad Judicial:** Ni el Acusador ni el Acusado pueden votar en su propio juicio.
  - Escrutinio en tiempo real reflejado en el Embed con barra visual de bloques (`🟥` y `🟩`) y porcentaje.

### 2.3. Veredicto y Sentencia Automática
Al expirar los 120 segundos:
1. **Quorum Mínimo:** Se requieren al menos **2 votos de jurado** ajenos a las partes implicadas.
   - Si no hay quorum: Caso desestimado por falta de pruebas y desinterés ciudadano. Se devuelven las fianzas retenidas íntegramente.
2. **Sentencia de Culpabilidad (Votos Culpable > Inocente):**
   - El Acusado es declarado **CULPABLE**.
   - **Sanción Económica (si fianza > 0):** El demandante se lleva el pozo de la fianza (su fianza recuperada + la fianza del acusado).
   - **Sentencia Moral:** Veredicto satírico fulminante redactado por el Asistente.
   - **Sanción de Rol:** Intento de asignación temporal por **1 hora** del rol humorístico `"Culpable de Skill Issue"` (si existe en la guild).
3. **Sentencia de Absolución (Votos Inocente > Culpable):**
   - El Acusado es declarado **INOCENTE**.
   - **Costas por Falsa Acusación (si fianza > 0):** El acusado se lleva el pozo de la fianza como indemnización por daños y perjuicios a su honor.
   - **Sentencia Moral:** Desestimación pública de la fiscalía con burla al acusador.
4. **Empate Judicial (Votos Culpable == Inocente):**
   - *In dubio pro reo*: Absolución sin costas. Se devuelven las fianzas retenidas a ambas partes.

---

## 3. Arquitectura de Módulos

- **`modulos/juicios_discord.py`**: Lógica de sesiones, estados en memoria, retención económica con `ECONOMY_LOCK`, vista interactiva `TrialView`, temporizador concurrente de 120s y resolución.
- **`modulos/comandos_generales.py`**: Registro del comando `/juicio`.
- **`modulos/comandos.py`**: Reexportación para la fachada del bot.
- **`herramientas/test_juicios_discord.py`**: Suite de tests unitarios exhaustiva.

---

## 4. Registro de Decisiones y Estado Canónico

- [x] **[Confirmada · Jose · 25/10/2026]** Aprobación del nombre de comando `/juicio` con acciones `demandar` y `estado`.
- [x] **[Confirmada · Jose · 25/10/2026]** Modo Dual de Fianza: Opcional (`fianza > 0` con tasa de 50 Porros a jackpot o `fianza == 0` puramente moral).
- [x] **[Confirmada · Jose · 25/10/2026]** Duración del jurado popular fijada en 120 segundos (2 minutos).
- [x] **[Confirmada · Jose · 25/10/2026]** Sanción completa: Fianza/costas + veredicto satírico + rol temporal `"Culpable de Skill Issue"` (1h).
- [x] **[Confirmada · Jose · 25/10/2026]** Desvinculación total de El Tribunal Gaming (0 referencias a la web ni a notas de videojuegos).
- [ ] Implementación técnica de `modulos/juicios_discord.py` y registro de `/juicio`.
- [ ] Suite de pruebas unitarias en `herramientas/test_juicios_discord.py`.

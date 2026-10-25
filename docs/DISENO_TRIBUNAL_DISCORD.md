# ⚖️ Especificación de Diseño Vivo: Juicios Comunitarios de El Tribunal en Discord

> **Ámbito:** Dinámicas sociales de moderación lúdica, resolución de disputas comunitarias y entretenimiento en `#⚖️el-tribunal-gaming⚖️` (`1335345719816556554`).
> **Regla de origen:** Regla Global §13 (Compuertas 1 a 5).
> **Estado:** `[Confirmada · Jose · 25/10/2026]`

---

## 1. Visión General y Diferenciación Canónica con la Web Oficial

| Entidad | Plataforma | Propósito Canónico | Magistrados / Actores |
| :--- | :--- | :--- | :--- |
| **El Tribunal Gaming (Web Oficial)** | `https://el-tribunal-gaming.vercel.app` | Catálogo técnico de videojuegos, notas Metacritic/HLTB, análisis de rendimiento cooperativo y Muro de la Vergüenza. | Jose (Joselito) e Iván (racerwasp). |
| **Juicios de El Tribunal (Discord)** | `#⚖️el-tribunal-gaming⚖️` en Discord | Dinámica comunitaria interactiva de disputas por skill issue, traiciones en cooperativos o vaciladas, con jurado popular y sentencias económicas. | Comunidad entera como Jurado Popular + Asistente como Juez Instructor. |

> [!IMPORTANT]
> El sistema de Juicios en Discord **nunca altera ni contamina** la base de datos de videojuegos de la web. En el pie de página de cada juicio se incluye el enlace a la web oficial como referencia de los Magistrados Supremos.

---

## 2. Mecánica del Juicio Comunitario

### 2.1. Apertura del Proceso Judicial (`/juicio demandar` o `/tribunal juicio`)
- **Parámetros del comando:**
  - `acusado` (`discord.Member`): Miembro del servidor demandado. No puede ser un bot ni el propio demandante.
  - `motivo` (`str`): Causa de la acusación (ej. *"Tiró flash a su propio equipo en CS2"*, *"Prometió jugar y se fue a dormir"*). Máximo 250 caracteres.
  - `fianza` (`int`, opcional): Apuesta/sanción económica en Porros (mínimo 100, máximo 2.500; por defecto 300 Porros). Ambos participantes deben disponer del saldo en cartera.
- **Tasa judicial de apertura:** 50 Porros (tasa no reembolsable destinada a las arcas del `server_jackpot` para evitar spam de demandas frívolas).

### 2.2. Fase de Deliberación y Jurado Popular (3 Minutos)
- Al incoar el juicio, se envía un mensaje público interactivo con un Embed de alta solemnidad judicial.
- **Componentes interactivos (`discord.ui.View`):**
  - Botón `[⚖️ Declarar Culpable]` (Rojo / Peligro).
  - Botón `[🕊️ Declarar Inocente]` (Verde / Éxito).
  - Botón `[📜 Ver Cargos]` (Gris / Secundario, muestra alegatos de la fiscalía en modal/ephemeral).
- **Reglas del Jurado:**
  - Todos los miembros del servidor pueden emitir **1 voto**.
  - Si un usuario vuelve a pulsar el botón contrario, su voto se conmuta limpiamente.
  - **Incompatibilidad judicial:** Ni el Acusador ni el Acusado pueden votar en su propio juicio.
  - Tiempo de deliberación: **180 segundos (3 minutos)** con actualización periódica de la barra de veredicto.

### 2.3. Veredicto y Sentencia Automática
Al expirar el temporizador de 180 segundos:
1. **Quorum Mínimo:** Se requieren al menos **2 votos de jurado** ajenos a las partes. Si no hay quorum, el juicio queda *Desestimado por Falta de Pruebas y Desinterés Ciudadano* (se devuelven las fianzas retenidas).
2. **Sentencia de Culpabilidad (Votos Culpable > Inocente):**
   - El Acusado es declarado **CULPABLE**.
   - **Sanción Económica:** Se transfieren los Porros de la fianza del Acusado al Acusador.
   - **Sentencia Moral:** El Asistente redacta un veredicto satírico fulminante. Si el rol `"Culpable de Skill Issue"` existe en el servidor, se asigna temporalmente.
3. **Sentencia de Absolución (Votos Inocente > Culpable):**
   - El Acusado es declarado **INOCENTE Y LIBRE DE TODA CULPA**.
   - **Costas Judiciales por Falsa Acusación:** El Acusador paga la fianza al Acusado como indemnización por daños y perjuicios a su honor.
4. **Empate Judicial (Votos Culpable == Inocente):**
   - *In dubio pro reo*: Absolución sin costas económicas. Se devuelven las fianzas a ambas partes.

---

## 3. Arquitectura Técnica

- **Módulo de Lógica:** `modulos/tribunal_discord.py` (aislado de la base de datos de videojuegos de `modulos/juegos.py`).
- **Comando Slash:** Registrado en `modulos/comandos_generales.py` como `/juicio [accion] [acusado] [motivo] [fianza]`.
- **Integración con Economía:** Utiliza las funciones atómicas de `modulos/economia_core.py` (`get_user_data`, `save_user_data`, `transferir_porros`).
- **Gestión de Concurrencia:** Solo puede haber **un juicio activo simultáneo por canal** para evitar colisiones de mensajes y dilución de votos.

---

## 4. Registro de Decisiones y Estado Canónico

- [x] **[Confirmada · Jose · 25/10/2026]** Aprobación del sistema de Juicios Comunitarios de El Tribunal en Discord, diferenciado explícitamente de la web oficial `el-tribunal-gaming.vercel.app`.
- [x] **[Confirmada · Jose · 25/10/2026]** Duración fijada en 180 segundos (3 minutos) con votación interactiva `[⚖️ Declarar Culpable]` y `[🕊️ Declarar Inocente]`.
- [x] **[Confirmada · Jose · 25/10/2026]** Transferencia de fianza/costas en Porros y rol humorístico temporal `"Culpable de Skill Issue"`.
- [x] Implementación de `modulos/tribunal_discord.py` y registro del comando `/juicio`.
- [x] Suite de pruebas unitarias en `herramientas/test_tribunal_discord.py` (15/15 tests en verde).

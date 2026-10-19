# 👑 Especificación Maestra de Medición de Aura (`docs/AURA_BAREMO.md`)

> **Estado**: `Vigente / Aprobada por Jose` `[Confirmada · Jose · 18/10/2026]`
> **Origen y Evolución**:
> - v1 (13/10/2026): Primer borrador exploratorio de chat de texto (Chat 2).
> - v2-v3 (13/10/2026): Ajuste de momentos tras lectura del historial y descarte de "dropear".
> - **v4 Oficial (18/10/2026)**: Descarte total de minijuegos artificiales del bot (`/trivial`, `/ajedrez`, `/tribunal`) y reestructuración completa en los **3 Pilares Reales de Convivencia** (45% Voz / 35% Chat / 20% Momentos) sobre **10.000 puntos máximos** con telemetría de voz anti-AFK e integración 50/50 en la Bolsa Sanvi.

---

## 🏛️ Los 3 Pilares Reales del Servidor (10.000 Puntos Máximos)

```text
┌────────────────────────────────────────────────────────────────────────┐
│                      ÍNDICE DE AURA (10.000 PUNTOS)                    │
├───────────────────────────────┬────────────┬───────────────────────────┤
│ Pilar                         │ Porcentaje │ Puntos Máximos            │
├───────────────────────────────┼────────────┼───────────────────────────┤
│ 🎙️ 1. Voz y Convivencia      │ 45%        │ 4.500 pts                 │
│ 💬 2. Chat y Comunidad        │ 35%        │ 3.500 pts                 │
│ 🌟 3. Momentos y Hazañas      │ 20%        │ 2.000 pts                 │
└───────────────────────────────┴────────────┴───────────────────────────┘
```

$$\text{Aura Total} = \text{Voz (4.500)} + \text{Chat (3.500)} + \text{Momentos (2.000)} = 10.000 \text{ pts}$$

---

## 🎙️ Pilar 1: Voz y Convivencia en Directo (45% — 4.500 Puntos)

> **Estado**: `[Reabierto para revisión · Jose · 19/10/2026]`


Es el núcleo donde se forja el servidor: partidas cooperativas, competitivo de Brawl Stars, charlas nocturnas y streaming de partidas.

### 1. Telemetría Automatizada (`on_voice_state_update`)
Se mide en tiempo real mediante el evento nativo de Discord sin grabaciones invasivas:

1. **Filtro Anti-Farmeo (Mínimo 2 personas)**:
   - Los minutos en sala solo computan si hay **al menos 2 miembros humanos** en el canal.
   - Estar solo en sala = **0 puntos** (bloqueo absoluto de farmeo AFK nocturno).
2. **Tratamiento de Muteo vs Ensordecido**:
   - `self_deaf == True` (Ensordecido): **0% de rendimiento**. Si no escuchas a tus colegas, no estás en la convivencia.
   - `self_mute == True` (Muteado de micro pero escuchando): **50% de rendimiento**. Reconoce a quienes juegan y escuchan las partidas sin micro o de noche por ruido familiar.
3. **Curva Suave de Rendimientos Decrecientes Diarios**:
   - **0 a 3 horas (0 a 180 min)**: **100%** de puntos.
   - **3 a 6 horas (180 a 360 min)**: **75%** de puntos.
   - **Más de 6 horas (> 360 min)**: **50%** de puntos.
   - *Finalidad*: No castiga las tardes sanas de vicio en grupo y mitiga anomalías desproporcionadas de 14 horas seguidas.
4. **Bonus por Retransmisión (`self_stream`)**:
   - Compartir pantalla de la partida o retransmitir contenido para los colegas otorga un multiplicador de bonificación sobre el tiempo en sala.
5. **Heartbeat de Persistencia (Cada 5 minutos)**:
   - Chequeo periódico en segundo plano que consolida minutos en memoria/JSON, tolerando reinicios de Render sin perder más de 4 minutos de sesión.

---

## 💬 Pilar 2: Chat, Conversación y Comunidad (35% — 3.500 Puntos)

> **Estado**: `[Propuesta · Chat 1 · 19/10/2026]` · `[Pendiente de matizar: reparto de puntos entre métricas, longitud mínima de mensaje y ventana móvil]`



Mide la interacción social que mantiene vivo el servidor durante el día cuando no se puede jugar en llamada.

### 1. Ponderación por Zonas del Servidor
No todas las salas tienen el mismo valor cultural:

| Zona / Canales | Multiplicador |
| :--- | :---: |
| **Zona Gaming** (`#🎮gaming-general🎮`, recomendaciones) | $\times 1{,}5$ |
| **General & Comunidad** (`#🗨️la-shit-de-todos-los-dias🗨️`, `#📖cultura📖`) | $\times 1{,}5$ |
| **Shitpost, Brawl Stars, Torneos, Categoría Pro, Extra** | $\times 1{,}0$ |
| **Casino & Economía** | $\times 0{,}3$ |
| **`#🤖bots🤖` y `#⌨️comandos⌨️`** | $\times 0{,}3$ |
| **Administración** | $\times 0{,}0$ |

### 2. Cuatro Métricas Base de Chat:
1. **Constancia**: Días con al menos un mensaje válido, ponderado por la mejor zona del día. (Escribir 30 mensajes seguidos para farmear nivel cuenta como 1 día).
2. **Conversación**: Respuestas y menciones recibidas de otros miembros (tope: 1 por persona y día para evitar spam).
3. **Celebración**: Mensajes con reacciones de al menos 2 personas distintas (auto-reacciones excluidas).
4. **Alcance**: Cuántos miembros distintos han respondido, mencionado o reaccionado al usuario en el periodo.

> ℹ️ *Exclusiones*: No computan mensajes a bots, menciones a `@Asistente`, comandos, ni mensajes vacíos con solo un enlace o código de sala.

---

## 🌟 Pilar 3: Momentos de Lore y Hazañas (20% — 2.000 Puntos)

> **Estado**: `[Propuesta · Chat 1 · 19/10/2026]` · `[Pendiente de matizar: sistema de registro de momentos y caducidad]`

El carisma, los memes legendarios y el historial de comportamiento. Todos parten de **1.000 puntos base**. Cada momento suma o resta puntos con un mensaje citable real. (Rango final: 0 a 2.000 pts).


### Acciones que Suman (+ Puntos):
- **Hazaña en un juego**: Clutch, pasarse un juego juntos, hito cooperativo difícil (+150 a +350 pts).
- **Frase mítica del lore**: Hace reír y la celebran al menos 2 personas (+100 a +250 pts).
- **Construir algo para el servidor**: Crear la web del Tribunal, familia de Steam, torneos (+150 a +350 pts).
- **Aportar a la familia de Steam o regalar un juego** (+100 a +250 pts).
- **Convocar un plan que sale adelante**: Organizar sesión de juego (+100 a +200 pts).
- **Salvarle el día a un colega**: Avisos académicos, ayuda técnica o de hardware (+100 a +200 pts).
- **Defender a un amigo que no está delante** (+100 a +200 pts).
- **Redención**: Arreglar el micro tras meses, ponerse los roles (+50 a +150 pts).

### Acciones que Restan (- Puntos):
- **Plantón**: Confirmar asistencia a una partida y no aparecer sin avisar (-150 a -300 pts).
- **El "luego" eterno**: Aplazar sin fecha una y otra vez ("ya veré", "otro día") (-75 a -200 pts).
- **Excusa de ganas recurrente**: Pereza constante para instalar 3 GB o unirse (-75 a -200 pts).
- **Trampear un sistema**: Spamear letras para subir de nivel en Cakey Bot (-150 a -300 pts).
- **Llorar una derrota o culpar a los randoms de forma tóxica** (-50 a -150 pts).
- **Deber y no pagar**: Solo deudas de Porros en el casino, nunca dinero real (-75 a -150 pts).
- **Dejar en visto**: Te preguntan o mencionan directamente para jugar y no contestas en 48h (-75 a -150 pts).
- **Hablarle a las paredes**: Insistir 3 o más veces con un tema que nadie sigue (-50 a -100 pts).

### Qué NO Resta Jamás:
- Falta de medios (no tener PC, micro, gráfica o dinero).
- Obligaciones reales (estudios, exámenes, trabajo, familia, médico).
- Avisar con antelación de que no se puede jugar (eso es educación, no plantón).
- Dropear un juego (jugar a lo que a uno le divierte es libre).
- Proponer un plan que no sale por falta de quórum (la iniciativa suma, la falta de gente no castiga).

---

## 📈 Integración con la Bolsa Sanvi (`Sanvi Exchange`)

El Aura Total opera como el **Valor Fundamental (50%)** de la cotización de cada miembro en la Bolsa:

$$P_{\text{acción}} = 0{,}50 \cdot P_{\text{fundamental}} (\text{Aura / 10.000}) + 0{,}50 \cdot P_{\text{mercado}} (\text{Oferta y Demanda})$$

- **Suelo Fundamental (50%)**: Usuarios con alto Aura tienen un suelo de cotización elevado e inmune a especulaciones destructivas. Cuentas inactivas o fantasma tienen un suelo cercano a 0.
- **Presión de Mercado (50%)**: Las compras y ventas reales con Porros hacen oscilar el precio en el corto plazo, generando volatilidad y especulación divertida.

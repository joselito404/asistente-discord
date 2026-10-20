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

> **Estado**: `[Aprobado · Jose · 20/10/2026]` (Cerrado al 100%: Fórmula de Minuto Efectivo + Techo de 40h/mes)

Es el núcleo donde se forja el servidor: partidas cooperativas, competitivo de Brawl Stars, charlas nocturnas y streaming de partidas.

### 1. Telemetría y Ecuación del Minuto Efectivo (`on_voice_state_update`)
Se mide en tiempo real mediante el evento nativo de Discord sin grabaciones invasivas. Cada minuto en llamada se convierte en **Minutos Efectivos ($M_e$)**:

$$M_e = 1 \text{ min} \times F_{\text{estado}} \times F_{\text{curva}} \times F_{\text{stream}}$$

1. **Factor de Estado ($F_{\text{estado}}$)**:
   - **Hablando / Escuchando normal**: **$\times 1{,}0$** (100%).
   - **Muteado pero escuchando (`self_mute == True`)**: **$\times 0{,}5$** (50%). Reconoce a quienes juegan y escuchan las partidas de noche o sin micro.
   - **Ensordecido (`self_deaf == True`)**: **$\times 0{,}0$** (0%, pausa inmediata). Si no escuchas a tus colegas, no estás en la convivencia.
   - **Filtro Anti-Farmeo**: Estar solo en sala o acompañado únicamente por bots = **$\times 0{,}0$** (mínimo **2 humanos reales** para computar). Canal AFK oficial = **$\times 0{,}0$**.
2. **Factor de Curva Diaria Suave ($F_{\text{curva}}$)**:
   - **0 a 3 horas en el día (0 a 180 min)**: **$\times 1{,}0$** (100% de puntos).
   - **3 a 6 horas en el día (180 a 360 min)**: **$\times 0{,}75$** (75% de puntos).
   - **Más de 6 horas en el día (> 360 min)**: **$\times 0{,}50$** (50% de puntos).
   - *Finalidad*: No frena el vicio sano entre colegas en tardes largas y mitiga anomalías desproporcionadas de 14 horas seguidas.
3. **Factor de Retransmisión ($F_{\text{stream}}$)**:
   - **Sin retransmitir**: **$\times 1{,}0$**.
   - **Compartiendo pantalla/partida (`self_stream == True`)**: **$\times 1{,}20$** (+20% de bonus por aportar contenido y streaming a la sala).
4. **Heartbeat de Persistencia (Cada 5 minutos)**:
   - Chequeo periódico en segundo plano que consolida minutos en memoria/JSON, tolerando reinicios de Render sin perder más de 4 minutos de sesión.

### 2. Tasa de Conversión y Techo Mensual (40 Horas) `[Aprobado · Jose · 20/10/2026]`
- **Techo Mensual (100% del pilar)**: **40 horas efectivas al mes** ($2.400 \text{ minutos efectivos}$, equivalente a ~1h 20m al día o ~9-10h a la semana).
- **Tasa Exacta de Conversión**:
  $$\text{Puntos}_{\text{voz}} = \min\left(4.500,\; \sum M_e \times 1{,}875\right)$$
  - **1 minuto efectivo ($M_e$)** = **$1{,}875 \text{ puntos de Aura}$**.
  - **1 hora efectiva ($60 \text{ min}$)** = **$112{,}5 \text{ puntos de Aura}$**.
  - **1 hora con streaming ($\times 1{,}20$)** = **$135{,}0 \text{ puntos de Aura}$**.
  - **1 hora muteado escuchando ($\times 0{,}50$)** = **$56{,}25 \text{ puntos de Aura}$**.

---

## 💬 Pilar 2: Chat, Conversación y Comunidad (35% — 3.500 Puntos)

> **Estado**: `[Aprobado · Jose · 20/10/2026]` (100% Cerrado)

Mide la interacción social que mantiene vivo el servidor durante el día cuando no se puede jugar en llamada (evaluado sobre una **ventana móvil de los últimos 30 días**, al igual que el Pilar 1).

### 1. Ponderación por Zonas del Servidor (`[Aprobado · Jose · 20/10/2026]`)
No todas las salas tienen el mismo valor cultural:

| Zona / Canales | Multiplicador |
| :--- | :---: |
| **Zona Gaming y Núcleo Social** (`#💬general`, `#🔥off-topic`, `#📖cultura`, `#💩shit-post`, `#🥊violencia`, canales de juegos) | $\times 1{,}5$ |
| **Utilidad Comunitaria** (`#💡sugerencias`, `#🎭roles`, `#🎂cumpleaños`, `#🏆torneos`, Categoría Pro, Extra) | $\times 1{,}0$ |
| **Zona de Farmeo / Bots** (`#🎰casino-y-apuestas`, `#🏪tienda-y-mercado`, `#🤖bots`, `#⌨️comandos`, `#🚀spam`) | $\times 0{,}3$ |
| **Administración y Staff** (Canales privados de mods/logs) | $\times 0{,}0$ |

### 2. Las 3 Métricas Oficiales de Chat (3.500 Puntos Totales) (`[Aprobado · Jose · 20/10/2026]`):

1. **Constancia — Días Activos (`1.000 pts máx.`)**:
   - **$50 \text{ pts}$ por día activo** (mínimo 1 mensaje válido en el día; escribir 30 mensajes seguidos en un mismo día cuenta como 1 único día activo).
   - **Tope mensual (100%)**: **20 días activos de 30** ($20 \times 50 = 1.000 \text{ pts}$).

2. **Conversación — Respuestas y Menciones Recibidas (`1.250 pts máx.`)**:
   - **$12{,}5 \text{ pts}$ por cada interacción recibida** cuando otro humano del servidor te responde (`reply`) o te menciona (`@usuario`).
   - **Límite anti-farmeo por par**: **Hasta 4 interacciones por persona y día** (permite varias charlas reales al día entre amigos sin que un ping-pong de 100 mensajes rompa la métrica).
   - **Tope mensual (100%)**: **100 respuestas/menciones válidas al mes** ($100 \times 12{,}5 = 1.250 \text{ pts}$).

3. **Aportación de Contenido y Vida al Chat (`1.250 pts máx.`)**:
   - Mide las aportaciones escritas y multimedia aplicando el **Multiplicador de Zona** ($\times 1{,}5$, $\times 1{,}0$ o $\times 0{,}3$):
     - **Mensaje de conversación normal** ($\ge 15$ caracteres, sin flood): **$5 \text{ pts base}$** ($7{,}5 \text{ pts}$ en zona $\times 1{,}5$).
     - **Aporte Multimedia / Debate** (subir meme/foto/clip de partida, compartir enlace/recomendación o escribir un post de debate en `#📖cultura` de $\ge 120$ caracteres): **$20 \text{ pts base}$** ($30 \text{ pts}$ en zona $\times 1{,}5$).
   - **Límite diario anti-spam**: Máximo **$100 \text{ pts diarios}$** acumulables en este bloque (impide farmear los 1.250 puntos en una sola tarde).
   - **Tope mensual (100%)**: **$1.250 \text{ pts}$**.

> ℹ️ *Exclusiones*: No computan mensajes de $<4$ caracteres, flood repetido, mensajes a bots, menciones a `@Asistente` o `@Economia Asistente`, comandos slash/prefijo, ni mensajes con solo un código de sala.

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

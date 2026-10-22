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
│ 🏅 3. Veteranía y Prestigio   │ 20%        │ 2.000 pts                 │
└───────────────────────────────┴────────────┴───────────────────────────┘
```

$$\text{Aura Total} = \text{Voz (4.500)} + \text{Chat (3.500)} + \text{Veteranía (2.000)} = 10.000 \text{ pts}$$

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

> **Estado**: `[Aprobado · Jose · 20/10/2026]` (100% Cerrado con topes realistas para grupo de amigos)

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
   - **$83{,}33 \text{ pts}$ por día activo** (mínimo 1 mensaje válido en el día; escribir 30 mensajes seguidos en un mismo día cuenta como 1 único día activo).
   - **Tope mensual (100%)**: **12 días activos de 30** ($\approx 3 \text{ días/semana} \rightarrow 1.000 \text{ pts}$).

2. **Conversación — Respuestas y Menciones Recibidas (`1.250 pts máx.`)**:
   - **$50 \text{ pts}$ por cada interacción recibida** cuando otro humano del servidor te responde (`reply`) o te menciona (`@usuario`).
   - **Límite anti-farmeo por par**: **Hasta 4 interacciones por persona y día**.
   - **Tope mensual (100%)**: **25 respuestas/menciones válidas al mes** ($\approx 1 \text{ al día} \rightarrow 25 \times 50 = 1.250 \text{ pts}$).

3. **Aportación de Contenido y Vida al Chat (`1.250 pts máx.`)**:
   - Mide las aportaciones escritas y multimedia aplicando el **Multiplicador de Zona** ($\times 1{,}5$, $\times 1{,}0$ o $\times 0{,}3$):
     - **Mensaje de conversación normal** ($\ge 10$ caracteres, sin flood): **$25 \text{ pts base}$** ($37{,}5 \text{ pts}$ en zona $\times 1{,}5$).
     - **Aporte Multimedia / Debate** (subir meme/foto/clip de partida, compartir enlace/recomendación o escribir un post de debate en `#📖cultura` de $\ge 120$ caracteres): **$75 \text{ pts base}$** ($112{,}5 \text{ pts}$ en zona $\times 1{,}5$).
   - **Tope mensual (100%)**: **$1.250 \text{ pts}$** (se alcanza con ~1 mensaje al día o ~10 memes/debates en el mes).

> ℹ️ *Exclusiones*: No computan mensajes de $<4$ caracteres, flood repetido, mensajes a bots, menciones a `@Asistente` o `@Economia Asistente`, comandos slash/prefijo, ni mensajes con solo un código de sala.

---

## 🏅 Pilar 3: Veteranía y Prestigio en el Servidor (20% — 2.000 Puntos)

> **Estado**: `[Aprobado · Jose · 20/10/2026]` (100% Cerrado)

Mientras que los Pilares 1 y 2 miden la actividad reciente (ventana móvil de 30 días), el **Pilar 3 mide la trayectoria histórica acumulada desde el día 1 (01/09/2026)**, otorgando un suelo permanente de prestigio a los veteranos del servidor aunque un mes tengan exámenes o menos tiempo.

### 1. Rango de Nivel en el Servidor (`1.000 pts máx.`) `[Aprobado · Jose · 20/10/2026]`
Calculado automáticamente leyendo el nivel/rol del miembro:
- **Sin rango (`< Nivel 10`)**: `100 pts`
- **`🔷 Pendejo de Rango Medio` (`Nivel 10+`)**: `350 pts`
- **`⚔️ Veterano` (`Nivel 20+` / Acceso a Categoría Pro)**: `650 pts`
- **`🔥 Experimentado` (`Nivel 30+`)**: `850 pts`
- **`💎 Alto Rango / Élite / Maestro+` (`Nivel 40+`)**: **`1.000 pts` (Tope)**

### 2. Trayectoria Histórica Acumulada — Voz y Mensajes desde el Día 1 (`1.000 pts máx.`) `[Aprobado · Jose · 20/10/2026]`
Premia las horas de llamada y los mensajes con XP totales acumulados por el miembro en toda la historia del servidor:
1. **Voz Histórica Total (`600 pts máx.`)** `[Aprobado · Jose · 20/10/2026]`:
   - **Tasa**: **$10 \text{ pts por hora histórica}$** en llamadas ($\approx 0{,}1667 \text{ pts/min}$).
   - **Tope (100%)**: **60 horas históricas acumuladas (`3.600 min`)** ($60 \times 10 = 600 \text{ pts}$).
2. **Mensajes Históricos Totales (`400 pts máx.`)** `[Aprobado · Jose · 20/10/2026]`:
   - **Tasa**: **$1 \text{ pt por mensaje con XP histórico}$**.
   - **Tope (100%)**: **400 mensajes con XP históricos acumulados** ($400 \times 1 = 400 \text{ pts}$).

### 3. Semilla Histórica Oficial (Snapshot Cakey Bot 01/09/2026 – 20/10/2026) y Migración a Niveles Nativos `[Aprobado · Jose · 20/10/2026]`
Aprobado en la hoja de ruta sustituir a Cakey Bot por un **Sistema de Niveles Nativo en `Asistente` (`datos/niveles.json`)**, importando 1:1 los datos históricos acumulados desde el 1 de septiembre de 2026 y conectándolo en tiempo real con el Aura, el Podio (`Top 1/2/3`), los Salarios (`/salario`) y los Pases de XP de `/tienda`:

| # | Usuario | XP Messages | XP Voice Minutes (Horas) | Nivel Actual | XP Total | Puntos Pilar 3 Actuales (Rango + Voz Hist + Msg Hist) |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `joselito3499` | 658 | 3.950 min (65,8 h) | **Lvl 54** | 340.600 XP | $1.000 + 600 + 400 = \mathbf{2.000 \text{ pts}}$ |
| 2 | `terreneiror` | 196 | 1.502 min (25,0 h) | **Lvl 37** | 122.900 XP | $850 + 250 + 196 = \mathbf{1.296 \text{ pts}}$ |
| 3 | `omen2042_38051` | 148 | 1.787 min (29,8 h) | **Lvl 36** | 114.000 XP | $850 + 298 + 148 = \mathbf{1.296 \text{ pts}}$ |
| 4 | `racerwasp` | 129 | 1.738 min (29,0 h) | **Lvl 33** | 88.200 XP | $850 + 290 + 129 = \mathbf{1.269 \text{ pts}}$ |
| 5 | `mpx56.` | 42 | 0 min (0,0 h) | **Lvl 16** | 13.900 XP | $350 + 0 + 42 = \mathbf{392 \text{ pts}}$ |
| 6 | `carlitosmf__` | 0 | 362 min (6,0 h) | **Lvl 15** | 12.500 XP | $350 + 60 + 0 = \mathbf{410 \text{ pts}}$ |
| 7 | `vexus_1128` | 40 | 0 min (0,0 h) | **Lvl 14** | 10.900 XP | $350 + 0 + 40 = \mathbf{390 \text{ pts}}$ |
| 8 | `ccmen1408` | 39 | 0 min (0,0 h) | **Lvl 14** | 10.100 XP | $350 + 0 + 39 = \mathbf{389 \text{ pts}}$ |
| 9 | `zixxer_donnuts_05511` | 15 | 29 min (0,5 h) | **Lvl 12** | 7.200 XP | $350 + 5 + 15 = \mathbf{370 \text{ pts}}$ |
| 10 | `alexpro0812` | 24 | 0 min (0,0 h) | **Lvl 10** | 5.700 XP | $350 + 0 + 24 = \mathbf{374 \text{ pts}}$ |
| 11 | `motor123ewfvioq3590tj_68922` | 1 | 69 min (1,15 h) | **Lvl 6** | 2.000 XP | $100 + 12 + 1 = \mathbf{113 \text{ pts}}$ |

#### 3.1. Fuente de Verdad Oficial: Mantener Cakey Bot vía Leaderboard Web `[Aprobado · Jose · 20/10/2026]`
- Ratificada la permanencia de Cakey Bot como fuente de verdad canónica de niveles, XP acumulada, mensajes históricos y minutos de voz. Se desestima la creación de un sistema de niveles propio en `Asistente` para evitar duplicidad y sobrecarga.
- **Mecanismo de Ingesta Directa**: `Asistente` abandona la lectura de `#bots` con regex y pasa a consultar directamente el **leaderboard web público** oficial de Cakey Bot (`https://cakey.bot/leaderboard/id/1446143936891715616?tab=leveling`), el cual entrega datos limpios de cada miembro:
  - `username` / ID
  - `messages` (mensajes históricos con XP)
  - `voice_minutes` (minutos de llamada históricos acumulados)
  - `level` (nivel exacto)
  - `xp` (XP total acumulada)
- Una caché en memoria de 5 a 15 minutos en `Asistente` previene consultas repetitivas.
- Salarios (`/salario`), rangos, bonos, perfil (`/perfil`), cálculo de XP (`/xp`), Aura (Pilares 1, 2 y 3) y la Bolsa Sanvi consumen exclusivamente esta fuente unificada.

---

## 📈 Integración con la Bolsa Sanvi (`Sanvi Exchange`)

> **Estado:** `Ratificado por Jose` `[Aprobado · Jose · 22/10/2026]`

El Aura se define formalmente como el **Precio Fundamental Base ($P_{\text{base}}$)** de cada miembro cotizado en el mercado, erradicando escalas arbitrarias desconectadas y unificando la economía y el prestigio:

$$P_{\text{base}} = \text{Aura} = \text{Book Value (Patrimonio Histórico)} + \text{Rendimiento Mensual (Earnings}_{30d})$$

- **Patrimonio Histórico (*Book Value / Equity*)**: La trayectoria acumulada de por vida extraída de Cakey Bot establece el suelo patrimonial inmutable que impide la quiebra:
  $$BV = 10 + (0{,}8 \times \text{Nivel}) + (0{,}2 \times \text{Horas Históricas Voz}) + (0{,}02 \times \text{Mensajes Históricos})$$
- **Rendimiento Mensual (*Trailing 30-Day Earnings* — Ponderación 50/50)**: Mide la actividad reciente (voz y chat de los últimos 30 días) calculada limpiamente mediante la **diferencia entre snapshots diarios de Cakey Bot** (`datos/cakey_history.json`):
  $$E_{30d} = (0{,}50 \times \Delta\text{Horas Voz}_{30d}) + (0{,}05 \times \Delta\text{Mensajes}_{30d})$$
  - **1 hora de voz** en 30 días = **$+0{,}50 \text{ Porros}$**.
  - **10 mensajes con XP** en 30 días = **$+0{,}50 \text{ Porros}$** ($0{,}05 \text{ Porros/msg}$).
- **Precio Final de Mercado ($P_{\text{mercado}}$)**: La presión compradora y vendedora de los miembros en el Market Maker ajusta la cotización:
  $$P_{\text{mercado}} = P_{\text{base}} \times \left(1 + \frac{\text{Acciones en Cartera de Usuarios} - 100}{2.000}\right)$$

- **Sinergia de Cartera (Utilidad y Multiplicador)**: Poseer acciones de miembros con alto Aura otorga un bono activo de $+5\%$ a $+25\%$ en la retribución de [`/trabajar`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/economia.py).
- **Indicadores Técnicos Cuantitativos (100% Informativos)**:
  - **RSI a 14 Días**: Mide la aceleración del momentum diario de actividad.
  - **Medias Móviles SMA / EMA**: 14, 50, 100 y 200 días para detección de tendencias y cruces (*Golden Cross / Death Cross*).
  - **Análisis Narrativo de Asistente IA**: El bot genera dictámenes financieros contextualizados (*Comprar / Mantener / Tomar Beneficios*) en `/bolsa informe` y `/aura`.

---

## 📋 Registro de Decisiones y Estado Canónico (Compuerta 5 — Regla Global §13)

- [x] Baremo unificado con la Bolsa Sanvi: El Aura constituye el Precio Fundamental Base de la acción ($P_{\text{base}}$) (`[Aprobado · Jose · 22/10/2026]`).
- [x] Mantenimiento de Cakey Bot como fuente canónica de niveles, XP, minutos y mensajes vía Leaderboard Web (`[Aprobado · Jose · 20/10/2026]`).
- [x] Desestimación de niveles nativos propios (`datos/niveles.json`) (`[Aprobado · Jose · 20/10/2026]`).
- [x] Ventana móvil de 30 días calculada mediante snapshots diarios de Cakey Bot a las 00:00 UTC en `datos/cakey_history.json` (`[Aprobado · Jose · 22/10/2026]`).
- [x] Fórmulas matemáticas ratificadas de Book Value y Earnings 30d (`[Aprobado · Jose · 22/10/2026]`).
- [x] Curva de elasticidad del Market Maker con factor $K=2.000$ (+5% por 100 acciones, suelo en $P_{\text{base}}$) (`[Aprobado · Jose · 22/10/2026]`).
- [x] Tríada Financiera de Incentivos ratificada: Plusvalía de Mercado (AMM), Sinergia de Cartera por Aura (+5% a +25% en /trabajar) y Fondo Real de Dividendos semanal (50% spread Bolsa + 1% rake slots) (`[Aprobado · Jose · 22/10/2026]`).
- [x] Indicadores técnicos institucionales ratificados: Medias móviles (SMA/EMA 14, 50, 100 y 200 días), RSI a 14 días (100% informativos) e informes narrativos de Asistente IA (`[Aprobado · Jose · 22/10/2026]`).
- [x] Ponderación de Earnings 30d ratificada al 50/50: 1h voz = +0,50 Porros, 10 msgs = +0,50 Porros (`[Aprobado · Jose · 22/10/2026]`).




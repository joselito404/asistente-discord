# 📈 Especificación de Diseño: Mercado de Valores ("Bolsa Sanvi" / Aura Market)

> **Documento de Diseño Vivo (Regla Global §13)**: Este archivo se engorda y refina en tiempo real durante las sesiones de diseño antes de programar código. Registra todas las decisiones matemáticas, fórmulas de cotización y modelos de persistencia acordados con Jose.
> **Estado:** `Borrador Activo / En Refinamiento`

---

## 1. Visión General del Sistema

La **Bolsa Sanvi** es un mercado de valores financiero-comunitario donde cada miembro activo del servidor cuenta con un *ticker* cotizado (ej. `$JOSE`, `$IVAN`, `$OMEN`, `$TERRE`, etc.). Los miembros utilizan la divisa del servidor (porros/monedas) para comprar, vender y especular con las acciones de sus colegas.

---

## 2. Modelo de Cotización Híbrido (Aprobado)

El precio de cotización de la acción de un usuario ($P_{\text{acción}}$) se rige por un equilibrio 50/50 entre su valor fundamental y la presión del mercado:

$$P_{\text{acción}} = 0{,}50 \cdot P_{\text{fundamental}} + 0{,}50 \cdot P_{\text{mercado}}$$

- **$P_{\text{fundamental}}$ (50%)**: Suelo de valor respaldado por su puntuación en el **Índice de Aura** (escala de 0 a 10.000 puntos). Garantiza que usuarios activos y queridos tengan un valor intrínseco sólido y que nadie pueda inflar una cuenta inactiva o fantasma.
  $$\mathbf{P_{\text{fundamental}} = \max\left(200,\; \frac{\text{Aura}}{2}\right) \text{ Porros}} \quad \text{[Aprobado · Jose · 20/10/2026]}$$
  - Un usuario con 10.000 puntos de Aura alcanza un valor fundamental máximo de **5.000 Porros / acción**.
  - Los fundadores activos rondan entre **2.000 y 4.250 Porros / acción** de suelo fundamental.
  - Se establece un suelo mínimo garantizado de **200 Porros / acción** para evitar valores cero en cuentas sin actividad reciente.
- **$P_{\text{mercado}}$ (50%)**: Variación dinámica por **oferta y demanda real en la propia bolsa**. Las compras netas elevan el precio sobre su valor fundamental (creando *hype* o burbuja); las ventas masivas o *dumps* castigan la cotización hacia su suelo.

---

## 3. Telemetría de Voz y Presencia Activa (Aprobado)

En sustitución de la transcripción continua por IA (inviable 24/7), se mide la telemetría directa de Discord mediante `on_voice_state_update`:

1. **Filtro de Convivencia (Mínimo 2 personas)**:
   - Los minutos en sala solo computan si hay **al menos 2 miembros humanos** en el canal. Estar solo en sala = **0 puntos** (evita AFK farming).
2. **Tratamiento de Muteo vs Ensordecido**:
   - `self_deaf == True` (Ensordecido): **0% de rendimiento** (pausa inmediata). Si no escucha a los demás, no participa.
   - `self_mute == True` (Muteado de micro pero escuchando): **50% de rendimiento**. Reconoce a quienes juegan y escuchan las partidas sin micro o de noche.
3. **Curva Ligera de Rendimientos Decrecientes Diarios**:
   - **0 a 3 horas (0 a 180 min)**: **100%** de puntuación.
   - **3 a 6 horas (180 a 360 min)**: **75%** de puntuación.
   - **Más de 6 horas (> 360 min)**: **50%** de puntuación.
4. **Heartbeat de Persistencia (Cada 5 minutos)**:
   - Chequeo periódico en segundo plano que consolida minutos en memoria/JSON, tolerando reinicios de Render sin perder más de 4 minutos de sesión.
5. **Bonus por Retransmisión**:
   - `self_stream == True` (compartiendo pantalla/partida para los demás) otorga un multiplicador adicional mientras esté activo.

---

## 4. Distribución del Índice de Aura (10.000 Puntos Máximos)

> **Estado**: `Aprobado por Jose` `[Confirmada · Jose · 18/10/2026]` (Detalle completo en [`docs/AURA_BAREMO.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/AURA_BAREMO.md)).

Tras descartar los minijuegos artificiales del bot (`/trivial`, `/ajedrez`, `/tribunal`) por no tener impacto en el día a día del grupo, el Índice se estructura en los **3 Pilares Reales de Convivencia**:

| Pilar | % Oficial | Puntos Máximos | Qué Computa |
| :--- | :---: | :---: | :--- |
| **🎙️ 1. Convivencia en Voz** | 45% | 4.500 pts | Ventana 30d: Minutos efectivos en llamada ($M_e$, mínimo 2 humanos, mute 50%, deaf 0%, curva 3h/6h, stream +20%) con techo de **40h/mes** ($112{,}5\text{ pts/h}$). |
| **💬 2. Chat y Comunidad** | 35% | 3.500 pts | Ventana 30d: Constancia (`1.000 pts`, 12 días activos), Conversación (`1.250 pts`, 25 respuestas/menciones recibidas, máx 4/persona/día) y Aportación de Contenido (`1.250 pts`, $25\text{ pts}$ msg normal / $75\text{ pts}$ meme o debate $\times$ multiplicador de zona). |
| **🏅 3. Veteranía y Prestigio** | 20% | 2.000 pts | Histórico acumulado desde el día 1: Rango de Nivel (`1.000 pts`, Lvl 10 a 40+) + Trayectoria Histórica (`600 pts` Voz Histórica tope 60h + `400 pts` Mensajes Históricos tope 400 msgs). |

$$\text{Total Aura Fundamental} = \text{Voz (4.500)} + \text{Chat (3.500)} + \text{Veteranía (2.000)} = 10.000 \text{ pts}$$

---

## 5. Decisiones Aprobadas y Pendientes
- [x] **Pesos Definitivos del Índice de Aura**: 3 Pilares Reales (45% Voz / 35% Chat / 20% Veteranía sobre 10.000 pts) `[Aprobado · Jose · 20/10/2026]`.
- [x] **Pilar 1 (Voz y Convivencia — 4.500 pts)**: Cerrado al 100%. Ecuación $M_e = 1\text{ min} \times F_{\text{estado}} \times F_{\text{curva}} \times F_{\text{stream}}$ y **techo mensual de 40 horas efectivas** ($1\text{ min} = 1{,}875\text{ pts}$ / $1\text{ h} = 112{,}5\text{ pts}$) `[Aprobado · Jose · 20/10/2026]`.
- [x] **Pilar 2 (Chat y Comunidad — 3.500 pts)**: Cerrado al 100%. Constancia (`1.000 pts` en 12 días activos), Conversación (`1.250 pts` en 25 respuestas/menciones, máx 4/persona/día) y Aportación (`1.250 pts`, $25\text{ pts}$ msg / $75\text{ pts}$ meme o debate $\times$ zona) `[Aprobado · Jose · 20/10/2026]`.
- [x] **Pilar 3 (Veteranía y Prestigio — 2.000 pts)**: Cerrado al 100%. Rango de Nivel (`1.000 pts`) + Trayectoria Histórica Acumulada (`600 pts` Voz Histórica tope 60h + `400 pts` Mensajes Históricos tope 400 msgs) `[Aprobado · Jose · 20/10/2026]`.
- [x] **Hoja de Ruta — Sistema de Niveles Nativo (Reemplazo Cakey Bot)**: Aprobado crear `datos/niveles.json` y motor nativo en `Asistente` importando 1:1 la tabla histórica de Cakey Bot desde el 01/09/2026 `[Aprobado · Jose · 20/10/2026]`.
- [x] **Algoritmo de Mercado (50%)**: Opción A — Modelo AMM / Bonding Curve continua tipo Uniswap con liquidez infinita contra la banca y comisión fija del 1% (spread de quema de Porros) `[Aprobado · Jose · 19/10/2026]`.
- [x] **Diseño de Interfaz Gráfica (Híbrido Dual)**: Render nativo en Discord (Pillow) + Web interactiva en Vercel (TradingView Lightweight Charts) con estética idéntica a Trading 212 `[Aprobado · Jose · 19/10/2026]`.
- [x] **Catálogo de Tickers y Requisito de Salida a Bolsa (IPO Nivel 20+)**: Requisito de Nivel 20+ (desbloqueo de `CATEGORÍA PRO`) para cotizar en bolsa. Fundadores iniciales: `$JOSE`, `$TERRE`, `$OMEN`, `$RACER`. Tickers aprobados para futuros aspirantes cuando alcancen Nvl 20 `[Aprobado · Jose · 20/10/2026]`.
- [x] **Conversión de Aura a Precio Fundamental ($P_{\text{fundamental}}$)**: Escala $\div 2$ con fórmula $P_{\text{fundamental}} = \max\left(200,\; \frac{\text{Aura}}{2}\right)$ (techo 5.000 Porros a 10.000 Aura, suelo mínimo 200 Porros) `[Aprobado · Jose · 20/10/2026]`.
- [x] **Arquitectura de Suministro Fijo e Insider Holding**: 10.000 acciones fijas por ticker. Asignación inicial al fundador fijada exactamente en el **1% (100 acciones)** y **99% (9.900 acciones)** en el Free Float del Market Maker `[Aprobado · Jose · 20/10/2026]`.
- [x] **Mecánica de Dividendos Pasivos (Incentivo al Hold)**: Retención del **5% del `/salario` diario** del miembro en [`modulos/economia_core.py`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/economia_core.py), repartido proporcionalmente entre sus accionistas como dividendos en Porros limpios sin inflación `[Aprobado · Jose · 20/10/2026]`.
- [x] **Market Maker con Spread (Contrapartida Inmediata 24/7)**: Horquilla fija del 1% (Ask $+0{,}5\%$, Bid $-0{,}5\%$) con quema deflacionaria automática del spread `[Aprobado · Jose · 20/10/2026]`.
- [ ] **Curva de Mercado AMM ($P_{\text{mercado}}$)**: `[Pendiente de matizar: cómo mueven las compras y ventas netas el componente de mercado]`.
- [ ] **Frecuencia de Formación de Velas Japonesas**: `[Pendiente de matizar: temporalidad de cierre de velas (1 hora vs 1 día)]`.

---

## 6. Catálogo de Tickers y Requisitos de Salida a Bolsa (IPO)

> **Estado:** `Aprobado por Jose` `[Aprobado · Jose · 20/10/2026]`

Para otorgar verdadero prestigio a cotizar en los mercados y evitar saturar el sistema con miembros inactivos o fantasmas, la salida a bolsa (*Oferta Pública Inicial / IPO*) está vinculada al hito de **Nivel 20** (el mismo umbral que otorga acceso a la `CATEGORÍA PRO` del servidor):

### 6.1. Requisito de Cotización (Nivel 20+)
- **Condición de Salida a Bolsa**: Solo los miembros que alcancen o superen el **Nivel 20** en el servidor adquieren su propio *ticker* y comienzan a cotizar en la Bolsa Sanvi.
- **Quiénes pueden operar**: Todos los miembros del servidor pueden **comprar y vender** acciones desde Nivel 0; el requisito de Nivel 20 aplica exclusivamente a **tener una acción propia cotizando**.

### 6.2. Cuarteto Fundador Activo (Cotización Inmediata)
Actualmente, 4 miembros cumplen el requisito de Nivel 20+ en el servidor y forman el mercado inicial:

| Ticker | Miembro | Nivel Actual | XP Acumulada | Rol en el Mercado |
| :---: | :--- | :---: | :---: | :--- |
| **`$JOSE`** | `joselito3499` | Nivel 54 | 340.600 XP | *Mega Cap* / Fundador del Servidor |
| **`$TERRE`** | `terreneiror` | Nivel 37 | 122.900 XP | *Large Cap* / Veterano Activo |
| **`$OMEN`** | `omen2042_38051` | Nivel 36 | 114.000 XP | *Large Cap* / Veterano Activo |
| **`$RACER`** | `racerwasp` | Nivel 33 | 88.200 XP | *Large Cap* / Veterano Activo |

### 6.3. Tickers Reservados para Nuevas Salidas a Bolsa (IPO Pipeline)
En cuanto un miembro alcance el Nivel 20, el sistema anunciará automáticamente su **Salida a Bolsa** con su ticker pre-aprobado:
> *Niveles corregidos el 20/10/2026 19:47 con el leaderboard web oficial de Cakey Bot (los valores previos 19/18/17/15/15 eran erróneos). Tickers sin cambios.*
- `mpx56.` (Nivel 16 $\rightarrow$ a 4 niveles de cotizar): **`$MPX`**
- `carlitosmf__` (Nivel 15 $\rightarrow$ a 5 niveles de cotizar): **`$CARL`**
- `vexus_1128` (Nivel 14): **`$VEXUS`**
- `ccmen1408` (Nivel 14): **`$CCMEN`**
- `zixxer_donnuts_05511` (Nivel 12): **`$ZIXX`**
- `alexpro0812` (Nivel 10): **`$ALEX`**
- `motor123...` (Nivel 6): **`$MOTOR`**

---

## 7. Estructura Accionarial, Suministro Fijo, Dividendos y Market Maker

> **Estado:** `Aprobado por Jose` `[Aprobado · Jose · 20/10/2026]`

Para replicar con realismo la dinámica bursátil de Trading 212 y resolver la falta de liquidez en un grupo de amigos:

### 7.1. Suministro Fijo de Acciones y Asignación Inicial
1. **Suministro Fijo (*Total Shares Outstanding*)**:
   - Cada miembro que sale a bolsa tiene exactamente **10.000 acciones emitidas**.
   - No se imprimen acciones infinitas de la nada, garantizando escasez estricta y valor matemático a la capitalización bursátil (*Market Cap*).
2. **Asignación al Fundador (*Insider Holding* - 1%)**:
   - El titular del ticker recibe exactamente el **1% (100 acciones)** en su cartera inicial (`portfolio`).
   - Evita regalos desproporcionados de liquidez líquida y alinea sus intereses con el crecimiento del valor de su acción a largo plazo.
3. **Free Float en Custodia del Market Maker (99%)**:
   - Las **9.900 acciones restantes (99%)** constituyen el mercado abierto administrado por el bot para que los miembros las adquieran con sus Porros.

### 7.2. Tríada Financiera de Incentivos y Dividendos (Hold, Utilidad y Rendimiento)
> **Estado:** `Ratificado por Jose` `[Aprobado · Jose · 22/10/2026]`

Queda erradicado cualquier impuesto o deducción forzada sobre los salarios personales de los miembros. El sistema se asienta sobre tres pilares independientes y complementarios:

1. **Pilar 1: Plusvalía de Capital (*Trading y Crecimiento 24/7*)**:
   - Orientado al *trader* activo.
   - Rendimiento directo por la apreciación del precio fundamental ($P_{\text{base}}$ por subidas de nivel y actividad en Cakey Bot) y la presión compradora de la comunidad en el creador de mercado ($P_{\text{mercado}}$ vía AMM).
   - Beneficio limpio al vender contra el bot en momentos alcistas.

2. **Pilar 2: Sinergia de Cartera por Aura (*Incentivo Activo al Hold y Utilidad Real*)**:
   - Orientado al inversor que mantiene acciones a medio y largo plazo.
   - Poseer acciones de miembros con alto Aura transfiere pasivamente su influencia a la cuenta del accionista:
     $$\text{Aura Total Cartera} = \sum (\text{Acciones poseídas de } i \times \text{Aura fundamental de } i)$$
   - Otorga un bono multiplicador permanente sobre la recompensa del comando [`/trabajar`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/economia.py):
     - *Inversor Junior (1.000 a 5.000 Porros en Aura):* **$+5\%$** en `/trabajar`.
     - *Inversor Senior (5.001 a 20.000 Porros en Aura):* **$+10\%$** en `/trabajar`.
     - *Fondo de Inversión (20.001 a 50.000 Porros en Aura):* **$+15\%$** en `/trabajar`.
     - *Ballena de Sanvi (>50.000 Porros en Aura):* **$+25\%$** en `/trabajar` (Tope máximo).
   - Vender acciones para especular reduce de inmediato el Aura en cartera y el multiplicador, desincentivando las ventas masivas de pánico.

3. **Pilar 3: Fondo Real de Dividendos (*Yield Pool Semanal en Efectivo*)**:
   - Orientado al inversor pasivo.
   - Cero dinero inventado de la nada: el bote se financia exclusivamente de la actividad económica real del servidor:
     - El **50% del spread bursátil** (0,5% compra / 0,5% venta) recaudado por el AMM (el otro 50% se quema como freno deflacionario).
     - El **1% de las apuestas netas** recaudadas en la tragaperras [`/slots`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/economia.py).
   - **Reparto Automatizado:**
     - Cada **domingo a las 23:59 UTC**, el bote acumulado en `datos/bolsa_pool.json` se acredita automáticamente en el banco de cada accionista de forma proporcional al valor de su cartera:
       $$\text{Dividendo del Usuario} = \text{Bote Semanal} \times \frac{\text{Valor de tu Cartera en Circulación}}{\text{Capital Total Invertido por Usuarios}}$$

### 7.3. Creador de Mercado del Bot (*Automated Market Maker*) y Spread
- Para evitar que las órdenes de compra o venta queden bloqueadas esperando a que otro humano las acepte, el bot actúa como **Market Maker central** garantizando ejecución 24/7.
- **Horquilla Bid/Ask (Spread del 1%)**:
  - **Precio Ask (Compra):** $\text{Precio de Cotización} \times 1{,}005$ ($+0{,}5\%$).
  - **Precio Bid (Venta):** $\text{Precio de Cotización} \times 0{,}995$ ($-0{,}5\%$).
  - La horquilla neta del **1%** se destruye/quema directamente de la base monetaria en [`datos/economia.json`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/datos/economia.json), actuando como freno deflacionario al arbitraje de alta frecuencia.

---

## 8. Arquitectura de Interfaz y Gráficas de Cotización (Estilo Trading 212)

Aprobado el modelo híbrido dual para máxima comodidad y profundidad visual:

1. **Terminal Nativo en Discord (Comando `/bolsa [ticker]` o `/grafica`)**:
   - **Renderizado Dinámico en Servidor**: Generación al vuelo de imagen PNG de alta definición mediante Python (`Pillow` / `mplfinance` personalizado).
   - **Paleta Visual Trading 212**:
     - Fondo negro puro (`#000000`).
     - Velas japonesas alcistas en verde neón (`#00E676`) y bajistas en rojo vivo (`#FF5252`).
     - Línea horizontal de precio actual en azul cian (`#00A3FF`) con etiqueta flotante de cotización.
     - Eje derecho de precios y selector temporal inferior (`1D`, `1S`, `1M`, `3M`, `1A`, `MAX`).
   - **Controles Interactivos de Discord (Components V2 / ActionRows)**:
     - Fila 1: Botones de temporalidad `[ 1D ]` `[ 1S ]` `[ 1M ]` `[ 1A ]` `[ MAX ]` que redibujan la gráfica al instante editando el mensaje.
     - Fila 2: Botón verde `[ 🛒 Comprar ]` y botón rojo `[ 💰 Vender ]` que abren ventanas modales nativas para introducir cantidad de acciones a operar.
     - Fila 2 (Enlace): Botón `[ 🌐 Ver Terminal Web ]` con link directo.

2. **Terminal Web Interactivo (Vercel / Next.js + TradingView)**:
   - Despliegue de un portal complementario conectado a la API de Render (similar a Tribunal Gaming).
   - Uso de la librería oficial **TradingView Lightweight Charts** (open-source):
     - Paneo lateral fluido y zoom interactivo con la rueda del ratón.
     - Tooltip en tiempo real al pasar el cursor (Apertura, Máximo, Mínimo, Cierre, Volumen).
     - Libro de compras y ventas recientes en vivo.

---

## 9. Modelo de Valoración Dinámico (Aura Fundamental + Flujo de Mercado con PER)

> **Estado:** `Ratificado por Jose` `[Aprobado · Jose · 22/10/2026]`

Arquitectura contable bursátil real ratificada para el Sanvi Exchange:

### 9.1. Ventana Móvil de 30 Días con Snapshots Diarios de Cakey Bot
> **Estado:** `[Aprobado · Jose · 22/10/2026]`

En sustitución de oyentes complejos en vivo de audio y texto en Discord:
- El bot almacena diariamente a las 00:00 UTC una instantánea en `datos/cakey_history.json` a través de [`modulos/cakey_client.py`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/cakey_client.py).
- El **Rendimiento de los últimos 30 días** se obtiene como la diferencia respecto al snapshot de hace 30 días:
  $$\Delta \text{Voz}_{30d} = \text{Voz}_{\text{hoy}} - \text{Voz}_{\text{hace 30 días}}$$
  $$\Delta \text{Mensajes}_{30d} = \text{Mensajes}_{\text{hoy}} - \text{Mensajes}_{\text{hace 30 días}}$$
- Cero listeners pesados en Discord, cero desincronizaciones y persistencia tolerante a reinicios en Render.

### 9.2. El Aura como Base del Precio y Fuerte Sensibilidad al Flujo de Órdenes
> **Estado:** `[Aprobado · Jose · 22/10/2026]`

1. **Aura = Precio Fundamental Base ($P_{\text{base}}$)**:
   - El Aura se define como el valor fundamental intrínseco de cada acción individual en Porros:
     $$P_{\text{base}} = \text{Book Value (Suelo Indestructible)} + \text{Earnings Mensuales (30 días)}$$
   - **Book Value ($BV$)**: Premia el nivel y la veteranía de por vida extraída de Cakey Bot:
     $$BV = 10 + (0{,}8 \times \text{Nivel}) + (0{,}2 \times \text{Horas Históricas Voz}) + (0{,}02 \times \text{Mensajes Históricos})$$
     - *Joselito (Lvl 54, 65.8h voz, 658 msgs)*: **79,52 Porros**
     - *Terre (Lvl 37, 25.0h voz, 196 msgs)*: **48,52 Porros**
     - *Omen (Lvl 36, 29.8h voz, 148 msgs)*: **47,72 Porros**
     - *Racer (Lvl 33, 29.0h voz, 129 msgs)*: **44,78 Porros**
     - *Aspirante Nivel 20 (IPO mínima)*: **~30,00 Porros**
   - **Rendimiento Mensual Temporal ($\text{Earnings}_{30d}$ — Ponderación 50/50)**:
     > **Estado:** `[Aprobado · Jose · 22/10/2026]`
     $$E_{30d} = (0{,}50 \times \Delta\text{Horas Voz}_{30d}) + (0{,}05 \times \Delta\text{Mensajes}_{30d})$$
     - **Equilibrio 50% Voz / 50% Chat**:
       - **1 hora de llamada** en los últimos 30 días = **$+0{,}50 \text{ Porros}$**.
       - **10 mensajes con XP** en los últimos 30 días = **$+0{,}50 \text{ Porros}$** ($0{,}05 \text{ Porros/msg}$).
       - Para un miembro activo medio con **20 horas de voz** y **200 mensajes** en el mes: la voz aporta **$+10 \text{ Porros}$ (50%)** y el chat aporta **$+10 \text{ Porros}$ (50%)**.
     - La actividad reciente en la ventana móvil de 30 días añade valor a la acción; si el miembro reduce su actividad o está de exámenes, decae suavemente a 0 sin tocar el suelo $BV$.

2. **Curva de Elasticidad del Market Maker ($P_{\text{mercado}}$)**:
   > **Estado:** `[Aprobado · Jose · 22/10/2026]`
   - El precio de mercado ($P_{\text{mercado}}$) responde directamente a las acciones netas absorbidas por los miembros:
     $$P_{\text{mercado}} = P_{\text{base}} \times \left(1 + \frac{\text{Acciones en Cartera de Usuarios} - 100}{2.000}\right)$$
     - Cada **100 acciones** compradas: **$+5\%$** de subida.
     - Cada **200 acciones** compradas: **$+10\%$** de subida.
     - Cada **500 acciones** compradas: **$+25\%$** de subida.
     - **1.000 acciones** compradas (10% del float): **$+50\%$** de subida (*rally* alcista).
     - **2.000 acciones** compradas (20% del float): **$+100\%$** de subida ($2\times$ el valor base).
   - **Suelo Garantizado:** $P_{\text{mercado}} \ge P_{\text{base}}$ (las ventas devuelven el precio a su valor contable objetivo).
   - **Blindaje Anti-Ballenas:** Máximo **500 acciones** por transacción y **30 segundos** de cooldown por usuario en el mismo ticker.

---

### 9.3. Indicadores Técnicos Institucionales y Análisis de Asistente IA
> **Estado:** `Ratificado por Jose` `[Aprobado · Jose · 22/10/2026]`

Los indicadores cuantitativos se computan sobre la serie temporal de snapshots diarios en [`datos/cakey_history.json`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/datos/cakey_history.json). Son **estrictamente informativos** (análisis técnico para los inversores; no alteran artificialmente el precio del AMM):

1. **Oscilador de Momentum (RSI a 14 Días)**:
   - Mide la aceleración y desaceleración de actividad diaria en una escala de 0 a 100:
     - `RSI > 70` (*Sobrecomprado*): Racha intensa de actividad reciente; máxima atención comunitaria.
     - `30 <= RSI <= 70` (*Consolidación*): Ritmo regular y saludable de actividad.
     - `RSI < 30` (*Sobrevendido / Oportunidad de Valor*): Actividad reciente baja (ej. exámenes o trabajo temporal); suelo $BV$ intacto, representando un descuento atractivo ("*Buy the dip*").

2. **Batería Institucional de Medias Móviles (SMA y EMA de 14, 50, 100 y 200 Días)**:
   - **14 Días:** Pulso a corto plazo y aceleración semanal.
   - **50 Días:** Tendencia intermedia mensual.
   - **100 Días:** Media de medio plazo (trimestral).
   - **200 Días:** Media móvil institucional de largo plazo (soporte macro histórico del miembro).
   - **Señales de Cruce:** Detección automática de *Golden Cross* (cruce alcista de corto sobre largo plazo) y *Death Cross* (cruce bajista).

3. **Asistente IA como Analista Financiero Jefe de Sanvi Capital**:
   - Mediante el comando `/bolsa informe [ticker]` o dentro del embed de `/aura [usuario]`, el bot `Asistente` procesa estos indicadores numéricos y genera con IA (Gemini) un informe financiero con tono analítico y de colega, sintetizando fundamentales, momentum técnico y un dictamen claro (*Comprar / Mantener / Tomar Beneficios*).

---

## 10. Registro de Decisiones y Estado Canónico (Compuerta 5 — Regla Global §13)

- [x] Ticker bursátil propio por miembro cotizado (ej. `$JOSE`, `$TERRE`) (`[Aprobado · Jose · 20/10/2026]`).
- [x] Suministro fijo de 10.000 acciones por miembro cotizado (`[Aprobado · Jose · 20/10/2026]`).
- [x] Asignación inicial: 100 acciones (1%) al fundador en su cartera, 9.900 acciones (99%) al Market Maker del bot (`[Aprobado · Jose · 20/10/2026]`).
- [x] Horquilla Bid/Ask con spread del 1% (0,5% compra / 0,5% venta) quemado como tasa deflacionaria (`[Aprobado · Jose · 20/10/2026]`).
- [x] Interfaz gráfica de velas japonesas estilo Trading 212 en Pillow + Components V2 interactivos (`[Aprobado · Jose · 20/10/2026]`).
- [x] Ventana móvil de 30 días calculada mediante snapshots diarios de Cakey Bot en `datos/cakey_history.json` (`[Aprobado · Jose · 22/10/2026]`).
- [x] El Aura se redefine como el Precio Fundamental Base ($P_{\text{base}} = \text{Book Value} + \text{Earnings}_{30d}$) (`[Aprobado · Jose · 22/10/2026]`).
- [x] Fórmulas matemáticas ratificadas de Book Value y Earnings 30d (`[Aprobado · Jose · 22/10/2026]`).
- [x] Curva de elasticidad del Market Maker con factor $K=2.000$ (+5% por 100 acciones, suelo en $P_{\text{base}}$) (`[Aprobado · Jose · 22/10/2026]`).
- [x] Blindaje anti-ballenas: tope de 500 acciones/orden y cooldown de 30s (`[Aprobado · Jose · 22/10/2026]`).
- [x] Tríada Financiera de Incentivos ratificada: Plusvalía de Mercado (AMM), Sinergia de Cartera por Aura (+5% a +25% en /trabajar) y Fondo Real de Dividendos semanal (50% spread Bolsa + 1% rake slots) (`[Aprobado · Jose · 22/10/2026]`).
- [x] Indicadores técnicos institucionales ratificados: Medias móviles (SMA/EMA 14, 50, 100 y 200 días), RSI a 14 días (100% informativos) e informes narrativos de Asistente IA (`[Aprobado · Jose · 22/10/2026]`).
- [x] Ponderación de Earnings 30d ratificada al 50/50: 1h voz = +0,50 Porros, 10 msgs = +0,50 Porros (`[Aprobado · Jose · 22/10/2026]`).
- [x] Régimen Operativo Continuo 24/7 ratificado: negociación ininterrumpida los 7 días de la semana (`[Confirmada · Jose · 22/10/2026]`).
- [x] Paro de Emergencia y Mantenimiento Técnico: el mercado solo se suspende manualmente ante contingencias o ajustes críticos mediante el interruptor administrativo `emergency_halt` (`[Confirmada · Jose · 22/10/2026]`).
- [x] Temporalidades Intradía Reales para fases tempranas ratificadas: `[Trades]` (vela por orden), `[15m]` (velas 1 min), `[1h]` (velas 2 min), `[4h]` (velas 10 min) y `[1D]` (velas 30 min), con indicación explícita de resolución de vela en la cabecera/footer (`[Confirmada · Jose · 22/10/2026]`).
- [x] Terminal Web Bursátil Interactiva en Render (`/bolsa`) ratificada: panel web servido en puerto 10000 con TradingView Lightweight Charts (velas interactivas, zoom, los 4 tickers, libro de órdenes y cartera) (`[Confirmada · Jose · 22/10/2026]`).
- [x] Batería completa de 8 temporalidades ratificada (Discord y Web): incorporación de `[1S]` (velas de 4h, 42 velas), `[1M]` (velas de 1D, 30 velas) y `[MAX]` (velas de 1D/adaptativas desde el origen, hasta 60 velas) distribuidas en 2 filas de 4 botones (`[Trades, 15m, 1h, 4h]` y `[1D, 1S, 1M, MAX]`) (`[Confirmada · Jose · 23/10/2026]`).
- [x] Selección nativa de Tickers sin escritura manual ratificada: `@app_commands.choices` en `/bolsa` + menú desplegable `Select` en la Fila 3 de la terminal para cambiar de ticker al instante (`[Confirmada · Jose · 23/10/2026]`).
- [x] Unificación técnica de Informe IA y renderizado de emojis: fuente única de verdad (`get_ticker_technical_metrics`) entre la terminal y `generate_market_report`, conversión automática con `format_server_emojis` y presentación en Embed institucional coloreado según dictamen (`[Confirmada · Jose · 23/10/2026]`).
- [x] Rediseño visual HD (960x540) de gráfica Pillow y Embed de Terminal: eliminación de rayas verdes en cubetas con `volume=0` (línea gris tenue sin barra de volumen), curva EMA 14 superpuesta, eje X con fechas/horas, caja de estadísticas (Máx/Mín/Vol) y barra de progreso de Float/Liquidez con emojis nativos del servidor (`[Confirmada · Jose · 23/10/2026]`).




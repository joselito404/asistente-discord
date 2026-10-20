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
- `mpx56.` (Nivel 19 $\rightarrow$ a 1 nivel de cotizar): **`$MPX`**
- `carlitosmf__` (Nivel 18 $\rightarrow$ a 2 niveles de cotizar): **`$CARL`**
- `vexus_1128` (Nivel 17): **`$VEXUS`**
- `ccmen1408` (Nivel 15): **`$CCMEN`**
- `zixxer_donnuts_05511` (Nivel 15): **`$ZIXX`**
- `alexpro0812` (Nivel 10): **`$ALEX`**
- `motor123...` (Nivel 10): **`$MOTOR`**

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

### 7.2. Sistema de Dividendos Pasivos (Incentivo Real al *Hold*)
- **Mecánica de Financiación (Impuesto de Sociedades / 5% del Salario)**:
  - Cada vez que el miembro cotizado reclama su `/salario` diario en [`modulos/economia_core.py`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/economia_core.py), se deduce automáticamente un **5%** para alimentar el bote de dividendos de su acción.
  - El 95% restante del salario entra directo a su efectivo limpio.
  - **Cero Inflación**: Los dividendos proceden de riqueza real generada por el usuario, sin imprimir moneda de la nada.
- **Distribución Proporcional**:
  - El bote del 5% se reparte automáticamente entre todas las acciones en manos de usuarios (incluyendo el 1% del propio fundador).
  - *Ejemplo práctico:* Si Terre (Nvl 37) cobra su salario base de **5.700 Porros**:
    - Terre recibe **5.415 Porros** (95%).
    - Se genera un bote de dividendos de **285 Porros** (5%).
    - Si Jose posee el 40% de las acciones de Terre en circulación, Jose recibe **114 Porros pasivos** en su cuenta de inmediato.

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



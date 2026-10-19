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
| **🎙️ Convivencia en Voz** | 45% | 4.500 pts | Minutos en llamada (mínimo 2 personas, mute 50%, deaf 0%, curva 0-3h 100%, 3-6h 75%, >6h 50%) y streaming. |
| **💬 Chat y Comunidad** | 35% | 3.500 pts | Constancia por zonas ($\times 1{,}5$ Gaming/General, $\times 0{,}3$ Casino/Bots), respuestas recibidas, celebraciones ($\ge 2$ reactores) y alcance. |
| **🌟 Momentos de Lore y Hazañas** | 20% | 2.000 pts | Base 1.000 pts $\pm$ momentos citables reales (hazañas, memes top, Steam vs plantones, "luego" eterno, dejar en visto). |

$$\text{Total Aura Fundamental} = \text{Voz (4.500)} + \text{Chat (3.500)} + \text{Momentos (2.000)} = 10.000 \text{ pts}$$

---

## 5. Decisiones Aprobadas y Pendientes
- [x] **Pesos Definitivos del Índice de Aura**: 3 Pilares Reales (45% Voz / 35% Chat / 20% Momentos sobre 10.000 pts) `[Aprobado · Jose · 18/10/2026]`.
- [ ] **Pilar 1 (Voz y Convivencia)**: `[Reabierto para revisión · Jose · 19/10/2026]`.

- [x] **Algoritmo de Mercado (50%)**: Opción A — Modelo AMM / Bonding Curve continua tipo Uniswap con liquidez infinita contra la banca y comisión fija del 1% (spread de quema de Porros) `[Aprobado · Jose · 19/10/2026]`.
- [x] **Diseño de Interfaz Gráfica (Híbrido Dual)**: Render nativo en Discord (Pillow) + Web interactiva en Vercel (TradingView Lightweight Charts) con estética idéntica a Trading 212 `[Aprobado · Jose · 19/10/2026]`.
- [ ] **Pilar 2 (Chat y Comunidad)**: `[Propuesta · Chat 1 · 19/10/2026]` · `[Pendiente de matizar: reparto de puntos, longitud mínima y ventana móvil]`.
- [ ] **Pilar 3 (Momentos de Lore)**: `[Propuesta · Chat 1 · 19/10/2026]` · `[Pendiente de matizar: canal o comando de registro y jueces]`.
- [ ] **Frecuencia de Formación de Velas Japonesas**: `[Propuesta · Chat 1 · 19/10/2026]` · `[Pendiente de matizar: temporalidad de cierre de velas (1 hora vs 1 día)]`.


---

## 6. Arquitectura de Interfaz y Gráficas de Cotización (Estilo Trading 212)

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



# 💰 Especificación de Diseño Viva: Economía Nativa e Independencia de UnbelievaBoat

> **Estado del Documento**: `Vigente (Regla §13)`
> **Fecha de Aprobación**: 20 de Octubre de 2026
> **Autoría y Decisiones**: `[Aprobado · Jose · 20/10/2026]`
> **Responsable**: Chat 3 (Economía Pura y Dura) en paralelo con Chat 1 (Bolsa Sanvi)

---

## 1. Alcance Oficial Aprobado y Descartado

### ✅ Sistemas Aprobados (`[Aprobado · Jose · 20/10/2026]`)
1. **Recalibración de `/trabajar` y Multiplicadores por Rol de Nivel**:
   - Cooldown oficial: **4 horas** (`14.400` segundos).
   - Rango de recompensa base: **1.000 a 2.500 Porros**.
   - **Multiplicadores por Rol de Nivel** (se toma el multiplicador más alto que posea el miembro, aplicable tanto a `/trabajar` como a `/crimen`):
     - Nivel 10 (`🔷 Pendejo de Rango Medio`): **$+10\%$** ($\times 1.10$)
     - Nivel 30 (`🌸 Pendejo Experimentado`): **$+20\%$** ($\times 1.20$)
     - Nivel 50 (`⚔️ Pendejo de Élite`): **$+25\%$** ($\times 1.25$)
     - Nivel 70 (`🌟 Pendejo Legendario`): **$+30\%$** ($\times 1.30$)
     - Nivel 80+ (`👑 Pendejo Mítico` / `Ancestral` / `Supremo`): **$+40\%$** ($\times 1.40$)
2. **Delitos de Alto Riesgo (`/crimen`)**:
   - Cooldown oficial: **12 horas** (`43.200` segundos).
   - Probabilidad de éxito: **50%** (`0.50`).
   - Recompensa en éxito: **1.800 a 3.500 Porros** base, multiplicada por el bono de rol de nivel del usuario.
   - Penalización en fallo (50%): **Multa del 10% del efectivo (`cash`)** con suelo mínimo de **500 Porros** (si el usuario tiene menos de 500 Porros en efectivo, pierde todo su efectivo restante quedando en `0`, nunca en negativo). El **3%** de la multa recaudada alimenta el `server_jackpot`.
   - Textos narrativos propios ambientados en el lore del servidor (tanto para golpes exitosos como para redadas fallidas).
3. **Atracos a Carteras (`/robar`) (`[Aprobado · Jose · 20/10/2026]`)**:
   - Cooldown oficial: **24 horas** (`86.400` segundos).
   - Probabilidad de éxito: **50%** (salvo si la víctima posee `🛡️ Cartera Blindada`, donde falla el **100%** de las veces).
   - Botín en caso de éxito: Entre el **20% y el 33%** (`0.20` a `0.33`) del efectivo (`cash`) de la víctima (el banco es 100% inmune).
   - Multa en caso de fallo (normal o por `🛡️ Cartera Blindada`): Se deduce un **15% del efectivo del ladrón** (mínimo 100 Porros, sin bajar de 0), repartido exactamente así:
     - **10% del efectivo del ladrón** ($\frac{2}{3}$ de la multa) va a la **víctima** como indemnización directa.
     - **5% del efectivo del ladrón** ($\frac{1}{3}$ de la multa) se inyecta directamente al **bote acumulado del servidor (`server_jackpot`)**.
4. **Restricción de Canales y Límites del Casino (`[Aprobado · Jose · 20/10/2026]`)**:
   - **Filtro Estricto de Canales**: Todos los comandos de economía y casino solo pueden ejecutarse dentro de los canales de la categoría `🎲・CASINO & ECONOMÍA・🎲` (ID `1549512417610956871`: `#🎰casino-y-apuestas🎰`, `#🎰casino-y-apuestas-2🎰`, `#🏪tienda-y-mercado🏪`) y en `#🛠️apps-solo-mods🛠️` (`1537574896605265970`). Si un usuario los invoca en cualquier otro canal (ej. `#💬general💬`), el bot bloquea la ejecución y responde en efímero (`ephemeral=True`) redirigiéndolo a los canales oficiales.
   - **Apuesta Mínima Unificada**: **100 Porros** de apuesta mínima en todos los juegos del casino (`/slots`, `/blackjack`, `/bj`, `/ruleta`, `/coinflip`). Apuesta máxima sin límite (`all` / `todo` permitido).
   - **Fluidez de Tiradas**: Sin límite de 4 partidas cada 5 minutos.
5. **Clasificación de Riqueza (`/ranking`)**:
   - Visibilidad: **Pública** (`ephemeral=False`) para fomentar la competitividad en los canales de economía.
   - Interfaz interactiva (`RankingView`) con menú desplegable (`Select`) para alternar en vivo entre:
     - `💎 Patrimonio Total` (`cash + bank`)
     - `💵 Efectivo (Cash)`
     - `🏦 Banco (Bank)`
   - Muestra el Top 10 de miembros del servidor con medallas (`🥇`, `🥈`, `🥉`) y destaca en el pie la posición exacta y saldo del usuario que ejecuta el comando.
4. **Tienda Actualizada, `/inventario`, `/usar` y Watcher de Expiración**:
   - **Sustitución del Pollo de Pelea (`[Aprobado · Jose · 20/10/2026]`)**: Se reemplaza `🍗 Pollo de Pelea Dopado` por **`🥤 Monster Blanco`** (`monster_blanco`, **25.000 Porros**, acumulable). Al consumirse con `/usar`, resetea de inmediato los cooldowns activos de `/trabajar`, `/crimen` y `/robar`.
   - **Pases Temporales de XP en Inventario (`[Aprobado · Jose · 20/10/2026]`)**:
     - Al comprar `⚡ Chute de XP (24h)`, `🔥 Pase Semanal de XP` o `💠 Pase Mensual de XP` en `/tienda`, el artículo se guarda en el `inventory` del usuario (permitiendo almacenarlos o comprarlos por adelantado).
     - Los roles permanentes (`🛡️ Cartera Blindada`, `🚬 Camello del Barrio`, `🎰 Ludópata Rehabilitado`, `👑 Aura de XP Permanente`) se siguen asignando automáticamente al momento de la compra.
   - **Comando `/inventario` (`[Aprobado · Jose · 20/10/2026]`)**:
     - Consulta el inventario de artículos en propiedad (agrupados por cantidad, ej. `×2`), roles permanentes adquiridos y pases temporales de XP activos con su tiempo restante exacto.
     - Visibilidad: **Efímero** (`ephemeral=True`) al consultar el propio, e incluye un botón interactivo **`[📢 Mostrar en público]`** para que el usuario pueda publicarlo en el canal si desea presumir. Si se consulta el inventario de otro miembro (`/inventario usuario:@alguien`), también es efímero para no hacer spam.
   - **Comando `/usar` (`[Aprobado · Jose · 20/10/2026]`)**:
     - Permite consumir un artículo activable del inventario (con autocompletado o selector de ítems usables: `🥤 Monster Blanco`, `⚡ Chute de XP (24h)`, `🔥 Pase Semanal de XP`, `💠 Pase Mensual de XP`).
     - Al usar un pase temporal de XP: consume 1 unidad del inventario, asigna el rol correspondiente de Discord al miembro y registra en `user["active_buffs"]` la entrada `{item_id, role_id, name, expires_at}`. Si ya tenía ese mismo pase activo, extiende su duración sumando las horas al `expires_at` vigente.
   - **Comando `/regalar` (`[Aprobado · Jose · 20/10/2026]`)**:
     - Permite a un miembro regalar artículos transferibles de su `/inventario` a otro miembro humano del servidor (`/regalar usuario:@miembro articulo:<choice> cantidad:<int>`).
     - Son transferibles únicamente los coleccionables, consumibles y pases temporales sin activar (`🚬 Porro de Oro`, `🥤 Monster Blanco`, `⚡ Chute de XP (24h)`, `🔥 Pase Semanal de XP`, `💠 Pase Mensual de XP`). Los roles permanentes únicos (`🛡️ Cartera Blindada`, `🚬 Camello del Barrio`, `🎰 Ludópata Rehabilitado`, `👑 Aura de XP Permanente`) no son transferibles una vez comprados.
   - **Watcher de Expiración en `bot_service.py` (`[Aprobado · Jose · 20/10/2026]`)**:
     - Tarea asíncrona en segundo plano que revisa periódicamente (cada 15-60 minutos y al arrancar el bot) las entradas de `active_buffs` de todos los usuarios en `datos/economia.json`.
     - Cuando `now >= expires_at`, retira el rol de Discord del miembro en el servidor y limpia el buff expirado de `datos/economia.json`.
5. **Panel de Control Financiero de Administración (`/admin_dinero`)**:
   - Restringido estrictamente a Administradores (`@app_commands.default_permissions(administrator=True)` y chequeo `interaction.user.guild_permissions.administrator`):
     - `accion`: `dar` | `quitar` | `fijar` | `airdrop`
     - `cantidad`: Entero positivo (o $\ge 0$ para `fijar`).
     - `usuario`: Miembro objetivo (para `dar`, `quitar`, `fijar`).
     - `rol`: Rol objetivo (para `airdrop`, reparte `cantidad` a todos los miembros humanos que posean dicho rol).
     - `destino`: `efectivo` (`cash`) o `banco` (`bank`).
6. **Sincronización Final de Saldos de UnbelievaBoat**:
   - Verificado en vivo el 20/10/2026 via API REST: los saldos de [`datos/economia.json`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/datos/economia.json) están 100% al día con el estado real de UnbelievaBoat.
   - La retirada/desconexión final de UnbelievaBoat queda reservada exclusivamente a Jose (`seguridad_credenciales.md` §2).

### ❌ Bloques Descartados Expresamente (`[Aprobado · Jose · 20/10/2026]`)
- **Descartado `/trapicheo` (`/slut`)**: No se incluye comando intermedio redundante.
- **Descartado `/pelea_gallos` (`/cockfight`)**: Descartado por completo y reemplazado su ítem en tienda por `🥤 Monster Blanco`.
- **Descartados *Ruleta Rusa* y *Mayor o Menor (High-Low)***: Se consolidan exclusivamente los **4 juegos estrella** (`/slots` a RTP 110%, `/blackjack`, `/ruleta` y `/coinflip`).
- **Descartado *Chat Money***: Sin pagos automáticos por mensaje.

---

## 2. Sistema de Salario Progresivo por Nivel Exacto (`/salario`) (`[Aprobado · Jose · 20/10/2026]`)

En lugar de cobrar únicamente por saltos de rol cada 10 niveles, `/salario` interpola linealmente el salario diario base $S(L)$ según el **nivel real exacto** $L$ del usuario en Cakey Bot (obtenido en vivo de `get_live_levels_dict()`, con fallback al nivel mínimo del rol de jerarquía más alto que posea en Discord si no consta en caché):

### 2.1. Escala Progresiva por Tramos de Nivel
- **Nivel $< 10$**: `0` Porros/día (la categoría de Casino y Economía requiere Nivel 10).
- **Tramo 10 – 19 (`🔷 Rango Medio`)**: $2.000 + (L - 10) \times 200$ Porros/día.
- **Tramo 20 – 29 (`🔮 Veterano`)**: $4.000 + (L - 20) \times 300$ Porros/día.
- **Tramo 30 – 39 (`🌸 Experimentado`)**: $7.000 + (L - 30) \times 450$ Porros/día.
- **Tramo 40 – 49 (`🔥 Alto Rango`)**: $11.500 + (L - 40) \times 650$ Porros/día.
- **Tramo 50 – 59 (`⚔️ Élite`)**: $18.000 + (L - 50) \times 1.000$ Porros/día.
- **Tramo 60 – 69 (`⚡ Maestro`)**: $28.000 + (L - 60) \times 1.400$ Porros/día.
- **Tramo 70 – 79 (`🌟 Legendario`)**: $42.000 + (L - 70) \times 2.000$ Porros/día.
- **Tramo 80 – 89 (`👑 Mítico`)**: $62.000 + (L - 80) \times 2.800$ Porros/día.
- **Tramo 90 – 99 (`🔱 Ancestral`)**: $90.000 + (L - 90) \times 4.000$ Porros/día.
- **Tramo $\ge 100$ (`💠 Supremo`)**: $130.000 + (L - 100) \times 5.000$ Porros/día.

### 2.2. Plus de Podio y Acumulación con Decaimiento
- **Plus de Podio (acumulable al salario de nivel)**:
  - `🥇 Top 1`: **$+8.000$** Porros/día.
  - `🥈 Top 2`: **$+5.000$** Porros/día.
  - `🥉 Top 3`: **$+3.000$** Porros/día.
- **Acumulación Multi-Día**: Mantiene la fórmula de decaimiento diario del **5%** ($P = S \cdot \frac{1 - (1-d)^n}{d}$, asíntota $20 \times S$) con cooldown mínimo de **24 horas** entre cobros.

---

## 3. Plan de Orden y Modularización de Scripts Grandes (`[Aprobado en Hoja de Ruta · Jose · 20/10/2026]`)

### 3.1. Diagnóstico de Tamaño Actual en `modulos/`
- `modulos/economia.py`: **4.787 líneas (187,9 KB)** — Demasiado grande; ralentiza la lectura y edición de los agentes (límite de 800 líneas por lectura).
- `modulos/comandos.py`: **2.317 líneas (96,4 KB)** — Agrupa los 22 comandos generales y los 20 de economía en un solo fichero.

### 3.2. Arquitectura de División Aprobada para la Sesión de Orden (`[Aprobado · Jose · 20/10/2026]`)
1. **Desglosar `modulos/economia.py` (4.787 líneas $\to$ submódulos de ~600–900 líneas)** manteniendo `modulos/economia.py` como fachada de reexportación 100% retrocompatible:
   - `modulos/economia_core.py`: Persistencia atómica (`economia.json`), saldos, banca (`/depositar`, `/retirar`, `/transferir`), `/trabajar`, `/crimen`, `/robar`, `/salario`, `/ranking` y `/admin_dinero`.
   - `modulos/economia_tienda.py`: Catálogo `SHOP_ITEMS`, `ShopInteractiveView`, `/inventario`, `/usar`, `/regalar` y watcher de expiración de pases XP (`check_and_expire_buffs`).
   - `modulos/casino_slots.py`: Motor `SlotEngine` 5x3, símbolos, líneas y vistas V2 (`SlotsLayoutView`).
   - `modulos/casino_juegos.py`: Motores y vistas de `BlackjackEngine`, `RouletteEngine`, `CoinflipEngine` y `CasinoHubView`.
2. **Desglosar `modulos/comandos.py` (2.317 líneas $\to$ 2 módulos por bot)**:
   - `modulos/comandos_generales.py`: Los 22 comandos del bot `Asistente`.
   - `modulos/comandos_economia.py`: Los 20 comandos del bot `Economia Asistente` y `ensure_economy_channel`.
   - `modulos/comandos.py`: Fachada ligera (~50 líneas) que une y reexporta ambos árboles para no romper ningún test ni import en `bot_service.py`.

---

## 4. Plantilla Lista para `#⌨️comandos⌨️` y Tópicos de Canales (`[Aprobado · Jose · 20/10/2026]`)

### 4.1. Nuevos Tópicos de Canales (para aplicar al desplegar)
- **`#🎰casino-y-apuestas🎰` (`1549458785485987890`)**:
  `🎰 Casino Oficial de Porros (Economia Asistente) • Apuesta mínima: 100 Porros (¡All-in libre!) • Comandos: /casino, /slots, /blackjack (/bj), /ruleta, /coinflip, /trabajar, /crimen, /robar, /salario`
- **`#🎰casino-y-apuestas-2🎰` (`1550894047382610081`)**:
  `🎰 Sala 2 del Casino Oficial de Porros • Tiradas simultáneas sin esperas • /casino, /slots, /blackjack (/bj), /ruleta, /coinflip`
- **`#🏪tienda-y-mercado🏪` (`1549512919694442547`)**:
  `🏪 Tienda e Inventario Oficial de Porros • Usa /tienda para comprar roles, pases de XP y Monster Blanco, /inventario para ver tus objetos, /usar para activarlos, /regalar para enviarlos y /ranking para ver el Top de ricos.`

### 4.2. Texto Renovado para `#⌨️comandos⌨️` (ZONA DE COMANDOS — ECONOMÍA Y CASINO)
```markdown
## 💰 ECONOMÍA OFICIAL DE PORROS Y CASINO (`@Economia Asistente`)
> 📍 *Todos los comandos de economía y casino se usan exclusivamente en los canales de la categoría **🎲・CASINO & ECONOMÍA・🎲**.*

### 🏦 Banca, Cartera y Clasificación
- **`/balance [usuario]`** — Consulta tus <:Porro:1535685303317172305> Porros en efectivo, banco, patrimonio total y el bote acumulado del servidor.
- **`/depositar <cantidad | all>`** — Guarda tus Porros en el banco (100% protegidos frente a `/robar`).
- **`/retirar <cantidad | all>`** — Saca Porros del banco a tu mano para apostar o comprar en la tienda.
- **`/transferir <@usuario> <cantidad>`** — Envía Porros en efectivo a otro miembro sin comisiones.
- **`/ranking`** — Tabla de clasificación interactiva en vivo (*Patrimonio Total*, *Efectivo* y *Banco*).

### 💼 Cómo Ganar Porros (Ingresos y Delitos)
- **`/trabajar`** *(cada 4h)* — Curra en el servidor y gana entre **1.000 y 2.500 Porros** (+ tu multiplicador de rol de nivel: de `+10%` a `+40%`).
- **`/salario`** *(cada 24h, acumulativo)* — Cobra tu sueldo diario progresivo según tu **nivel exacto** en el servidor (desde Nivel 10) + bonus de Podio (`🥇 Top 1`, `🥈 Top 2`, `🥉 Top 3`). Si tardas varios días en cobrar, se acumula con un 5% de decaimiento diario.
- **`/crimen`** *(cada 12h)* — Delito de alto riesgo: **50% de éxito** (**1.800 a 3.500 Porros** + bono de nivel) y **50% de fallo** (multa del **10%** de tu efectivo, mín. 500 Porros, aportando el 3% al bote).
- **`/robar <@usuario>`** *(cada 24h)* — Intenta atracar el efectivo de otro miembro (**50% de éxito**, robas del **20% al 33%** de su efectivo). Si fallas o tiene `🛡️ Cartera Blindada`, pagas un **15% de multa** (**10%** va a la víctima y **5%** al bote del servidor).

### 🏪 Tienda, Inventario y Regalos
- **`/tienda`** — Catálogo interactivo oficial: compra roles permanentes (`🛡️ Cartera Blindada`, `🚬 Camello del Barrio`, `🎰 Ludópata Rehabilitado`, `👑 Aura de XP`), coleccionables (`🚬 Porro de Oro`), pases temporales de XP y **`🥤 Monster Blanco`** (*resetea al instante tus cooldowns de `/trabajar`, `/crimen` y `/robar`*).
- **`/inventario [usuario]`** — Consulta tus artículos, roles y el tiempo restante de tus pases de XP activos (con botón para mostrarlo en público).
- **`/usar <artículo>`** — Bebe un `🥤 Monster Blanco` o activa cuando quieras un pase temporal de XP (`24h`, `7 días` o `30 días`) guardado en tu inventario.
- **`/regalar <@usuario> <artículo> [cantidad]`** — Regala objetos, Monster Blanco o pases de XP de tu inventario a otro miembro.

### 🎰 Casino Oficial (Apuesta mín: 100 Porros | Máx: All-in)
- **`/casino`** — Centro de control interactivo con el bote acumulado, reglas y RTP de cada juego.
- **`/slots <apuesta | all>`** — Tragaperras 5x3 limpia: 3 líneas horizontales y diagonales de 3 casillas reales (sin figuras raras ni Scatters), Comodín WILD, Pantalla Completa a $\times 500$ y Bote Progresivo (**RTP 110%**).
- **`/blackjack <apuesta | all>`** *(o `/bj`)* — Blackjack 21 interactivo contra el crupier (6 barajas, pago 3:2 en Blackjack natural, pedir, plantarse y doblar).

---

## 5. Rediseño Geométrico de Tragaperras 5x3 Limpia (`[Aprobado · Jose · 20/10/2026]`)

1. **Erradicación de Figuras Forzadas y Scatters**:
   - Eliminadas definitivamente las líneas en "V Suave", "V Invertida", "Zigzag" o "Escalones".
   - Eliminado el símbolo SCATTER y la mecánica de Free Spins (partidas instantáneas sin pantallas extra ni frenazos).
   - Conservado el comodín **WILD** (`:absolutecinema:`) que sustituye a cualquier regular y premia por sí mismo.
   - Conservados el **Grand Jackpot** (100% bote), **Mini Jackpot** (25% bote) y la **Pantalla Completa 15/15** ($\times 500.0$).

2. **Líneas y Diagonales Reales en Matriz 5x3**:
   - **3 Líneas Horizontales Completas**:
     * `Horizontal Centro`: `[(1, 0), (1, 1), (1, 2), (1, 3), (1, 4)]` (premia por 3, 4 o 5 seguidos).
     * `Horizontal Arriba`: `[(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)]` (premia por 3, 4 o 5 seguidos).
     * `Horizontal Abajo`: `[(2, 0), (2, 1), (2, 2), (2, 3), (2, 4)]` (premia por 3, 4 o 5 seguidos).
   - **Diagonales Rectas de 3 Casillas Reales**:
     * `Diagonal Descendente Izq \`: `[(0, 0), (1, 1), (2, 2)]`
     * `Diagonal Descendente Centro \`: `[(0, 1), (1, 2), (2, 3)]`
     * `Diagonal Descendente Der \`: `[(0, 2), (1, 3), (2, 4)]`
     * `Diagonal Ascendente Izq /`: `[(2, 0), (1, 1), (0, 2)]`
     * `Diagonal Ascendente Centro /`: `[(2, 1), (1, 2), (0, 3)]`
     * `Diagonal Ascendente Der /`: `[(2, 2), (1, 3), (0, 4)]`
   - Toda línea premiada se corresponde exactamente con una recta o diagonal real visible sin engaños visuales.
   - Calibración matemática de multiplicadores en simulación Monte Carlo para mantener **RTP 110.0%**.
- **`/ruleta <apuesta | all> <suerte>`** — Ruleta europea de 37 casillas (rojo/negro, par/impar, docenas, columnas y pleno 35:1) con botones de re-apuesta.
- **`/coinflip <apuesta | all> <cara | cruz> [@rival]`** — Cara o cruz al instante contra la casa (PvE) o duelo directo 1v1 por Porros contra otro miembro (PvP).
```

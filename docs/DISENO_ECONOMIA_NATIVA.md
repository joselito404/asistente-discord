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
3. **Clasificación de Riqueza (`/ranking`)**:
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
- **Descartado *Chat Money***: Sin pagos automáticos por mensaje.

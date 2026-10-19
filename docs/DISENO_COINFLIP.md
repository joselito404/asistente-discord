# Especificación de Diseño: Coinflip Dual (PvP y PvE) (`/coinflip`)

> **Ámbito**: Sistema de Casino y Duelos entre Miembros (`Economia Asistente`).  
> **Estado**: `[Aprobado · Jose · 19/10/2026]`  
> **Referencia de Arquitectura**: Regla Global §13 (Documentación Viva).  

---

## 1. Visión y Objetivos

El **Coinflip** (Cara o Cruz) es el juego más directo y de ritmo más rápido del casino. Esta especificación amplía las mecánicas de azar del servidor implementando una modalidad dual en el bot `Economia Asistente`:
1. **Modo PvP (Duelo entre Miembros)**: Permite a dos usuarios desafiarse directamente por Porros en `#🎰casino-y-apuestas🎰`, con aceptación interactiva por botón y comisión del $2\%$ al bote progresivo del servidor (`server_jackpot`).
2. **Modo PvE (Contra la Casa)**: Lanzamiento rápido 50/50 individual contra el casino con cobro $1:1$ y re-apuesta instantánea.

---

## 2. Mecánicas y Reglas del Juego

### A. Modo Duelo PvP (`/coinflip apuesta:<str> rival:@usuario [lado:cara|cruz]`)
* **Desafío**:
  * El autor indica la apuesta ($\ge 50$ Porros o `all`) y menciona al rival.
  * Se deduce y reserva inmediatamente la apuesta de la cartera (`cash`) del retador bajo `ECONOMY_LOCK` para evitar cancelaciones fraudulentas o dobles gastos.
  * Si el autor elige `cara`, el rival recibe automáticamente `cruz` (y viceversa).
* **Interacción del Retado (`CoinflipChallengeView`)**:
  * Se despliega un embed con mención ping al rival y dos botones interactivos:
    * **`[ ⚔️ Aceptar Desafío ]`** (`ButtonStyle.success`): Solo clickable por el rival.
    * **`[ 🏳️ Rechazar ]`** (`ButtonStyle.danger`): Clickable por el rival (o por el autor para cancelar).
* **Resolución y Cobro**:
  * Si el rival rechaza o transcurren **60 segundos sin respuesta (Timeout)**, el duelo se cancela y se devuelve el $100\%$ del importe retenido al retador.
  * Si el rival acepta:
    * Se verifica que el rival cuente con fondos suficientes. Si no tiene saldo, se rechaza y reembolsa.
    * Se deduce la apuesta del rival.
    * Lanzamiento justo 50/50 (`random.choice(["cara", "cruz"])`).
    * **Reparto del Bote**:
      * Bote Total: $2 \times \text{apuesta}$.
      * Comisión Comunitaria ($2\%$): Se transfiere al `server_jackpot` en [`datos/economia.json`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/datos/economia.json).
      * Premio del Ganador ($98\%$ del bote): Se abona de forma instantánea al saldo del vencedor.

---

### B. Modo Individual PvE (`/coinflip apuesta:<str> lado:cara|cruz`)
* Si no se menciona ningún rival, el jugador apuesta directamente contra el casino.
* **Probabilidad**: $50\%$ justa.
* **Pagos**:
  * Acierto: Pago **$1:1$** (ganancia neta igual a la apuesta, retorno $2\times$).
  * Fallo: Pérdida de la apuesta; el $3\%$ de la pérdida neta alimenta el `server_jackpot`.
* **Botón de Re-apuesta Rápida (`CoinflipActionView`)**:
  * `[ 🔄 Tirar Otra Vez ]`: Repite la misma tirada con 1 clic si el usuario tiene saldo.

---

## 3. Experiencia Visual en Discord

* Emoticonos temáticos: Moneda de Oro animada (`🪙`), Espadas cruzadas (`⚔️`), Corona de ganador (`👑`).
* Embed con colores dinámicos:
  * Amarillo Oro (`#F1C40F`) durante el desafío activo y animación de lanzamiento.
  * Verde Victoria (`#2ECC71`) al resolverse con el ganador proclamado en grande y el desglose de Porros transferidos.
  * Rojo Derrota o Cancelación (`#E74C3C`).

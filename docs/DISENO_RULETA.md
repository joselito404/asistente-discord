# Especificación de Diseño: Ruleta Europea 37 Casillas (`/ruleta`)

> **Ámbito**: Sistema de Casino Nativo de Discord (`Economia Asistente`).  
> **Estado**: `[Aprobado · Jose · 19/10/2026]`  
> **Referencia de Arquitectura**: Regla Global §13 (Documentación Viva).  

---

## 1. Visión y Objetivos

La **Ruleta Europea** es el juego de azar por excelencia de los casinos. Esta implementación dota a `Economia Asistente` de un motor de ruleta matemática precisa de 37 casillas ($0$ al $36$) con un Return to Player (RTP) teórico del $97.30\%$ (ventaja de la casa fija del $2.70\%$ por la presencia del cero verde).

Sustituye por completo al comando `!roulette` de UnbelievaBoat, ofreciendo una experiencia inmersiva en Discord con visualización del cilindro europeo, desglose de apuestas múltiples y botones de acción rápida para re-apostar.

---

## 2. Rueda Europea y Distribución de Números

El cilindro de la Ruleta Europea estándar sigue la secuencia circular oficial:
`0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26`

* **Cero ($0$)**: Verde (`🟩`).
* **Rojos ($18$ números)**: `1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36` (`🟥`).
* **Negros ($18$ números)**: `2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35` (`⬛`).

---

## 3. Tipos de Apuesta y Pagos Oficiales

| Tipo de Apuesta | Opciones Válidas | Casillas Cubiertas | Probabilidad | Pago Ganador (Neto) | Retorno Total |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Pleno / Número Directo** | `0` al `36` | 1 | $\frac{1}{37} \approx 2.70\%$ | **$35:1$** | $36\times$ apuesta |
| **Color** | `rojo` (`red`), `negro` (`black`) | 18 | $\frac{18}{37} \approx 48.65\%$ | **$1:1$** | $2\times$ apuesta |
| **Paridad** | `par` (`even`), `impar` (`odd`) | 18 | $\frac{18}{37} \approx 48.65\%$ | **$1:1$** | $2\times$ apuesta |
| **Rango (Mitades)** | `1-18` (baja/falta), `19-36` (alta/pasa) | 18 | $\frac{18}{37} \approx 48.65\%$ | **$1:1$** | $2\times$ apuesta |
| **Docenas** | `1-12` (1ª docena), `13-24` (2ª), `25-36` (3ª) | 12 | $\frac{12}{37} \approx 32.43\%$ | **$2:1$** | $3\times$ apuesta |
| **Columnas** | `col1`, `col2`, `col3` | 12 | $\frac{12}{37} \approx 32.43\%$ | **$2:1$** | $3\times$ apuesta |

> [!NOTE]
> Si la bola cae en **$0$ (verde)**, todas las suertes sencillas (color, paridad, mitades), docenas y columnas pierden. Solo ganan las apuestas a pleno directo sobre el `0`.

---

## 4. Alimentación del Bote Progresivo (`server_jackpot`)

Al igual que en las tragaperras y en el Blackjack, el **3% de las pérdidas netas** de cada tirada de ruleta se destina automáticamente a alimentar el `server_jackpot` en [`datos/economia.json`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/datos/economia.json), enriqueciendo el bote global que luego premia las jugadas de máxima élite.

---

## 5. Experiencia de Usuario y Componentes Discord

1. **Comando Slash**:
   * `/ruleta apuesta:<str> tipo:<choice> [numero:<int>]`:
     * `apuesta`: Monto entero $\ge 50$, o `all`/`todo`.
     * `tipo`: Menú desplegable de Discord con:
       * `🔴 Rojo`
       * `⚫ Negro`
       * `⚖️ Par`
       * `⚡ Impar`
       * `📉 1-18 (Baja)`
       * `📈 19-36 (Alta)`
       * `1️⃣ 1ª Docena (1-12)`
       * `2️⃣ 2ª Docena (13-24)`
       * `3️⃣ 3ª Docena (25-36)`
       * `🏛️ Columna 1`
       * `🏛️ Columna 2`
       * `🏛️ Columna 3`
       * `🎯 Pleno (Número exacto 0-36)`
     * `numero`: Requerido únicamente si `tipo == pleno` (0 a 36).
2. **Representación Visual en Embed**:
   * Color del embed: Verde casino (`#2ECC71`), Rojo (`#E74C3C`) o Negro/Gris oscuro según el resultado ganador.
   * Visualización del cilindro: Muestra la bola aterrizando entre los números vecinos del cilindro real:
     `... [ 15🟥 ] ➔ 👑 [ 32🟥 ] 👑 ➔ [ 19🟥 ] ...`
   * Resumen claro de apuesta, número ganador, color, paridad, docena y ganancia neta.
3. **Botones de Re-apuesta Rápida (`RouletteActionView`)**:
   * `[ 🔄 Repetir Apuesta ]` (`ButtonStyle.primary`): Permite volver a lanzar la misma apuesta con 1 clic si el usuario tiene saldo.
   * `[ 🪙 Doblar Apuesta ]` (`ButtonStyle.success`): Repite la apuesta pero multiplicando el importe $\times 2$.

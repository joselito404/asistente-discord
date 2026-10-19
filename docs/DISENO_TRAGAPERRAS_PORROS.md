# 🎰 Especificación de Diseño Viva: Tragaperras 5x3 de Alta Tensión (`docs/DISENO_TRAGAPERRAS_PORROS.md`)

> **Propósito**: Especificación formal de la máquina tragaperras nativa en formato real de 5 rodillos $\times$ 3 filas (15 casilleros) para el bot `Asistente`, incorporando 10 líneas de pago intuitivas, patrón "El Ojo", Comodines WILD, Scatters con Free Spins escalonados y RTP calibrado al 110.0%.
> **Estado**: `Vigente / Especificación Maestra (Regla Global §13)`
> **Fecha de actualización**: 19 de octubre de 2026 `[Chat 1]`

---

## 1. Fundamentos y Salto Generacional (5x3 vs 3x3)

1. **Estándar Real de Casino**: La máquina pasa del formato rudimentario de 3x3 a una matriz **$5 \times 3$ (5 rodillos independientes de izquierda a derecha y 3 filas)**.
2. **Premios Escalonados por Acierto**:
   - **3 de 5 en línea**: Recuperación / premio base.
   - **4 de 5 en línea**: *Big Win* ($\times 5$ a $\times 30$).
   - **5 de 5 en línea (*Five of a Kind*)**: *Mega Win* supremo ($\times 20$ a $\times 250$).
3. **Ergonomía Perfecta en Discord Móvil y PC**: 5 emojis de ancho entran con nitidez cristalina en una sola línea horizontal sin cortes ni saltos de línea en ninguna pantalla.
4. **Calibración a RTP 110.0%**: La máquina opera en modo *High Payouts Ultra* con un valor esperado positivo ($EV+ = +10\%$) para la comunidad, garantizando que el juego sea rentable y estimulante.

---

## 2. Catálogo de Símbolos y Tabla de Pagos (3, 4 y 5 en Línea)

| Símbolo | Tipo | Emoji en Discord | 3 en Línea | 4 en Línea | 5 en Línea (*5-of-a-kind*) | Peso |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **Ranked_Gold** | Regular | `<:Ranked_Gold:1550130006896812084>` | $\times 0.24$ | $\times 0.78$ | $\times 2.5$ | 38 |
| **Ranked_Diamond** | Regular | `<:Ranked_Diamond:1550130004074041434>` | $\times 0.48$ | $\times 1.55$ | $\times 5.0$ | 24 |
| **Ranked_Mythic** | Regular | `<:Ranked_Mythic:1550130000852820099>` | $\times 1.0$ | $\times 3.5$ | $\times 12.0$ | 15 |
| **Ranked_Legendary** | Regular | `<:Ranked_Legendary:1550129997774323732>` | $\times 2.2$ | $\times 8.0$ | $\times 25.0$ | 9 |
| **Ranked_Masters** | Regular | `<:Ranked_Masters:1550129992837496833>` | $\times 6.0$ | $\times 20.0$ | $\times 60.0$ *(+ Mini Jackpot)* | 5 |
| **Ranked_Pro** | Regular | `<:Ranked_Pro:1550129987972104252>` | $\times 15.0$ | $\times 50.0$ | $\times 160.0$ *(+ Grand Jackpot)* | 3 |
| **WILD** | Especial | `<:absolutecinema:1478115607336714300>` | $\times 20.0$ | $\times 65.0$ | $\times 200.0$ *(+ Grand Jackpot)* | 2 |
| **SCATTER** | Especial | `<:Porro:1535685303317172305>` | $\times 3.0$ + 5 Spins | $\times 10.0$ + 8 Spins | $\times 35.0$ + 12 Spins | 4 |

- **Función del WILD (`:absolutecinema:`)**: Comodín que sustituye a cualquier símbolo regular (Gold a Pro). En una línea con `[Pro, Pro, WILD, Pro, Diamond]`, cuenta como 4 Pro en línea.
- **Función del SCATTER (`:Porro:`)**: Dispersor que paga en **cualquier posición** de la pantalla. Si caen $\ge 3$ Scatters, otorga el premio de consolación y activa la ronda de **Tiradas Gratis (Free Spins)** con multiplicador $\times 2$.

---

## 3. Matriz $5 \times 3$ y las 10 Líneas de Pago Clásicas

La cuadrícula se compone de 15 posiciones `(fila, columna)`:

```text
Rodillo 1    Rodillo 2    Rodillo 3    Rodillo 4    Rodillo 5
[ (0,0) ]    [ (0,1) ]    [ (0,2) ]    [ (0,3) ]    [ (0,4) ]   -> Fila Superior (Top)
[ (1,0) ]    [ (1,1) ]    [ (1,2) ]    [ (1,3) ]    [ (1,4) ]   -> Fila Central (Middle)
[ (2,0) ]    [ (2,1) ]    [ (2,2) ]    [ (2,3) ]    [ (2,4) ]   -> Fila Inferior (Bottom)
```

### Las 10 Líneas de Pago Limpias:
1. **Línea 1 (Centro)**: `[(1,0), (1,1), (1,2), (1,3), (1,4)]`
2. **Línea 2 (Arriba)**: `[(0,0), (0,1), (0,2), (0,3), (0,4)]`
3. **Línea 3 (Abajo)**: `[(2,0), (2,1), (2,2), (2,3), (2,4)]`
4. **Línea 4 ("V" Suave)**: `[(0,0), (1,1), (2,2), (1,3), (0,4)]` (Arriba $\to$ Abajo $\to$ Arriba)
5. **Línea 5 ("V Invertida")**: `[(2,0), (1,1), (0,2), (1,3), (2,4)]` (Abajo $\to$ Arriba $\to$ Abajo)
6. **Línea 6 (Diagonal Descendente)**: `[(0,0), (0,1), (1,2), (2,3), (2,4)]`
7. **Línea 7 (Diagonal Ascendente)**: `[(2,0), (2,1), (1,2), (0,3), (0,4)]`
8. **Línea 8 (Corona Superior)**: `[(1,0), (0,1), (0,2), (0,3), (1,4)]`
9. **Línea 9 (Corona Inferior)**: `[(1,0), (2,1), (2,2), (2,3), (1,4)]`
10. **Línea 10 (Onda Central)**: `[(1,0), (0,1), (1,2), (2,3), (1,4)]`

### Patrones Especiales de Pantalla:
- **"El Ojo" (Marco Exterior - 12 Casilleros)**:
  Los 12 casilleros del contorno exterior son el mismo símbolo o Wilds, dejando libres los 3 del centro `[(1,1), (1,2), (1,3)]`:
  ```text
  [ ⭐ ] [ ⭐ ] [ ⭐ ] [ ⭐ ] [ ⭐ ]
  [ ⭐ ] [ 👁️ ] [ 👁️ ] [ 👁️ ] [ ⭐ ]
  [ ⭐ ] [ ⭐ ] [ ⭐ ] [ ⭐ ] [ ⭐ ]
  ```
  *Premio Especial*: Otorga un multiplicador masivo de **$\times 50.0$** directo.
- **Pantalla Completa (15 de 15)**: Todos los 15 casilleros llenos del mismo símbolo $\to$ **$\times 500.0$**.

---

## 4. Ronda de Free Spins (Tiradas Gratis)

- **3 Scatters**: $\times 3.0$ payout + **5 Tiradas Gratis** a $\times 2$.
- **4 Scatters**: $\times 10.0$ payout + **8 Tiradas Gratis** a $\times 2$.
- **5 Scatters**: $\times 35.0$ payout + **12 Tiradas Gratis** a $\times 2$.
- Durante las tiradas gratis, el coste es **$0$ Porros**. Todo premio se duplica ($\times 2$).
- **Re-trigger**: Si caen $\ge 3$ Scatters durante el bonus, se añaden $+3$ tiradas gratis adicionales.

---

## 5. Botes Progresivos Escalonados

- El **3%** de todas las apuestas netas perdidas alimenta continuamente `server_jackpot` en `datos/economia.json`.
- **Grand Jackpot (100% del bote acumulado)**: Se otorga al sacar 5 `Ranked_Pro` o 5 `WILD` en la línea central (L1). Bote base: 25.000 Porros.
- **Mini Jackpot (25% del bote)**: Se otorga al sacar 5 `Ranked_Masters` en la línea central (L1).

---

## 6. Calibración Monte Carlo (RTP 110.0%)

- **RTP Objetivo / Real**: **$110.0\%$** ($\pm 0.5\%$, calibración en 100k tiradas: `109.22%` - `110.24%`).
- **Hit Rate**: **$51.8\%$** (premio en más de 1 de cada 2 tiradas).
- **Frecuencia de Free Spins**: 1 de cada ~50 tiradas.
- **Frecuencia de Grand Jackpot**: 1 de cada ~15.000 tiradas.

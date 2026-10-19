# 🎰 Especificación de Diseño Viva: Tragaperras V2 de Alta Tensión (`docs/DISENO_TRAGAPERRAS_PORROS.md`)

> **Propósito**: Especificación formal de la máquina tragaperras nativa de alta fidelidad para el bot `Asistente`, superando el modelo plano de UnbelievaBoat mediante mecánicas reales de casino (9 líneas de pago, Comodines WILD, Scatters y Ronda de Free Spins).
> **Estado**: `Vigente / Especificación Maestra (Regla Global §13)`
> **Fecha de actualización**: 19 de octubre de 2026 `[Chat 1]`

---

## 1. Fundamentos y Veredicto Técnico

### ¿Por qué superar a UnbelievaBoat?
1. **Mecánicas Reales de Casino**: UnbelievaBoat se limitaba a 5 líneas básicas con aciertos estáticos y sin emoción. La Tragaperras V2 introduce comodines dinámicos (**WILD**), bonificaciones en cualquier posición (**SCATTER**) y una fase de juego adicional (**Free Spins / Tiradas Gratis**).
2. **Matemáticas Certificadas**: Calibración con simulador Monte Carlo para mantener un **RTP saludable del 94% - 96%** con un **Hit Rate superior (~42% - 45%)**, aumentando la frecuencia de premios y la retención del jugador sin desestabilizar la economía de Porros.
3. **Persistencia Atómica Multihilo**: Almacenamiento directo en `datos/economia.json` con `safe_write_json` y cerrojo `threading.RLock()`.
4. **Discord Components V2**: Contenedores interactivos (`type: 17`), divisores decorativos (`type: 14`) y botones persistentes para revancha inmediata y consulta de pagos.

---

## 2. Catálogo de Símbolos, Pesos y Multiplicadores

La tragaperras opera con 8 símbolos: 6 regulares (Brawl Stars Ranked), 1 Comodín (WILD) y 1 Dispersor de Bonificación (SCATTER):

| Símbolo | Tipo | Emoji en Servidor | Multiplicador Base (3 en Línea) | Función / Efecto Especial | Peso en Rodillo |
| :--- | :---: | :--- | :---: | :--- | :---: |
| **WILD** | Especial | `<:absolutecinema:1478115607336714300>` | **$\times 65.0$** | **Comodín Universal**: Sustituye a cualquier símbolo regular (Gold a Pro). 3 Wilds pagan el mayor multiplicador fijo y en L1 otorgan Grand Jackpot. | 2 |
| **SCATTER** | Especial | `<:Porro:1535685303317172305>` | **$\times 5.0$** | **Ronda de Bonus**: Paga en **cualquier posición** (no exige línea). Si caen **3 Scatters** en pantalla, otorga $\times 5$ de consolación y activa **5 Tiradas Gratis (Free Spins)** con multiplicador doble $\times 2$. | 4 |
| **Ranked_Pro** | Regular | `<:Ranked_Pro:1550129987972104252>` | **$\times 32.0$** | Premio Supremo Regular. Si coincide con 3 en línea central (L1), otorga el **Grand Jackpot** (100% del bote). | 3 |
| **Ranked_Masters** | Regular | `<:Ranked_Masters:1550129992837496833>` | **$\times 15.0$** | Premio Mítico. Si coincide en línea central (L1), otorga el **Mini Jackpot** (25% del bote). | 5 |
| **Ranked_Legendary** | Regular | `<:Ranked_Legendary:1550129997774323732>` | **$\times 5.8$** | Premio Épico. | 9 |
| **Ranked_Mythic** | Regular | `<:Ranked_Mythic:1550130000852820099>` | **$\times 3.0$** | Premio Raro. | 15 |
| **Ranked_Diamond** | Regular | `<:Ranked_Diamond:1550130004074041434>` | **$\times 1.68$** | Premio Poco Común. | 24 |
| **Ranked_Gold** | Regular | `<:Ranked_Gold:1550130006896812084>` | **$\times 0.86$** | Premio Base Común. | 38 |

- **Moneda de Apuesta**: `<:Porro:1535685303317172305>` (`PORRO_EMOJI`).

---

## 3. Matriz $3 \times 3$ y las 9 Líneas de Pago (Paylines)

La matriz se indexa como `(fila, columna)` de izquierda a derecha:

```text
Rodillo 1    Rodillo 2    Rodillo 3
[ (0,0) ]    [ (0,1) ]    [ (0,2) ]   -> Fila Superior (Top)
[ (1,0) ]    [ (1,1) ]    [ (1,2) ]   -> Fila Central (Middle)
[ (2,0) ]    [ (2,1) ]    [ (2,2) ]   -> Fila Inferior (Bottom)
```

Se evalúan simultáneamente **9 líneas de pago** reales de izquierda a derecha:

| ID Línea | Nombre de Línea | Coordenadas `(Fila, Columna)` | Patrón Visual |
| :---: | :--- | :--- | :---: |
| **L1** | Horizontal Centro | `[(1,0), (1,1), (1,2)]` | `― ― ―` |
| **L2** | Horizontal Arriba | `[(0,0), (0,1), (0,2)]` | `― ― ―` (Arriba) |
| **L3** | Horizontal Abajo | `[(2,0), (2,1), (2,2)]` | `― ― ―` (Abajo) |
| **L4** | Diagonal Descendente | `[(0,0), (1,1), (2,2)]` | `╲` |
| **L5** | Diagonal Ascendente | `[(2,0), (1,1), (0,2)]` | `╱` |
| **L6** | Zig-Zag en "V" | `[(0,0), (1,1), (0,2)]` | `╲ ╱` (Arriba - Centro - Arriba) |
| **L7** | Zig-Zag en "V Invertida" | `[(2,0), (1,1), (2,2)]` | `╱ ╲` (Abajo - Centro - Abajo) |
| **L8** | Onda Descendente | `[(0,0), (0,1), (1,2)]` | `― ― ╲` |
| **L9** | Onda Ascendente | `[(2,0), (2,1), (1,2)]` | `― ― ╱` |

### Reglas de Evaluación de Línea:
1. Una línea premia si los 3 rodillos contienen el mismo símbolo regular, o una combinación de ese símbolo con uno o más comodines **WILD**.
2. **Prioridad del Wild**: Si una línea contiene `[WILD, Gold, Gold]`, el Wild adopta el valor de `Gold`. Si una línea tiene `[WILD, Pro, WILD]`, los Wilds adoptan `Pro` (pagando $\times 50$). Tres Wilds juntos pagan su multiplicador supremo de $\times 100$.
3. **Multi-Línea Acumulativa**: Si se premian múltiples líneas en un mismo giro, los multiplicadores se suman:
   $$\text{Multiplicador Total} = \sum_{k \in \text{Líneas Ganadoras}} \text{Multiplicador}_k$$
   $$\text{Ganancia Base} = \lfloor \text{Apuesta} \times \text{Multiplicador Total} \rfloor$$

---

## 4. Mecánica Especial de Bonus: Free Spins (Tiradas Gratis)

1. **Activación**: Se evalúan todos los 9 casilleros de la pantalla. Si aparecen **3 Scatters** (`<:Porro:...>`) en cualquier posición (sin necesidad de alinearse en payline):
   - El jugador recibe inmediatamente un pago de consolación de $\times 5$ su apuesta.
   - Se activa la **Ronda de 5 Tiradas Gratis**.
2. **Dinámica de Free Spins**:
   - Se presenta una interfaz especial con contenedor dorado (`accent_color: #FFD700`).
   - Las 5 tiradas se ejecutan consecutivamente con un botón interactivo `[Girar Tirada Gratis (X restantes)]` o en secuencia automática con pausas dramáticas.
   - **Coste**: $0$ Porros deducidos de la cartera.
   - **Multiplicador Global**: Todas las ganancias obtenidas durante las Free Spins se multiplican por $\times 2$.
   - **Re-trigger**: Si durante las tiradas gratis vuelven a salir 3 Scatters, se añaden $+3$ tiradas gratis adicionales.
3. **Cierre de Bonus**: Al terminar, se muestra un resumen con el total de porros ganados en la sesión de tiradas gratis y se ingresa el premio íntegro al saldo del usuario.

---

## 5. Bote Progresivo Escalonado (Jackpots)

El sistema de economía gestiona un bote progresivo acumulativo en `datos/economia.json` (`server_jackpot`):
- **Alimentación**: El **3%** de todas las apuestas netas perdidas se inyecta directamente al bote.
- **Niveles de Jackpots**:
  - **Grand Jackpot (100% del bote acumulado)**: Se otorga al alinear 3 `Ranked_Pro` en la línea central (L1) o 3 `WILD` en la línea central. El bote se reinicia a su base de 25.000 Porros.
  - **Mini Jackpot (25% del bote acumulado)**: Se otorga al alinear 3 `Ranked_Masters` en la línea central (L1). El 25% del bote se descuenta y se entrega al ganador.

---

## 6. Calibración Matemática Monte Carlo (Modo High Payouts Ultra)

- **RTP Objetivo (Return to Player)**: **$110.0\%$** (margen $109.5\% - 110.5\%$, modo ultra generoso con ventaja matemática positiva EV+ de un +10% para los jugadores de la comunidad).
- **Hit Rate (Frecuencia de Acierto)**: $45.0\% - 48.0\%$ (alta frecuencia de premios gracias a las 9 líneas activas, comodines Wilds y rondas de bonus).
- **Frecuencia de Free Spins**: 1 de cada ~70 - 85 tiradas (evento de bonificación emocionante y recurrente).
- **Frecuencia de Grand Jackpot**: 1 de cada ~10.000 tiradas.

---

## 7. Interfaz Visual Discord (Components V2)

- **Normal Win**: Contenedor verde esmeralda (`#66B96A`), desglose de líneas ganadoras (`L1`, `L4`, etc.), payout y botones `[Volver a Girar]` y `[Tabla de Pagos]`.
- **Big Win ($\ge \times 20$)**: Contenedor dorado con animación y mensaje destacado.
- **Free Spins Trigger**: Contenedor violeta neón con aviso de bonus y botón para iniciar las tiradas gratis.
- **No Win**: Contenedor rojo suave (`#EF5350`) con los mismos botones para revancha.

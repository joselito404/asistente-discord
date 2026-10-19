# Especificación de Diseño: Centro de Control del Casino (`/casino`)

> **Ámbito**: Sistema de Casino y Experiencia de Usuario (`Economia Asistente`).  
> **Estado**: `[Aprobado · Jose · 19/10/2026]`  
> **Referencia de Arquitectura**: Regla Global §13 (Documentación Viva).  

---

## 1. Visión y Objetivos

Con la incorporación de Tragaperras 5x3, Blackjack 21, Ruleta Europea, Coinflip Dual y Peleas de Gallos, el servidor cuenta ahora con una suite completa de azar nativa que sustituye al 100% a UnbelievaBoat.

El comando **/casino** (o **/juegos**) opera como el **Hub Central e Interactivo** del casino, permitiendo a los miembros:
1. Consultar el estado en vivo del **Bote Progresivo Acumulado (`server_jackpot`)**.
2. Ver el catálogo completo de juegos activos con sus pagos, RTPs y probabilidades oficiales.
3. Navegar interactivamente mediante un menú desplegable (`discord.ui.Select`) para obtener guías rápidas, trucos y sintaxis de cada comando.

---

## 2. Catálogo Oficial de Juegos del Casino

| Juego | Comando | Tipo | Retorno / RTP | Descripción y Reglas Clave |
| :--- | :---: | :---: | :---: | :--- |
| **Tragaperras 5x3** | `/slots` | Solitario / Bote | **$110.03\%$ RTP** | Matriz 5x3, 7 líneas limpias, racha consecutiva de 3 a 5, Free Spins a $\times 2$, y Grand Jackpot con 3 Pro en L1. |
| **Blackjack 21** | `/blackjack` (`/bj`) | Cartas vs Casa | **$\approx 99.5\%$ RTP** | Zapato de 6 barajas, crupier plantado en 17, Blackjack natural $3:2$, botones Hit, Stand y Double Down. |
| **Ruleta Europea** | `/ruleta` | Mesa / Suertes | **$97.30\%$ RTP** | Cilindro oficial de 37 casillas ($0-36$). Suertes sencillas ($1:1$), docenas/columnas ($2:1$), y plenos directos ($35:1$). |
| **Coinflip Dual** | `/coinflip` | Duelo / Azar | **$50/50$ Justo** | Modo individual contra la casa ($1:1$) y duelos PvP 1v1 con aceptación de reto (98% ganador, 2% jackpot). |
| **Peleas de Gallos**| `/cockfight` | Combate / Lore | **$50\%$ / $65\%$ Dopado**| Crónicas de combate por asaltos. Ventaja $+15\%$ con `🍗 Pollo de Pelea Dopado` y riesgo de sobredosis del $10\%$. |

---

## 3. Componentes Interactivos (`CasinoHubView`)

* **Embed Principal**:
  * Título: `🎰 Casino Central Sanvi — Juegos y Apuestas Oficiales`
  * Indicador gigante del **Bote del Servidor**: `<:Porro:1535685303317172305> **{server_jackpot:,}** Porros en juego`.
  * Resumen de la cartera personal del usuario (`cash` y `bank`).
* **Menú Desplegable (`Select`)**:
  * Opciones: `🎰 Tragaperras 5x3`, `🃏 Blackjack 21`, `🎡 Ruleta Europea`, `🪙 Coinflip Dual`, `🍗 Peleas de Gallos`.
  * Al seleccionar un juego, la vista actualiza el embed mostrando:
    * Modo de juego y opciones.
    * Tabla de pagos y ventaja matemática.
    * Ejemplo visual de sintaxis y cómo apostar.

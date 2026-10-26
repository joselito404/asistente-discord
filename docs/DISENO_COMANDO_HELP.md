# Especificación de Diseño Canónico — Comando `/help` y Presencia de Bots

> **Estado:** Confirmado  
> **Fecha de Aprobación:** 26/10/2026 (`[Confirmada · Jose · 26/10/2026]`)  
> **Ámbito:** Interfaz de usuario en Discord, autoservicio de comandos, accesibilidad y presencia visual en lista de miembros.

---

## 1. Justificación y Propósito

El servidor de Discord cuenta con dos aplicaciones activas (`Asistente#6024` y `Economia Asistente#5317`) y más de 45 comandos slash interactivos.
Actualmente los usuarios no disponen de una guía centralizada dentro del servidor para descubrir comandos, sintaxis, ejemplos y límites de cada sistema.

El objetivo de esta especificación es:
1. **Proveer `/help` unificado:** Un comando interactivo, visual y libre de spam (`ephemeral=True`) con un menú desplegable (`Select`) dividido en 5 categorías funcionales que cubren la totalidad del ecosistema.
2. **Actualizar la presencia en lista de miembros:** Mostrar en la actividad de Discord la llamada a la acción `/help` junto a la función insignia de cada bot, alineándolo con el estándar de la comunidad (ej. Cakey Bot y Carl-bot).

---

## 2. Categorías y Mapeo de Comandos

El selector desplegable (`HelpSelect`) permite navegar entre las siguientes 5 categorías:

### 1. 🤖 IA Conversacional y Creatividad
* **`/chat` (o mención `@Asistente`):** Conversación fluida con Gemini 2.5 Flash / Flash Lite, lectura de Google Docs/Sheets, memoria persistente de usuario y búsqueda web en vivo.
* **`/dibuja [prompt]:`** Generación de imágenes en alta definición (1024x1024) a coste 0€ mediante clúster FLUX.1 con botón interactivo de re-roll.
* **`/musica [cancion]:`** Búsqueda y recomendación musical contextual con portadas y enlaces.
* **`/pregunta [duda]:`** Consulta rápida directa a la IA sin abrir hilo.
* **`/perfil [@usuario]:`** Ficha técnica de actividad, nivel, XP, memoria y afinidad con el servidor.
* **`/recuerda [dato]:`** Almacena un recuerdo o preferencia personal en la memoria a largo plazo del bot.
* **`/xp [@usuario]:`** Consulta detallada de progreso de nivel Cakey y cálculo cuadrático del tramo restante.

### 2. 🎙️ Voz Neuronal y Gemini Live
* **`/unete:`** Conecta a Asistente a tu canal de voz actual e inicia la sesión bidireccional interactiva de voz con Gemini Live Audio en tiempo real (baja latencia).
* **`/desconecta:`** Finaliza la sesión de voz y desconecta al bot limpiamente.
* **`/habla [texto] [voz]:`** Síntesis de voz neuronal Edge-TTS en el canal de voz actual.
* **`/cambiar_voz [voz]:`** Configura tu voz TTS preferida por defecto entre las disponibles.
* **`/para_audio:`** Detiene cualquier reproducción de audio o locución en curso de inmediato.
* **`/resumen_llamada [horas]:`** Genera un informe y crónica estructurada de los temas tratados en el canal de voz durante el periodo seleccionado.

### 3. 🏛️ Bolsa Sanvi y Finanzas
* **`/bolsa ver:`** Terminal interactiva bursátil con cotizaciones, libro de órdenes, capitalización y selector de velas dinámicas por timeframe (15m, 1h, 4h, 1D).
* **`/bolsa ticker [TICKER]:`** Ficha técnica detallada de una empresa o usuario cotizante (RSI, medias, Book Value y dividendos).
* **`/cartera:`** Consulta tus acciones en propiedad, precio medio de compra, ganancias no realizadas y tramo de sinergia activo.
* **`/aura [@usuario]:`** Análisis del Baremo de Aura, Book Value y desglose de Earnings 30d que determinan el precio fundamental.
* **`/trabajar:`** Turno laboral con remuneración en Porros (`¢`), multiplicado por tu rol de nivel Cakey y con hasta +25% de sinergia si posees cartera bursátil.
* **`/salario:`** Reclama el dividendo básico diario del servidor (con decaimiento del 5% si no se cobra).
* **`/balance [@usuario]:`** Consulta tu saldo disponible en mano, en el banco y patrimonio neto.

### 4. 🎲 Casino y Minijuegos
* **`/slots [apuesta]:`** Tragaperras 5x3 exclusiva Sanvi con 9 líneas de pago reales, símbolos de Brawl Stars Ranked, comodines WILD y bote progresivo.
* **`/blackjack [apuesta] (o /bj):`** Mesa de Blackjack 21 contra el crupier con reglas de casino, seguro, split y Double Down interactivo.
* **`/ruleta [apuesta] [tipo]:`** Ruleta Europea de 37 casillas con suertes sencillas, plenos (35:1), docenas y smart argument swap.
* **`/coinflip [apuesta] [@rival]:`** Cara o cruz 50/50 contra la casa o duelo 1v1 PvP con fianza retenida.
* **`/casino:`** Hub central interactivo con catálogo de juegos, telemetría del Jackpot del servidor y probabilidades oficiales.
* **`/crimen:`** Actividad ilegal de alto riesgo: gran recompensa o arresto con multa económica.
* **`/robar [@victima]:`** Intento de hurto sobre el saldo en mano de otro usuario (bloqueado si posee escudo activo).
* **`/tienda:`** Catálogo de compras de la comunidad (roles cosméticos, pases de doble XP y consumibles Monster Blanco).
* **`/inventario:`** Gestión de objetos en posesión, activación de buffs temporales y regalos entre miembros.
* **`/trivial [categoria]:`** Preguntas de conocimiento interactivo con botones y ranking comunitario.
* **`/tres_en_raya / /conecta4 / /ajedrez:`** Duelos clásicos por turnos con tablero visual contra la IA o amigos.
* **`/steam [juego] / /tribunal [juego]:`** Búsqueda de videojuegos y juicios satíricos de El Tribunal Gaming.
* **`/juicio [@acusado] [motivo]:`** Inicia un juicio comunitario con jurado popular y rol temporal de Skill Issue.

### 5. 💡 Comunidad y Servidor
* **`/sugerencia:`** Envía una propuesta formal para el servidor mediante un modal estructurado con hilo de debate automático y veredicto satírico por IA.
* **`/panel_sugerencias:`** Panel administrativo para evaluar, aprobar o descartar sugerencias comunitarias.
* **`/autoroles:`** Menú interactivo para auto-asignarse o retirarse roles temáticos de notificación, juegos y canales privados.
* **`/ranking:`** Tabla de líderes de riqueza, nivel, actividad y patrimonio del servidor.

---

## 3. Presencia en Discord (Activities)

Actualización de los estados de presencia de ambos bots en `bot_service.py`:
* **`Asistente#6024`:**
  * Tipo: `discord.ActivityType.listening`
  * Nombre: `"/help | Gemini Live (/unete)"`
* **`Economia Asistente#5317`:**
  * Tipo: `discord.ActivityType.watching`
  * Nombre: `"/help | Casino & Bolsa (/bolsa)"`

---

## 4. Registro de Decisiones y Estado Canónico

- [x] `[Confirmada · Jose · 26/10/2026]` Aprobación de la creación del comando interactivo `/help` con selector de categorías y actualización de los estados de presencia.
- [x] `[Confirmada · Jose · 26/10/2026]` Implementación efímera (`ephemeral=True`) para evitar saturación de canales públicos.
- [x] `[Confirmada · Jose · 26/10/2026]` Cobertura integral de los más de 45 comandos slash de ambos bots en una sola interfaz guiada.

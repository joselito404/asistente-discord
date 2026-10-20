# Paquete `modulos/` — Arquitectura Modular del Bot Asistente

Esta carpeta contiene los submódulos funcionales extraídos de `bot_service.py` para mantener el núcleo del bot limpio, legible y mantenible, respetando la regla de no añadir ficheros `.py` sueltos en la raíz del repositorio (`.agents/chats/reglas.md` §6).

## ¿Quién puede escribir aquí?
Cualquier agente o desarrollador autorizado que trabaje en nuevas funcionalidades o mantenimiento del bot `Asistente`. Todo símbolo público añadido aquí debe reexportarse en `bot_service.py` si es consumido por comandos, eventos o suites de tests en `herramientas/test_*.py`.

## Estructura y Responsabilidades de cada Módulo

1. **`__init__.py`**: Inicializador del paquete `modulos`.
2. **`graficos.py`**: Renderizado gráfico y multimodal a coste 0€:
   - Generación de imágenes con **FLUX.1** (`generate_image_flux`, `enhance_image_prompt`, `ImageActionView` con botón `[🔄 Re-roll]`).
   - Fórmulas matemáticas LaTeX (`render_math_image`, `sanitize_discord_math_text`, `replace_frac`, `_parse_latex_braces`).
   - Gráficos estadísticos con Matplotlib (`render_chart_image`).
   - Diagramas de flujo y arquitectura con Graphviz (`render_diagram_image`).
   - Tarjetas de código con resaltado sintáctico Pygments (`render_code_card_image`).
   - Extracción robusta de bloques JSON de acción (`extract_action_block`).
3. **`autoroles.py`**: Reemplazo nativo de Carl-bot:
   - Catálogo completo de 25 auto-roles en 5 categorías (`AUTOROLES_CATALOG`, `AUTOROLE_INFO_BY_ID`, `ALL_AUTOROLE_IDS`).
   - Vistas persistentes (`AutoRolesPersistentView`, `AutoRoleCategoryView`, `PersonalAutoRolesView`) y cálculo de cambios (`compute_autorole_toggle`, `compute_autorole_category_sync`).
   - Sistema interactivo de sugerencias comunitarias con votos persistentes (`SuggestionPersistentView`, `SuggestionDecisionModal`, `SUGGESTION_VOTES_STATE`).
4. **`juegos.py`**: Ecosistema de minijuegos, entretenimiento y El Tribunal Gaming:
   - Consultas en tiempo real a Steam Store y veredictos de El Tribunal Gaming (`fetch_steam_game`, `get_tribunal_query_ctx`, `get_steam_query_ctx`, `SteamView`, `TribunalView`).
   - Trivial interactivo (banco local de 110+ preguntas + generador infinito con Gemini IA: `TriviaView`, `handle_next_trivia`, `generate_gemini_trivia_question`).
   - Tres en Raya con IA Minimax (`TicTacToeView`, `get_tictactoe_bot_move`, `check_ttt_winner_and_line`).
   - Conecta 4 con heurística táctica (`Connect4View`, `get_connect4_bot_move`, `check_connect4_winner`).
   - Ajedrez vs Asistente con motor Stockfish y tableros visuales (`ChessGame`, `ChessView`, `chess_bot_move`, `chess_try_typed_move`).
5. **`voz.py`**: Voz en tiempo real, TTS y grabaciones 24h:
   - Parche de protocolo **DAVE E2EE** (`apply_dave_patch`) para compatibilidad con llamadas de Discord.
   - Síntesis de voz neuronal Edge-TTS (`generate_speech_audio`, `clean_text_for_tts`, `TTS_VOICES`).
   - Gestión de estado de desconexión manual/interna (`VOICE_MANUALLY_DISCONNECTED`, `set_voice_manually_disconnected`, `mark_internal_voice_disconnect`).
   - Receptor de audio bidireccional en vivo con **Gemini Live 2.5 Native Audio** (`GeminiLiveVoiceSink`, `ensure_voice_connection`, `play_audio_in_voice`) y retención de grabaciones 24h (`RECORDINGS_DIR`, `load_recordings_metadata`).
6. **`web_server.py`**: Servidor HTTP de diagnóstico y portal de grabaciones (puerto 10000 en Render):
   - Health-check `HTTP 200 OK` (`/`), estado JSON (`/status`), visor de logs en vivo (`/logs`) y portal/API de grabaciones de voz de las últimas 24h (`/audios`, `/audios/zip`, `/api/audios`).
7. **`chat_ia.py`**: Motor conversacional y orquestador LLM de Gemini:
   - System Prompt con lore del servidor, Circuit Breaker inteligente de modelos (`MODELS_PRIORITY`, `mark_model_cooldown`), cliente multi-turno (`call_gemini_multiturn`).
   - Monitor de niveles reales de Cakey Bot (`get_live_levels_dict`), cálculo cuadrático de XP (`calculate_xp_gap`), memoria de usuarios (`user_memory`).
   - Catálogo canónico de 124 emojis del servidor (`SERVER_EMOJIS_DATA`), auto-conversor pre-envío regex (`format_server_emojis`) y arquitectura resiliente ante expiración de Server Boost con fallbacks limpios (`DISABLED_EMOJI_FALLBACK`).
   - Búsqueda web contextual en vivo (`search_web_lite`), radar de voz, censos y enrutador principal de mensajes (`_handle_message_safe`).
8. **`comandos.py`**: Registro unificado de Comandos Slash nativos en Arquitectura Dual Runner:
   - Declaración de los 41 comandos interactivos (`@app_commands.command`) organizados por dominios de bots:
     * `GENERAL_SLASH_COMMANDS` (22 comandos para el bot `Asistente`): `/dibuja`, `/musica`, `/steam`, `/tribunal`, `/perfil`, `/pregunta`, `/voz`, `/recuerda`, `/xp`, `/habla`, `/geminilive`, `/cambiar_voz`, `/unete`, `/desconecta`, `/para_audio`, `/trivial`, `/ranking_trivial`, `/tres_en_raya`, `/conecta4`, `/ajedrez`, `/autoroles`, `/sugerencia`.
     * `ECONOMY_SLASH_COMMANDS` (19 comandos para el bot `Economia Asistente`): `/slots`, `/balance`, `/trabajar`, `/transferir`, `/depositar`, `/retirar`, `/robar`, `/tienda`, `/salario`, `/blackjack`, `/bj`, `/ruleta`, `/coinflip`, `/casino`, `/crimen`, `/ranking`, `/inventario`, `/usar`, `/admin_dinero`.
     * `ALL_SLASH_COMMANDS`: unión de las dos listas (41 comandos) garantizando retrocompatibilidad total.
   - Funciones modulares de registro:
     * `register_general_commands(tree)`: vincula los 22 comandos generales al árbol de `Asistente`.
     * `register_economy_commands(tree)`: vincula los 19 comandos de economía al árbol de `Economia Asistente`.
     * `register_slash_commands(tree)`: registra ambos árboles si se invoca para compatibilidad retrospectiva.
9. **`economia.py`**: Motor nativo de economía comunitaria, banca, robos, delitos, tienda, inventario, salarios, rankings, administración y casino:
   - Moneda oficial: Porros (`PORRO_EMOJI` `<:Porro:1535685303317172305>`).
   - Persistencia segura y atómica en `datos/economia.json` con bloqueo `ECONOMY_LOCK` (`RLock`) y escritura temporal `safe_write_json`.
   - Gestión de saldos: `get_balance`, `modify_balance`, `transfer_funds`.
   - Módulo de Banca (`/depositar`, `/retirar`): gestión segura de efectivo y banco con soporte de montos numéricos y opción `'all'`/`'todo'`.
   - Multiplicadores por Rol de Nivel (`get_level_role_multiplier`): evalúa roles del servidor (Nivel 10 `+10%`, Nivel 30 `+20%`, Nivel 50 `+25%`, Nivel 70 `+30%`, Nivel 80+ `+40%`) aplicables a `/trabajar` y `/crimen`.
   - Jornada laboral (`/trabajar`): historias cómicas del lore del servidor (`WORK_MESSAGES`), retribución base de 1.000 a 2.500 Porros ($\times$ bono de rol de nivel) y cooldown de 4 horas.
   - Delitos de Alto Riesgo (`/crimen`): 50% de éxito (1.800 a 3.500 Porros base $\times$ bono de rol de nivel) y 50% de fallo con multa del 10% del efectivo (mínimo 500 Porros, sin saldo negativo y aportando el 3% al `server_jackpot`), con cooldown de 12 horas.
   - Sistema de Robo (`/robar`): probabilidad de éxito 50%, hurto de 20-50% de efectivo, chequeo estricto de inmunidad contra `🛡️ Cartera Blindada` (falla 100% y multa 15%) y cooldown anti-spam.
   - Catálogo Oficial de Tienda V2 (`/tienda`), Inventario (`/inventario`) y Uso de Consumibles (`/usar`):
     * 9 artículos oficiales: roles permanentes auto-asignables al comprar (`🛡️ Cartera Blindada`, `🚬 Camello del Barrio`, `🎰 Ludópata Rehabilitado`, `👑 Aura de XP Permanente`), coleccionable (`🚬 Porro de Oro`), consumible (`🥤 Monster Blanco`, 25.000 Porros, resetea cooldowns de `/trabajar`, `/crimen` y `/robar`) y pases temporales de XP (`⚡ Chute de XP (24h)`, `🔥 Pase Semanal de XP`, `💠 Pase Mensual de XP`) que se almacenan en el inventario al comprarse y se activan/extienden bajo demanda con `/usar`.
     * Consulta de inventario (`/inventario`): vista efímera con desglose de artículos, roles y tiempo restante de `active_buffs`, e incluye botón `[📢 Mostrar en público]` (`InventoryView`).
     * Expiración automática (`check_and_expire_buffs`): auditado periódicamente por `_xp_passes_expiration_watcher()` en `bot_service.py` para retirar automáticamente de Discord los roles temporales vencidos.
   - Clasificación de Riqueza (`/ranking`): tabla de líderes pública (`RankingView` y `RankingCategorySelect`) para alternar en vivo entre `💎 Patrimonio Total`, `💵 Efectivo (Cash)` y `🏦 Banco (Bank)`, mostrando el Top 10 y la posición del solicitante.
   - Panel de Administración Financiera (`/admin_dinero`): exclusivo para Administradores (`admin_modify_money`, `admin_airdrop_role`) con acciones `dar`, `quitar`, `fijar` y `airdrop` masivo por rol.
   - Salario Acumulativo (`/salario` / `/cobrar`): cálculo continuo por roles de nivel (Nivel 10 a 100) y podio (Top 1, 2, 3) con fórmula de decaimiento del 5% diario ($P = S \times \frac{1 - (1 - d)^n}{d}$, tope asintótico $20 \times S$).
   - Centro de Control del Casino (`/casino`):
     * Hub Central interactivo (`CasinoHubView`) con timeout de 90s y control estricto de autoría (bloqueo efímero a terceros).
     * Embed Principal con Bote Acumulado del servidor (`server_jackpot`) visible en grande, resumen de cartera del usuario (`cash`, `bank`, `total`) y catálogo rápido de juegos.
     * Menú desplegable interactivo (`CasinoHubSelect`) con los 4 juegos oficiales (`🎰 Tragaperras 5x3`, `🃏 Blackjack 21`, `🎡 Ruleta Europea`, `🪙 Coinflip Dual`) que actualiza la vista con el desglose de reglas, pagos, comandos de ejemplo y RTP calibrado.
     * Botón `[ 🏠 Menú Principal ]` (`ButtonStyle.secondary`) para regresar instantáneamente a la vista general.
   - Máquina tragaperras 5x3 de Alta Tensión (`/slots`):
     * Matriz 5 rodillos $\times$ 3 filas (15 casilleros) y 8 símbolos: 6 Brawl Stars Ranked, Comodín WILD (`<:absolutecinema:...>`) y Dispersor SCATTER (`<:Porro:...>`).
     * 7 Líneas de Pago Limpias evaluadas de izquierda a derecha para 3, 4 y 5 aciertos (`SLOT_PAYLINES`).
     * Patrón Especial "Pantalla Completa" (15 casillas a $\times 500.0$).
     * Ronda de Free Spins escalonada (3/4/5 Scatters $\to$ 5/8/12 giros a $\times 2$ con re-triggers $+3$).
     * Bote Progresivo Escalonado: Grand Jackpot (100% bote con 5 Pro o 5 Wild en L1 central) y Mini Jackpot (25% bote con 5 Masters en L1).
     * Calibración Monte Carlo a RTP 110.0% ($\pm 0.5\%$, Hit Rate ~73.83%, modo High Payouts EV+ ordenado por Jose).
     * Interfaz nativa con **Discord Components V2** (`SlotsLayoutView`): contenedores tipo 17 con `accent_color`, separadores tipo 14, textos tipo 10 y botones `[Play Again]`, `[🌀 Jugar Tiradas Gratis]` y `[Payouts]` en fila de acciones tipo 1.
   - Minijuego de Casino: **Blackjack 21 Nativo** (`/blackjack`, `/bj`):
     * Zapato estándar de casino de 6 barajas (312 cartas) con palos (♠️, ♥️, ♦️, ♣️) y rangos (A, 2-10, J, Q, K), con rebarajado automático al bajar de 52 cartas (`BlackjackEngine`).
     * Evaluación dinámica de Ases flexibles (11 o 1) para manos blandas y duras (`is_soft`, `is_bust`) y detección de Blackjack natural inicial de 2 cartas (`is_blackjack`).
     * Reglas del Crupier: S17 (*Dealer stands on all 17s*, pide carta obligatoriamente con $\le 16$).
     * Interfaz nativa interactiva (`BlackjackView` con timeout de 60s y auto-stand):
       - `[ 🃏 Pedir ]` (`ButtonStyle.primary`): roba carta con chequeo de bust y auto-stand en 21.
       - `[ 🛑 Plantarse ]` (`ButtonStyle.danger`): pasa turno al crupier y resuelve resultado.
       - `[ ⚡ Doblar ]` (`ButtonStyle.success`): duplica la apuesta (con 2 cartas y fondos suficientes), da exactamente 1 carta más y resuelve inmediatamente al crupier.
       - Control de concurrencia: 1 partida simultánea por usuario (`ACTIVE_BLACKJACK_GAMES`).
       - Control de permisos: interacción efímera de bloqueo para terceros.
     * Liquidación financiera: Blackjack natural paga 3:2 (ganancia neta 1.5x, retorno 2.5x), victoria regular paga 1:1 (ganancia neta 1.0x, retorno 2.0x), empate push (devolución 100% de la apuesta), y pérdidas netas aportan el 3% al `server_jackpot` del servidor.
   - Minijuego de Casino: **Ruleta Europea 37 Casillas** (`/ruleta`):
     * Cilindro europeo de 37 casillas (0 a 36) con secuencia circular oficial: `[0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]` (`RouletteEngine`).
     * Distribución matemática oficial: 18 rojos (`ROULETTE_RED`), 18 negros (`ROULETTE_BLACK`) y 1 verde (`0`).
     * Catálogo completo de 13 opciones de apuesta (suertes sencillas 1:1, docenas 2:1, columnas 2:1 y pleno 35:1).
     * Regla canónica del 0 verde con RTP teórico del 97.30%.
     * Interfaz interactiva (`RouletteActionView` con timeout 60s): botones `[ 🔄 Repetir Apuesta ]` y `[ 🪙 Duplicar Apuesta ]`.
     * Alimentación del 3% de pérdidas netas al bote progresivo `server_jackpot`.
   - Minijuego de Casino y Duelos: **Coinflip Dual (PvP y PvE)** (`/coinflip`):
     * **Modo PvE (Contra la Casa)**: lanzamiento individual 50/50 justo (`random.choice(["cara", "cruz"])`) con cobro 1:1 en caso de acierto (retorno 2x la apuesta) y alimentación del 3% de la pérdida neta al `server_jackpot` en caso de fallo. Re-apuesta instantánea con `CoinflipActionView` (`[ 🔄 Tirar Otra Vez ]`) con timeout de 60s y verificación de saldo.
     * **Modo PvP (Duelo entre Miembros)**:
       - Retención atómica de la fianza del retador bajo `ECONOMY_LOCK` y registro en `ACTIVE_COINFLIP_DUELS` para prevenir dobles desafíos y exploits concurrentes.
       - Despliegue interactivo con `CoinflipChallengeView`:
         * `[ ⚔️ Aceptar Desafío ]` (`ButtonStyle.success`): exclusivo para el rival desafiado. Comprueba atómicamente saldo suficiente; si no dispone de fondos, cancela el duelo y reembolsa la fianza al retador.
         * `[ 🏳️ Rechazar ]` (`ButtonStyle.danger`): accionable por el rival o por el retador para cancelar.
         * Timeout de seguridad a 60 segundos con cancelación automática y reembolso del 100% al retador.
       - Reparto determinista de fondos al resolver: 2% del bote total ($2 \times \text{apuesta}$) destinado al `server_jackpot` de la comunidad, y el 98% restante abonado al vencedor de forma instantánea.

## Cómo se usa e integra con `bot_service.py`
- `bot_service.py` actúa como punto de entrada único (`python bot_service.py`) y orquestador central bajo una **Arquitectura de Runner Dual**:
  * Ejecuta concurrentemente en el mismo proceso y contenedor de Render los dos clientes de Discord (`bot` para `Asistente` y `economy_bot` para `Economia Asistente`) utilizando un supervisor asíncrono `asyncio.gather(*tasks)` envuelto en un bucle persistente `while True`.
  * Sincroniza de forma independiente el árbol general `tree` (22 comandos) y el árbol de economía `economy_tree` (19 comandos) con el servidor `1446143936891715616`.
  * Ejecuta en segundo plano `_xp_passes_expiration_watcher()` para auditar cada 30 minutos los pases temporales de XP (`active_buffs`) y retirar automáticamente los roles vencidos en Discord.
  * Maneja las presencias personalizadas de cada bot (`listening: Gemini Live en voz (/unete)` para Asistente y `watching: Casino y Porros (/slots)` para Economia Asistente).
  * Encamina eventos de componentes interactivos (`slots:`, `bj:`, `roulette:`, `coinflip:`, `casino:`) hacia sus respectivas vistas.
  * Registra `sys.modules.setdefault("bot_service", sys.modules[__name__])` y reexporta todas las funciones, clases y constantes de `modulos.*`.
- Para permitir que los tests unitarios (`herramientas/test_*.py`) hagan monkeypatching sobre atributos de `bot_service` (como `bot_service.mark_model_cooldown` o `bot_service.ensure_voice_connection`), los submódulos acceden dinámicamente a la instancia de `bot_service` mediante el helper interno `_bs()`.

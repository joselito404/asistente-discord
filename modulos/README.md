# Paquete `modulos/` â Arquitectura Modular del Bot Asistente

Esta carpeta contiene los submÃ³dulos funcionales extraÃ­dos de `bot_service.py` para mantener el nÃºcleo del bot limpio, legible y mantenible, respetando la regla de no aÃ±adir ficheros `.py` sueltos en la raÃ­z del repositorio (`.agents/chats/reglas.md` Â§6).

## Â¿QuiÃ©n puede escribir aquÃ­?
Cualquier agente o desarrollador autorizado que trabaje en nuevas funcionalidades o mantenimiento del bot `Asistente`. Todo sÃ­mbolo pÃºblico aÃ±adido aquÃ­ debe reexportarse en `bot_service.py` si es consumido por comandos, eventos o suites de tests en `herramientas/test_*.py`.

## Estructura y Responsabilidades de cada MÃ³dulo

1. **`__init__.py`**: Inicializador del paquete `modulos`.
2. **`graficos.py`**: Renderizado grÃ¡fico y multimodal a coste 0â¬:
   - GeneraciÃ³n de imÃ¡genes con **FLUX.1** (`generate_image_flux`, `enhance_image_prompt`, `ImageActionView` con botÃ³n `[ð Re-roll]`).
   - FÃ³rmulas matemÃ¡ticas LaTeX (`render_math_image`, `sanitize_discord_math_text`, `replace_frac`, `_parse_latex_braces`).
   - GrÃ¡ficos estadÃ­sticos con Matplotlib (`render_chart_image`).
   - Diagramas de flujo y arquitectura con Graphviz (`render_diagram_image`).
   - Tarjetas de cÃ³digo con resaltado sintÃ¡ctico Pygments (`render_code_card_image`).
   - ExtracciÃ³n robusta de bloques JSON de acciÃ³n (`extract_action_block`).
3. **`autoroles.py`**: Reemplazo nativo de Carl-bot para roles automÃ¡ticos:
   - CatÃ¡logo completo de 25 auto-roles en 5 categorÃ­as (`AUTOROLES_CATALOG`, `AUTOROLE_INFO_BY_ID`, `ALL_AUTOROLE_IDS`).
   - Vistas persistentes (`AutoRolesPersistentView`, `AutoRoleCategoryView`, `PersonalAutoRolesView`) y cÃ¡lculo de cambios (`compute_autorole_toggle`, `compute_autorole_category_sync`).
   - ReexportaciÃ³n retrocompatible del subsistema de sugerencias desde `modulos.sugerencias`.
4. **`sugerencias.py`**: Sistema de Sugerencias Comunitarias 2.0 (Reemplazo Integral de Carl-bot en `#ð¡sugerenciasð¡`, especificaciÃ³n [`docs/DISENO_SUGERENCIAS_2.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/DISENO_SUGERENCIAS_2.md)):
   - Modales estructurados Discord V2 (`SuggestionSubmitModal` para enviar tÃ­tulo, categorÃ­a y explicaciÃ³n detallada; `SuggestionDecisionModal` para resoluciÃ³n administrativa).
   - Tarjetas vivas con barra de progreso emoji dinÃ¡mica (`format_progress_bar`, `build_suggestion_embed`: 10 bloques `ð©`/`ð¥`, porcentajes y colores segÃºn estado: azul `0x3B82F6` para votaciÃ³n, verde `0x22C55E` para aprobadas y rojo `0xEF4444` para descartadas).
   - Apertura automÃ¡tica de hilos de debate dedicados (`ð¡ Sugerencia #X - Titulo`) en cada mensaje publicado con bienvenida para concentrar la discusiÃ³n comunitaria.
   - Veredictos satÃ­ricos, honestos y Ã¡cidos con IA Gemini (`get_or_generate_ai_verdict`) con cacheo persistente en disco para evitar consumo duplicado de tokens.
   - Vistas interactivas persistentes 24/7 (`SuggestionActiveView`, `SuggestionClosedView`, `SuggestionHubView`, `publish_suggestions_hub`).
   - Persistencia atÃ³mica y segura en `datos/sugerencias.json` bajo cerrojo asÃ­ncrono `SUGGESTIONS_LOCK` (arranque correlativo en ID 9).
5. **`juegos.py`**: Ecosistema de minijuegos, entretenimiento y El Tribunal Gaming:
   - Consultas en tiempo real a Steam Store y veredictos de El Tribunal Gaming (`fetch_steam_game`, `get_tribunal_query_ctx`, `get_steam_query_ctx`, `SteamView`, `TribunalView`).
   - Trivial interactivo (banco local de 110+ preguntas + generador infinito con Gemini IA: `TriviaView`, `handle_next_trivia`, `generate_gemini_trivia_question`).
   - Tres en Raya con IA Minimax (`TicTacToeView`, `get_tictactoe_bot_move`, `check_ttt_winner_and_line`).
   - Conecta 4 con heurÃ­stica tÃ¡ctica (`Connect4View`, `get_connect4_bot_move`, `check_connect4_winner`).
   - Ajedrez vs Asistente con motor Stockfish y tableros visuales (`ChessGame`, `ChessView`, `chess_bot_move`, `chess_try_typed_move`).
6. **`voz.py`**: Voz en tiempo real, TTS y grabaciones 24h:
   - Parche de protocolo **DAVE E2EE** (`apply_dave_patch`) para compatibilidad con llamadas de Discord.
   - SÃ­ntesis de voz neuronal Edge-TTS (`generate_speech_audio`, `clean_text_for_tts`, `TTS_VOICES`).
   - GestiÃ³n de estado de desconexiÃ³n manual/interna (`VOICE_MANUALLY_DISCONNECTED`, `set_voice_manually_disconnected`, `mark_internal_voice_disconnect`).
   - Receptor de audio bidireccional en vivo con **Gemini Live 2.5 Native Audio** (`GeminiLiveVoiceSink`, `ensure_voice_connection`, `play_audio_in_voice`) y retenciÃ³n de grabaciones 24h (`RECORDINGS_DIR`, `load_recordings_metadata`).
7. **`web_server.py`**: Servidor HTTP de diagnÃ³stico y portal de grabaciones (puerto 10000 en Render):
   - Health-check `HTTP 200 OK` (`/`), estado JSON (`/status`), visor de logs en vivo (`/logs`) y portal/API de grabaciones de voz de las Ãºltimas 24h (`/audios`, `/audios/zip`, `/api/audios`).
8. **`chat_ia.py`**: Motor conversacional y orquestador LLM de Gemini:
   - System Prompt con lore del servidor, Circuit Breaker inteligente de modelos (`MODELS_PRIORITY`, `mark_model_cooldown`), cliente multi-turno (`call_gemini_multiturn`).
   - Monitor de niveles reales de Cakey Bot (`get_live_levels_dict`), cÃ¡lculo cuadrÃ¡tico de XP (`calculate_xp_gap`), memoria de usuarios (`user_memory`).
   - CatÃ¡logo canÃ³nico de 124 emojis del servidor (`SERVER_EMOJIS_DATA`), auto-conversor pre-envÃ­o regex (`format_server_emojis`) y arquitectura resiliente ante expiraciÃ³n de Server Boost con fallbacks limpios (`DISABLED_EMOJI_FALLBACK`).
   - BÃºsqueda web contextual en vivo (`search_web_lite`), radar de voz, censos y enrutador principal de mensajes (`_handle_message_safe`).
9. **`comandos.py` (Fachada)** y sus submÃ³dulos especializados:
   - **`comandos_generales.py`**: Comandos Slash del bot `Asistente` (23 comandos generales: `/dibuja`, `/musica`, `/steam`, `/tribunal`, `/perfil`, `/pregunta`, `/voz`, `/recuerda`, `/xp`, `/habla`, `/geminilive`, `/cambiar_voz`, `/unete`, `/desconecta`, `/para_audio`, `/trivial`, `/ranking_trivial`, `/tres_en_raya`, `/conecta4`, `/ajedrez`, `/autoroles`, `/sugerencia`, `/panel_sugerencias`), lista `GENERAL_SLASH_COMMANDS` y registro modular `register_general_commands(tree)`.
   - **`comandos_economia.py`**: Comandos Slash del bot `Economia Asistente` (25 comandos de economÃ­a, casino y administraciÃ³n bursÃ¡til: `/slots`, `/balance`, `/trabajar`, `/transferir`, `/depositar`, `/retirar`, `/robar`, `/tienda`, `/salario`, `/blackjack`, `/bj`, `/ruleta`, `/coinflip`, `/casino`, `/crimen`, `/ranking`, `/inventario`, `/usar`, `/regalar`, `/admin_dinero`, `/admin_bolsa`, `/admin_economia`, `/bolsa`, `/cartera`, `/aura`), restricciÃ³n estricta de canales (`ensure_economy_channel`), lista `ECONOMY_SLASH_COMMANDS` y registro modular `register_economy_commands(tree)`.
   - **`comandos.py`**: Fachada ligera de reexportaciÃ³n 100% retrocompatible que agrupa `ALL_SLASH_COMMANDS` (48 comandos en total), expone `register_slash_commands(tree)` y propaga mutaciones dinÃ¡micas a travÃ©s de `_FachadaComandos`.
10. **`economia.py` (Fachada)** y sus 4 submÃ³dulos atÃ³micos:
   - **`economia_core.py`**: Motor central de persistencia atÃ³mica (`datos/economia.json`) bajo `ECONOMY_LOCK` (`RLock`), gestiÃ³n de saldos (`get_balance`, `modify_balance`), paro de emergencia transaccional (`is_economy_halted`, `set_economy_halt`), bote global del servidor (`get_server_jackpot`, `modify_server_jackpot`), banca (`deposit_cash`, `withdraw_cash`), transferencias (`transfer_funds`), multiplicadores por rol de nivel (`LEVEL_ROLE_MULTIPLIERS`, `get_level_role_multiplier`), trabajo (`can_work`, `execute_work`), delitos (`can_crime`, `execute_crime`), robos e inmunidad (`user_has_shield`, `can_rob`, `execute_rob`), salario progresivo con decaimiento del 5% (`calculate_daily_salary`, `claim_salary`), tabla de lÃ­deres (`get_economy_leaderboard`, `build_ranking_embed`, `RankingView`) y panel financiero de administraciÃ³n (`admin_modify_money`, `admin_airdrop_role`).
   - **`economia_tienda.py`**: CatÃ¡logo oficial de artÃ­culos `SHOP_ITEMS` (roles permanentes, pases temporales XP y consumibles como `ð¥¤ Monster Blanco`), compra interactiva (`build_shop_embed`, `ShopInteractiveView`), inventario (`build_inventory_embed`, `InventoryView`), consumo y extensiÃ³n de pases (`use_inventory_item`), transferencias entre miembros (`gift_inventory_item`) y watcher de expiraciÃ³n de buffs temporales (`check_and_expire_buffs`).
   - **`casino_slots.py`**: Motor de la tragaperras 5x3 (`SlotEngine`, `slot_engine`), 7 sÃ­mbolos de Brawl Stars Ranked y WILD (sin Scatters ni Free Spins), 9 lÃ­neas de pago limpias reales (3 Horizontales evaluadas en ventanas consecutivas con regla de casino *Highest Win Paid per Line* + 6 Diagonales rectas de 3 casillas diferenciadas), pantalla completa $\times 500$, bote progresivo (Grand y Mini), calibraciÃ³n Monte Carlo a RTP 110.0% (+/- 0.5%) y Hit Rate ~70.9%, interfaz 100% en espaÃ±ol, componentes interactivos Discord V2 (`SlotsLayoutView`, `SlotsPlayAgainButton`, `SlotsPayoutsButton`) y manejador `handle_slots_spin`.
   - **`casino_juegos.py`**: Motores y vistas interactivas del resto del casino nativo:
     * **Blackjack 21 Nativo** (`BlackjackEngine`, `blackjack_engine`, `BlackjackHand`, `BlackjackView`): zapato de 6 barajas con rebarajado automÃ¡tico, ases flexibles, reglas S17 del crupier, detecciÃ³n de Blackjack natural 3:2, opciÃ³n de doblar (`Double Down`), control de concurrencia y timeout de 60s con auto-stand.
     * **Ruleta Europea 37 Casillas** (`RouletteEngine`, `roulette_engine`, `RouletteActionView`): cilindro de 37 casillas con orden oficial de vecinos circulares, clasificaciÃ³n matemÃ¡tica de suertes sencillas/mÃºltiples, regla del 0 verde, RTP calibrado al 97.30%, Smart Argument Swap (/ruleta negro 500, /ruleta negro all, /ruleta negro) y botones interactivos [ð Repetir], [ðª Duplicar], [ð´ Apostar al Rojo] y [â« Apostar al Negro].
     * **Coinflip Dual** (`CoinflipEngine`, `coinflip_engine`, `CoinflipActionView`, `CoinflipChallengeView`): modo individual PvE 50/50 contra la casa y duelos 1v1 PvP con fianza atÃ³mica retenida, aceptaciÃ³n de reto, protecciÃ³n contra rival tieso y reparto determinista de fondos.
     * **Centro de Control del Casino (/casino)** (`CASINO_GAMES_INFO`, `build_casino_hub_embed`, `CasinoHubSelect`, `CasinoHubView`): hub interactivo con el bote acumulado visible, saldo del usuario, menÃº desplegable para consultar reglas y RTP de los 4 juegos, y botÃ³n de navegaciÃ³n de vuelta al menÃº principal.
   - **`economia.py`**: Fachada ligera de reexportaciÃ³n que unifica los 4 submÃ³dulos para `bot_service.py` y las suites de pruebas, implementando sincronizaciÃ³n dinÃ¡mica de variables (`_FachadaEconomia`) para propagar mutaciones en tiempo de ejecuciÃ³n (como `ECONOMY_DATA_PATH` en tests unitarios).
11. **`persistencia_discord.py`**: Mecanismo de persistencia distribuida y respaldo continuo en Discord (Render Cloud 24/7, especificaciÃ³n [`docs/PERSISTENCIA_DATOS.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/PERSISTENCIA_DATOS.md)):
    - HidrataciÃ³n inicial determinista al arrancar (`restore_from_discord`): localiza o crea el canal privado `#ðbackup-datos` en la categorÃ­a Staff/AdministraciÃ³n (`GUILD_ID = 1446143936891715616`), inspecciona los Ãºltimos 10 mensajes, descarga los adjuntos mÃ¡s recientes de `economia.json`, `user_memory.json` y `sugerencias.json`, valida sintaxis JSON estricta (`json.loads`) y realiza sobrescritura atÃ³mica con reemplazo seguro (`safe_write_json` con `.tmp` y `os.replace`).
    - Respaldo cÃ­clico automatizado (`tasks.loop(minutes=5)` en `setup_persistence`): audita marcas de modificaciÃ³n (`mtime`) y genera copias periÃ³dicas automÃ¡ticas enviadas con embed estructurado y adjuntos a `#ðbackup-datos`.
    - Respaldo de cierre controlado ante redeploys de Render (`backup_to_discord` en interceptor de seÃ±ales `SIGTERM` y `SIGINT`): captura la orden de apagado del contenedor, fuerza el vaciado de buffers en disco (`save_economy_data`, `save_user_memory`, `save_suggestions_data`) y despacha un backup sÃ­ncrono final antes de salir, blindando el 100% de los datos econÃ³micos, memorias y sugerencias sin pÃ©rdida entre despliegues.
12. **`cakey_client.py`**: Cliente del Leaderboard Web pÃºblico oficial de Cakey Bot ([`docs/AURA_BAREMO.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/AURA_BAREMO.md) Â§3.1):
    - Fuente canÃ³nica y unificada de verdad para niveles, XP acumulada, mensajes histÃ³ricos y minutos de voz en llamadas (`CAKEY_LEADERBOARD_URL = "https://cakey.bot/leaderboard/id/1446143936891715616?tab=leveling"`).
    - Parseo de HTML SSR (`parse_cakey_leaderboard_html`) con extracciÃ³n de `user_id` desde avatares de Discord CDN, `rank`, `username`, `messages`, `voice_minutes`, `level` y valor normalizado de XP (`parse_xp_value`).
    - GestiÃ³n de concurrencia y cachÃ© en memoria (`_LOCK = asyncio.Lock()`, `TTL = 300.0s`, `_CACHE`) con fast-path y fallback tolerante a fallos de red (`get_cakey_leaderboard`).
    - BÃºsqueda polimÃ³rfica de miembros (`get_user_cakey_data`): resoluciÃ³n por ID (int/str) y coincidencia insensible a mayÃºsculas por `username`, `global_name` o `display_name`.
    - Integrado prioritariamente en `get_live_levels_dict()` de `modulos/chat_ia.py` con preservaciÃ³n de fallback a regex en `#bots`.
13. **`starboard.py`**: The Sanvi Daily / Starboard GrÃ¡fico 2.0 (Reemplazo Integral de Carl-bot en `#â­muro-de-la-famaâ­`, especificaciÃ³n [`docs/DISENO_SANVI_DAILY.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/DISENO_SANVI_DAILY.md)):
    - Renderizador visual con Pillow a coste 0â¬ (`render_sanvi_daily_cover`): portadas de periÃ³dico vintage (800x1000 px), fondo pergamino, cabecera de rotativo *The Sanvi Daily*, avatar del autor con marco circular, cita tipogrÃ¡fica con comillas y ajuste automÃ¡tico, fotos adjuntas en filtro sepia y sello de autenticidad aprobado por el pueblo.
    - CÃ³mputo estricto anti-autobombo: exclusiÃ³n algorÃ­tmica de reacciones â­ del propio autor del mensaje.
    - Umbral canÃ³nico de activaciÃ³n de $\ge 2$ estrellas vÃ¡lidas con botÃ³n interactivo de salto al mensaje original.
    - Idempotencia y permanencia irrevocable: si un mensaje recibe mÃ¡s estrellas, se edita el mensaje existente en Discord actualizando el contador sin reimprimir portadas ni duplicar ediciones; si caen las reacciones, la portada jamÃ¡s se elimina.
    - Persistencia atÃ³mica en `datos/starboard.json` y respaldos automÃ¡ticos en `#ðbackup-datos` vÃ­a `persistencia_discord.py`.
14. **`bolsa_sanvi.py`**: Motor BursÃ¡til Central de Sanvi Exchange & Aura Market ([`docs/DISENO_BOLSA_SANVI.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/DISENO_BOLSA_SANVI.md) y [`docs/AURA_BAREMO.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/AURA_BAREMO.md)):
    - ValuaciÃ³n contable (Book Value de por vida `calculate_book_value`) y rendimiento temporal (Earnings 30d 50/50 `calculate_earnings_30d`).
    - Curva AMM con factor $K=2000$ (`calculate_market_price`) y suelo indestructible en $P_{\text{base}}$ (`calculate_base_price`).
    - Horquilla Bid/Ask fija del 1.0% (`get_bid_ask_prices`), retenciÃ³n del 50% al Yield Pool semanal y 50% quemado.
    - Ãrdenes bursÃ¡tiles con blindaje anti-ballenas (`execute_buy_order`, `execute_sell_order`): tope de 500 acciones por orden y cooldown de 30s.
    - Sinergia de Cartera y Utilidad Real (`get_user_portfolio_aura`, `get_user_portfolio_buff`): bono pasivo en `/trabajar` de +5% a +25%.
    - Bote de dividendos semanal (`distribute_weekly_dividends`): reparto ponderado en cuenta `bank` de los accionistas.
    - Indicadores tÃ©cnicos institucionales (`calculate_rsi`, `calculate_moving_averages`, `detect_crosses`), fuente Ãºnica de mÃ©tricas (`get_ticker_technical_metrics`) y analista financiero IA (`generate_market_report`, `_format_and_sanitize_report_emojis`).
15. **`bolsa_graficas.py`**: Renderizado GrÃ¡fico HD de Velas Japonesas con Pillow (PIL):
    - GrÃ¡ficos institucionales estilo Trading 212 a **960x540 px HD** (`generate_candlestick_chart`).
    - Paleta de alto contraste: fondo negro puro (`#000000`), velas alcistas verde neÃ³n (`#00E676`), bajistas rojo vivo (`#FF5252`), y trazo gris azulado (`#3A4659`) sin barra de volumen en cubetas planas con `volume=0`.
    - **8 Temporalidades completas** (`TIMEFRAME_CONFIG`): `Trades` (1 vela por orden), `15m` (velas de 1m), `1h` (velas de 2m), `4h` (velas de 10m), `1D` (velas de 30m), `1S` (velas de 4h, 42 velas), `1M` (velas de 1D, 30 velas) y `MAX` (velas de 1D/adaptativas desde el origen, hasta 45-60 velas).
    - SuperposiciÃ³n de curva **EMA 14** (`#FFB300`), eje X inferior con fechas/horas reales y caja de estadÃ­sticas (`MÃX`, `MÃN`, `VOL`) junto al badge de resoluciÃ³n.
    - SubgrÃ¡fico inferior de volumen, lÃ­nea horizontal de cotizaciÃ³n cian (`#00A3FF`) con badge flotante en el eje de precios y grid tenue (`#1E1E1E`).
    - Retorno de buffer `io.BytesIO` en formato PNG nativo para `discord.File`.
16. **`web_server.py`**: Servidor HTTP en puerto 10000 para Render:
    - Endpoints de salud y logs: `GET /status`, `GET /logs`.
    - Streaming de audios: `GET /audios`, `GET /audios/zip`, `GET /api/audios`.
    - **Terminal Web BursÃ¡til**: `GET /bolsa` con interfaz oscura interactiva basada en **TradingView Lightweight Charts v4.2.0** (velas, volumen, zoom, selector de 4 tickers y las 8 temporalidades `Trades, 15m, 1h, 4h, 1D, 1S, 1M, MAX`, mÃ©tricas en directo, libro de Ã³rdenes y dividendos).
    - **API BursÃ¡til en Tiempo Real**: `GET /api/bolsa/data` con cotizaciones, estadÃ­sticas, pool y series OHLCV monÃ³tonas en tiempo.

## CÃ³mo se usa e integra con `bot_service.py`
- `bot_service.py` actÃºa como punto de entrada Ãºnico (`python bot_service.py`) y orquestador central bajo una **Arquitectura de Runner Dual**:
  * Ejecuta concurrentemente en el mismo proceso y contenedor de Render los dos clientes de Discord (`bot` para `Asistente` y `economy_bot` para `Economia Asistente`) utilizando un supervisor asÃ­ncrono `asyncio.gather(*tasks)` envuelto en un bucle persistente `while True`.
  * Sincroniza de forma independiente el Ã¡rbol general `tree` (23 comandos) y el Ã¡rbol de economÃ­a `economy_tree` (20 comandos) con el servidor `1446143936891715616` (43 comandos en total).
  * Ejecuta en segundo plano `_xp_passes_expiration_watcher()` para auditar cada 30 minutos los pases temporales de XP (`active_buffs`) y retirar automÃ¡ticamente los roles vencidos en Discord.
  * Maneja las presencias personalizadas de cada bot (`listening: Gemini Live en voz (/unete)` para Asistente y `watching: Casino y Porros (/slots)` para Economia Asistente).
  * Encamina eventos de componentes interactivos (`slots:`, `bj:`, `roulette:`, `coinflip:`, `casino:`) hacia sus respectivas vistas.
  * Registra `sys.modules.setdefault("bot_service", sys.modules[__name__])` y reexporta todas las funciones, clases y constantes de `modulos.*`.
- Para permitir que los tests unitarios (`herramientas/test_*.py`) hagan monkeypatching sobre atributos de `bot_service` (como `bot_service.mark_model_cooldown` o `bot_service.ensure_voice_connection`), los submÃ³dulos acceden dinÃ¡micamente a la instancia de `bot_service` mediante el helper interno `_bs()`.

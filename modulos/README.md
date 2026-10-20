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
8. **`comandos.py` (Fachada)** y sus submódulos especializados:
   - **`comandos_generales.py`**: Comandos Slash del bot `Asistente` (22 comandos generales: `/dibuja`, `/musica`, `/steam`, `/tribunal`, `/perfil`, `/pregunta`, `/voz`, `/recuerda`, `/xp`, `/habla`, `/geminilive`, `/cambiar_voz`, `/unete`, `/desconecta`, `/para_audio`, `/trivial`, `/ranking_trivial`, `/tres_en_raya`, `/conecta4`, `/ajedrez`, `/autoroles`, `/sugerencia`), lista `GENERAL_SLASH_COMMANDS` y registro modular `register_general_commands(tree)`.
   - **`comandos_economia.py`**: Comandos Slash del bot `Economia Asistente` (20 comandos de economía y casino: `/slots`, `/balance`, `/trabajar`, `/transferir`, `/depositar`, `/retirar`, `/robar`, `/tienda`, `/salario`, `/blackjack`, `/bj`, `/ruleta`, `/coinflip`, `/casino`, `/crimen`, `/ranking`, `/inventario`, `/usar`, `/regalar`, `/admin_dinero`), restricción estricta de canales (`ensure_economy_channel`), lista `ECONOMY_SLASH_COMMANDS` y registro modular `register_economy_commands(tree)`.
   - **`comandos.py`**: Fachada ligera de reexportación 100% retrocompatible que agrupa `ALL_SLASH_COMMANDS`, expone `register_slash_commands(tree)` y propaga mutaciones dinámicas a través de `_FachadaComandos`.
9. **`economia.py` (Fachada)** y sus 4 submódulos atómicos:
   - **`economia_core.py`**: Motor central de persistencia atómica (`datos/economia.json`) bajo `ECONOMY_LOCK` (`RLock`), gestión de saldos (`get_balance`, `modify_balance`), bote global del servidor (`get_server_jackpot`, `modify_server_jackpot`), banca (`deposit_cash`, `withdraw_cash`), transferencias (`transfer_funds`), multiplicadores por rol de nivel (`LEVEL_ROLE_MULTIPLIERS`, `get_level_role_multiplier`), trabajo (`can_work`, `execute_work`), delitos (`can_crime`, `execute_crime`), robos e inmunidad (`user_has_shield`, `can_rob`, `execute_rob`), salario progresivo con decaimiento del 5% (`calculate_daily_salary`, `claim_salary`), tabla de líderes (`get_economy_leaderboard`, `build_ranking_embed`, `RankingView`) y panel financiero de administración (`admin_modify_money`, `admin_airdrop_role`).
   - **`economia_tienda.py`**: Catálogo oficial de artículos `SHOP_ITEMS` (roles permanentes, pases temporales XP y consumibles como `🥤 Monster Blanco`), compra interactiva (`build_shop_embed`, `ShopInteractiveView`), inventario (`build_inventory_embed`, `InventoryView`), consumo y extensión de pases (`use_inventory_item`), transferencias entre miembros (`gift_inventory_item`) y watcher de expiración de buffs temporales (`check_and_expire_buffs`).
   - **`casino_slots.py`**: Motor de la tragaperras 5x3 (`SlotEngine`, `slot_engine`), 7 símbolos de Brawl Stars Ranked y WILD (sin Scatters ni Free Spins), 9 líneas de pago limpias reales (3 Horizontales evaluadas en ventanas consecutivas + 6 Diagonales rectas de 3 casillas), pantalla completa $\times 500$, bote progresivo (Grand y Mini), calibración Monte Carlo a RTP 110.0% (+/- 0.5%) y Hit Rate ~70.9%, componentes interactivos Discord V2 (`SlotsLayoutView`, `SlotsPlayAgainButton`, `SlotsPayoutsButton`) y manejador `handle_slots_spin`.
   - **`casino_juegos.py`**: Motores y vistas interactivas del resto del casino nativo:
     * **Blackjack 21 Nativo** (`BlackjackEngine`, `blackjack_engine`, `BlackjackHand`, `BlackjackView`): zapato de 6 barajas con rebarajado automático, ases flexibles, reglas S17 del crupier, detección de Blackjack natural 3:2, opción de doblar (`Double Down`), control de concurrencia y timeout de 60s con auto-stand.
     * **Ruleta Europea 37 Casillas** (`RouletteEngine`, `roulette_engine`, `RouletteActionView`): cilindro de 37 casillas con orden oficial de vecinos circulares, clasificación matemática de suertes sencillas/múltiples, regla del 0 verde, RTP calibrado al 97.30% y botones para repetir o duplicar tirada.
     * **Coinflip Dual** (`CoinflipEngine`, `coinflip_engine`, `CoinflipActionView`, `CoinflipChallengeView`): modo individual PvE 50/50 contra la casa y duelos 1v1 PvP con fianza atómica retenida, aceptación de reto, protección contra rival tieso y reparto determinista de fondos.
     * **Centro de Control del Casino (/casino)** (`CASINO_GAMES_INFO`, `build_casino_hub_embed`, `CasinoHubSelect`, `CasinoHubView`): hub interactivo con el bote acumulado visible, saldo del usuario, menú desplegable para consultar reglas y RTP de los 4 juegos, y botón de navegación de vuelta al menú principal.
   - **`economia.py`**: Fachada ligera de reexportación que unifica los 4 submódulos para `bot_service.py` y las suites de pruebas, implementando sincronización dinámica de variables (`_FachadaEconomia`) para propagar mutaciones en tiempo de ejecución (como `ECONOMY_DATA_PATH` en tests unitarios).
10. **`persistencia_discord.py`**: Mecanismo de persistencia distribuida y respaldo continuo en Discord (Render Cloud 24/7, especificación [`docs/PERSISTENCIA_DATOS.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/PERSISTENCIA_DATOS.md)):
    - Hidratación inicial determinista al arrancar (`restore_from_discord`): localiza o crea el canal privado `#🔒backup-datos` en la categoría Staff/Administración (`GUILD_ID = 1446143936891715616`), inspecciona los últimos 10 mensajes, descarga los adjuntos más recientes de `economia.json` y `user_memory.json`, valida sintaxis JSON estricta (`json.loads`) y realiza sobrescritura atómica con reemplazo seguro (`safe_write_json` con `.tmp` y `os.replace`).
    - Respaldo cíclico automatizado (`tasks.loop(minutes=5)` en `setup_persistence`): audita marcas de modificación (`mtime`) y genera copias periódicas automáticas enviadas con embed estructurado y adjuntos a `#🔒backup-datos`.
    - Respaldo de cierre controlado ante redeploys de Render (`backup_to_discord` en interceptor de señales `SIGTERM` y `SIGINT`): captura la orden de apagado del contenedor, fuerza el vaciado de buffers en disco (`save_economy_data` y `save_user_memory`) y despacha un backup síncrono final antes de salir, blindando el 100% de los datos económicos y memorias sin pérdida entre despliegues.
11. **`cakey_client.py`**: Cliente del Leaderboard Web público oficial de Cakey Bot ([`docs/AURA_BAREMO.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/AURA_BAREMO.md) §3.1):
    - Fuente canónica y unificada de verdad para niveles, XP acumulada, mensajes históricos y minutos de voz en llamadas (`CAKEY_LEADERBOARD_URL = "https://cakey.bot/leaderboard/id/1446143936891715616?tab=leveling"`).
    - Parseo de HTML SSR (`parse_cakey_leaderboard_html`) con extracción de `user_id` desde avatares de Discord CDN, `rank`, `username`, `messages`, `voice_minutes`, `level` y valor normalizado de XP (`parse_xp_value`).
    - Gestión de concurrencia y caché en memoria (`_LOCK = asyncio.Lock()`, `TTL = 300.0s`, `_CACHE`) con fast-path y fallback tolerante a fallos de red (`get_cakey_leaderboard`).
    - Búsqueda polimórfica de miembros (`get_user_cakey_data`): resolución por ID (int/str) y coincidencia insensible a mayúsculas por `username`, `global_name` o `display_name`.
    - Integrado prioritariamente en `get_live_levels_dict()` de `modulos/chat_ia.py` con preservación de fallback a regex en `#bots`.

## Cómo se usa e integra con `bot_service.py`
- `bot_service.py` actúa como punto de entrada único (`python bot_service.py`) y orquestador central bajo una **Arquitectura de Runner Dual**:
  * Ejecuta concurrentemente en el mismo proceso y contenedor de Render los dos clientes de Discord (`bot` para `Asistente` y `economy_bot` para `Economia Asistente`) utilizando un supervisor asíncrono `asyncio.gather(*tasks)` envuelto en un bucle persistente `while True`.
  * Sincroniza de forma independiente el árbol general `tree` (22 comandos) y el árbol de economía `economy_tree` (19 comandos) con el servidor `1446143936891715616`.
  * Ejecuta en segundo plano `_xp_passes_expiration_watcher()` para auditar cada 30 minutos los pases temporales de XP (`active_buffs`) y retirar automáticamente los roles vencidos en Discord.
  * Maneja las presencias personalizadas de cada bot (`listening: Gemini Live en voz (/unete)` para Asistente y `watching: Casino y Porros (/slots)` para Economia Asistente).
  * Encamina eventos de componentes interactivos (`slots:`, `bj:`, `roulette:`, `coinflip:`, `casino:`) hacia sus respectivas vistas.
  * Registra `sys.modules.setdefault("bot_service", sys.modules[__name__])` y reexporta todas las funciones, clases y constantes de `modulos.*`.
- Para permitir que los tests unitarios (`herramientas/test_*.py`) hagan monkeypatching sobre atributos de `bot_service` (como `bot_service.mark_model_cooldown` o `bot_service.ensure_voice_connection`), los submódulos acceden dinámicamente a la instancia de `bot_service` mediante el helper interno `_bs()`.

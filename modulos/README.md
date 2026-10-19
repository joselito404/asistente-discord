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
   - Declaración de los 31 comandos interactivos (`@app_commands.command`) organizados por dominios de bots:
     * `GENERAL_SLASH_COMMANDS` (22 comandos para el bot `Asistente`): `/dibuja`, `/musica`, `/steam`, `/tribunal`, `/perfil`, `/pregunta`, `/voz`, `/recuerda`, `/xp`, `/habla`, `/geminilive`, `/cambiar_voz`, `/unete`, `/desconecta`, `/para_audio`, `/trivial`, `/ranking_trivial`, `/tres_en_raya`, `/conecta4`, `/ajedrez`, `/autoroles`, `/sugerencia`.
     * `ECONOMY_SLASH_COMMANDS` (9 comandos para el bot `Economia Asistente`): `/slots`, `/balance`, `/trabajar`, `/transferir`, `/depositar`, `/retirar`, `/robar`, `/tienda`, `/salario`.
     * `ALL_SLASH_COMMANDS`: unión de las dos listas (31 comandos) garantizando retrocompatibilidad total.
   - Funciones modulares de registro:
     * `register_general_commands(tree)`: vincula los 22 comandos generales al árbol de `Asistente`.
     * `register_economy_commands(tree)`: vincula los 9 comandos de economía al árbol de `Economia Asistente`.
     * `register_slash_commands(tree)`: registra ambos árboles si se invoca para compatibilidad retrospectiva.
9. **`economia.py`**: Motor nativo de economía comunitaria, banca, robos, tienda, salarios y casino:
   - Moneda oficial: Porros (`PORRO_EMOJI` `<:Porro:1535685303317172305>`).
   - Persistencia segura y atómica en `datos/economia.json` con bloqueo `ECONOMY_LOCK` (`RLock`) y escritura temporal `safe_write_json`.
   - Gestión de saldos: `get_balance`, `modify_balance`, `transfer_funds`.
   - Módulo de Banca (`/depositar`, `/retirar`): gestión segura de efectivo y banco con soporte de montos numéricos y opción `'all'`/`'todo'`.
   - Sistema de Robo (`/robar`): probabilidad de éxito 50%, hurto de 20-50% de efectivo, chequeo estricto de inmunidad contra `🛡️ Cartera Blindada` (falla 100% y multa 15%) y cooldown anti-spam.
   - Catálogo Oficial de Tienda V2 (`/tienda`): vista interactiva sin parámetros con embed categorizado (Roles, Ítems, XP), menú desplegable de 9 artículos y botón explícito de confirmación de compra (`ShopInteractiveView`) para evitar compras accidentales, con auto-asignación de roles vía Discord API.
   - Salario Acumulativo (`/salario` / `/cobrar`): cálculo continuo por roles de nivel (Nivel 10 a 100) y podio (Top 1, 2, 3) con fórmula de decaimiento del 5% diario ($P = S \times \frac{1 - (1 - d)^n}{d}$, tope asintótico $20 \times S$).
   - Jornada laboral (`/trabajar`): historias cómicas del lore del servidor (`WORK_MESSAGES`), retribución de 200 a 800 porros y cooldown estricto de 2 horas.
   - Máquina tragaperras 5x3 de Alta Tensión (`/slots`):
     * Matriz 5 rodillos $\times$ 3 filas (15 casilleros) y 8 símbolos: 6 Brawl Stars Ranked, Comodín WILD (`<:absolutecinema:...>`) y Dispersor SCATTER (`<:Porro:...>`).
     * 7 Líneas de Pago Limpias evaluadas de izquierda a derecha para 3, 4 y 5 aciertos (`SLOT_PAYLINES`).
     * Patrón Especial "Pantalla Completa" (15 casillas a $\times 500.0$).
     * Ronda de Free Spins escalonada (3/4/5 Scatters $\to$ 5/8/12 giros a $\times 2$ con re-triggers $+3$).
     * Bote Progresivo Escalonado: Grand Jackpot (100% bote con 5 Pro o 5 Wild en L1 central) y Mini Jackpot (25% bote con 5 Masters en L1).
     * Calibración Monte Carlo a RTP 110.0% ($\pm 0.5\%$, Hit Rate ~43.80%, modo High Payouts EV+ ordenado por Jose).
     * Interfaz nativa con **Discord Components V2** (`SlotsLayoutView`): contenedores tipo 17 con `accent_color`, separadores tipo 14, textos tipo 10 y botones `[Play Again]`, `[🌀 Jugar Tiradas Gratis]` y `[Payouts]` en fila de acciones tipo 1.

## Cómo se usa e integra con `bot_service.py`
- `bot_service.py` actúa como punto de entrada único (`python bot_service.py`) y orquestador central bajo una **Arquitectura de Runner Dual**:
  * Ejecuta concurrentemente en el mismo proceso y contenedor de Render los dos clientes de Discord (`bot` para `Asistente` y `economy_bot` para `Economia Asistente`) utilizando un supervisor asíncrono `asyncio.gather(*tasks)` envuelto en un bucle persistente `while True`.
  * Sincroniza de forma independiente el árbol general `tree` (22 comandos) y el árbol de economía `economy_tree` (9 comandos) con el servidor `1446143936891715616`.
  * Maneja las presencias personalizadas de cada bot (`listening: Gemini Live en voz (/unete)` para Asistente y `watching: Casino y Porros (/slots)` para Economia Asistente).
  * Encamina eventos de componentes interactivos (`slots:`) hacia `handle_slots_interaction`.
  * Registra `sys.modules.setdefault("bot_service", sys.modules[__name__])` y reexporta todas las funciones, clases y constantes de `modulos.*`.
- Para permitir que los tests unitarios (`herramientas/test_*.py`) hagan monkeypatching sobre atributos de `bot_service` (como `bot_service.mark_model_cooldown` o `bot_service.ensure_voice_connection`), los submódulos acceden dinámicamente a la instancia de `bot_service` mediante el helper interno `_bs()`.

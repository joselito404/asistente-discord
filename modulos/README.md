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
8. **`comandos.py`**: Registro unificado de Comandos Slash nativos:
   - Declaración de los 26 comandos interactivos (`@app_commands.command`) con descripciones y choices.
   - Función `register_slash_commands(tree)` para registro limpio en el `CommandTree`.
9. **`economia.py`**: Motor nativo de economía comunitaria y casino:
   - Moneda oficial: Porros (`PORRO_EMOJI` `<:Porro:1535685303317172305>`).
   - Persistencia segura y atómica en `datos/economia.json` con bloqueo `ECONOMY_LOCK` (`RLock`) y escritura temporal `safe_write_json`.
   - Gestión de saldos: `get_balance`, `modify_balance`, `transfer_funds`.
   - Jornada laboral (`/trabajar`): historias cómicas del lore del servidor (`WORK_MESSAGES`), retribución calibrada de 200 a 800 porros y cooldown estricto de 2 horas.
   - Máquina tragaperras (`/slots`):
     * Réplica matemática 1:1 de UnbelievaBoat calibrada mediante Monte Carlo (`SlotEngine`, RTP 94-96%, WinRate ~36.5%).
     * 6 símbolos Brawl Stars Ranked con 5 líneas de pago evaluadas simultáneamente (`SLOT_SYMBOLS`, `SLOT_PAYLINES`).
     * Bote Progresivo (`server_jackpot`): un 3% de las pérdidas en tiradas no ganadoras alimenta el jackpot acumulado, reclamable al alinear la línea de Ranked Pro.
     * Interfaz nativa con **Discord Components V2** (`SlotsLayoutView`): contenedores tipo 17 con `accent_color`, separadores tipo 14, textos tipo 10 y botones `[Play Again]` y `[Payouts]` en fila de acciones tipo 1.

## Cómo se usa e integra con `bot_service.py`
- `bot_service.py` actúa como punto de entrada único (`python bot_service.py`), registra `sys.modules.setdefault("bot_service", sys.modules[__name__])` y reexporta las funciones, clases y constantes de `modulos.*`.
- Para permitir que los tests unitarios (`herramientas/test_*.py`) hagan monkeypatching sobre atributos de `bot_service` (como `bot_service.mark_model_cooldown` o `bot_service.ensure_voice_connection`), los submódulos acceden dinámicamente a la instancia de `bot_service` mediante el helper interno `_bs()`.

# 🛠️ Herramientas, Tests y Scripts Auxiliares (`herramientas/`)

> **Propósito de la carpeta**: Alberga herramientas operativas de producción, suites de pruebas unitarias y de regresión, y scripts auxiliares de análisis y mantenimiento local.
> **Quién puede escribir**: Desarrolladores y agentes de IA.
> **Regla de origen**: Cumple con la Regla Global §8 (README por carpeta).

---

## 🚀 1. Scripts Operativos de Producción

| Script | Uso y Comando | Descripción |
| :--- | :--- | :--- |
| `deploy_render.py` | `python herramientas/deploy_render.py` | Despliegue manual en Render Cloud llamando a la API de Render con la clave de `config/config_discord.json`. |
| `discord_client.py` | Importable o interactivo | Cliente HTTP REST ligero para consultar canales, leer censos, enviar mensajes o modificar tópicos sin iniciar el proceso local del bot. |
| `sync_voice_recordings.py` | `python herramientas/sync_voice_recordings.py` | Descarga y sincroniza las grabaciones de voz temporales desde Render Cloud hacia `datos_locales/recordings_backup/`. |
| `sync_info_servidor.py` | `python herramientas/sync_info_servidor.py` | Audita y sincroniza en segundos los canales, roles y censos reales de Discord contra `docs/INFO_SERVIDOR.md`. |
| `audit_emojis_telemetry.py` | `python herramientas/audit_emojis_telemetry.py` | Descarga respaldo local de los 124 emojis en `datos_locales/emojis_backup/`, genera `manifest.json` y escanea mensajes y reacciones en los 33 canales de texto para telemetría real de uso. |
| `update_discord_channels.py` | `python herramientas/update_discord_channels.py` | Actualiza los tópicos de canales de economía y casino en Discord y gestiona la publicación y fijado de guías maestras en `#⌨️comandos⌨️`. |

---

## 🧪 2. Suites de Pruebas Unitarias y de Regresión

Ejecutar antes de cualquier commit o despliegue en Render Cloud:

| Suite | Comando | Qué Valida |
| :--- | :--- | :--- |
| `test_carlbot_replacement.py` | `python herramientas/test_carlbot_replacement.py` | Auto-Roles completo: embeds con contadores `👥`, selects públicos, vistas efímeras personales con checks `✅` y catálogo. |
| `test_phase1.py` | `python herramientas/test_phase1.py` | Subsistema de utilidades y gráficas (Pillow, QuickChart). |
| `test_phase2.py` | `python herramientas/test_phase2.py` | Subsistema de juegos, trivia y tribunal. |
| `test_phase3.py` | `python herramientas/test_phase3.py` | Subsistema de voz, transcripción y servidor web en puerto 10000. |
| `test_live_voice_improvements.py` | `python herramientas/test_live_voice_improvements.py` | Resiliencia de voz y buffer VAD en llamadas. |
| `test_voice_reconnection.py` | `python herramientas/test_voice_reconnection.py` | Reconexión del bot ante expulsiones o caídas de WebSocket. |
| `test_prompts_key_files.py` | `python herramientas/test_prompts_key_files.py` | Integridad sintáctica de prompts y dependencias de archivos. |
| `test_audio_models.py` | `python herramientas/test_audio_models.py` | Compatibilidad de modelos de voz y Edge-TTS. |
| `test_emoji_converter.py` | `python herramientas/test_emoji_converter.py` | Auto-conversor de emojis (:aura:, :Porro:, :gigachad:, Brawl Stars Ranked), insensibilidad a mayúsculas, protección de bloques de código y resiliencia ante pérdida de Server Boost (available=False fallback). |
| `test_slots_engine.py` | `python herramientas/test_slots_engine.py` | Simulación Monte Carlo de 100k tiradas y calibración de RTP (94-96%) y win rate (36.5%) de la tragaperras. |
| `test_economy.py` | `python herramientas/test_economy.py` | Suite integral de economía nativa y tragaperras 5x3 (24/24 tests verdes): persistencia atómica, saldos, banca (/depositar, /retirar), multiplicadores de rol de nivel (+10% a +40%), jornada laboral (/trabajar 1.000-2.500 cada 4h), delitos de alto riesgo (/crimen 1.800-3.500 cada 12h con multa 10% mín 500 y 3% jackpot), robos con escudo (/robar 24h, robo 20-33% y multa 15% repartida 10% víctima + 5% bote), tienda V2 interactiva (/tienda), inventario, uso y regalo (/inventario, /usar con '🥤 Monster Blanco' y pases XP temporales + expiración automática, /regalar), filtro de canales (ensure_economy_channel), ranking de riqueza (/ranking), panel admin (/admin_dinero dar, quitar, fijar, airdrop), salario progresivo por nivel exacto (/salario Opción A con decaimiento 5%), 7 líneas de pago 5x3, 42 slash commands (20 economía) y simulación Monte Carlo RTP 110.0%. |
| `test_blackjack.py` | `python herramientas/test_blackjack.py` | Suite completa de Blackjack 21 Nativo (11/11 tests verdes): zapato de 6 barajas (312 cartas), rebarajado automático (<52 cartas), Ases dinámicos blandos/duros, detección natural de Blackjack, crupier S17 (stands 17+, hits <=16), validación de apuestas (min 100, all-in), liquidación financiera (descuento, pago 3:2, pago 1:1, push, 3% jackpot), Doblar (Double Down), concurrencia (ACTIVE_BLACKJACK_GAMES), bloqueo de terceros, auto-stand en timeout (60s) y registro de /blackjack y /bj en Runner Dual (20 comandos de economía, 42 totales). |
| `test_roulette.py` | `python herramientas/test_roulette.py` | Suite completa de Ruleta Europea 37 Casillas (8/8 tests verdes): cilindro europeo de 37 casillas (0 a 36) y rotación circular de vecinos (`RouletteEngine`), clasificación de colores (18 rojos, 18 negros, 1 verde), paridad, mitades, docenas y columnas, regla canónica del 0 verde, pagos exactos (1:1, 2:1, 35:1), simulación Monte Carlo de 50.000 tiradas verificando RTP 97.30% (+/- 0.5%), liquidación atómica y 3% a jackpot en pérdidas, botones interactivos (`RouletteActionView`: repetir y duplicar apuesta), seguridad efímera contra terceros y presencia de /ruleta en ECONOMY_SLASH_COMMANDS (20 comandos de economía, 42 totales). |
| `test_coinflip.py` | `python herramientas/test_coinflip.py` | Suite completa de Coinflip Dual PvP y PvE (11/11 tests verdes): resolución 50/50 justa, simulación Monte Carlo de 5.000 tiradas, pagos 1:1 y 3% jackpot feed en PvE, retención atómica de fianza bajo `ECONOMY_LOCK`, reparto PvP (98% ganador, 2% jackpot y conservación total de masa monetaria), cancelación manual y timeout de 60s con reembolso del 100%, protección contra rival sin fondos, control de permisos en `CoinflipChallengeView` y `CoinflipActionView`, y presencia de /coinflip en el Runner Dual (20 comandos de economía, 42 totales). |
| `test_casino_hub.py` | `python herramientas/test_casino_hub.py` | Suite completa del Centro de Control del Casino (/casino) (8/8 tests verdes): generación de embed principal con bote acumulado y cartera de usuario, 4 vistas de detalle (slots, blackjack, ruleta, coinflip) con RTP oficial y comandos, navegación interactiva en `CasinoHubView` (Select de 4 juegos y botón `[ 🏠 Menú Principal ]`), bloqueo efímero a terceros, timeout de 90s con desactivación limpia, presencia de /casino en ECONOMY_SLASH_COMMANDS (20 cmds) y ALL_SLASH_COMMANDS (42 cmds) y reexportación en bot_service.py. |
| `test_persistencia_cakey.py` | `python herramientas/test_persistencia_cakey.py` | Suite completa de persistencia en Discord y cliente Cakey Bot (9/9 tests verdes): parser de leaderboard web de Cakey Bot (HTML mock y live), conversión de valores de XP (`parse_xp_value`), búsqueda polimórfica de usuarios (`get_user_cakey_data`), escritura atómica en disco (`safe_write_json`), hidratación y rechazo estricto de JSON corrupto en `restore_from_discord`, armado de embeds y adjuntos en `backup_to_discord`, y configuración del loop cíclico (5 min) y señales SIGTERM/SIGINT en `setup_persistence`. |
| `test_bolsa.py` | `python herramientas/test_bolsa.py` | Suite integral del Sanvi Exchange y Aura Market (12/12 tests verdes): cálculo canónico de Book Value exacto para Joselito (79.52), Terre (48.52), Omen (47.72) y Racer (44.78); Earnings 30d 50/50; curva AMM factor K=2000 y suelo P_base; horquilla Bid/Ask 1% y reparto 50% Yield Pool / 50% quema en compras y ventas; blindaje anti-ballenas (máx 500 acciones y cooldown 30s); Sinergia de Cartera (+5% a +25% en /trabajar); indicadores técnicos cuantitativos (RSI 14 y medias móviles institucionales); renderizado gráfico de velas japonesas en Pillow con buffer PNG válido; interruptor de paro de emergencia administrativo (emergency_halt); validación de 5 temporalidades intradía reales (Trades, 15m, 1h, 4h, 1D); y validación de endpoints de la Terminal Web (/bolsa HTML5 y /api/bolsa/data JSON). |
| `test_refined_transcription.py` | `python herramientas/test_refined_transcription.py` | Pruebas de transcripción refinada de audio y mitigación de alucinaciones en llamadas. |
| `test_transcribe_all.py` | `python herramientas/test_transcribe_all.py` | Validación en lote de transcripción de audios de prueba de voz. |

---

## 📦 3. Utilidades Auxiliares y Compilación

- **Configuración de Entorno Local**: `registrar_protocolo_ide.ps1` (asocia el protocolo URL personalizado `antigravity-ide://` en el Registro de Windows para abrir el IDE).
- **Compiladores de Documentación**: `build_pdf.js`, `build_cap10_pdf.js`, `build_audio_guide_pdf.js` (renderizado local de PDFs con `marked`).
- **Análisis de Audio y Estadísticas**: `analyze_zip_durations.py`, `audit_zip_transcriptions.py`, `analyze_slots.ps1`, `calculate_stats.ps1`.
- **Generación de Contenido**: `generate_trivia_pool.py`.

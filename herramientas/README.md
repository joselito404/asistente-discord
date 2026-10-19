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
| `test_economy.py` | `python herramientas/test_economy.py` | Suite integral de economía: persistencia atómica, saldos, jornada laboral (/trabajar), transferencias (/transferir), tragaperras (/slots) con Discord Components V2, bote progresivo y concurrencia multihilo. |
| `test_refined_transcription.py` | `python herramientas/test_refined_transcription.py` | Pruebas de transcripción refinada de audio y mitigación de alucinaciones en llamadas. |
| `test_transcribe_all.py` | `python herramientas/test_transcribe_all.py` | Validación en lote de transcripción de audios de prueba de voz. |

---

## 📦 3. Utilidades Auxiliares y Compilación

- **Configuración de Entorno Local**: `registrar_protocolo_ide.ps1` (asocia el protocolo URL personalizado `antigravity-ide://` en el Registro de Windows para abrir el IDE).
- **Compiladores de Documentación**: `build_pdf.js`, `build_cap10_pdf.js`, `build_audio_guide_pdf.js` (renderizado local de PDFs con `marked`).
- **Análisis de Audio y Estadísticas**: `analyze_zip_durations.py`, `audit_zip_transcriptions.py`, `analyze_slots.ps1`, `calculate_stats.ps1`.
- **Generación de Contenido**: `generate_trivia_pool.py`.

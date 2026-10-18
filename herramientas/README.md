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

---

## 📦 3. Utilidades Auxiliares y Compilación

- **Compiladores de Documentación**: `build_pdf.js`, `build_cap10_pdf.js`, `build_audio_guide_pdf.js` (renderizado local de PDFs con `marked`).
- **Análisis de Audio y Estadísticas**: `analyze_zip_durations.py`, `audit_zip_transcriptions.py`, `analyze_slots.ps1`, `calculate_stats.ps1`.
- **Generación de Contenido**: `generate_trivia_pool.py`.

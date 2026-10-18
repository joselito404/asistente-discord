# 🗄️ Datos Locales y Archivos Temporales (`datos_locales/`)

> **Propósito de la carpeta**: Contenedor para archivos pesados, instaladores locales, logs de depuración y respaldos de grabaciones que no deben sincronizarse en la nube ni formar parte del repositorio Git.
> **Quién puede escribir**: Scripts locales (`sync_voice_recordings.py`), procesos de depuración y el usuario.
> **Regla de origen**: Cumple con la Regla Global §8 (README por carpeta).

---

## 🚫 Estado Gitignored Total

Todo el contenido de esta carpeta está excluido de Git por `.gitignore`:
- `*.exe` (instaladores locales como `Claude Setup.exe`).
- `logs/` (volcados temporales de registros de consola).
- `recordings_backup/` (copias de seguridad locales descargadas de Render).
- `emojis_backup/` (copia de seguridad local de alta resolución de los 124 emojis del servidor con `manifest.json`).
- `grabaciones/` (archivos WAV temporales).

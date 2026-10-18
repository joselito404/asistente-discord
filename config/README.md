# ⚙️ Configuración y Secretos (`config/`)

> **Propósito de la carpeta**: Almacena secretos locales y credenciales privadas del bot de Discord y servicios vinculados.
> **Quién puede escribir**: Jose (configuración de tokens) o asistentes bajo su autorización expresa.
> **Regla de origen**: Cumple con la Regla Global §8 (README por carpeta).

---

## 🔒 Archivo `config_discord.json` (Gitignored)

Este archivo está estrictamente excluido del repositorio Git (`.gitignore`) y sincronizado únicamente mediante OneDrive privado.

### Estructura de claves requerida:
```json
{
  "bot_token": "Token_del_Bot_de_Discord",
  "gemini_api_key": "Clave_API_de_Google_Gemini",
  "render_api_key": "Clave_API_de_Render_para_deploy_render.py",
  "render_service_id": "srv-daqo5rbtqb8s73bbj7l0",
  "guild_id": "1446143936891715616"
}
```

> [!CAUTION]
> **Nunca subir claves al repositorio**: Cualquier commit que contenga tokens reales causará la invalidación inmediata de las credenciales por parte de Discord o GitHub.

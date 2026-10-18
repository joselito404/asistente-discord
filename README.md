# 🤖 Antigravity-discord (Bot 'Asistente')

> **Bot Oficial Multi-Herramienta 24/7** para el servidor de Discord *LOS MONGOLOS DEL SANVI Y SUS AMIGOS*.
> Aloja utilidades conversacionales con IA (Gemini), síntesis neuronal de voz y escucha en llamadas, motor gráfico FLUX.1/LaTeX/gráficos, gestión de auto-roles 24/7, minijuegos y subsistema económico nativo.

---

## 🏗️ Arquitectura del Repositorio

El proyecto sigue una arquitectura modular y desacoplada para garantizar portabilidad total entre entornos multi-PC (**AM4** y **AM5**) y despliegue continuo en **Render Cloud**:

```text
Antigravity-discord/
├── bot_service.py          # Orquestador central y supervisor de ejecución 24/7
├── config/                 # Credenciales locales y tokens (config_discord.json, gitignored)
├── modulos/                # Lógica funcional modular del bot
│   ├── chat_ia.py          # IA conversacional Gemini con Circuit Breaker y memoria multi-turn
│   ├── autoroles.py        # Panel interactivo 24/7 de Auto-Roles con Discord Components
│   ├── comandos.py         # Registro y lógica de Comandos Slash nativos
│   ├── juegos.py           # Minijuegos (Ajedrez, Conecta 4, Trivial, Steam, Tragaperras)
│   ├── graficos.py         # Motor gráfico (FLUX.1, tarjetas LaTeX, gráficas con Pillow)
│   ├── voz.py              # Síntesis neuronal TTS (25 voces) y recepción de audio
│   └── web_server.py       # Servidor HTTP para health-checks y galería de grabaciones
├── datos/                  # Persistencia y estados versionados en JSON (trivias, memorias)
├── docs/                   # Biblioteca central de lore, specs vivas, censo y diseños (Regla §13)
├── herramientas/           # Utilidades, cliente nativo de Discord y scripts de auditoría
├── datos_locales/          # Grabaciones locales temporales, cachés y volcados (gitignored)
└── .agents/chats/          # Memoria operativa de desarrollo (reglas.md, resumen.md, raw/)
```

---

## 🚀 Despliegue e Infraestructura

* **Runtime**: Python 3.12 (Dockerizado sobre Debian con `ffmpeg` y `libopus`).
* **Alojamiento 24/7**: Web Service en **Render Cloud** (Frankfurt, Free Tier) con auto-ping cada 5 min vía `cron-job.org` para evitar suspensión (*spin-down*).
* **Despliegue Manual**: El servicio no autodespliega por git push; se activa con:
  ```powershell
  python herramientas/deploy_render.py
  ```

---

## 📚 Documentación y Enlaces Clave

* **Constitución Operativa**: [.agents/chats/reglas.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/.agents/chats/reglas.md)
* **Histórico y Relevos**: [.agents/chats/resumen.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/.agents/chats/resumen.md)
* **Biblioteca Central de Conocimiento**: [docs/README.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/README.md)
  * [INFO_SERVIDOR.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/INFO_SERVIDOR.md): Censo vivo de canales (49) y roles (73).
  * [PERSONALIDAD_BOT.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/PERSONALIDAD_BOT.md): Tono, directrices canónicas y relaciones.
  * [DISENO_TRAGAPERRAS_PORROS.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/DISENO_TRAGAPERRAS_PORROS.md): Especificación viva de la tragaperras y economía de porros.
  * [DISENO_BOLSA_SANVI.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/DISENO_BOLSA_SANVI.md): Especificación viva del Mercado de Valores de Miembros.

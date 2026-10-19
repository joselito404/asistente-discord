---
trigger: always_on
description: "Reglas de despliegue y alojamiento 24/7 en Render Cloud, supervisor y prevención de spin-down."
---

# Reglas de Despliegue y Alojamiento 24/7 en Render Cloud

> **Ámbito:** Operativa de ejecución continua en la nube, supervisor del proceso y despliegue del bot.

---

## 1. Supervisión Continua contra Caídas
- El proceso principal de Discord debe correr bajo un supervisor persistente (`start_bot_persistent()`) con bucle `while True` para reconectar inmediatamente ante cortes de WebSocket sin terminar el proceso de Python.
- El servidor HTTP en puerto 10000 debe utilizar `ReusableTCPServer` con `allow_reuse_address = True` para responder de inmediato `HTTP 200 OK` al health-check de Render.

---

## 2. Prevención de Suspensión por Inactividad (Anti Spin-Down)
- Mantener un cron job activo en `cron-job.org` configurado con peticiones GET cada **5 minutos exactos** a la URL del Web Service de Render (`https://asistente-discord-sj3k.onrender.com`), superando el umbral de suspensión de 15 minutos del Free Tier.
- Como respaldo secundario, se mantiene activo el workflow automatizado de GitHub Actions.

---

## 3. Despliegue Manual en Render y Obligación de Notificación
- Render **no autodespliega con Git**. Tras enviar cambios a la rama `main` de GitHub, es obligatorio ejecutar `python herramientas/deploy_render.py` (utiliza la clave de Render en `config/config_discord.json`). `[Confirmada · Jose · 10/10/2026]` [Chat 2]
- Si un asistente realiza modificaciones en archivos de `modulos/` o en `bot_service.py`, tiene la obligación de ejecutar el script de deploy o advertir expresamente a Jose de que producción tiene código antiguo pendiente de despliegue.

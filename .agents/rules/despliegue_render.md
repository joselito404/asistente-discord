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

## 3. Despliegue en Render Exclusivamente bajo Permiso Explícito de Jose
- **VETO ESTRICTO A DESPLIEGUES NO AUTORIZADOS:** Queda terminantemente prohibido ejecutar `python herramientas/deploy_render.py` o realizar cualquier despliegue en Render Cloud sin el consentimiento, orden o permiso explícito y previo de Jose en el chat. `[Confirmada · Jose · 25/10/2026]` [Chat 1]
- **Causa Crítica (Persistencia Efímera vs Datos en Caliente):** El contenedor en Render Cloud opera sobre un sistema de archivos efímero que se restablece al código de Git en cada nuevo despliegue. Desplegar sin autorización previa o sin sincronizar los datos locales/remotos sobreescribe y destruye compras de acciones en la bolsa (`datos/bolsa_mercado.json`), transacciones de economía (`datos/economia.json`) y el fondo de dividendos acumulado (`datos/bolsa_pool.json`).
- Si un asistente realiza modificaciones en archivos de `modulos/` o en `bot_service.py`, únicamente debe commitear y pushear a GitHub (si procede) y advertir expresamente a Jose de los cambios pendientes, solicitando su visto bueno antes de tocar el entorno en vivo.

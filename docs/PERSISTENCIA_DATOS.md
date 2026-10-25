# 💾 Arquitectura de Persistencia de Datos en Discord (`docs/PERSISTENCIA_DATOS.md`)

> **Ámbito:** Mecanismo de persistencia distribuida y respaldo continuo para entornos sin disco persistente (Render Cloud Free Tier).  
> **Estado:** `[Aprobado · Jose · 20/10/2026]`  
> **Fuentes de Datos Blindadas:** [`datos/economia.json`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/datos/economia.json) y [`datos/user_memory.json`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/datos/user_memory.json).

---

## 1. Diagnóstico del Problema Técnico en Render Cloud

1. **Entorno Efímero de Render (Free Tier)**:
   - El servicio web en Render (`srv-daqo5rbtqb8s73bbj7l0`) opera bajo el plan gratuito (`plan: free`, `disk: None`).
   - El contenedor Docker ejecuta `COPY . .`, lo que empaqueta los archivos JSON versionados en Git al momento del despliegue.
   - En cada nuevo despliegue manual o reinicio automático por inactividad/mantenimiento de Render, el sistema de archivos del contenedor se destruye y reconstruye desde la imagen base de Git, provocando la **pérdida irreversible** de los datos acumulados en tiempo de ejecución (saldos de Porros, botes de tragaperras, compras en la tienda, carteras de acciones y memorias de usuario).

2. **Requisitos de la Solución**:
   - Coste 0€.
   - Sin dependencias de servicios externos complejos (bases de datos pagas o configuraciones frágiles de tokens de GitHub).
   - Restauración instantánea y determinista al arrancar.
   - Respaldo continuo y en parada controlada sin latencia para el usuario final.

---

## 2. Especificación Técnica de la Solución Aprobada

### 2.1. Canal de Respaldo Privado (`#🔒backup-datos`)
- **Ubicación**: Categoría de Administración / Staff del servidor (`LOS MONGOLOS DEL SANVI Y SUS AMIGOS` - `1446143936891715616`).
- **Permisos**:
  - `@everyone`: Acceso denegado (`view_channel = False`).
  - Rol de Administrador / Jose (`joselito3499`): Acceso completo con lectura y descarga.
  - Bots (`Asistente` y `Economia Asistente`): Permiso de lectura, envío de mensajes y subida de archivos adjuntos.
- Si el canal no existe al iniciar, el bot lo busca por nombre o por ID configurado (`BACKUP_CHANNEL_ID`), o lo crea automáticamente bajo la categoría restringida.

### 2.2. Ciclo de Hidratación al Iniciar (`On-Ready Restore`)
1. Durante el evento `on_ready` de los clientes en [`bot_service.py`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/bot_service.py):
   - El bot accede al canal `#🔒backup-datos` y consulta los últimos mensajes (`history(limit=10)`).
   - Localiza el mensaje más reciente que contenga adjuntos de tipo `.json` (`economia.json` y/o `user_memory.json`).
   - Descarga los bytes vía HTTPS, valida que el JSON sea sintácticamente válido y no esté corrupto, y sobrescribe de forma atómica en disco local (`datos/economia.json` y `datos/user_memory.json`).
   - Si no hay copias previas en el canal, arranca de forma segura con la versión local inicial.
   - Registra en `bot_log` el timestamp y tamaño de la restauración completada con éxito.

### 2.3. Respaldo Cíclico en Tiempo Real (Intervalo: 1 Minuto)
- Un bucle persistente asíncrono (`tasks.loop(minutes=1)`) monitoriza las marcas de modificación (`mtime`) de los archivos clave (`[Confirmada · Jose · 25/10/2026]`).
- Cada **1 minuto**, si se ha producido alguna mutación económica, de bolsa o de memoria, empaqueta los archivos y los envía como adjuntos al canal `#🔒backup-datos` con un mensaje estructurado:
  `📦 Backup Automático • [YYYY-MM-DD HH:MM:SS UTC] • Base: economia.json + user_memory.json + bolsa_mercado.json + bolsa_pool.json...`
- Mantiene limpio el canal purgando o dejando histórico ordenado según conveniencia.

### 2.4. Respaldo Atómico en Apagado Controlado (`Graceful Shutdown`)
- Render envía una señal estándar `SIGTERM` antes de terminar o reciclar un contenedor (dando un margen de gracia de hasta 30 segundos).
- El proceso principal intercepta `signal.SIGTERM` y `signal.SIGINT`:
  1. Detiene nuevas interacciones.
  2. Fuerza la escritura en disco local de cualquier dato en buffer con `save_economy_data()`.
  3. Ejecuta una subida prioritaria y síncrona/bloqueante de última hora a `#🔒backup-datos`:
     `🛑 Backup de Cierre Controlado (SIGTERM/Deploy) • [YYYY-MM-DD HH:MM:SS UTC]`
  4. Cierra limpiamente las conexiones de Discord y termina el proceso.
- Garantiza que **un despliegue manual o redeploy de Render no pierde ni un solo Porro ni acción bursátil**.

---

## 3. Integración con el Módulo de Economía y Bolsa Sanvi

- [`modulos/economia_core.py`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/economia_core.py) delega la sincronización de carga y guardado en este mecanismo.
- Las futuras carteras de la Bolsa Sanvi (`portfolio` de cada usuario dentro de `datos/economia.json`) quedan automáticamente blindadas bajo el mismo paraguas de persistencia sin necesidad de tablas ni bases de datos separadas.

---

## 📋 Registro de Decisiones y Estado Canónico (Compuerta 5 — Regla Global §13)

- [x] Diagnóstico de riesgo en Render Free Tier verificado (`[Aprobado · Jose · 20/10/2026]`).
- [x] Arquitectura de persistencia mediante canal privado de Discord (`#🔒backup-datos`) (`[Aprobado · Jose · 20/10/2026]`).
- [x] Cadencia de respaldo periódico reducida a **1 minuto exacto** ante mutaciones de datos (`[Confirmada · Jose · 25/10/2026]`).
- [x] Interceptación de `SIGTERM`/`SIGINT` para volcado final en despliegues (`[Aprobado · Jose · 20/10/2026]`).
- [x] Inclusión de `datos/user_memory.json`, `bolsa_mercado.json`, `bolsa_pool.json`, `sugerencias.json`, `starboard.json` y `cakey_history.json` junto a `datos/economia.json` en el respaldo (`[Aprobado · Jose · 20/10/2026]`).
- [ ] [Pendiente de matizar: política de retención de mensajes en `#🔒backup-datos` (ej. purgar backups de más de 7 días para no saturar el canal)].

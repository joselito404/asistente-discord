# Lista Única de Pendientes (`docs/pendientes.md`)

> **Regla de origen (Regla Global §21):** Fuente de verdad única de trabajo por hacer, encargos en espera, ideas aparcadas y decisiones que esperan a Jose en `Antigravity-discord`.
> **Gobernanza:** Sincronización obligatoria atómica (§14). Toda tarea completada se retira de este archivo (el historial reside en Git y `.agents/chats/resumen.md`).

---

## 📈 Área 1: Bolsa Sanvi & Aura

### 1.1. Validación Empírica en Vivo de la Bolsa Sanvi y Aura
- **Qué falta:** Probar en canales reales de Discord los nuevos comandos `/bolsa [ticker]`, `/cartera` y `/aura`, verificando el renderizado de gráficas Pillow, modales interactivos de compra/venta y bonificación pasiva en `/trabajar`.
- **Por qué importa:** Confirmar la experiencia de usuario y verificar la paridad con Trading 212 en vivo.
- **Siguiente paso:** Feedback de Jose tras interactuar con la terminal en Discord.
- **Responsable:** Jose / Chat 1.
- **Estado:** `en espera de Jose`.
- **Detalle:** [docs/DISENO_BOLSA_SANVI.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/DISENO_BOLSA_SANVI.md) y [modulos/bolsa_sanvi.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/bolsa_sanvi.py).

---

## 🧠 Área 2: Inteligencia Contextual, Lectura Real de Documentos y Acceso Profundo al Servidor

### 2.1. Mejora de Inteligencia del Bot, Lectura Nativa de Google Docs y Acceso Multi-Canal al Servidor
- **Qué falta:**
  1. **Lectura real de Google Docs y enlaces en el historial reciente:** Cuando un usuario comparta un enlace de Google Docs (`docs.google.com/document/d/<ID>/...`), transformar la URL al endpoint de exportación en texto plano (`/export?format=txt`, soportando pestañas `tab=`) para extraer el contenido íntegro real en vez de solo la cabecera HTML/OpenGraph, y mantener ese contenido accesible en los turnos siguientes de la conversación (no solo en el mensaje donde se pegó el link).
  2. **Mayor acceso a mensajes, pins y lectura transversal del servidor:** Ampliar la capacidad de `modulos/chat_ia.py` para consultar mensajes fijados (pins) e historial reciente de cualquier canal relevante del servidor (como `#cultura`, `#el-tribunal-gaming`, `#la-shit-de-todos-los-dias`, etc.) aunque la pregunta se haga desde otro canal (ej. `#🛠️apps-solo-mods🛠️`), evitando que el bot invente o alucine títulos (como ocurrió al preguntar por el Top 1 de manhwas de la Tier List de Joselito).
  3. **Resiliencia de cuota y prohibición de alucinar datos no leídos:** Reforzar los reintentos/modelos para evitar mensajes de `"Cuota de IA temporalmente saturada"` en preguntas seguidas y prohibir que el modelo invente el contenido de un documento o mensaje si no lo tiene delante.
- **Por qué importa:** Evita que `Asistente` finja haber leído un documento o canal e invente respuestas genéricas (como citar *Solo Leveling* u *ORV* al azar cuando le preguntan por el Top 1 real de la Tier List de Joselito), dotándolo de comprensión real del servidor y de los enlaces compartidos.
- **Siguiente paso:** Diseñar e implementar en `modulos/chat_ia.py` el extractor nativo de Google Docs (`/export?format=txt`), la persistencia de enlaces en el contexto reciente del canal y el buscador transversal de mensajes/pins entre canales del servidor.
- **Responsable:** Chat 3 / Especialista de Código.
- **Estado:** `por hacer`.
- **Detalle:** [modulos/chat_ia.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/chat_ia.py) y [docs/PERSONALIDAD_BOT.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/PERSONALIDAD_BOT.md).



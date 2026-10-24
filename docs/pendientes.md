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

## 🤖 Área 2: Chat IA y Personalidad de Asistente

### 2.1. Capacidad de Reaccionar con Emojis a Mensajes de Usuarios
- **Qué falta:** Implementar en `modulos/chat_ia.py` la capacidad de que Asistente añada reacciones (`message.add_reaction`) a los mensajes a los que responde o en conversaciones del servidor, según el tono emocional, sarcástico o cómplice (ej. `🤔`, `💀`, `😂`, `❤️` o emojis personalizados del servidor).
- **Por qué importa:** Incrementa el dinamismo, la expresividad visual y el realismo de Asistente como colega y bot conversacional (emulando comportamientos como el de MAID mostrado por Jose).
- **Siguiente paso:** Diseñar la detección de reacción en el flujo de `chat_ia.py` (mediante directriz en `SYSTEM_PROMPT` con etiqueta parseable como `[REACCION: :emoji:]` o extracción heurística), implementar los tests unitarios correspondientes y desplegar a Render.
- **Responsable:** Chat 3 / Especialista de Código.
- **Estado:** `por hacer`.
- **Detalle:** [docs/PERSONALIDAD_BOT.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/PERSONALIDAD_BOT.md) y [modulos/chat_ia.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/chat_ia.py).

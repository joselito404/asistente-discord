# Lista Única de Pendientes (`docs/pendientes.md`)

> **Regla de origen (Regla Global §21):** Fuente de verdad única de trabajo por hacer, encargos en espera, ideas aparcadas y decisiones que esperan a Jose en `Antigravity-discord`.
> **Gobernanza:** Sincronización obligatoria atómica (§14). Toda tarea completada se retira de este archivo (el historial reside en Git y `.agents/chats/resumen.md`).

---

## 📰 Área 1: Servidor & Dinámicas Comunitarias

### 1.1. The Sanvi Daily / Starboard Gráfico (Reemplazo Integral de Carl-bot)
- **Qué falta:** Diseñar e implementar el nuevo Starboard nativo que reemplaza a Carl-bot en `#⭐muro-de-la-fama⭐` (`1548043919827271740`). Al alcanzar 2 reacciones de estrella (⭐), el bot genera con Pillow una portada vintage de periódico (*The Sanvi Daily* / *Gaceta de los Mongolos*) con el mensaje inmortalizado, autor, avatar, titulares cómicos y fecha, con embed estilizado y enlace al mensaje original.
- **Por qué importa:** Erradica la última gran dependencia de Carl-bot en el servidor y eleva radicalmente el nivel estético y el humor comunitario frente a los mensajes planos de Carl-bot.
- **Siguiente paso:** Consolidar la especificación canónica en `docs/DISENO_SANVI_DAILY.md` y consensuar parámetros de diseño con Jose antes de delegar código a `especialista-codigo`.
- **Responsable:** Chat / Jose.
- **Estado:** `en curso`.
- **Detalle:** [docs/DISENO_SANVI_DAILY.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/DISENO_SANVI_DAILY.md).

---

## 📈 Área 2: Bolsa Sanvi & Aura

### 2.1. Validación Empírica en Vivo de la Bolsa Sanvi y Aura
- **Qué falta:** Probar en canales reales de Discord los nuevos comandos `/bolsa [ticker]`, `/cartera` y `/aura`, verificando el renderizado de gráficas Pillow, modales interactivos de compra/venta y bonificación pasiva en `/trabajar`.
- **Por qué importa:** Confirmar la experiencia de usuario y verificar la paridad con Trading 212 en vivo.
- **Siguiente paso:** Feedback de Jose tras interactuar con la terminal en Discord.
- **Responsable:** Jose / Chat 1.
- **Estado:** `en espera de Jose`.
- **Detalle:** [docs/DISENO_BOLSA_SANVI.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/DISENO_BOLSA_SANVI.md) y [modulos/bolsa_sanvi.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/bolsa_sanvi.py).


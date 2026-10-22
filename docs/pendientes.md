# Lista Única de Pendientes (`docs/pendientes.md`)

> **Regla de origen (Regla Global §21):** Fuente de verdad única de trabajo por hacer, encargos en espera, ideas aparcadas y decisiones que esperan a Jose en `Antigravity-discord`.
> **Gobernanza:** Sincronización obligatoria atómica (§14). Toda tarea completada se retira de este archivo (el historial reside en Git y `.agents/chats/resumen.md`).

---

## 🏛️ Área 1: Servidor & Operativa en Discord

### 1.1. Retirada Manual de UnbelievaBoat
- **Qué falta:** Expulsar o retirar al bot `UnbelievaBoat` del servidor de Discord `LOS MONGOLOS DEL SANVI Y SUS AMIGOS`.
- **Por qué importa:** La economía nativa y casino propio de `@Economia Asistente` (42 comandos en total) ya está desplegada al 100% en producción y sustituye todas sus funciones. La retirada de UnbelievaBoat evita duplicidad de comandos y confusión en los canales.
- **Siguiente paso:** Jose ejecuta la expulsión manual desde los ajustes de miembros de Discord (por directriz de seguridad en `.agents/rules/seguridad_credenciales.md` §2, los bots tienen estrictamente prohibido ejecutar `kick` o `ban`).
- **Responsable:** Jose.
- **Estado:** `en espera de Jose`.
- **Detalle:** [docs/DISENO_ECONOMIA_NATIVA.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/DISENO_ECONOMIA_NATIVA.md#L1).

---

## 🎰 Área 2: Casino & Economía Nativa

### 2.1. Validación Empírica en Vivo de la Tragaperras 5x3 Limpia
- **Qué falta:** Probar tiradas reales en Discord de la nueva geometría (3 Horizontales: Línea Arriba, Línea Centro, Línea Abajo; 6 Diagonales rectas de 3 casillas; sin Scatters y nombres limpios sin prefijos de código).
- **Por qué importa:** Verificar que la experiencia visual de los miembros sea intuitiva y sin ambigüedades tras el despliegue del commit `d8d69aa`.
- **Siguiente paso:** Feedback de Jose tras interactuar con `/slots` en `#🎰casino-y-apuestas🎰` o `#🎰casino-y-apuestas-2🎰`.
- **Responsable:** Jose / Chat.
- **Estado:** `en espera de Jose`.
- **Detalle:** [docs/DISENO_ECONOMIA_NATIVA.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/DISENO_ECONOMIA_NATIVA.md#L168-L192) y [modulos/casino_slots.py](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/modulos/casino_slots.py).

---

## ⚙️ Área 3: Entorno y Gobernanza Modular

### 3.1. Creación de Módulo Declarativo `harness_claudecode.md`
- **Qué falta:** Añadir `.agents/rules/harness_claudecode.md` con cabecera `trigger: model_decision` y descripción indicando «SOLO para Claude Code».
- **Por qué importa:** Completar la separación simétrica por entorno prescrita en `AGENTS_CORE.md` §7, asegurando que Claude Code disponga de su harness declarado si se abre sesión desde dicho CLI.
- **Siguiente paso:** Crear el archivo atómico en `.agents/rules/` e indexarlo en `.agents/rules/README.md`.
- **Responsable:** Chat.
- **Estado:** `por hacer`.
- **Detalle:** `AGENTS_CORE.md` §7 y `.agents/rules/harness_antigravity.md`.

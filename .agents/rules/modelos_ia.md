---
trigger: always_on
description: "Reglas técnicas de modelos de IA, generación FLUX.1 libre y Circuit Breaker de fallbacks."
---

# Reglas Técnicas de Modelos de IA (Gemini & FLUX.1)

> **Ámbito:** Integración de LLMs, síntesis visual y optimización de costes/tokens.

---

## 1. Generación de Imágenes a Coste 0€ (FLUX.1)
- Los modelos de imagen nativos de Google (`gemini-2.5-flash-image`, `imagen-3.0`) tienen cuota cero (`limit: 0`) en el Free Tier; requieren facturación de pago en Google Cloud.
- Para generación ilimitada y gratuita de imágenes a 1024x1024, se utiliza exclusivamente el clúster libre de difusión **FLUX.1** vía Pollinations con optimizador de prompts en inglés (`enhance_image_prompt`).
- Cada imagen generada debe incluir el componente interactivo `ImageActionView` con el botón `[🔄 Re-roll]` para permitir a los usuarios regenerar con nueva semilla sin escribir nada.
- El bot nunca debe simular imágenes en texto plano si no acompaña la acción real de renderizado.

---

## 2. Modelos de Texto y Circuit Breaker
- Priorizar la cascada configurada en `MODELS_PRIORITY` (`gemini-flash-lite-latest`, `gemini-3.5-flash-lite`, etc.) como modelos principales para chat conversacional por su velocidad (<0,8s) y alta cuota en Free Tier.
- Implementar siempre el **Circuit Breaker Inteligente**: cualquier modelo que arroje error HTTP 429 o 503 entra en cooldown de **60 segundos** en memoria (`mark_model_cooldown`), conmutando al instante al siguiente modelo de respaldo.
- **Veto a Modelos Gratuitos en Tareas Críticas:** Tareas con alto riesgo de alucinación o que exijan juicio complejo (ej. juicios en directo de El Tribunal Gaming, balance matemático de economía/TCG) quedan estrictamente vetadas para modelos lite autónomos. Deben ejecutarse en sesiones supervisadas con modelos de alta capacidad. `[Confirmada · Jose · 18/10/2026]` [Chat 1]

---

## 3. Gestión y Compresión de Tokens
- Inyección selectiva de contexto: censos amplios de miembros y mensajes fijados solo se deben inyectar al prompt si el usuario pregunta explícitamente por miembros, roles, el staff o recomendaciones.

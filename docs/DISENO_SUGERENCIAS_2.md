# 💡 Especificación de Diseño Vivo: Sugerencias 2.0 (Fin de Carl-bot)

> **Documento de Diseño y Especificación Técnica Viva**: Define la arquitectura completa, experiencia de usuario, interfaz interactiva Discord V2, integración de IA (Gemini), persistencia y moderación de `#💡sugerencias💡` en *"LOS MONGOLOS DEL SANVI Y SUS AMIGOS"*.
> **Regla de origen**: Cumple con la Regla Global §13 y §14. Reemplaza definitivamente cualquier función remanente de Carl-bot en el canal de sugerencias.

---

## 1. 🎯 Objetivos y Principios del Sistema

1. **Reemplazo Integral de Carl-bot**: Erradicar los comandos y embeds antiguos de Carl-bot. Todas las propuestas se gestionan de forma nativa por el bot principal `@Asistente`.
2. **Interacción Limpia vía Modales y Botones**: Los miembros no necesitan recordar sintaxis de comandos; un panel fijado con el botón `[💡 Proponer Idea]` y el comando slash `/sugerencia` abren un modal nativo de Discord con campos estructurados.
3. **Debate Ordenado en Hilos Automáticos**: Cada sugerencia aprobada para votación crea en el acto un hilo de discusión dedicado (`💡 Sugerencia #X - Titulo`) para concentrar el debate sin saturar el canal principal.
4. **Retroalimentación Visual Inmediata**: Barra de progreso dinámica generada con bloques emoji (`🟩🟩🟩🟩🟥🟥 67% A favor • 14 votos`), recalculada en vivo con cada voto y guardada en persistencia.
5. **Veredicto Sarcástico con IA (Gemini)**: Botón interactivo `[🧠 Veredicto de Asistente]` que genera un análisis satírico, humorístico y crítico sobre la viabilidad de la propuesta, publicado de forma abierta en el hilo de debate.
6. **Resolución Ejecutiva del Staff**: Botones directos `[✅ Aprobar]` y `[❌ Descartar]` para Jose y los administradores con modal de fundamentación y archivo automático del hilo tras la resolución.

---

## 2. 🏛️ Estructura y Flujo de Usuario

```
[Miembro pulsa botón o usa /sugerencia]
                 │
                 ▼
     [Modal Nativo de Discord]
     • Título / Idea corta (máx 80 caracteres)
     • Categoría (Servidor, Juegos, Bots, Ocio/Memes)
     • Explicación / Por qué beneficia al servidor (máx 1000 caracteres)
                 │
                 ▼
[Publicación de Tarjeta Viva en #💡sugerencias💡]
     • Embed coloreado con barra dinámica [🟩🟩🟩🟥🟥]
     • Componentes: [👍 Me mola (X)] [👎 Ni de coña (Y)] [🧠 Veredicto de Asistente]
     • Botones Staff (Admin): [✅ Aprobar] [❌ Descartar]
                 │
                 ▼
[Apertura Automática de Hilo de Debate]
     • Nombre: "💡 Sugerencia #X - <Título>"
     • Mensaje de bienvenida fijado en el hilo
                 │
                 ▼
[Interacción Comunitaria & Veredicto IA]
     • Votantes únicos (toggle/conmutación de voto)
     • Clic en [🧠 Veredicto] -> Análisis satírico de Gemini publicado en el hilo
                 │
                 ▼
[Resolución Staff (Jose / Admin)]
     • Modal de motivo de aprobación/descarte
     • Embed pasa a Verde (Aprobada) o Rojo (Descartada)
     • Botones de voto se congelan
     • Hilo de debate se cierra con mensaje final
```

---

## 3. 🎨 Componentes Visuales y Formatos

### 3.1. Panel Fijado de Bienvenida (`/panel_sugerencias`)
- **Canal de destino**: `#💡sugerencias💡` (ID: `1537582722812481696`).
- **Embed**:
  - Título: `💡 Buzón Comunitario de Sugerencias — Los Mongolos del Sanvi`
  - Descripción: Normas de convivencia para proponer ideas (nada de troleos absurdos, propuestas constructivas para canales, bots, eventos o juegos).
  - Botón: `[💡 Proponer Idea]` (verde o primario).

### 3.2. Modal Nativo (`SuggestionSubmitModal`)
1. **Título de la Propuesta**: `TextInput` corto (máx 80 car.), requerido.
2. **Categoría**: `TextInput` corto con placeholder `Servidor / Juegos / Bots / Ocio`, requerido.
3. **Descripción Detallada**: `TextInput` párrafo (máx 1000 car.), donde se explica la idea y el beneficio.

### 3.3. Tarjeta Viva de Votación (`build_suggestion_embed`)
- **Colores de Embed**:
  - `0x3B82F6` (Azul): En votación comunitaria.
  - `0x22C55E` (Verde): Aprobada por el staff.
  - `0xEF4444` (Rojo): Rechazada / Descartada por el staff.
- **Barra de Progreso Dinámica**:
  - Calculada en base a 10 bloques de color:
    $$\text{pct\_up} = \frac{\text{up}}{\text{up} + \text{down}} \times 100$$
  - Representación visual: `🟩🟩🟩🟩🟩🟩🟥🟥🟥🟥 60% A favor (6 👍 / 4 👎)`
  - Si no hay votos: `⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0 votos emitidos`.
- **Campos del Embed**:
  - `📁 Categoría`: Categoría introducida por el autor.
  - `📊 Estado`: `⏳ En votación comunitaria` | `✅ Aprobada` | `❌ Descartada`.
  - `🗳️ Votos`: Barra de progreso + desglose numérico y lista resumida de votantes (`👍: @Jose, @Ivan...`).
  - Si fue resuelta: Campo `⚖️ Decisión del Staff` con el autor de la resolución y el comentario/motivo.

### 3.4. Veredicto Satírico de Asistente con IA
- Prompt especializado inyectado a Gemini:
  - Tono: Canónico de Asistente (colega sarcástico, pragmático, que no se muerde la lengua pero evalúa con lucidez si la idea es factible o si es una fumada que romperá el servidor).
  - Publicación: Mensaje en el hilo automático de debate (`💡 Sugerencia #X`).
  - Cacheo: El veredicto generado se almacena en el JSON de la sugerencia; si otro usuario pulsa el botón posteriormente, se muestra el mismo veredicto sin gastar cuota de API.

---

## 4. 💾 Persistencia de Datos (`datos/sugerencias.json`)

Para evitar la pérdida de votos tras despliegues en Render Cloud, los datos se persisten bajo cerrojo asíncrono (`SUGGESTIONS_LOCK`):
```json
{
  "next_suggestion_id": 9,
  "suggestions": {
    "1537582722812481696_1234567890": {
      "id": 9,
      "message_id": 1234567890,
      "channel_id": 1537582722812481696,
      "thread_id": 1234567891,
      "author_id": 484391484196880406,
      "author_name": "Jose",
      "author_avatar": "https://cdn.discordapp.com/...",
      "title": "Añadir rol de pescador",
      "category": "Juegos",
      "description": "Propongo que pongamos un minijuego de pesca...",
      "created_at": "2026-10-22T16:00:00Z",
      "status": "voting",
      "up_votes": [484391484196880406],
      "down_votes": [],
      "ai_verdict": null,
      "resolved_by_id": null,
      "resolved_by_name": null,
      "resolution_reason": null,
      "resolved_at": null
    }
  }
}
```

---

## 5. 🛠️ Comandos y Permisos

1. `/sugerencia` (`cmd_sugerencia`):
   - Abre directamente el modal nativo `SuggestionSubmitModal`.
   - Disponible para cualquier miembro en cualquier canal (o restringido efímeramente si no es en el servidor).
2. `/panel_sugerencias` (`cmd_panel_sugerencias`):
   - Publica el embed maestro 24/7 con el botón `[💡 Proponer Idea]`.
   - Permiso: Solo Administradores (`guild_permissions.administrator`).
3. Botones interactivos en cada sugerencia:
   - `[👍 Me mola]`: Conmuta voto a favor (si ya votó 👍, lo retira; si votó 👎, lo cambia).
   - `[👎 Ni de coña]`: Conmuta voto en contra.
   - `[🧠 Veredicto de Asistente]`: Llama a Gemini y responde en el hilo.
   - `[✅ Aprobar]` / `[❌ Descartar]`: Solo para miembros con rol de Administrador o Moderador. Abre `SuggestionDecisionModal`.

---

## 6. 📋 Registro de Decisiones y Estado Canónico

> **Compuerta 5 de la Regla Global §13**: Lista de verificación obligatoria de estado canónico.

- [x] **Canal canónico de sugerencias**: `#💡sugerencias💡` (`1537582722812481696`) `[Confirmada · Jose · 22/10/2026]`.
- [x] **Modal nativo con campos limpios**: Título, Categoría y Explicación `[Confirmada · Jose · 22/10/2026]`.
- [x] **Apertura de hilos automáticos de debate**: Sí, cada propuesta abre un hilo `💡 Sugerencia #X - Titulo` para debate ordenado `[Confirmada · Jose · 22/10/2026]`.
- [x] **Veredicto con IA (Gemini)**: Publicación abierta en el hilo de la sugerencia con análisis satírico y cacheo en JSON `[Confirmada · Jose · 22/10/2026]`.
- [x] **Barra de progreso visual**: Barra dinámica de 10 bloques `🟩` / `🟥` con porcentajes `[Confirmada · Jose · 22/10/2026]`.
- [x] **Resolución administrativa**: Botones exclusivos de staff con modal de motivo `[Confirmada · Jose · 22/10/2026]`.
- [x] **Módulo de código aislado**: `modulos/sugerencias.py` separado de `autoroles.py` `[Confirmada · Jose · 22/10/2026]`.

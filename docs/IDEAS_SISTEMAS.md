# 💡 Catálogo de Ideas y Sistemas Futuros para Asistente

> **Documento de Diseño y Roadmap**: Recopilación exhaustiva de los sistemas exclusivos diseñados para transformar la interacción, la economía y la cultura del servidor *"LOS MONGOLOS DEL SANVI Y SUS AMIGOS"*, alejándose de clones genéricos y aprovechando las capacidades nativas de Asistente (IA, generación gráfica en tiempo real con Pillow/FLUX.1, componentes interactivos de Discord V2 y voz).

---

## 🗺️ Fases y Orden de Ejecución Acordado

```
[Inmediato] ──────────► [Fase 1] ───────────────► [Fase 2] ──────────────► [Fase 3] ────────────────► [Sesiones Especiales]
Ampliación de            Sugerencias 2.0           The Sanvi Daily           Bolsa Sanvi /             Tribunal 2.0 en Vivo
Auto-Roles (#roles)      (Fin de Carl-bot)         (Starboard Gráfico)       Aura Market (50/50)       y Sanvi TCG (Gama Alta)
```

---

## 1. 📈 Mercado de Valores de Miembros ("Bolsa Sanvi" / Aura Market)

- **Estado**: **Aprobado con entusiasmo** (*"ME MOLA BASTISIMO"*). Prioridad alta.
- **Canal de destino sugerido**: `#🎰casino-y-apuestas` o nuevo `#📈bolsa-sanvi📈`.
- **Concepto**: Cada miembro activo del servidor cuenta con su propia acción cotizada en el mercado ficticio del servidor (ej. `$JOSE`, `$IVAN`, `$OMEN`, `$TERRE`, etc.).
- **Fórmula de Cotización Híbrida y Realista (Aprobada por Jose)**:
  El precio de la acción no es arbitrario; se rige por un modelo ponderado:
  $$\text{Precio} = (w_{\text{aura}} \cdot \text{Valor Fundamental}) + (w_{\text{mercado}} \cdot \text{Presión de Mercado})$$
  - **50% - 67% Valor Fundamental (Aura)**: Basado en el baremo oficial de [docs/AURA_BAREMO.md](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/AURA_BAREMO.md). Computa constancia, respuestas recibidas, celebraciones comunitarias, momentos épicos de juego (+puntos) o troleos/plantones (-puntos).
  - **33% - 50% Presión de Mercado (Oferta y Demanda Real)**: Las compras masivas de los usuarios retiran títulos del mercado y elevan el precio; las ventas masivas o *dumps* provocan caídas inmediatas en la cotización.
- **Mecánicas e Interfaz**:
  - **Operativa**: Comandos y botones para comprar (`/bolsa comprar [ticker] [cantidad]`) o vender (`/bolsa vender`), transaccionando con porros/monedas del bot.
  - **Visualización Gráfica**: Generación dinámica con **Pillow** de tarjetas gráficas con gráficos de línea/velas que muestran la evolución histórica del valor de cada colega.
  - **Dividendos / Splits**: Si un usuario tiene un logro legendario en el servidor, su acción puede repartir dividendos a sus accionistas.

---

## 2. 💡 Sugerencias 2.0 (Reemplazo Total de Carl-bot en `#💡sugerencias💡`)

- **Estado**: **Aprobado** (*"vamos por orden"*). Siguiente desarrollo tras autoroles.
- **Canal de destino**: `#💡sugerencias💡`.
- **Objetivo**: Desterrar por completo el último rastro de Carl-bot en el servidor sustituyendo sus embeds grises por un sistema nativo interactivo.
- **Mecánicas e Interfaz**:
  - **Panel Fijado con Botón**: Un único mensaje en el canal con el botón `[💡 Proponer Idea]`.
  - **Modal Nativo de Discord**: Al pulsar el botón se abre una ventana modal con campos limpios:
    - *Título de la Propuesta*
    - *Descripción / Motivo*
    - *Categoría* (Servidor / Juegos / Bots y Canales / Memes y Ocio)
  - **Tarjeta de Votación Viva**: Al enviar la propuesta, se publica una tarjeta con:
    - Botones de voto: `[👍 Me mola]` y `[👎 Ni de coña]`.
    - **Barra de Progreso Dinámica**: Actualización en vivo del porcentaje de apoyo comunitario (`🟩🟩🟩🟩🟥🟥 67% A favor • 14 votos`) recalculada con cada clic.
    - Botón `[🧠 Veredicto de Asistente]`: Petición bajo demanda a Gemini que analiza con humor ácido la viabilidad o sensatez de la sugerencia sin generar spam.
  - **Gestión de Staff**: Botones exclusivos para Jose/Admin de `[✅ Aprobar]` o `[❌ Descartar]`.

---

## 3. 📰 The Sanvi Daily / Starboard Gráfico (Evolución de `#⭐muro-de-la-fama⭐`)

- **Estado**: **Aprobado** (*"Me parece increible esta tambien, apuntala"*).
- **Canal de destino**: `#⭐muro-de-la-fama⭐`.
- **Problema Actual**: El Starboard clásico se limita a reenviar un embed plano de texto cuando un mensaje alcanza 2 reacciones de `⭐`.
- **Mecánicas e Interfaz**:
  - **Renderizado Gráfico con Pillow**: Al alcanzar el umbral de 2 estrellas (excluyendo autoestrellas), Asistente genera una imagen PNG completa con estética de **portada de periódico sensacionalista vintage** (*"The Sanvi Daily"*).
  - **Contenido del Periódico**:
    - Cabecera clásica de prensa con fecha del día y edición especial.
    - Avatar del autor enmarcado como "sospechoso" o "protagonista".
    - Titular cómico y llamativo generado automáticamente a partir del contexto del mensaje.
    - Cita textual íntegra del mensaje o imagen incrustada.
  - **Resultado**: Archivo gráfico atractivo y coleccionable que los miembros guardan y comparten.

---

## 4. ⚖️ El Tribunal Gaming 2.0 (Juicios en Directo con Juez IA y Jurado Popular)

- **Estado**: **Aprobado con reserva técnica** (*"los modelos gratuitos alucinarían; reservado para sesiones conmigo encendido leyendo todo"*).
- **Canal de destino**: `#🥊violencia🥊` o hilo dedicado.
- **Concepto**: Llevar `/tribunal` de ser una lista fija de juegos a un sistema de arbitraje de disputas reales entre miembros de la comunidad.
- **Requisitos Técnicos**:
  - No usar modelos gratuitos pequeños (tipo flash-lite) para evitar alucinaciones en acusaciones complejas.
  - Ejecutar durante sesiones supervisadas o con agentes de alta capacidad (Antigravity / Claude Code) actuando como orquestador y Juez en tiempo real.
- **Mecánicas**:
  - **Apertura de Juicio**: Un miembro sienta en el banquillo a otro (`/juicio demandar a:@usuario motivo:... pruebas:...`).
  - **Asistente como Juez / Fiscal**: Analiza las pruebas con tono sarcástico y redacta el auto de acusación formal.
  - **Jurado Popular en Vivo**: Los demás miembros votan durante 15 minutos mediante botones `[Culpable]` o `[Inocente]`.
  - **Condenas Cómicas**:
    - Roles temporales deshonrosos de 2 horas (ej. `🚨 Troleador Confeso`).
    - Pérdida de títulos o multas en porros.
    - Entrada en llamada de voz con TTS para leer la sentencia con sonido de mazo si los implicados están en un canal de voz.

---

## 5. 🃏 Sanvi TCG / Cartas Coleccionables de la Comunidad

- **Estado**: **Aprobado para fase avanzada** (*"crearla con modelos más potentes, los gratuitos son basura, buena idea pero más difícil"*).
- **Concepto**: Juego de cartas coleccionables donde cada miembro del servidor, meme recurrente, hazaña o momento vergonzoso se convierte en una carta coleccionable con arte estilizado.
- **Requisitos Técnicos**:
  - Generación de arte con modelos de imagen de alta fidelidad (FLUX.1 optimizado o modelos de pago en sesiones dedicadas).
  - Generación de estadísticas coherentes y descripciones sin clichés.
- **Mecánicas**:
  - **Niveles de Rareza**: Común, Rara, Épica, Legendaria y Mítica.
  - **Stats de Juego**: *Troleo*, *Carisma*, *Puntería*, *Puntualidad* y *Habilidad Especial*.
  - **Comando `/sobre`**: Apertura diaria con animación y visualización en Canvas de las 3 cartas obtenidas.
  - **Intercambio / Trade**: Menú interactivo entre dos usuarios para cambiar repetidas.

---

## 6. 🎮 Radar de Vicio / Lobbies Interactivos ("¿Quién Juega?")

- **Estado**: Propuesta complementaria para la Zona Gaming.
- **Canal de destino**: `#🎮gaming-general🎮`.
- **Mecánicas**:
  - En lugar de pings masivos que molestan, comando `/lobby [juego] [plazas]`.
  - Genera una tarjeta visual con ranuras disponibles: `[👑 Jose] [👤 Hueco 2] [👤 Hueco 3] [👤 Hueco 4]`.
  - Botones directos `[🎮 Unirme]` y `[❌ Salir]`.
  - Al completarse el squad, notificación automática privada a los integrantes con enlace directo a la llamada de voz.

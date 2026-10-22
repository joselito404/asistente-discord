# Especificación Técnica: The Sanvi Daily / Starboard Gráfico 2.0

> **Propósito:** Reemplazo integral del Starboard de Carl-bot en `#⭐muro-de-la-fama⭐` (`1548043919827271740`) transformando mensajes célebres en portadas de periódico vintage (*The Sanvi Daily* / *Gaceta de los Mongolos*) generadas en tiempo real con Pillow.
> **Origen:** `[Confirmada · Jose · 22/10/2026]` tras comentarios en `docs/pendientes.md`.
> **Estado:** `en curso`.

---

## 1. Arquitectura y Reemplazo de Carl-bot

### 1.1. Contexto y Objetivos
1. **Erradicación definitiva de Carl-bot:** Carl-bot solo publica embeds simples de texto plano cuando un mensaje alcanza 2 estrellas. Al desactivar o ignorar el starboard de Carl-bot, Asistente asume el 100% de la funcionalidad con valor artístico diferencial.
2. **Generación Gráfica con Pillow (Zero Coste de Tokens):** Cada edición se renderiza localmente con Pillow en milisegundos mediante una plantilla de periódico vintage en tonos sepia/papiro, titular sensacionalista y foto de portada.
3. **Idempotencia y Edición Reactiva:** Si un mensaje sube de 2 a 3, 4 o 10 estrellas, no se genera una nueva publicación: se edita el mensaje existente en `#⭐muro-de-la-fama⭐` actualizando el contador y la cabecera.

---

## 2. Parámetros y Mecánicas Canónicas

### 2.1. Reglas de Activación
* **Canal destino:** `#⭐muro-de-la-fama⭐` (ID `1548043919827271740`).
* **Emoji disparador:** `⭐` (`\u2b50`).
* **Umbral mínimo:** **2 estrellas** (`[Confirmada · Jose · 22/10/2026]`).
* **Anti-Autobombo:** Las reacciones de estrella del propio autor del mensaje quedan estrictamente excluidas del cómputo de las 2 estrellas (`[Confirmada · Jose · 22/10/2026]`).
* **Filtro de canales excluidos:**
  * `#⭐muro-de-la-fama⭐` (para evitar bucles recursivos).
  * Canales privados de Staff/Administración (`#🔒backup-datos`, `#🛠️apps-solo-mods🛠️`, `#🔒staff-sanvi🔒`).

---

## 3. Motor de Renderizado Gráfico (Pillow)

### 3.1. Dimensiones y Estilo Visual
* **Dimensiones del periódico:** 800 x 1000 px.
* **Paleta cromática vintage:**
  * Fondo: Papel envejecido / pergamino (`#F4EEDD` / `#EADBB6`).
  * Tinta principal: Negro carboncillo desgastado (`#1C1917`).
  * Acentos y filetes: Tinta sepia oscura (`#44382A`) y líneas dobles de rotativo clásico.
* **Estructura de la Portada:**
  1. **Cabecera de Periódico:**
     * Título principal: **THE SANVI DAILY** (`[Confirmada · Jose · 22/10/2026]`).
     * Lema inferior: *"La verdad duele, pero las capturas duelen más"* / *"Edición Histórica Comunitaria"*.
     * Cintillo superior: Fecha de edición (UTC) • Edición Nº correlativa • Precio simbólico *"Gratis con 2 estrellas"*.
  2. **Sección Titular y Noticia:**
     * Avatar del autor enmarcado con textura de semitono o marco clásico.
     * Titular principal en mayúsculas tipográficas.
     * Cuerpo del mensaje formateado en columnas de rotativo o caja destacada con comillas de cita de prensa.
  3. **Incrustación de Imágenes Adjuntas:**
     * Si el mensaje original adjuntaba una foto, se procesa en semitono / sepia monocromo y se incrusta en el recuadro central como *"Fotografía exclusiva del lugar de los hechos"*.
  4. **Pie de Rotativo:**
     * Firma: *"Archivo oficial de Los Mongolos del Sanvi • Inmortalizado por la comunidad"*.
     * Sello de cera o tampón circular: *"APROBADO POR EL PUEBLO • ⭐ 2"*.

---

## 4. Persistencia y Control de Duplicados

### 4.1. Esquema de Datos (`datos/starboard.json`)
```json
{
  "next_edition_number": 1,
  "entries": {
    "1537574896605265970_1234567890": {
      "edition_number": 1,
      "orig_channel_id": 1537574896605265970,
      "orig_message_id": 1234567890,
      "starboard_message_id": 9876543210,
      "author_id": 1170704124631846993,
      "author_name": "joselito3499",
      "stars_count": 2,
      "stargazers": [123456, 789012],
      "created_at": "2026-10-22T20:45:00+00:00",
      "has_image": true
    }
  }
}
```

### 4.2. Comportamiento Reactivo (`on_raw_reaction_add` / `remove`)
* **Subida de estrellas ($\ge 2$):** Si ya existe en `datos/starboard.json`, actualiza `stars_count` y edita el mensaje en Discord (actualizando el embed/botón con el nuevo recuento: ej. `⭐ 3`, `⭐ 5`).
* **Permanencia irrevocable ante bajada de estrellas ($< 2$):** Una vez que un mensaje alcanza el umbral de 2 estrellas y se imprime la portada, permanece en `#⭐muro-de-la-fama⭐` para siempre, incluso si los usuarios retiran sus reacciones (`[Confirmada · Jose · 22/10/2026]`).

---

## 5. Componentes de Interfaz Discord V2

* **Embed Dorado (`0xF59E0B`):**
  * Título: `⭐ #{edición} | Portada de The Sanvi Daily`
  * Autor: `Enviado por {autor} en #{canal}`
  * Imagen: Archivo adjunto `sanvi_daily_{edicion}.png`.
* **Botón de Enlace Directo:**
  * Componente `discord.ui.Button` con URL directa al mensaje original (`https://discord.com/channels/{guild_id}/{channel_id}/{message_id}`).

---

## 6. Registro de Decisiones y Estado Canónico

- [x] **Canal canónico de publicación:** `#⭐muro-de-la-fama⭐` (`1548043919827271740`) `[Confirmada · Jose · 22/10/2026]`.
- [x] **Umbral mínimo de estrellas:** 2 reacciones de `⭐` `[Confirmada · Jose · 22/10/2026]`.
- [x] **Renderizado gráfico con Pillow:** Portada estilo periódico vintage (*The Sanvi Daily*) a coste 0€ de tokens `[Confirmada · Jose · 22/10/2026]`.
- [x] **Persistencia e Idempotencia:** `datos/starboard.json` respaldado en `#🔒backup-datos` evitando duplicados en re-reacciones `[Confirmada · Jose · 22/10/2026]`.
- [x] **Exclusión estricta de auto-voto (Anti-autobombo):** La estrella del propio autor del mensaje queda excluida del cómputo para alcanzar las 2 estrellas `[Confirmada · Jose · 22/10/2026]`.
- [x] **Permanencia irrevocable de portada:** Una vez que el mensaje alcanza 2 estrellas y se publica la portada en `#⭐muro-de-la-fama⭐`, queda inmortalizada de forma permanente aunque usuarios retiren sus reacciones `[Confirmada · Jose · 22/10/2026]`.
- [x] **Cabecera principal canónica:** Rotativo bajo el título oficial **THE SANVI DAILY** con subtítulo de lema comunitario `[Confirmada · Jose · 22/10/2026]`.

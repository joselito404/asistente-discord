# 🎭 Catálogo Maestro de Emojis del Servidor (`docs/EMOJIS_SERVIDOR.md`)

> **Documento Vivo de Referencia y Lore (Regla Global §13)**: Registro exhaustivo de los 124 emojis personalizados del servidor *"LOS MONGOLOS DEL SANVI Y SUS AMIGOS"*, su jerarquía técnica, significados humorísticos/culturales en la comunidad y el análisis de impacto ante la caducidad del Server Boost.  
> **Última sincronización con Discord API**: 18 de Octubre de 2026 (Chat 3 — Telemetría en tiempo real vía API v10 de Discord).

---

## ⚡ 1. Análisis de Impacto: Expiración de Server Boosts de Jose

### 1.1. Contexto y Situación Actual
- **Servidor**: `LOS MONGOLOS DEL SANVI Y SUS AMIGOS` (ID: `1446143936891715616`)
- **Estado Actual de Mejoras**: **Tier 1** (2 mejoras activas otorgadas por Joselito `@joselito3499`).
- **Aviso de Jose**: *"ten en cuenta que mis dos mejoras se van dentro de poco, una pena"*.
- **Consecuencia Directa**: Al expirar los 2 boosts, el servidor perderá el nivel Tier 1 y descenderá a **Tier 0 (Free Tier / Nivel Gratuito de Discord)**.

### 1.2. Límites de Emojis según Nivel de Servidor
| Nivel de Servidor | Mejoras (Boosts) | Límite Emojis Estáticos | Límite Emojis Animados | Total Emojis Soportados |
| :--- | :---: | :---: | :---: | :---: |
| **Tier 0 (Gratuito)** | 0 | **50** | **50** | **100** |
| **Tier 1 (Actual)** | 2 | **100** | **100** | **200** |
| **Tier 2** | 7 | **150** | **150** | **300** |
| **Tier 3** | 14 | **250** | **250** | **500** |

### 1.3. Censo Real del Servidor y Veredicto de Retención
- **Total Emojis en el Servidor**: **124 emojis**
  - **Estáticos**: **98 emojis**
  - **Animados**: **26 emojis**

#### 🟢 Emojis Animados (26/50) — 100% SEGUROS
Dado que el servidor cuenta con 26 emojis animados y el límite del Free Tier es de 50:
- **Ningún emoji animado se verá afectado**. Todos los 26 permanecerán 100% activos y utilizables por bots y usuarios con Discord Nitro.

#### 🟡 Emojis Estáticos (98/50) — IMPACTO DE GRADUACIÓN
Discord gestiona los slots de emojis por **orden cronológico estricto de subida** (determinado por el Snowflake ID de cada emoji):
1. **Slots 1 al 50 (Antiguos — SAFE)**: Se mantienen activos e interactivos en el servidor para todos los miembros.
2. **Slots 51 al 98 (Nuevos — AT RISK / INACTIVOS)**: Discord los congela automáticamente (`available: false`). No se eliminan físicamente de la configuración del servidor, pero quedan bloqueados y no pueden enviarse ni seleccionarse en el selector hasta que el servidor recupere el Tier 1.

> ⚠️ **Emojis Críticos en Zona de Riesgo (Slots 51-98)**:
> Entre los 48 emojis que quedarán temporalmente inactivos tras perder el Boost se encuentran varios de los más icónicos del chat diario: `:aura:`, `:Porro:`, `:Messirve:`, `:cooked:`, `:skillissue:`, `:nobodycares:`, `:grass:` y los 6 rangos competitivos de Brawl Stars (`:Ranked_Pro:` a `:Ranked_Gold:`).

### 1.4. Arquitectura de Resiliencia del Bot Asistente
Para evitar que el bot envíe menciones rotas en texto plano (`<:aura:1535728704129466462>`) cuando un emoji pase a estar deshabilitado:
1. **Inspección en Tiempo Real (`guild.emojis`)**: La función `format_server_emojis` inspecciona el atributo `e.available` en memoria de discord.py.
2. **Fallback Inteligente (`DISABLED_EMOJI_FALLBACK`)**: Si un emoji está deshabilitado por falta de Boost, el conversor lo conmuta automáticamente a un emoji seguro equivalente del primer bloque de 50 o a un carácter Unicode descriptivo, garantizando que el texto del bot **nunca falle ni muestre sintaxis cruda de Discord**.
3. **Catálogo Canónico Offline (`SERVER_EMOJIS_DATA`)**: En entornos sin conexión al guild (tests unitarios o mensajes directos), el conversor utiliza el catálogo canónico precompilado de los 124 emojis.

---

## 🎭 2. Lore, Cultura y Significado Humorístico de los Emojis

El servidor cuenta con una identidad forjada en memes de Discord, jerga de internet, anime/manhwas y videojuegos competitivos:

### 👑 A. Aura, Gigachad y la Filosofía Sigma
- `:aura:` (`ID: 1535728704129466462` — Slot 85): Representa la presencia imponente, respeto descomunal y jugadas maestras (+10.000 aura). Si alguien hace algo legendario o responde con clase, merece `:aura:`. *(Fallback si boost expira: `:gigachad:` / `✨`)*.
- `:gigachad:` (`ID: 1535682070536519730` — Slot 33 [SAFE]): El Chad definitivo. Seguridad absoluta, aplomo y perfección masculina.
- `<a:chadgif:1535680346199162982>` (`ID: 1535680346199162982` — Anim #10 [SAFE]): Gigachad animado asintiendo lentamente con aprobación.
- `:sigmajawline:` (`ID: 1476986259883950121` — Slot 01 [SAFE]): Mandíbula esculpida, sesión intensiva de mewing.
- `:Sigma_Male_Bale:` (`ID: 1535677801808535702` — Slot 29 [SAFE]): Patrick Bateman (Christian Bale) escuchando música con auriculares y cara imperturbable.
- `:facherita:` (`ID: 1484580141618303021` — Slot 08 [SAFE]): Emoji sonriente con gafas de sol oscuras: estilo, elegancia y swag.

### 🚬 B. Reacciones Épicas y Cine
- `:Porro:` (`ID: 1535685303317172305` — Slot 58): La calada legendaria. Situaciones surrealistas, fumadas cósmicas, teorías imposibles o relajación absoluta. *(Fallback: `🚬`)*.
- `:absolutecinema:` (`ID: 1478115607336714300` — Slot 05 [SAFE]): Martin Scorsese con los brazos abiertos: "Absolute Cinema". Obligatorio cuando se debate sobre manhwas top (Top 69 de Joselito en #cultura), giros de guion o jugadas maestras.
- `:Messirve:` (`ID: 1535726367847743528` — Slot 73): Messi asintiendo complacido. Para dar el visto bueno a una propuesta, aceptar un trato o conformarse con algo bueno. *(Fallback: `:facherita:`)*.
- `:cooked:` (`ID: 1535726716901789726` — Slot 76): Calavera ardiendo / "Let him cook" / "Estamos cocinados". Para cuando alguien está acorralado, ha suspendido un examen o se ha quedado sin dinero en el casino. *(Fallback: `💀`)*.
- `:skillissue:` (`ID: 1535727329156931624` — Slot 80): Falta de manos, error de novato o excusas baratas. Vacile amistoso indispensable en debates de gaming. *(Fallback: `:pepeCringe:`)*.
- `<a:Thisisfine:1535679070312857672>` (`ID: 1535679070312857672` — Anim #02 [SAFE]): El perrito tomando café mientras la habitación arde. Ideal para caídas de bots, pérdidas en apuestas o exámenes sorpresa.
- `<a:KEKWLaugh:1535679941059018903>` (`ID: 1535679941059018903` — Anim #07 [SAFE]): Risitas desternillándose. La risa máxima del chat.
- `<a:GalaxyBrainMeme:1535680100060766311>` (`ID: 1535680100060766311` — Anim #08 [SAFE]): Cerebro galáctico iluminándose ante una deducción de 200 IQ.
- `<a:Donowall:1535679683918831676>` (`ID: 1535679683918831676` — Anim #06 [SAFE]): Hablarle a una pared de ladrillos cuando nadie contesta en el chat.

### 🏆 C. Brawl Stars & Gaming Competitivo
Añadidos especialmente para Iván (`racerwasp`), Joselito y el grupo de Brawl Stars:
- `:Ranked_Masters:` (`ID: 1550129992837496833` — Slot 94): Rango Maestros (la cima absoluta).
- `:Ranked_Legendary:` (`ID: 1550129997774323732` — Slot 95): Rango Legendario.
- `:Ranked_Mythic:` (`ID: 1550130000852820099` — Slot 96): Rango Mítico.
- `:Ranked_Diamond:` (`ID: 1550130004074041434` — Slot 97): Rango Diamante.
- `:Ranked_Gold:` (`ID: 1550130006896812084` — Slot 98): Rango Oro.
- `:Ranked_Pro:` (`ID: 1550129987972104252` — Slot 93): Emblema competitivo Pro.

### 🐸 D. Pepe, Wojaks y Memes Clásicos
- `:pepeCRY:` (`ID: 1530995788182847649` — Slot 09 [SAFE]): Tristeza cómica desconsolada.
- `:pepeCringe:` (`ID: 1530996221810966690` — Slot 10 [SAFE]): Vergüenza ajena pura ante un comentario lamentable.
- `:pepecuerda:` (`ID: 1535680479330701433` — Slot 30 [SAFE]): Pepe al borde del abismo por desesperación en exámenes o apuestas.
- `<a:pepe_simp:1535679584819875950>` (`ID: 1535679584819875950` — Anim #05 [SAFE]): Aplauso fervoroso de fanboy/simp.
- `:bruh:` (`ID: 1535682294139060235` — Slot 36 [SAFE]): Expresión inexpresiva de "no me lo creo".
- `:DwayneEyebrow:` (`ID: 1535682237817823362` — Slot 35 [SAFE]): La Roca alzando la ceja con suspicacia.
- `:uno_reverse:` (`ID: 1535682567968129095` — Slot 39 [SAFE]): Contraataque definitivo en cualquier debate.
- `:bonk:` (`ID: 1535681979843092620` — Slot 32 [SAFE]): Cheems arreando con un bate (manda a la horny jail).
- `:grass:` (`ID: 1535727100365901855` — Slot 79): "Toca césped". Para mandar a respirar aire fresco al que lleve 12h pegado al PC.

---

## 📋 3. Catálogo Completo de Emojis

### 3.1. Emojis Estáticos Seguros (Slots 1 al 50 — Free Tier Garantizado)
| # | Nombre | Sintaxis Discord | ID de Snowflake | Fecha Subida | Categoría / Lore |
| :---: | :--- | :--- | :---: | :---: | :--- |
| 1 | `sigmajawline` | `<:sigmajawline:1476986259883950121>` | `1476986259883950121` | 2026-03-01 | Sigma / Mewing |
| 2 | `Dislike` | `<:Dislike:1476986782053568604>` | `1476986782053568604` | 2026-03-01 | Pulgar abajo / Rechazo |
| 3 | `smash` | `<:smash:1476989162715349053>` | `1476989162715349053` | 2026-03-01 | Smash or Pass |
| 4 | `pensando` | `<:pensando:1476989472502452255>` | `1476989472502452255` | 2026-03-01 | Pensativo clásico |
| 5 | `absolutecinema` | `<:absolutecinema:1478115607336714300>` | `1478115607336714300` | 2026-03-04 | Scorsese / Cine y Manhwas |
| 6 | `67` | `<:67:1480177258931949659>` | `1480177258931949659` | 2026-03-10 | Meme numérico |
| 7 | `sanchez_view` | `<:sanchez_view:1484579256758567023>` | `1484579256758567023` | 2026-03-22 | Pedro Sánchez observando |
| 8 | `facherita` | `<:facherita:1484580141618303021>` | `1484580141618303021` | 2026-03-22 | Carita con gafas / Swag |
| 9 | `pepeCRY` | `<:pepeCRY:1530995788182847649>` | `1530995788182847649` | 2026-08-01 | Pepe llorando desconsolado |
| 10 | `pepeCringe` | `<:pepeCringe:1530996221810966690>` | `1530996221810966690` | 2026-08-01 | Pepe con mueca de cringe |
| 11 | `GoodGame` | `<:GoodGame:1530996598195097640>` | `1530996598195097640` | 2026-08-01 | GG / Buen juego |
| 12 | `blob_off` | `<:blob_off:1530996740298375410>` | `1530996740298375410` | 2026-08-01 | Blob apagado / Offline |
| 13 | `amongus_ass` | `<:amongus_ass:1530996947098271965>` | `1530996947098271965` | 2026-08-01 | Meme Among Us |
| 14 | `Diamante` | `<:Diamante:1530997108520255753>` | `1530997108520255753` | 2026-08-01 | Diamante brillante |
| 15 | `catpointandlaugh` | `<:catpointandlaugh:1530997580350357565>` | `1530997580350357565` | 2026-08-01 | Gato señalando y riéndose |
| 16 | `goofy_ah_cat` | `<:goofy_ah_cat:1530997748340363399>` | `1530997748340363399` | 2026-08-01 | Gato tonto cómico |
| 17 | `nerd` | `<:nerd:1531000077462540440>` | `1531000077462540440` | 2026-08-01 | Nerd / "Ehh de hecho 🤓" |
| 18 | `patrick` | `<:patrick:1531000481776799888>` | `1531000481776799888` | 2026-08-01 | Patricio Estrella |
| 19 | `side_eye` | `<:side_eye:1531001406733947001>` | `1531001406733947001` | 2026-08-01 | Mirada de reojo suspicaz |
| 20 | `bros` | `<:bros:1531001502066413678>` | `1531001502066413678` | 2026-08-01 | Colegas / Hermandad |
| 21 | `dead_stare` | `<:dead_stare:1531001721915183244>` | `1531001721915183244` | 2026-08-01 | Mirada inexpresiva vacía |
| 22 | `Nazi` | `<:Nazi:1531002011682607301>` | `1531002011682607301` | 2026-08-01 | Meme de humor negro |
| 23 | `franco` | `<:franco:1531002139562872912>` | `1531002139562872912` | 2026-08-01 | Meme de historia de España |
| 24 | `Spain_empire` | `<:Spain_empire:1531002554656358584>` | `1531002554656358584` | 2026-08-01 | Cruz de Borgoña / Imperio |
| 25 | `GAY` | `<:GAY:1531003064272814142>` | `1531003064272814142` | 2026-08-01 | Meme / Arcoíris |
| 26 | `sonimcrine` | `<:sonimcrine:1535676442636189817>` | `1535676442636189817` | 2026-08-14 | Sonic llorando cómico |
| 27 | `SaySwear` | `<:SaySwear:1535676796362825839>` | `1535676796362825839` | 2026-08-14 | "Júralo" / Say swear |
| 28 | `sybauspeed` | `<:sybauspeed:1535677246734598275>` | `1535677246734598275` | 2026-08-14 | IShowSpeed / Euforia |
| 29 | `Sigma_Male_Bale` | `<:Sigma_Male_Bale:1535677801808535702>` | `1535677801808535702` | 2026-08-14 | Christian Bale Sigma |
| 30 | `pepecuerda` | `<:pepecuerda:1535680479330701433>` | `1535680479330701433` | 2026-08-14 | Pepe desesperado / cuerda |
| 31 | `95_CryThumbsUp` | `<:95_CryThumbsUp:1535681917473656882>` | `1535681917473656882` | 2026-08-14 | Llorando con pulgar arriba |
| 32 | `bonk` | `<:bonk:1535681979843092620>` | `1535681979843092620` | 2026-08-14 | Cheems golpeando con bate |
| 33 | `gigachad` | `<:gigachad:1535682070536519730>` | `1535682070536519730` | 2026-08-14 | Gigachad supremo |
| 34 | `Trolled` | `<:Trolled:1535682153818357802>` | `1535682153818357802` | 2026-08-14 | Trollface clásico |
| 35 | `DwayneEyebrow` | `<:DwayneEyebrow:1535682237817823362>` | `1535682237817823362` | 2026-08-14 | La Roca levantando la ceja |
| 36 | `bruh` | `<:bruh:1535682294139060235>` | `1535682294139060235` | 2026-08-14 | Momento bruh |
| 37 | `emojigg_OMG` | `<:emojigg_OMG:1535682384450691153>` | `1535682384450691153` | 2026-08-14 | Exclamación OMG |
| 38 | `what_in_the_hell` | `<:what_in_the_hell:1535682520698585180>` | `1535682520698585180` | 2026-08-14 | "¿Qué demonios es esto?" |
| 39 | `uno_reverse` | `<:uno_reverse:1535682567968129095>` | `1535682567968129095` | 2026-08-14 | Tarjeta reversa de UNO |
| 40 | `Cat_Sus` | `<:Cat_Sus:1535682639544197212>` | `1535682639544197212` | 2026-08-14 | Gato sospechando |
| 41 | `shrug` | `<:shrug:1535682710306029638>` | `1535682710306029638` | 2026-08-14 | Encogerse de hombros ¯\_(ツ)_/¯ |
| 42 | `CryingMan` | `<:CryingMan:1535682791755481141>` | `1535682791755481141` | 2026-08-14 | Hombre llorando dramático |
| 43 | `pixel_rip_tombstone`| `<:pixel_rip_tombstone:1535682950056906752>`| `1535682950056906752` | 2026-08-14 | Lápida RIP (Joselito RIP) |
| 44 | `knowledge` | `<:knowledge:1535683001533337640>` | `1535683001533337640` | 2026-08-14 | Conocimiento / Sabiduría |
| 45 | `doomed` | `<:doomed:1535683080294236220>` | `1535683080294236220` | 2026-08-14 | Condenado / Sin salvación |
| 46 | `wahhhhh` | `<:wahhhhh:1535683162628169760>` | `1535683162628169760` | 2026-08-14 | Llanto de bebé exagerado |
| 47 | `my_honest_reaction`| `<:my_honest_reaction:1535683205879832767>`| `1535683205879832767` | 2026-08-14 | "Mi honesta reacción" |
| 48 | `Heartache` | `<:Heartache:1535683279334805635>` | `1535683279334805635` | 2026-08-14 | Dolor en el pecho cósmico |
| 49 | `MrIncredible` | `<:MrIncredible:1535683403158921338>`| `1535683403158921338` | 2026-08-14 | Mr. Increíble Uncanny |
| 50 | `yb_angry2` | `<:yb_angry2:1535683502937350145>` | `1535683502937350145` | 2026-08-14 | Enfadado / Rabia |

---

### 3.2. Emojis Estáticos en Riesgo (Slots 51 al 98 — Deshabilitados al perder Boost)
Estos emojis quedarán inactivos en Discord cuando expiren los 2 boosts de Jose. El bot Asistente intercepta sus llamadas y aplica el fallback indicado:

| # | Nombre | Sintaxis Discord | ID de Snowflake | Fallback Activo si Caduca Boost |
| :---: | :--- | :--- | :---: | :--- |
| 51 | `Doakes` | `<:Doakes:1535683572910784652>` | `1535683572910784652` | "Surprise motherfucker" / 🤨 |
| 52 | `Im_done` | `<:Im_done:1535683692779802664>` | `1535683692779802664` | `🤦‍♂️` / Ya no puedo más |
| 53 | `yb_ayo` | `<:yb_ayo:1535683762182955051>` | `1535683762182955051` | "Ayo?!" / 😳 |
| 54 | `monkeythink` | `<:monkeythink:1535684318993584219>` | `1535684318993584219` | `🐵🤔` |
| 55 | `9999IQ` | `<:9999IQ:1535684433011540078>` | `1535684433011540078` | `<:gigachad:1535682070536519730>` |
| 56 | `pensivebetrayal`| `<:pensivebetrayal:1535684508542832690>`| `1535684508542832690`| 😔🗡️ |
| 57 | `emojigg_HUH` | `<:emojigg_HUH:1535684921795026984>` | `1535684921795026984` | 🤨 "¿HUH?" |
| 58 | `Porro` | `<:Porro:1535685303317172305>` | `1535685303317172305` | `🚬` |
| 59 | `cathink` | `<:cathink:1535685385424867400>` | `1535685385424867400` | `🐱🤔` |
| 60 | `thousandyardstare`| `<:thousandyardstare:1535685557525545062>`|`1535685557525545062`| 😳 Mirada de las 1.000 yardas |
| 61 | `4k_ultra_hd` | `<:4k_ultra_hd:1535685617026080911>` | `1535685617026080911` | 📸 4K Ultra HD |
| 62 | `BaldwinHand` | `<:BaldwinHand:1535724200013201408>` | `1535724200013201408` | ✋ Mano de desaprobación |
| 63 | `dumbass_stare` | `<:dumbass_stare:1535724333756977253>`| `1535724333756977253`| 😐 Mirada perdida |
| 64 | `PoorHomeless` | `<:PoorHomeless:1535724701698228234>`| `1535724701698228234`| 🏚️ En la ruina |
| 65 | `PatrickLeash` | `<:PatrickLeash:1535724791644954691>`| `1535724791644954691`| 🪢 Patricio atado |
| 66 | `bb_thumbs_up` | `<:bb_thumbs_up:1535725204175855726>`| `1535725204175855726`| 👍 Pulgar arriba |
| 67 | `oh_god` | `<:oh_god:1535725370723147939>` | `1535725370723147939` | 😱 Oh dios mío |
| 68 | `fruity_sus` | `<:fruity_sus:1535725573190455308>` | `1535725573190455308` | 🤨 Sospechoso |
| 69 | `Florkwhat` | `<:Florkwhat:1535725634779619472>` | `1535725634779619472` | 🥢 Flork sorprendido |
| 70 | `Tungtungtungsahur`| `<:Tungtungtungsahur:1535725729503772813>`|`1535725729503772813`| 🥁 Meme sonoro |
| 71 | `skeleton` | `<:skeleton:1535725933032382556>` | `1535725933032382556` | `💀` Esqueleto |
| 72 | `nobodycares` | `<:nobodycares:1535726064293257298>` | `1535726064293257298` | 🤷‍♂️ A nadie le importa |
| 73 | `Messirve` | `<:Messirve:1535726367847743528>` | `1535726367847743528` | `<:facherita:1484580141618303021>` |
| 74 | `Mindblown` | `<:Mindblown:1535726556318793798>` | `1535726556318793798` | `🤯` Mente explotada |
| 75 | `Autism` | `<:Autism:1535726626049101926>` | `1535726626049101926` | 🎉 Yippee! (Rol de Iván) |
| 76 | `cooked` | `<:cooked:1535726716901789726>` | `1535726716901789726` | `💀` Cocinado / Game Over |
| 77 | `mortroll` | `<:mortroll:1535726810086641795>` | `1535726810086641795` | 🃏 Mordecai troll |
| 78 | `blue_screen` | `<:blue_screen:1535726947831914576>` | `1535726947831914576` | 💻💥 Pantallazo azul |
| 79 | `grass` | `<:grass:1535727100365901855>` | `1535727100365901855` | `🌱` Toca césped |
| 80 | `skillissue` | `<:skillissue:1535727329156931624>` | `1535727329156931624` | `<:pepeCringe:1530996221810966690>` |
| 81 | `emojigg_bot` | `<:emojigg_bot:1535727917441744937>` | `1535727917441744937` | 🤖 Bot badge |
| 82 | `Serious` | `<:Serious:1535728149038366851>` | `1535728149038366851` | 😐 Serio / No bromas |
| 83 | `POINT_GAY` | `<:POINT_GAY:1535728247696789564>` | `1535728247696789564` | 👉 Señalando |
| 84 | `emojigg_BAN` | `<:emojigg_BAN:1535728476181495870>` | `1535728476181495870` | 🔨 Banhammer |
| 85 | `aura` | `<:aura:1535728704129466462>` | `1535728704129466462` | `<:gigachad:1535682070536519730>` |
| 86 | `ahegao` | `<:ahegao:1535728782630191174>` | `1535728782630191174` | 😵 Expresión anime |
| 87 | `take_my_money` | `<:take_my_money:1535728830097133751>`| `1535728830097133751`| 💸 ¡Toma mi dinero! |
| 88 | `STFU` | `<:STFU:1535728963371147296>` | `1535728963371147296` | 🤫 Cállate |
| 89 | `true` | `<:true:1535729025794838609>` | `1535729025794838609` | ✅ Verdadero |
| 90 | `same` | `<:same:1535729270582943824>` | `1535729270582943824` | 🤝 Yo igual |
| 91 | `False` | `<:False:1535729373947109487>` | `1535729373947109487` | ❌ Falso |
| 92 | `thankyou` | `<:thankyou:1535730204977406062>` | `1535730204977406062` | 🙏 Gracias |
| 93 | `Ranked_Pro` | `<:Ranked_Pro:1550129987972104252>` | `1550129987972104252` | 🏆 Brawl Stars Pro |
| 94 | `Ranked_Masters`| `<:Ranked_Masters:1550129992837496833>`|`1550129992837496833`| 👑 Brawl Stars Maestros |
| 95 | `Ranked_Legendary`|`<:Ranked_Legendary:1550129997774323732>`|`1550129997774323732`| 🌟 Brawl Stars Legendario |
| 96 | `Ranked_Mythic` | `<:Ranked_Mythic:1550130000852820099>`| `1550130000852820099`| 🟣 Brawl Stars Mítico |
| 97 | `Ranked_Diamond`| `<:Ranked_Diamond:1550130004074041434>`|`1550130004074041434`| 💎 Brawl Stars Diamante |
| 98 | `Ranked_Gold` | `<:Ranked_Gold:1550130006896812084>` | `1550130006896812084` | 🥇 Brawl Stars Oro |

---

### 3.3. Emojis Animados (Todos 100% Seguros — 26/50 Free Tier)
| # | Nombre | Sintaxis Discord | ID de Snowflake | Fecha Subida | Descripción y Efecto |
| :---: | :--- | :--- | :---: | :---: | :--- |
| 1 | `hello_wave` | `<a:hello_wave:1535678953870725121>` | `1535678953870725121` | 2026-08-14 | Mano saludando con energía |
| 2 | `Thisisfine` | `<a:Thisisfine:1535679070312857672>` | `1535679070312857672` | 2026-08-14 | Perro en llamas tomando café |
| 3 | `hulk_gif` | `<a:hulk_gif:1535679185803018361>` | `1535679185803018361` | 2026-08-14 | Hulk enfurecido |
| 4 | `pain` | `<a:pain:1535679465383002192>` | `1535679465383002192` | 2026-08-14 | Dolor continuo en bucle |
| 5 | `pepe_simp` | `<a:pepe_simp:1535679584819875950>` | `1535679584819875950` | 2026-08-14 | Pepe aplaudiendo como un fanboy |
| 6 | `Donowall` | `<a:Donowall:1535679683918831676>` | `1535679683918831676` | 2026-08-14 | Hablar a una pared / Ignorado |
| 7 | `KEKWLaugh` | `<a:KEKWLaugh:1535679941059018903>` | `1535679941059018903` | 2026-08-14 | Risa máxima de KEKW |
| 8 | `GalaxyBrainMeme`| `<a:GalaxyBrainMeme:1535680100060766311>`|`1535680100060766311`| 2026-08-14 | Cerebro cósmico expandiéndose |
| 9 | `cat_bitting` | `<a:cat_bitting:1535680234207191100>`| `1535680234207191100`| 2026-08-14 | Gato mordiendo repetidamente |
| 10 | `chadgif` | `<a:chadgif:1535680346199162982>` | `1535680346199162982` | 2026-08-14 | Gigachad asintiendo con aplomo |
| 11 | `flashbang` | `<a:flashbang:1535680549660655616>` | `1535680549660655616` | 2026-08-14 | Destello cegador blanco |
| 12 | `ACTUALLY_IM` | `<a:ACTUALLY_IM:1535680603179974678>`| `1535680603179974678`| 2026-08-14 | "Actually I'm..." |
| 13 | `cat_boom` | `<a:cat_boom:1535725821652770836>` | `1535725821652770836` | 2026-08-14 | Gato explotando cómicamente |
| 14 | `dead_spin` | `<a:dead_spin:1535726486168932353>` | `1535726486168932353` | 2026-08-14 | Calavera dando vueltas |
| 15 | `yummy` | `<a:yummy:1535726899018338346>` | `1535726899018338346` | 2026-08-14 | Delicioso / Ñam ñam |
| 16 | `Scubbacat` | `<a:Scubbacat:1535727498602618890>` | `1535727498602618890` | 2026-08-14 | Gato con escafandra buceando |
| 17 | `ai_baby` | `<a:ai_baby:1535727719948623872>` | `1535727719948623872` | 2026-08-14 | Bebé generado por IA |
| 18 | `freaky_lick` | `<a:freaky_lick:1535727845014241320>`| `1535727845014241320`| 2026-08-14 | Meme freaky |
| 19 | `Reze` | `<a:Reze:1535727967232069642>` | `1535727967232069642` | 2026-08-14 | Reze de Chainsaw Man |
| 20 | `PanickedNo` | `<a:PanickedNo:1535728525431013437>` | `1535728525431013437` | 2026-08-14 | Negación con pánico |
| 21 | `cornershaking`| `<a:cornershaking:1535728585665548298>`|`1535728585665548298`| 2026-08-14 | Temblor en la esquina |
| 22 | `emojigg_67` | `<a:emojigg_67:1535729079657963661>` | `1535729079657963661` | 2026-08-14 | Animación 67 |
| 23 | `SpinningFish` | `<a:SpinningFish:1535729132208656395>`| `1535729132208656395`| 2026-08-14 | Pescado girando a 1000 RPM |
| 24 | `ononono` | `<a:ononono:1535729205982269570>` | `1535729205982269570` | 2026-08-14 | Risita de "Oh no no no" |
| 25 | `Think` | `<a:Think:1535729557469011968>` | `1535729557469011968` | 2026-08-14 | Emoji pensante animado |
| 26 | `ZOOOM` | `<a:ZOOOM:1535729987116736554>` | `1535729987116736554` | 2026-08-14 | Efecto de velocidad supersónica |

---

## 💻 4. Integración Técnica en el Bot Asistente

1. **Escritura Natural en el `SYSTEM_PROMPT`**: El bot puede redactar libremente `:aura:`, `:Porro:`, `:gigachad:`, `:absolutecinema:`, `:KEKWLaugh:`, etc. No necesita memorizar IDs de Discord.
2. **Auto-conversión Pre-Envío**:
   ```python
   response_text = format_server_emojis(response_text, guild=message.guild)
   ```
3. **Compatibilidad Total**:
   - Insensible a mayúsculas/minúsculas (`:porro:` -> `<:Porro:1535685303317172305>`).
   - Respeta bloques de código (bloques ` ``` ` y código inline `` ` ``).
   - Ignora emojis ya formateados (`<:name:id>` o `<a:name:id>`) sin duplicar reemplazos.
   - Si caduca el Server Boost y Discord marca `available: False`, el bot utiliza el mapeo a un emoji seguro del servidor o un Unicode limpio, protegiendo la estética del chat.

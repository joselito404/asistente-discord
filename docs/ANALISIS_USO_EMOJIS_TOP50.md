# 📊 Auditoría de Telemetría Real y Top 50 Emojis del Servidor (`docs/ANALISIS_USO_EMOJIS_TOP50.md`)

> **Documento Maestro de Telemetría y Plan de Retención (Regla Global §13 y §14)**: Auditoría exhaustiva de 10.700 mensajes y 1.008 reacciones en los 33 canales de texto del servidor *"LOS MONGOLOS DEL SANVI Y SUS AMIGOS"* (Guild ID: `1446143936891715616`), ranking de uso real de los 124 emojis (98 estáticos y 26 animados) y plan de acción preventivo ante la expiración de las mejoras de Server Boost el **2 de Noviembre de 2026**.
> **Fecha de Ejecución del Escaneo**: 18-19 de Octubre de 2026 (Chat 3 — Auditoría mediante `herramientas/audit_emojis_telemetry.py` vía API v10 de Discord).
> **ESTADO DE EJECUCIÓN**: **🟢 PURGA OFICIAL COMPLETADA CON ÉXITO (19 de Octubre de 2026)**. Servidor blindado en exactamente **50 Emojis Estáticos (Top 50)** y **26 Emojis Animados** (76 emojis en total). Cero riesgo ante la pérdida de Boosts.

---

## 📈 1. Resumen Ejecutivo de la Auditoría

- **Servidor Discord**: `LOS MONGOLOS DEL SANVI Y SUS AMIGOS` (ID: `1446143936891715616`)
- **Fecha Crítica**: **2 de Noviembre de 2026** (Expiran los 2 Server Boosts de Jose; el servidor desciende de Tier 1 a Tier 0 / Gratuito).
- **Límites de Emojis en Tier 0 (Gratuito)**: **50 Emojis Estáticos** y **50 Emojis Animados**.
- **Censo Auditado Inicial**: **124 Emojis Totales** (98 estáticos y 26 animados).
- **Censo Actual Post-Purga**: **76 Emojis Totales** (**50 estáticos** y **26 animados**).
- **Volumen Histórico Analizado**: **10,700 mensajes** y **1,008 reacciones** analizadas en **33 canales**.
- **Copia de Seguridad Local**: 124 archivos preservados a 128x128 en `datos_locales/emojis_backup/` con índice criptográfico SHA-256 en `datos_locales/emojis_backup/manifest.json`.

### 1.1. Diagnóstico y Resolución del Blindaje
1. **🟢 Emojis Animados (26/50) — RIESGO CERO (100% Seguros)**:
   - Al haber solo 26 emojis animados y ser el cupo gratuito de 50, **ningún emoji animado se tocó ni se perderá** el 2 de noviembre. Permanecen los 26 intactos y sobran 24 slots libres.
2. **🟢 Emojis Estáticos (50/50) — BLINDAJE TIER 0 COMPLETADO (0% Riesgo)**:
   - Se ejecutó la purga de los **48 emojis estáticos sobrantes** vía API REST v10 de Discord.
   - **Conservados al 100% los 50 emojis estáticos del Top 50 oficial**.
   - Al quedar exactamente 50 emojis estáticos en el servidor, **todos entran dentro de la cuota gratuita de Tier 0**, garantizando que **ningún emoji quedará congelado (`available: true` permanente)**.
   - **Preservación de IDs**: Se mantuvieron intactos los Snowflake IDs originales de la moneda oficial (`<:Porro:1535685303317172305>`), `:cooked:`, `:monkeythink:` y los **6 rangos de Brawl Stars (`:Ranked_Gold:` a `:Ranked_Pro:`)**, evitando roturas en mensajes antiguos y comandos de bots.

### 1.2. Desglose de Telemetría por Canal

| Canal | Tipo | Mensajes Auditados | Reacciones Auditadas | Emojis Únicos del Server Usados |
| :--- | :---: | :---: | :---: | :---: |
| `#🎰casino-y-apuestas🎰` | Texto | 3,704 | 66 | 20 |
| `#🗨️la-shit-de-todos-los-dias🗨️` | Texto | 2,553 | 297 | 44 |
| `#🎮gaming-general🎮` | Texto | 1,007 | 235 | 24 |
| `#🤖bots🤖` | Texto | 500 | 31 | 8 |
| `#🧠brawl-stars🧠` | Texto | 492 | 65 | 17 |
| `#📖cultura📖` | Texto | 490 | 31 | 17 |
| `#🛠️apps-solo-mods🛠️` | Texto | 320 | 32 | 35 |
| `#👥familia-steam👥` | Texto | 213 | 41 | 16 |
| `#💩shit-post💩` | Texto | 152 | 21 | 8 |
| `#🎰casino-y-apuestas-2🎰` | Texto | 149 | 1 | 2 |
| `#🏫only-sanvi-and-ex-sanvi🏫` | Texto | 149 | 11 | 6 |
| `#⌨️comandos⌨️` | Texto | 116 | 26 | 6 |
| `#💎recomendaciones-gaming💎` | Texto | 115 | 29 | 8 |
| `#🎁free-games🎁` | Texto | 115 | 3 | 2 |
| `#⚖️el-tribunal-gaming⚖️` | Texto | 104 | 6 | 3 |
| `#👾・games-pro・👾` | Texto | 91 | 10 | 5 |
| `#🤝juegos-cooperativos🤝` | Texto | 82 | 12 | 4 |
| `#🏪tienda-y-mercado🏪` | Texto | 56 | 3 | 6 |
| `#torneos` | Texto | 56 | 6 | 5 |
| `#🥊violencia🥊` | Texto | 52 | 20 | 5 |
| `#📣anuncios📣` | Anuncios | 44 | 3 | 1 |
| `#torneos-general` | Texto | 33 | 6 | 1 |
| `#🥂・la-shit-de-todos-los-dias-pro・🥂` | Texto | 24 | 1 | 1 |
| `#uni-programación` | Texto | 17 | 1 | 1 |
| `#📣anuncios-privado📣` | Anuncios | 17 | 1 | 1 |
| `#💣・shit-post-pro・💣` | Texto | 11 | 1 | 3 |
| `#reglas` | Texto | 10 | 9 | 5 |
| `#⭐muro-de-la-fama⭐` | Texto | 7 | 2 | 0 |
| `#💡sugerencias💡` | Texto | 7 | 32 | 1 |
| `#📜normas📜` | Texto | 5 | 5 | 2 |
| `#🎂cumpleaños🎂` | Texto | 5 | 0 | 0 |
| `#📚・cultura-pro・📚` | Texto | 3 | 1 | 2 |
| `#🎭roles🎭` | Texto | 1 | 0 | 0 |

---

## 🏆 2. Tabla de Clasificación: Ranking Top 50 Emojis Estáticos del Servidor

> Este ranking representa el orden de mérito real según el uso combinado en cuerpo de mensajes y reacciones. Si el servidor solo puede conservar 50 emojis estáticos, **estos son exactamente los 50 que deben estar en los slots 1 al 50**.

| Pos | Emoji | Nombre | Snowflake ID | Slot Actual | Usos Cuerpo | Usos Reacciones | Total Usos | Estado Actual ante Fin de Boost |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
|  1 | `<:absolutecinema:1478115607336714300>` | `:absolutecinema:` | `1478115607336714300` | **Slot 05** | 37 | 73 | **110** | 🟢 Blindado (Activo 50/50) |
|  2 | `<:patrick:1531000481776799888>` | `:patrick:` | `1531000481776799888` | **Slot 18** | 23 | 14 | **37** | 🟢 Blindado (Activo 50/50) |
|  3 | `<:sanchez_view:1484579256758567023>` | `:sanchez_view:` | `1484579256758567023` | **Slot 07** | 14 | 20 | **34** | 🟢 Blindado (Activo 50/50) |
|  4 | `<:GAY:1531003064272814142>` | `:GAY:` | `1531003064272814142` | **Slot 25** | 0 | 31 | **31** | 🟢 Blindado (Activo 50/50) |
|  5 | `<:amongus_ass:1530996947098271965>` | `:amongus_ass:` | `1530996947098271965` | **Slot 13** | 7 | 19 | **26** | 🟢 Blindado (Activo 50/50) |
|  6 | `<:Dislike:1476986782053568604>` | `:Dislike:` | `1476986782053568604` | **Slot 02** | 5 | 18 | **23** | 🟢 Blindado (Activo 50/50) |
|  7 | `<:pepeCRY:1530995788182847649>` | `:pepeCRY:` | `1530995788182847649` | **Slot 09** | 8 | 15 | **23** | 🟢 Blindado (Activo 50/50) |
|  8 | `<:Porro:1535685303317172305>` | `:Porro:` | `1535685303317172305` | **Slot 58** | 18 | 3 | **21** | 🟢 Blindado (Activo 50/50) |
|  9 | `<:monkeythink:1535684318993584219>` | `:monkeythink:` | `1535684318993584219` | **Slot 54** | 21 | 0 | **21** | 🟢 Blindado (Activo 50/50) |
| 10 | `<:dead_stare:1531001721915183244>` | `:dead_stare:` | `1531001721915183244` | **Slot 21** | 2 | 11 | **13** | 🟢 Blindado (Activo 50/50) |
| 11 | `<:67:1480177258931949659>` | `:67:` | `1480177258931949659` | **Slot 06** | 3 | 10 | **13** | 🟢 Blindado (Activo 50/50) |
| 12 | `<:nerd:1531000077462540440>` | `:nerd:` | `1531000077462540440` | **Slot 17** | 5 | 7 | **12** | 🟢 Blindado (Activo 50/50) |
| 13 | `<:facherita:1484580141618303021>` | `:facherita:` | `1484580141618303021` | **Slot 08** | 6 | 6 | **12** | 🟢 Blindado (Activo 50/50) |
| 14 | `<:sigmajawline:1476986259883950121>` | `:sigmajawline:` | `1476986259883950121` | **Slot 01** | 2 | 9 | **11** | 🟢 Blindado (Activo 50/50) |
| 15 | `<:side_eye:1531001406733947001>` | `:side_eye:` | `1531001406733947001` | **Slot 19** | 6 | 5 | **11** | 🟢 Blindado (Activo 50/50) |
| 16 | `<:cooked:1535726716901789726>` | `:cooked:` | `1535726716901789726` | **Slot 76** | 8 | 3 | **11** | 🟢 Blindado (Activo 50/50) |
| 17 | `<:Nazi:1531002011682607301>` | `:Nazi:` | `1531002011682607301` | **Slot 22** | 1 | 9 | **10** | 🟢 Blindado (Activo 50/50) |
| 18 | `<:Spain_empire:1531002554656358584>` | `:Spain_empire:` | `1531002554656358584` | **Slot 24** | 0 | 9 | **9** | 🟢 Blindado (Activo 50/50) |
| 19 | `<:Diamante:1530997108520255753>` | `:Diamante:` | `1530997108520255753` | **Slot 14** | 1 | 7 | **8** | 🟢 Blindado (Activo 50/50) |
| 20 | `<:GoodGame:1530996598195097640>` | `:GoodGame:` | `1530996598195097640` | **Slot 11** | 1 | 5 | **6** | 🟢 Blindado (Activo 50/50) |
| 21 | `<:true:1535729025794838609>` | `:true:` | `1535729025794838609` | **Slot 89** | 1 | 5 | **6** | 🟢 Blindado (Activo 50/50) |
| 22 | `<:sonimcrine:1535676442636189817>` | `:sonimcrine:` | `1535676442636189817` | **Slot 26** | 3 | 3 | **6** | 🟢 Blindado (Activo 50/50) |
| 23 | `<:Ranked_Gold:1550130006896812084>` | `:Ranked_Gold:` | `1550130006896812084` | **Slot 98** | 5 | 1 | **6** | 🟢 Blindado (Activo 50/50) |
| 24 | `<:smash:1476989162715349053>` | `:smash:` | `1476989162715349053` | **Slot 03** | 0 | 5 | **5** | 🟢 Blindado (Activo 50/50) |
| 25 | `<:franco:1531002139562872912>` | `:franco:` | `1531002139562872912` | **Slot 23** | 0 | 5 | **5** | 🟢 Blindado (Activo 50/50) |
| 26 | `<:Sigma_Male_Bale:1535677801808535702>` | `:Sigma_Male_Bale:` | `1535677801808535702` | **Slot 29** | 1 | 4 | **5** | 🟢 Blindado (Activo 50/50) |
| 27 | `<:9999IQ:1535684433011540078>` | `:9999IQ:` | `1535684433011540078` | **Slot 55** | 4 | 1 | **5** | 🟢 Blindado (Activo 50/50) |
| 28 | `<:sybauspeed:1535677246734598275>` | `:sybauspeed:` | `1535677246734598275` | **Slot 28** | 2 | 2 | **4** | 🟢 Blindado (Activo 50/50) |
| 29 | `<:Ranked_Pro:1550129987972104252>` | `:Ranked_Pro:` | `1550129987972104252` | **Slot 93** | 4 | 0 | **4** | 🟢 Blindado (Activo 50/50) |
| 30 | `<:Ranked_Masters:1550129992837496833>` | `:Ranked_Masters:` | `1550129992837496833` | **Slot 94** | 4 | 0 | **4** | 🟢 Blindado (Activo 50/50) |
| 31 | `<:gigachad:1535682070536519730>` | `:gigachad:` | `1535682070536519730` | **Slot 33** | 0 | 3 | **3** | 🟢 Blindado (Activo 50/50) |
| 32 | `<:thousandyardstare:1535685557525545062>` | `:thousandyardstare:` | `1535685557525545062` | **Slot 60** | 0 | 3 | **3** | 🟢 Blindado (Activo 50/50) |
| 33 | `<:skeleton:1535725933032382556>` | `:skeleton:` | `1535725933032382556` | **Slot 71** | 1 | 2 | **3** | 🟢 Blindado (Activo 50/50) |
| 34 | `<:Im_done:1535683692779802664>` | `:Im_done:` | `1535683692779802664` | **Slot 52** | 2 | 1 | **3** | 🟢 Blindado (Activo 50/50) |
| 35 | `<:grass:1535727100365901855>` | `:grass:` | `1535727100365901855` | **Slot 79** | 2 | 1 | **3** | 🟢 Blindado (Activo 50/50) |
| 36 | `<:Doakes:1535683572910784652>` | `:Doakes:` | `1535683572910784652` | **Slot 51** | 3 | 0 | **3** | 🟢 Blindado (Activo 50/50) |
| 37 | `<:SaySwear:1535676796362825839>` | `:SaySwear:` | `1535676796362825839` | **Slot 27** | 0 | 2 | **2** | 🟢 Blindado (Activo 50/50) |
| 38 | `<:PoorHomeless:1535724701698228234>` | `:PoorHomeless:` | `1535724701698228234` | **Slot 64** | 0 | 2 | **2** | 🟢 Blindado (Activo 50/50) |
| 39 | `<:same:1535729270582943824>` | `:same:` | `1535729270582943824` | **Slot 90** | 0 | 2 | **2** | 🟢 Blindado (Activo 50/50) |
| 40 | `<:pensando:1476989472502452255>` | `:pensando:` | `1476989472502452255` | **Slot 04** | 1 | 1 | **2** | 🟢 Blindado (Activo 50/50) |
| 41 | `<:Heartache:1535683279334805635>` | `:Heartache:` | `1535683279334805635` | **Slot 48** | 1 | 1 | **2** | 🟢 Blindado (Activo 50/50) |
| 42 | `<:skillissue:1535727329156931624>` | `:skillissue:` | `1535727329156931624` | **Slot 80** | 1 | 1 | **2** | 🟢 Blindado (Activo 50/50) |
| 43 | `<:my_honest_reaction:1535683205879832767>` | `:my_honest_reaction:` | `1535683205879832767` | **Slot 47** | 2 | 0 | **2** | 🟢 Blindado (Activo 50/50) |
| 44 | `<:Ranked_Legendary:1550129997774323732>` | `:Ranked_Legendary:` | `1550129997774323732` | **Slot 95** | 2 | 0 | **2** | 🟢 Blindado (Activo 50/50) |
| 45 | `<:Ranked_Mythic:1550130000852820099>` | `:Ranked_Mythic:` | `1550130000852820099` | **Slot 96** | 2 | 0 | **2** | 🟢 Blindado (Activo 50/50) |
| 46 | `<:Ranked_Diamond:1550130004074041434>` | `:Ranked_Diamond:` | `1550130004074041434` | **Slot 97** | 2 | 0 | **2** | 🟢 Blindado (Activo 50/50) |
| 47 | `<:pepeCringe:1530996221810966690>` | `:pepeCringe:` | `1530996221810966690` | **Slot 10** | 0 | 1 | **1** | 🟢 Blindado (Activo 50/50) |
| 48 | `<:catpointandlaugh:1530997580350357565>` | `:catpointandlaugh:` | `1530997580350357565` | **Slot 15** | 0 | 1 | **1** | 🟢 Blindado (Activo 50/50) |
| 49 | `<:shrug:1535682710306029638>` | `:shrug:` | `1535682710306029638` | **Slot 41** | 0 | 1 | **1** | 🟢 Blindado (Activo 50/50) |
| 50 | `<:bb_thumbs_up:1535725204175855726>` | `:bb_thumbs_up:` | `1535725204175855726` | **Slot 66** | 0 | 1 | **1** | 🟢 Blindado (Activo 50/50) |

> 💡 **Observaciones Clave del Top 50**:
> - **Top 1 Indiscutible**: `:absolutecinema:` comanda con autoridad absoluta (**110 usos**: 37 en mensajes y 73 en reacciones). Afortunadamente está en el Slot 5 (Seguro).
> - **Top 2 y 3**: `:patrick:` (37 usos) y `:sanchez_view:` (34 usos), ambos seguros.
> - **Moneda Oficial en Peligro**: `:Porro:` es el **Top 8 del servidor** (21 usos: 18 en mensajes, 3 en reacciones). Al estar en el **Slot 58**, ¡quedará congelado si no se interviene!
> - **Brawl Stars Ranked**: `:Ranked_Gold:` (Top 23, 6 usos), `:Ranked_Pro:` (Top 29, 4 usos) y `:Ranked_Masters:` (Top 30, 4 usos), junto con `:Ranked_Legendary:`, `:Ranked_Mythic:` y `:Ranked_Diamond:` están todos en los slots 93-98 en zona de congelación.

---

## 🗑️ 3. Lista Negra de Emojis Muertos/Inútiles en los Slots 1 al 50

Discord mantiene activos los primeros 50 emojis según su antigüedad. A continuación se identifican los emojis que actualmente ocupan slots del 1 al 50 pero que la telemetría demuestra que están completamente muertos o son prescindibles:

### 3.1. Emojis con Cero (0) Usos en Slots 1 al 50 (Eliminación Inmediata)
| Slot Actual | Nombre | Snowflake ID | Usos Totales | Recomendación de Purga |
| :---: | :--- | :---: | :---: | :--- |
| **Slot 12** | `:blob_off:` | `1530996740298375410` | **0** | ❌ **Borrar inmediatamente** en Discord. |
| **Slot 16** | `:goofy_ah_cat:` | `1530997748340363399` | **0** | ❌ **Borrar inmediatamente** en Discord. |
| **Slot 30** | `:pepecuerda:` | `1535680479330701433` | **0** | ❌ **Borrar inmediatamente** en Discord. |
| **Slot 31** | `:95_CryThumbsUp:` | `1535681917473656882` | **0** | ❌ **Borrar inmediatamente** en Discord. |
| **Slot 32** | `:bonk:` | `1535681979843092620` | **0** | ❌ **Borrar inmediatamente** en Discord. |
| **Slot 36** | `:bruh:` | `1535682294139060235` | **0** | ❌ **Borrar inmediatamente** en Discord. |
| **Slot 38** | `:what_in_the_hell:` | `1535682520698585180` | **0** | ❌ **Borrar inmediatamente** en Discord. |
| **Slot 40** | `:Cat_Sus:` | `1535682639544197212` | **0** | ❌ **Borrar inmediatamente** en Discord. |
| **Slot 42** | `:CryingMan:` | `1535682791755481141` | **0** | ❌ **Borrar inmediatamente** en Discord. |
| **Slot 43** | `:pixel_rip_tombstone:` | `1535682950056906752` | **0** | ❌ **Borrar inmediatamente** en Discord. |
| **Slot 44** | `:knowledge:` | `1535683001533337640` | **0** | ❌ **Borrar inmediatamente** en Discord. |
| **Slot 49** | `:MrIncredible:` | `1535683403158921338` | **0** | ❌ **Borrar inmediatamente** en Discord. |
| **Slot 50** | `:yb_angry2:` | `1535683502937350145` | **0** | ❌ **Borrar inmediatamente** en Discord. |

*(Total de slots que se liberan de forma 100% limpia sin impacto en el servidor: **13 slots**)*.

### 3.2. Emojis Polémicos o de Bajo Uso en Slots 1 al 50 (Candidatos Secundarios)
| Slot Actual | Nombre | Snowflake ID | Usos Totales | Motivo de Recomendación |
| :---: | :--- | :---: | :---: | :--- |
| **Slot 22** | `:Nazi:` | `1531002011682607301` | 10 (9 reacts) | ⚠️ Riesgo ToS de Discord / Meme superado. Borrar para liberar hueco seguro. |
| **Slot 23** | `:franco:` | `1531002139562872912` | 5 (5 reacts) | ⚠️ Riesgo ToS de Discord / Meme superado. Borrar para liberar hueco seguro. |
| **Slot 24** | `:Spain_empire:` | `1531002554656358584` | 9 (9 reacts) | ⚠️ Riesgo ToS de Discord / Meme superado. Borrar para liberar hueco seguro. |
| **Slot 10** | `:pepeCringe:` | `1530996221810966690` | 1 (1 reacts) | ⚠️ Uso residual único. Prescindible ante la falta de slots. |
| **Slot 15** | `:catpointandlaugh:` | `1530997580350357565` | 1 (1 reacts) | ⚠️ Uso residual único. Prescindible ante la falta de slots. |
| **Slot 20** | `:bros:` | `1531001502066413678` | 1 (0 reacts) | ⚠️ Uso residual único. Prescindible ante la falta de slots. |
| **Slot 34** | `:Trolled:` | `1535682153818357802` | 1 (0 reacts) | ⚠️ Uso residual único. Prescindible ante la falta de slots. |
| **Slot 35** | `:DwayneEyebrow:` | `1535682237817823362` | 1 (0 reacts) | ⚠️ Uso residual único. Prescindible ante la falta de slots. |
| **Slot 37** | `:emojigg_OMG:` | `1535682384450691153` | 1 (0 reacts) | ⚠️ Uso residual único. Prescindible ante la falta de slots. |
| **Slot 39** | `:uno_reverse:` | `1535682567968129095` | 1 (0 reacts) | ⚠️ Uso residual único. Prescindible ante la falta de slots. |
| **Slot 41** | `:shrug:` | `1535682710306029638` | 1 (1 reacts) | ⚠️ Uso residual único. Prescindible ante la falta de slots. |
| **Slot 45** | `:doomed:` | `1535683080294236220` | 1 (0 reacts) | ⚠️ Uso residual único. Prescindible ante la falta de slots. |
| **Slot 46** | `:wahhhhh:` | `1535683162628169760` | 1 (0 reacts) | ⚠️ Uso residual único. Prescindible ante la falta de slots. |

## 🛠️ 4. Ejecución Oficial de la Purga y Blindaje Completado (19 de Octubre de 2026)

### 4.1. Estrategia Ejecutada: Purga Directa de Sobrantes vía API REST
- En lugar del laborioso proceso de borrar y resubir emojis críticos (lo que habría roto sus Snowflake IDs en mensajes históricos y configuraciones de bots), se adoptó la **estrategia de reducción matemática exacta**:
  - Al reducir el censo de emojis estáticos a **exactamente 50 (50/50)**, Discord activa **todos y cada uno de los 50 emojis estáticos existentes**, sin importar su fecha o Snowflake ID.
  - Se eliminaron los **48 emojis estáticos fuera del Top 50** llamando a `DELETE /guilds/1446143936891715616/emojis/{emoji_id}` con `herramientas/discord_client.py`.

### 4.2. Registro de la Purga
1. **Purgados los 13 emojis muertos con 0 usos de la Sección 3.1**:
   - `:blob_off:`, `:goofy_ah_cat:`, `:pepecuerda:`, `:95_CryThumbsUp:`, `:bonk:`, `:bruh:`, `:what_in_the_hell:`, `:Cat_Sus:`, `:CryingMan:`, `:pixel_rip_tombstone:`, `:knowledge:`, `:MrIncredible:`, `:yb_angry2:`.
2. **Purgados los 35 emojis estáticos adicionales fuera del Top 50**:
   - `:bros:`, `:Trolled:`, `:DwayneEyebrow:`, `:emojigg_OMG:`, `:uno_reverse:`, `:doomed:`, `:wahhhhh:`, `:yb_ayo:`, `:pensivebetrayal:`, `:emojigg_HUH:`, `:cathink:`, `:4k_ultra_hd:`, `:BaldwinHand:`, `:dumbass_stare:`, `:PatrickLeash:`, `:oh_god:`, `:fruity_sus:`, `:Florkwhat:`, `:Tungtungtungsahur:`, `:nobodycares:`, `:Messirve:`, `:Mindblown:`, `:Autism:`, `:mortroll:`, `:blue_screen:`, `:emojigg_bot:`, `:Serious:`, `:POINT_GAY:`, `:emojigg_BAN:`, `:aura:`, `:ahegao:`, `:take_my_money:`, `:STFU:`, `:False:`, `:thankyou:`.
3. **Control Automático de Rate Limits**:
   - Se manejaron adecuadamente los límites de tasa (HTTP 429) de Discord con pausas y reintentos, completando la eliminación sin incidencias.

### 4.3. Verificación Final en Discord (76 Emojis Totales)
- **Censo Final Confirmado por API**:
  - **Emojis Estáticos**: **50 / 50** (100% correspondientes al Top 50 oficial).
  - **Emojis Animados**: **26 / 50** (100% seguros, 24 slots libres).
  - **Total Servidor**: **76 / 100**.
- **Emojis Críticos Verificados en Vivo**:
  - `<:Porro:1535685303317172305>` (Moneda del servidor): **Activo y 100% operativo**.
  - `:cooked:` (`1535726716901789726`): **Activo y 100% operativo**.
  - `:monkeythink:` (`1535684318993584219`): **Activo y 100% operativo**.
  - Los 6 Rangos de Brawl Stars (`:Ranked_Gold:` a `:Ranked_Pro:`): **Activos y 100% operativos**.
- **Copia de Seguridad Preservada**:
  - Todos los 124 emojis originales siguen respaldados permanentemente a 128x128 en `datos_locales/emojis_backup/` con su `manifest.json`.

---

## 🎞️ 5. Análisis de los 26 Emojis Animados (100% Seguros)

- **Estado**: 26 emojis animados subidos de un máximo de 50 en Free Tier.
- **Seguridad**: **100% Garantizada**. No es necesario borrar ni alterar ningún emoji animado.
- **Capacidad Disponible**: 24 slots libres para añadir nuevos GIFs o memes animados sin coste.

### 5.1. Ranking de Uso de Emojis Animados
| Pos | Emoji Animado | Nombre | Snowflake ID | Slot Actual | Usos Cuerpo | Usos Reacciones | Total Usos | Estado |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
|  1 | `<a:Reze:1535727967232069642>` | `:Reze:` | `1535727967232069642` | Slot 19 | 4 | 0 | **4** | 🟢 Seguro (< 50) |
|  2 | `<a:Thisisfine:1535679070312857672>` | `:Thisisfine:` | `1535679070312857672` | Slot 02 | 2 | 1 | **3** | 🟢 Seguro (< 50) |
|  3 | `<a:ZOOOM:1535729987116736554>` | `:ZOOOM:` | `1535729987116736554` | Slot 26 | 2 | 1 | **3** | 🟢 Seguro (< 50) |
|  4 | `<a:Donowall:1535679683918831676>` | `:Donowall:` | `1535679683918831676` | Slot 06 | 0 | 2 | **2** | 🟢 Seguro (< 50) |
|  5 | `<a:KEKWLaugh:1535679941059018903>` | `:KEKWLaugh:` | `1535679941059018903` | Slot 07 | 1 | 1 | **2** | 🟢 Seguro (< 50) |
|  6 | `<a:dead_spin:1535726486168932353>` | `:dead_spin:` | `1535726486168932353` | Slot 14 | 1 | 1 | **2** | 🟢 Seguro (< 50) |
|  7 | `<a:Think:1535729557469011968>` | `:Think:` | `1535729557469011968` | Slot 25 | 2 | 0 | **2** | 🟢 Seguro (< 50) |
|  8 | `<a:hello_wave:1535678953870725121>` | `:hello_wave:` | `1535678953870725121` | Slot 01 | 0 | 1 | **1** | 🟢 Seguro (< 50) |
|  9 | `<a:pain:1535679465383002192>` | `:pain:` | `1535679465383002192` | Slot 04 | 0 | 1 | **1** | 🟢 Seguro (< 50) |
| 10 | `<a:pepe_simp:1535679584819875950>` | `:pepe_simp:` | `1535679584819875950` | Slot 05 | 0 | 1 | **1** | 🟢 Seguro (< 50) |
| 11 | `<a:ai_baby:1535727719948623872>` | `:ai_baby:` | `1535727719948623872` | Slot 17 | 0 | 1 | **1** | 🟢 Seguro (< 50) |
| 12 | `<a:GalaxyBrainMeme:1535680100060766311>` | `:GalaxyBrainMeme:` | `1535680100060766311` | Slot 08 | 1 | 0 | **1** | 🟢 Seguro (< 50) |
| 13 | `<a:cat_bitting:1535680234207191100>` | `:cat_bitting:` | `1535680234207191100` | Slot 09 | 1 | 0 | **1** | 🟢 Seguro (< 50) |
| 14 | `<a:chadgif:1535680346199162982>` | `:chadgif:` | `1535680346199162982` | Slot 10 | 1 | 0 | **1** | 🟢 Seguro (< 50) |
| 15 | `<a:yummy:1535726899018338346>` | `:yummy:` | `1535726899018338346` | Slot 15 | 1 | 0 | **1** | 🟢 Seguro (< 50) |
| 16 | `<a:emojigg_67:1535729079657963661>` | `:emojigg_67:` | `1535729079657963661` | Slot 22 | 1 | 0 | **1** | 🟢 Seguro (< 50) |
| 17 | `<a:hulk_gif:1535679185803018361>` | `:hulk_gif:` | `1535679185803018361` | Slot 03 | 0 | 0 | **0** | 🟢 Seguro (< 50) |
| 18 | `<a:flashbang:1535680549660655616>` | `:flashbang:` | `1535680549660655616` | Slot 11 | 0 | 0 | **0** | 🟢 Seguro (< 50) |
| 19 | `<a:ACTUALLY_IM:1535680603179974678>` | `:ACTUALLY_IM:` | `1535680603179974678` | Slot 12 | 0 | 0 | **0** | 🟢 Seguro (< 50) |
| 20 | `<a:cat_boom:1535725821652770836>` | `:cat_boom:` | `1535725821652770836` | Slot 13 | 0 | 0 | **0** | 🟢 Seguro (< 50) |
| 21 | `<a:Scubbacat:1535727498602618890>` | `:Scubbacat:` | `1535727498602618890` | Slot 16 | 0 | 0 | **0** | 🟢 Seguro (< 50) |
| 22 | `<a:freaky_lick:1535727845014241320>` | `:freaky_lick:` | `1535727845014241320` | Slot 18 | 0 | 0 | **0** | 🟢 Seguro (< 50) |
| 23 | `<a:PanickedNo:1535728525431013437>` | `:PanickedNo:` | `1535728525431013437` | Slot 20 | 0 | 0 | **0** | 🟢 Seguro (< 50) |
| 24 | `<a:cornershaking:1535728585665548298>` | `:cornershaking:` | `1535728585665548298` | Slot 21 | 0 | 0 | **0** | 🟢 Seguro (< 50) |
| 25 | `<a:SpinningFish:1535729132208656395>` | `:SpinningFish:` | `1535729132208656395` | Slot 23 | 0 | 0 | **0** | 🟢 Seguro (< 50) |
| 26 | `<a:ononono:1535729205982269570>` | `:ononono:` | `1535729205982269570` | Slot 24 | 0 | 0 | **0** | 🟢 Seguro (< 50) |

---

## 📜 6. Trazabilidad y Mantenimiento Continuo (Regla Global §8 y §14)

- **Herramienta Operativa**: `herramientas/audit_emojis_telemetry.py` (ejecutable en cualquier momento para re-auditar el uso de emojis en tiempo real).
- **Copia de Seguridad**: `datos_locales/emojis_backup/` con `manifest.json` (respaldo total preservado).
- **Documentos de Referencia Vinculados**:
  - [`docs/EMOJIS_SERVIDOR.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/EMOJIS_SERVIDOR.md): Lore, categorías y significado cultural.
  - [`docs/INFO_SERVIDOR.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/docs/INFO_SERVIDOR.md): Estructura general de canales y roles.
  - [`herramientas/README.md`](file:///c:/Users/jose/OneDrive/Antigravity-general/Antigravity-discord/herramientas/README.md): Registro del script de telemetría.

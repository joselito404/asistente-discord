"""
Script de actualización de canales y mensajes de guía en Discord.
Actualiza los tópicos de canales y publica las guías fijadas en #⌨️comandos⌨️.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config_discord.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

headers = {
    "Authorization": f"Bot {config['token']}",
    "Content-Type": "application/json",
    "User-Agent": "AntigravityDiscordClient/1.0"
}

def api_request(endpoint, method="GET", data=None):
    url = f"https://discord.com/api/v10{endpoint}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content) if content.strip() else {}
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        print(f"Error {e.code} en {method} {endpoint}: {error_msg}")
        raise

def update_topics():
    topics = {
        "1549458785485987890": "🎰 Casino Oficial de Porros (Economia Asistente) • Apuesta mínima: 100 Porros (¡All-in libre!) • Comandos: /casino, /slots, /blackjack (/bj), /ruleta, /coinflip, /trabajar, /crimen, /robar, /salario",
        "1550894047382610081": "🎰 Sala 2 del Casino Oficial de Porros • Tiradas simultáneas sin esperas • /casino, /slots, /blackjack (/bj), /ruleta, /coinflip",
        "1549512919694442547": "🏪 Tienda e Inventario Oficial de Porros • Usa /tienda para comprar roles, pases de XP y Monster Blanco, /inventario para ver tus objetos, /usar para activarlos, /regalar para enviarlos y /ranking para ver el Top de ricos."
    }
    for cid, topic in topics.items():
        res = api_request(f"/channels/{cid}", method="PATCH", data={"topic": topic})
        print(f"✅ Tópico actualizado en #{res.get('name', cid)}: {topic[:60]}...")

def delete_message(channel_id, message_id):
    try:
        api_request(f"/channels/{channel_id}/messages/{message_id}", method="DELETE")
        print(f"🗑️ Mensaje {message_id} eliminado de #{channel_id}")
    except Exception as e:
        print(f"⚠️ No se pudo eliminar mensaje {message_id}: {e}")

def pin_message(channel_id, message_id):
    try:
        api_request(f"/channels/{channel_id}/pins/{message_id}", method="PUT")
        print(f"📌 Mensaje {message_id} fijado con éxito en #{channel_id}")
    except Exception as e:
        print(f"⚠️ No se pudo fijar mensaje {message_id}: {e}")

def post_guide_messages():
    cid = "1537584204169355295" # #⌨️comandos⌨️
    
    # 1. Obtener mensajes existentes de Jose o del bot en #⌨️comandos⌨️
    # Los pines conocidos:
    old_pin_jose = "1537586268953649195"
    old_pin_bot = "1550862273050976406"
    
    # Eliminar pines antiguos
    delete_message(cid, old_pin_jose)
    delete_message(cid, old_pin_bot)
    
    # También borrar mensajes sueltos de Jose si hay en los últimos 20
    recent = api_request(f"/channels/{cid}/messages?limit=25")
    for m in recent:
        # Si es de Jose y no es mensaje del sistema
        if m["author"]["id"] == "857923274771136522":
            delete_message(cid, m["id"])
            time.sleep(0.5)

    # 2. Contenido de PARTE 1 — GENERAL, NIVELES Y UTILIDADES (dividido en mensajes <= 1950 caracteres)
    part_1a = (
        "🤖 **ZONA DE COMANDOS DEL SERVIDOR (PARTE 1) — GENERAL, NIVELES Y UTILIDADES** @here\n"
        "Usa este canal para interactuar con los bots y comandos de la comunidad para mantener limpios los chats principales.\n\n"
        "---\n\n"
        "🏆 **Niveles y Progresión de Cakey Bot:**\n"
        "• `/rank [@usuario]` ➔ Consulta tu nivel, progreso de XP y tarjeta de rango actual.\n"
        "• `/leaderboard` ➔ Accede a la clasificación y ranking web del servidor.\n"
        "• *Detalles de XP:* Ganas experiencia escribiendo en el chat (+10% en <#1446143938044887052> y <#1455700883378536559>, +15% en <#1465060820814921950>), en llamadas de voz y compartiendo clips/memes. ¡Atentos a las cajas sorpresa de XP que caen en <#1543002685492568185>!\n\n"
        "🎨 **Asistente IA, Audio y Vanguardia (`@Asistente`):**\n"
        "• `/dibuja <prompt>` ➔ Genera arte e imágenes ilimitadas en alta definición con FLUX.1 (con botón Re-roll).\n"
        "• `/habla <texto>` ➔ Sintetiza voz ultrarrealista en el canal de voz activo.\n"
        "• `/geminilive` ➔ Inicia sesión interactiva de conversación por voz con IA en directo.\n"
        "• `/musica <búsqueda | URL>` ➔ Reproduce música en streaming de alta calidad en tu canal de voz.\n"
        "• `/cambiar_voz <estilo>` ➔ Personaliza la voz y tono del bot en llamadas.\n"
        "• `/pregunta <duda>` ➔ Consulta a la IA con búsqueda web en vivo y contexto del servidor.\n"
        "• `/recuerda <nota>` ➔ Guarda notas en la memoria persistente del asistente.\n"
        "• `/perfil [@usuario]` ➔ Genera una tarjeta de perfil analítica y estadística."
    )

    part_1b = (
        "🎲 **Entretenimiento, Juegos y Minijuegos:**\n"
        "• `/trivial` y `/ranking_trivial` ➔ Trivial cultural y de gaming interactivo con podio en vivo.\n"
        "• `/tres_en_raya [@rival]` ➔ Reta a otro miembro a tres en raya con botones interactivos.\n"
        "• `/conecta4 [@rival]` ➔ Duelo clásico de conecta 4 con interfaz de tablero.\n"
        "• `/tictactoe [@usuario]` ➔ Minijuego clásico con Cakey Bot.\n"
        "• `/8ball <pregunta>` ➔ Hazle una pregunta a la bola 8 mágica.\n"
        "• `/fact` | `/animequote` ➔ Datos curiosos o frases célebres aleatorias de anime.\n"
        "• `/rp ship [@usuario] [usuario2]` ➔ Medidor de compatibilidad entre dos personas.\n\n"
        "🎂 **Sistema de Cumpleaños:**\n"
        "• `/birthday set <mes> <día>` ➔ Registra o edita tu fecha de cumpleaños.\n"
        "• `/birthday list` ➔ Abre el calendario de cumpleaños del servidor.\n"
        "• `/birthday next` ➔ Muestra quiénes son los próximos en cumplir años.\n\n"
        "🎭 **Auto-Roles, Sugerencias y Comunidad:**\n"
        "• Pásate por <#1537575617111920782> para asignarte tus roles de juegos y hobbies.\n"
        "• `/sugerencia [idea]` ➔ Abre el modal nativo de Discord V2 de Sugerencias 2.0 (o envía tu propuesta) a <#1537582722812481696> con barra dinámica de votos, hilos automáticos de debate y veredicto IA.\n"
        "• `/panel_sugerencias` ➔ Publica y fija el buzón interactivo permanente con botón `[💡 Proponer Idea]` en <#1537582722812481696> *(exclusivo Administradores)*.\n"
        "• `/serverinfo` | `/userinfo [@usuario]` | `/avatar [@usuario]` ➔ Estadísticas y fotos de perfil.\n\n"
        "---\n"
        "-# ℹ️ Para la guía oficial de Economía, Casino y Tienda de Porros, consulta la **Parte 2** fijada a continuación."
    )

    # 3. Contenido de PARTE 2 — ECONOMÍA OFICIAL DE PORROS Y CASINO
    part_2a = (
        "💰 **ZONA DE COMANDOS DEL SERVIDOR (PARTE 2) — ECONOMÍA Y CASINO NATIVO** @here\n"
        "> 📍 *Todos los comandos de economía y casino son gestionados por `@Economia Asistente` y se usan exclusivamente en <#1549458785485987890>, <#1550894047382610081> y <#1549512919694442547>.*\n\n"
        "---\n\n"
        "### 🏦 Banca, Cartera y Clasificación\n"
        "• **`/balance [usuario]`** ➔ Consulta tus <:Porro:1535685303317172305> Porros en mano, banco, patrimonio total y el bote comunitario acumulado.\n"
        "• **`/depositar <cantidad | all>`** ➔ Guarda Porros en tu cuenta bancaria *(¡100% inmune a robos de otros usuarios!)*.\n"
        "• **`/retirar <cantidad | all>`** ➔ Saca Porros del banco a tu cartera para apostar o comprar.\n"
        "• **`/transferir <@usuario> <cantidad>`** ➔ Envía Porros en efectivo directamente a otro miembro sin comisiones.\n"
        "• **`/ranking`** ➔ Clasificación interactiva en vivo con menú selector (*Patrimonio Total*, *Efectivo* y *Banco*).\n\n"
        "### 💼 Ingresos, Salarios y Delitos\n"
        "• **`/trabajar`** *(cada 4h)* ➔ Gana entre **1.000 y 2.500 Porros** legales (+ tu multiplicador de rol de nivel: `+10%` a `+40%`).\n"
        "• **`/salario`** *(cada 24h, acumulativo)* ➔ Cobra tu sueldo diario progresivo según tu **nivel exacto** en el servidor (a partir de Nivel 10) + bonus de Podio (`🥇 Top 1`, `🥈 Top 2`, `🥉 Top 3`). Se acumula si tardas días con decaimiento del 5%.\n"
        "• **`/crimen`** *(cada 12h)* ➔ Golpe arriesgado: **50% de éxito** (**1.800 a 3.500 Porros** × bono nivel) o **50% de fallo** (multa del **10%** de tu efectivo, mín. 500 Porros, aportando el 3% al bote).\n"
        "• **`/robar <@usuario>`** *(cada 24h)* ➔ Atraca la cartera de alguien (**50% de éxito**, robas del **20% al 33%** de su efectivo). Si fallas o la víctima tiene `🛡️ Cartera Blindada`, pagas un **15% de multa** (**10%** indemnización a la víctima y **5%** al bote)."
    )

    part_2b = (
        "### 🏪 Tienda Oficial, Inventario y Regalos (En <#1549512919694442547>)\n"
        "• **`/tienda`** ➔ Catálogo interactivo: compra roles permanentes (`🛡️ Cartera Blindada`, `🚬 Camello del Barrio`, `🎰 Ludópata Rehabilitado`, `👑 Aura de XP`), coleccionables (`🚬 Porro de Oro`), pases temporales de XP y **`🥤 Monster Blanco`** (*resetea al instante tus cooldowns de `/trabajar`, `/crimen` y `/robar`*).\n"
        "• **`/inventario [usuario]`** ➔ Revisa tus objetos guardados y la cuenta atrás exacta de tus pases de XP activos (con botón para fardar en público).\n"
        "• **`/usar <artículo>`** ➔ Tómate un `🥤 Monster Blanco` o activa cuando quieras tus pases de XP (`24h`, `7 días` o `30 días`).\n"
        "• **`/regalar <@usuario> <artículo> [cantidad]`** ➔ Regala objetos, pases o latas de Monster Blanco a un amigo.\n\n"
        "### 🎰 Casino Oficial (En <#1549458785485987890> y <#1550894047382610081>)\n"
        "• **`/casino`** ➔ Centro de control general: consulta el bote acumulado, reglas y RTP oficial de los 4 juegos.\n"
        "• **`/slots <apuesta | all>`** ➔ Tragaperras 5x3 limpia (3 Horizontales + 6 Diagonales rectas de 3 casillas), Comodín WILD, Bote Progresivo (Grand/Mini en Línea Centro) y Pantalla Completa x500 (**RTP 110%**, apuesta mín: 100).\n"
        "• **`/blackjack <apuesta | all>`** *(o `/bj`)* ➔ Blackjack 21 interactivo contra la casa (6 barajas, crupier se planta en 17, Blackjack natural paga 3:2, pedir, plantarse y doblar).\n"
        "• **`/ruleta <apuesta | all> <suerte>`** ➔ Ruleta europea 37 casillas (rojo/negro, par/impar, docenas, columnas y pleno 35:1) con botones de re-apuesta rápida.\n"
        "• **`/coinflip <apuesta | all> <cara | cruz> [@rival]`** ➔ Cara o cruz rápido contra la casa (PvE 50/50) o duelos directos 1v1 con fondos retenidos contra otro miembro (PvP).\n\n"
        "---\n"
        "-# 💎 Servidor libre e independiente de UnbelievaBoat. Moneda oficial: Porros <:Porro:1535685303317172305>."
    )

    print("Enviando mensajes de guía...")
    m1a = api_request(f"/channels/{cid}/messages", method="POST", data={"content": part_1a})
    time.sleep(1)
    m1b = api_request(f"/channels/{cid}/messages", method="POST", data={"content": part_1b})
    time.sleep(1)
    m2a = api_request(f"/channels/{cid}/messages", method="POST", data={"content": part_2a})
    time.sleep(1)
    m2b = api_request(f"/channels/{cid}/messages", method="POST", data={"content": part_2b})
    time.sleep(1)

    print("Fijando mensajes principales...")
    # Fijamos los encabezados principales (Parte 1 y Parte 2)
    pin_message(cid, m1a["id"])
    time.sleep(1)
    pin_message(cid, m2a["id"])

    print("🎉 Guías publicadas y fijadas con éxito en #⌨️comandos⌨️!")

if __name__ == "__main__":
    print("--- 1. Actualizando Tópicos de Canales ---")
    update_topics()
    print("\n--- 2. Publicando y Fijando Guías en #⌨️comandos⌨️ ---")
    post_guide_messages()
    print("\n✅ Toda la operación ha finalizado con éxito.")

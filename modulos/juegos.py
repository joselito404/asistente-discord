"""
Subsistema de Juegos y Entretenimiento para el bot 'Asistente':
- Steam Store en vivo (fetch_steam_game, get_steam_query_ctx, SteamView) y El Tribunal Gaming (get_tribunal_query_ctx, TribunalView).
- Trivial del Servidor con banco de 110+ preguntas y generación en vivo por Gemini IA (TriviaView, generate_gemini_trivia_question, handle_next_trivia).
- Tres en Raya interactivo PvP/PvE con algoritmo Minimax exhaustivo (TicTacToeView, get_tictactoe_bot_move).
- Conecta 4 interactivo PvP/PvE con IA heurística táctica (Connect4View, get_connect4_bot_move).
- Ajedrez contra Asistente con python-chess, Stockfish (4 niveles de ELO) y comentarios de Gemini (ChessGame, ChessView, chess_try_typed_move).
"""

import asyncio
import collections
import json
import random
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
import discord

try:
    import chess
    import chess.engine
except Exception as _chess_import_err:
    chess = None
    print(f"Aviso: python-chess no disponible ({_chess_import_err}). /ajedrez desactivado.")


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


def _bot_log(msg: str):
    bs = _bs()
    log_fn = getattr(bs, "bot_log", print)
    log_fn(msg)


# ==========================================
# STEAM STORE & EL TRIBUNAL GAMING
# ==========================================

def fetch_steam_game(query: str) -> dict:
    """Busca en Steam Store y devuelve ficha completa con precios en EUR, descuento y detalles."""
    try:
        encoded = urllib.parse.quote(query.strip())
        search_url = f"https://store.steampowered.com/api/storesearch/?term={encoded}&l=spanish&cc=ES"
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("items", [])
            if not items:
                return None
            app_id = items[0]["id"]

        detail_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=es&l=spanish"
        req2 = urllib.request.Request(detail_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req2, timeout=6) as resp2:
            d = json.loads(resp2.read().decode("utf-8"))
            game_data = d.get(str(app_id), {}).get("data", {})
            return game_data
    except Exception as e:
        print(f"Error consultando Steam Store: {e}")
        return None


def get_tribunal_query_ctx(text: str) -> str:
    """Busca menciones a juegos de El Tribunal Gaming y devuelve su ficha resumida."""
    low = text.lower()
    if not any(k in low for k in ["tribunal", "nota", "veredicto", "muro", "vergüenza", "cooperativo", "salvavidas", "guerreros", "pesados"]):
        return ""
    bs = _bs()
    t_data = getattr(bs, "tribunal_data", {"single": [], "coop": []})
    for g in t_data.get("single", []):
        t = g.get("title", "")
        if len(t) > 3 and t.lower() in low:
            hltb = g.get("hltb", {})
            return f"\n[FICHA EN EL TRIBUNAL GAMING: '{t}']:\n  * Metacritic: {g.get('metacritic', 'N/D')}\n  * HLTB: Historia {hltb.get('main', 'N/D')}, Completo {hltb.get('completionist', 'N/D')}\n  * Géneros: {', '.join(g.get('genres', [])[:3])}\n  * Web oficial: https://tribunal-gaming.vercel.app"
    for g in t_data.get("coop", []):
        t = g.get("title", "")
        if len(t) > 3 and t.lower() in low:
            return f"\n[FICHA COOPERATIVO EN EL TRIBUNAL GAMING: '{t}']:\n  * Categoría: {g.get('category', 'Coop')}\n  * Estado: {g.get('availability')}\n  * Rendimiento: {g.get('perf', 'N/D')}\n  * Web oficial: https://tribunal-gaming.vercel.app"
    return ""


def get_steam_query_ctx(text: str) -> str:
    """Detecta si se pregunta por el precio o ficha de Steam de un juego y aporta datos frescos."""
    low = text.lower()
    if not any(k in low for k in ["steam", "precio", "cuanto vale", "cuánto vale", "cuanto cuesta", "cuánto cuesta", "oferta", "descuento"]):
        return ""
    clean = re.sub(r"\b(steam|precio|de|cuanto|cuánto|vale|cuesta|oferta|descuento|en|el|juego|porfa|asistente)\b", "", low).strip()
    if len(clean) >= 3:
        game = fetch_steam_game(clean)
        if game:
            p = game.get("price_overview", {})
            price_str = (
                f"{p.get('final_formatted', 'N/D')}" + (f" (-{p.get('discount_percent')}% oferta)" if p.get("discount_percent", 0) > 0 else "")
                if p
                else ("Gratis" if game.get("is_free") else "Precio no disponible")
            )
            meta = game.get("metacritic", {}).get("score", "Sin nota")
            return f"\n[FICHA STEAM STORE EN VIVO: '{game.get('name')}']:\n  * Precio actual: {price_str}\n  * Metacritic: {meta}\n  * URL: https://store.steampowered.com/app/{game.get('steam_appid')}/"
    return ""


class SteamView(discord.ui.View):
    """Botones oficiales de acceso directo a Steam Store y Comunidad."""

    def __init__(self, app_id: int or str):
        super().__init__(timeout=None)
        if app_id:
            self.add_item(discord.ui.Button(label="Abrir en Steam", url=f"https://store.steampowered.com/app/{app_id}/", emoji="🛒"))
            self.add_item(discord.ui.Button(label="Comunidad & Guías", url=f"https://steamcommunity.com/app/{app_id}/", emoji="👥"))


class TribunalView(discord.ui.View):
    """Botones interactivos para El Tribunal Gaming."""

    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(discord.ui.Button(label="Ver en Web", url="https://tribunal-gaming.vercel.app", emoji="🌐"))

    @discord.ui.button(label="Juego Aleatorio", style=discord.ButtonStyle.secondary, emoji="🎲")
    async def random_game_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        bs = _bs()
        t_data = getattr(bs, "tribunal_data", {"single": [], "coop": []})
        pool = t_data.get("single", []) + t_data.get("coop", [])
        if not pool:
            await interaction.response.send_message("No hay juegos en la base de datos.", ephemeral=True)
            return
        g = random.choice(pool)
        title = g.get("title", "Juego")
        if "metacritic" in g:
            meta = g.get("metacritic", "N/D")
            desc = g.get("description", "")[:180]
            hltb = g.get("hltb", {}).get("main", "N/D")
            msg = f"🎲 **Recomendación Aleatoria:** **{title}**\n⭐ Metacritic: **{meta}** | ⏱️ Historia: **{hltb}**\n_{desc}..._"
        else:
            cat = g.get("category", "Coop")
            perf = g.get("perf", "Sin notas")
            msg = f"🎲 **Cooperativo Aleatorio:** **{title}** ({cat})\n⚙️ Rendimiento: {perf}"
        await interaction.response.send_message(msg, ephemeral=False)


# ==========================================
# TRIVIAL DEL SERVIDOR (BANCO 110+ & GEMINI IA)
# ==========================================

RECENT_TRIVIA_IDS = collections.deque(maxlen=40)

CATEGORY_ALIASES = {
    "all": "all",
    "manhwa": "manhwa",
    "manhwas": "manhwa",
    "anime": "manhwa",
    "gaming": "gaming",
    "videojuegos": "gaming",
    "juegos": "gaming",
    "tribunal": "tribunal",
    "lore": "lore",
    "servidor": "lore",
    "general": "general",
    "cultura": "general",
}

TRIVIA_CATEGORIES_INFO = {
    "all": ("todas las categorías de cultura pop, videojuegos, anime, manhwas y curiosidades generales", "🎲 Trivial General"),
    "manhwa": ("manhwas coreanos (Solo Leveling, The Greatest Estate Developer, Omniscient Reader, Tower of God, Lookism) y series icónicas de anime", "🎌 Manhwas & Anime"),
    "gaming": ("videojuegos célebres, FromSoftware (Elden Ring, Dark Souls), Hollow Knight, Brawl Stars, Nintendo, RPGs y clásicos", "🎮 Videojuegos"),
    "tribunal": ("El Tribunal Gaming (juegos cooperativos, Muro de la Vergüenza, rendimiento técnico, Iván racerwasp y Jose)", "⚖️ El Tribunal Gaming"),
    "lore": ("lore y anécdotas del servidor de Discord 'LOS MONGOLOS DEL SANVI', Terreneiror (Lázaro) y la tragaperras, Joselito, Iván, Cakey Bot y UnbelievaBoat", "📜 Lore del Servidor & Colegas"),
    "general": ("cultura general, ciencia, astronomía, historia, tecnología y geografía mundial", "🧠 Cultura General"),
}


def generate_gemini_trivia_question(category_key: str = "all") -> dict | None:
    """Genera dinámicamente con IA de Gemini una pregunta inédita de opción múltiple estructurada en JSON."""
    cat_key_clean = CATEGORY_ALIASES.get(category_key.lower(), category_key.lower())
    cat_desc, cat_name = TRIVIA_CATEGORIES_INFO.get(cat_key_clean, TRIVIA_CATEGORIES_INFO["all"])

    prompt = (
        f"Eres el creador de preguntas de trivial para el servidor de Discord 'LOS MONGOLOS DEL SANVI'.\n"
        f"Genera exactamente UNA pregunta inédita, entretenida y de dificultad media/alta sobre la temática: {cat_desc}.\n"
        f"Requisitos obligatorios:\n"
        f"1. La pregunta debe ser clara y en español.\n"
        f"2. Debe tener exactamente 4 opciones de respuesta verosímiles en una lista de texto (ninguna repetida).\n"
        f"3. Solo una opción es la correcta.\n"
        f"4. Proporciona una explicación breve (1-2 frases) del porqué de la respuesta correcta.\n"
        f"5. Devuelve EXCLUSIVAMENTE un objeto JSON válido con los campos:\n"
        f"   {{\n"
        f"     \"category\": \"{cat_key_clean if cat_key_clean != 'all' else 'general'}\",\n"
        f"     \"category_name\": \"{cat_name}\",\n"
        f"     \"question\": \"¿Texto de la pregunta?\",\n"
        f"     \"options\": [\"Opción A\", \"Opción B\", \"Opción C\", \"Opción D\"],\n"
        f"     \"correct\": 0,\n"
        f"     \"explanation\": \"Explicación concisa.\"\n"
        f"   }}\n"
        f"NO incluyas bloques de código markdown, comillas de inicio ni texto adicional fuera del JSON."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 600,
            "responseMimeType": "application/json",
        },
    }
    data = json.dumps(payload).encode("utf-8")

    bs = _bs()
    gemini_key = getattr(bs, "GEMINI_KEY", None)
    if not gemini_key:
        return None

    avail_fn = getattr(bs, "get_available_models", lambda: [])
    cooldown_fn = getattr(bs, "mark_model_cooldown", lambda m, s=60: None)

    for model_name in avail_fn():
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode("utf-8"))
            text = res.get("candidates", [])[0]["content"]["parts"][0]["text"].strip()
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
                text = re.sub(r"\s*```$", "", text)
            q_data = json.loads(text)
            if (
                isinstance(q_data, dict)
                and "question" in q_data
                and isinstance(q_data.get("options"), list)
                and len(q_data["options"]) == 4
                and isinstance(q_data.get("correct"), int)
                and 0 <= q_data["correct"] <= 3
                and "explanation" in q_data
            ):
                q_data["category_name"] = cat_name
                q_data["category"] = cat_key_clean if cat_key_clean != "all" else "general"
                return q_data
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503):
                cooldown_fn(model_name, 60)
        except Exception:
            pass

    return None


async def handle_next_trivia(interaction: discord.Interaction, category_key: str = "all"):
    """Lanza la siguiente pregunta de trivial con soporte dinámico de IA si se agota el banco local."""
    await interaction.response.defer()
    bs = _bs()
    load_fn = getattr(bs, "load_trivia_data", lambda: [])
    trivia_pool = load_fn()
    cat_val = CATEGORY_ALIASES.get(category_key.lower(), category_key.lower())

    question = None
    ia_notice = ""

    if cat_val != "all":
        pool = [q for q in trivia_pool if CATEGORY_ALIASES.get(q.get("category", "").lower(), q.get("category", "").lower()) == cat_val]
    else:
        pool = trivia_pool

    if not pool:
        pool = trivia_pool

    unplayed = [q for q in pool if q.get("id") not in RECENT_TRIVIA_IDS]
    if unplayed:
        question = random.choice(unplayed)
    else:
        # Fallback dinámico a Gemini al agotarse las preguntas inéditas locales
        gen_fn = getattr(bs, "generate_gemini_trivia_question", generate_gemini_trivia_question)
        gemini_q = await asyncio.to_thread(gen_fn, cat_val)
        if gemini_q:
            question = gemini_q
            ia_notice = "✨ *Preguntas locales agotadas recientemente. ¡Pregunta inédita generada en vivo por Gemini IA!*\n\n"
        elif pool:
            question = random.choice(pool)

    if not question:
        await interaction.followup.send("❌ No se pudo cargar una nueva pregunta de Trivial.", ephemeral=True)
        return

    if "id" in question:
        RECENT_TRIVIA_IDS.append(question["id"])

    letters = ["🇦", "🇧", "🇨", "🇩"]
    opts_txt = "\n".join([f"{letters[i]} **{opt}**" for i, opt in enumerate(question["options"][:4])])

    embed = discord.Embed(
        title=f"❓ Trivial: {question.get('category_name', 'Pregunta')}",
        description=f"{ia_notice}**{question['question']}**\n\n{opts_txt}\n\n*Pulsa el botón con la respuesta correcta abajo. ¡El primero en acertar se lleva 10 puntos!*",
        color=0x3B82F6,
    )
    embed.set_footer(text="Trivial Asistente • 60 segundos para responder • /ranking_trivial")
    new_view = TriviaView(question, interaction.user.id, category_key)
    msg = await interaction.followup.send(embed=embed, view=new_view, wait=True)
    new_view.message = msg


class TriviaView(discord.ui.View):
    """Botonera interactiva para rondas de preguntas de Trivial."""

    def __init__(self, question_data: dict, author_id: int, category_key: str = "all"):
        super().__init__(timeout=60)
        self.question_data = question_data
        self.author_id = author_id
        self.category_key = category_key
        self.answered = False
        self.message: discord.Message = None

        letters = ["A", "B", "C", "D"]
        for i, opt in enumerate(question_data.get("options", [])[:4]):
            btn = discord.ui.Button(
                label=f"{letters[i]}: {opt[:70]}",
                style=discord.ButtonStyle.primary,
            )
            btn.callback = self.make_callback(i)
            self.add_item(btn)

    def make_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            if not self.message and interaction.message:
                self.message = interaction.message
            if self.answered:
                await interaction.response.send_message("⚠️ Esta pregunta ya ha sido respondida.", ephemeral=True)
                return
            self.answered = True

            for item in self.children:
                item.disabled = True

            correct_idx = self.question_data.get("correct", 0)
            is_correct = index == correct_idx
            user = interaction.user
            uid_str = str(user.id)

            bs = _bs()
            u_mem = getattr(bs, "user_memory", {})
            save_mem_fn = getattr(bs, "save_user_memory", lambda d: None)

            if uid_str not in u_mem:
                u_mem[uid_str] = {
                    "name": user.display_name,
                    "display_name": user.display_name,
                    "username": user.name,
                    "role_in_server": user.top_role.name if getattr(user, "top_role", None) else "Miembro",
                    "fav_genres": [],
                    "fav_works": [],
                    "notes": [],
                    "trivia_points": 0,
                }
            else:
                u_mem[uid_str]["display_name"] = user.display_name
                u_mem[uid_str]["name"] = user.display_name

            if correct_idx < len(self.children):
                self.children[correct_idx].style = discord.ButtonStyle.success
            if not is_correct and index < len(self.children):
                self.children[index].style = discord.ButtonStyle.danger

            pts_gain = 10 if is_correct else 0
            u_mem[uid_str]["trivia_points"] = u_mem[uid_str].get("trivia_points", 0) + pts_gain
            save_mem_fn(u_mem)
            total_pts = u_mem[uid_str]["trivia_points"]

            color = 0x22C55E if is_correct else 0xEF4444
            title = "🎉 ¡RESPUESTA CORRECTA! (+10 pts)" if is_correct else "❌ ¡RESPUESTA INCORRECTA!"
            status_desc = (
                f"**{user.display_name}** acertó: **{self.question_data['options'][correct_idx]}**"
                if is_correct
                else f"**{user.display_name}** eligió '{self.question_data['options'][index]}', pero la correcta era: **{self.question_data['options'][correct_idx]}**"
            )

            # Botón interactivo para continuar jugando con la siguiente pregunta
            next_btn = discord.ui.Button(label="🔄 Siguiente Pregunta", style=discord.ButtonStyle.secondary, row=2)

            async def next_callback(next_interaction: discord.Interaction):
                next_btn.disabled = True
                try:
                    await next_interaction.message.edit(view=self)
                except Exception:
                    pass
                await handle_next_trivia(next_interaction, self.category_key)

            next_btn.callback = next_callback
            self.add_item(next_btn)

            embed = discord.Embed(
                title=title,
                description=f"{status_desc}\n\n💡 **Explicación:** {self.question_data.get('explanation', '')}\n\n🏆 Puntos acumulados de {user.display_name}: **{total_pts} pts**",
                color=color,
            )
            embed.set_footer(text=f"Categoría: {self.question_data.get('category_name', 'Trivial')} • Usa /ranking_trivial o pulsa Siguiente Pregunta")
            await interaction.response.edit_message(embed=embed, view=self)

        return callback

    async def on_timeout(self):
        if not self.answered:
            self.answered = True
            for item in self.children:
                item.disabled = True
            correct_idx = self.question_data.get("correct", 0)
            if correct_idx < len(self.children):
                self.children[correct_idx].style = discord.ButtonStyle.success

            next_btn = discord.ui.Button(label="🔄 Siguiente Pregunta", style=discord.ButtonStyle.secondary, row=2)

            async def next_callback(next_interaction: discord.Interaction):
                next_btn.disabled = True
                try:
                    await next_interaction.message.edit(view=self)
                except Exception:
                    pass
                await handle_next_trivia(next_interaction, self.category_key)

            next_btn.callback = next_callback
            self.add_item(next_btn)

            if self.message:
                try:
                    embed = discord.Embed(
                        title="⌛ Tiempo Agotado",
                        description=f"Se acabaron los 60 segundos.\n\nLa respuesta correcta era: **{self.question_data['options'][correct_idx]}**\n\n💡 **Explicación:** {self.question_data.get('explanation', '')}",
                        color=0x6B7280,
                    )
                    embed.set_footer(text=f"Categoría: {self.question_data.get('category_name', 'Trivial')} • Usa /ranking_trivial o pulsa Siguiente Pregunta")
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    pass


# ==========================================
# MOTOR INTERACTIVO DE TRES EN RAYA (TIC-TAC-TOE)
# ==========================================

def check_ttt_winner_and_line(board: list) -> tuple:
    """Comprueba si hay 3 en raya en el tablero y devuelve (ganador, tupla_linea)."""
    lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Filas
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Columnas
        (0, 4, 8), (2, 4, 6),             # Diagonales
    ]
    for a, b, c in lines:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a], (a, b, c)
    return None, None


def tictactoe_minimax(board: list, is_maximizing: bool, depth: int = 0) -> int:
    """Evaluación Minimax exhaustiva para IA de Tres en Raya con ponderación de profundidad."""
    winner, _ = check_ttt_winner_and_line(board)
    if winner == "O":
        return 10 - depth
    elif winner == "X":
        return depth - 10
    elif "" not in board:
        return 0

    if is_maximizing:
        best = -1000
        for i in range(9):
            if board[i] == "":
                board[i] = "O"
                val = tictactoe_minimax(board, False, depth + 1)
                board[i] = ""
                best = max(best, val)
        return best
    else:
        best = 1000
        for i in range(9):
            if board[i] == "":
                board[i] = "X"
                val = tictactoe_minimax(board, True, depth + 1)
                board[i] = ""
                best = min(best, val)
        return best


def get_tictactoe_bot_move(board: list) -> int:
    """Devuelve la mejor casilla para el bot (O) usando victoria inmediata, bloqueo y Minimax."""
    # 1. Comprobar victoria inmediata del bot
    for i in range(9):
        if board[i] == "":
            board[i] = "O"
            if check_ttt_winner_and_line(board)[0] == "O":
                board[i] = ""
                return i
            board[i] = ""

    # 2. Bloquear victoria inmediata del rival (X)
    for i in range(9):
        if board[i] == "":
            board[i] = "X"
            if check_ttt_winner_and_line(board)[0] == "X":
                board[i] = ""
                return i
            board[i] = ""

    # 3. Minimax
    best_score = -1000
    best_move = -1
    for i in range(9):
        if board[i] == "":
            board[i] = "O"
            score = tictactoe_minimax(board, False, depth=1)
            board[i] = ""
            if score > best_score:
                best_score = score
                best_move = i
    return best_move if best_move != -1 else board.index("")


class TicTacToeButton(discord.ui.Button):
    def __init__(self, index: int, row: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=row)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view
        await view.process_click(interaction, self.index)


class TicTacToeView(discord.ui.View):
    """Botonera interactiva en cuadrícula 3x3 para Tres en Raya."""

    def __init__(self, player_x: discord.User | discord.Member, player_o: discord.User | discord.Member | None):
        super().__init__(timeout=120)
        self.player_x = player_x
        self.player_o = player_o
        self.is_pve = player_o is None
        self.board = [""] * 9
        self.current_turn = "X"
        self.finished = False
        self.winner = None
        self.winning_line = None
        self.message: discord.Message = None

        for i in range(9):
            row = i // 3
            self.add_item(TicTacToeButton(i, row))

    def build_embed(self) -> discord.Embed:
        if self.is_pve:
            rival_desc = f"❌ **{self.player_x.display_name}** vs ⭕ **Asistente (IA)**"
        else:
            rival_desc = f"❌ **{self.player_x.display_name}** vs ⭕ **{self.player_o.display_name}**"

        if self.finished:
            if self.winner == "X":
                title = f"🏆 ¡Victoria de {self.player_x.display_name}!"
                desc = f"{rival_desc}\n\n🎉 ¡**{self.player_x.display_name}** (❌) ha ganado la partida formando 3 en raya!"
                color = 0x22C55E
            elif self.winner == "O":
                winner_name = "Asistente" if self.is_pve else self.player_o.display_name
                title = f"🏆 ¡Victoria de {winner_name}!"
                desc = f"{rival_desc}\n\n🎉 ¡**{winner_name}** (⭕) ha ganado la partida formando 3 en raya!"
                color = 0x3B82F6
            elif self.winner == "tie":
                title = "🤝 ¡Empate!"
                desc = f"{rival_desc}\n\nTablero completo sin ganador. ¡Tablas bien disputadas!"
                color = 0xF59E0B
            else:
                title = "⌛ Partida finalizada"
                desc = f"{rival_desc}\n\nLa partida ha finalizado."
                color = 0x6B7280
        else:
            turn_name = self.player_x.display_name if self.current_turn == "X" else ("Asistente" if self.is_pve else self.player_o.display_name)
            symbol = "❌" if self.current_turn == "X" else "⭕"
            title = f"🎮 Tres en Raya — Turno de {symbol} {turn_name}"
            desc = f"{rival_desc}\n\nEs el turno de **{turn_name}** ({symbol}). Pulsa una casilla vacía para mover."
            color = 0x8B5CF6

        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text="Tres en Raya interactivo • /tres_en_raya • 120s de inactividad")
        return embed

    def update_buttons(self):
        for item in self.children:
            if isinstance(item, TicTacToeButton):
                val = self.board[item.index]
                if val == "X":
                    item.label = "❌"
                    item.style = discord.ButtonStyle.danger
                    item.disabled = True
                elif val == "O":
                    item.label = "⭕"
                    item.style = discord.ButtonStyle.primary
                    item.disabled = True
                else:
                    item.label = "\u200b"
                    item.style = discord.ButtonStyle.secondary
                    item.disabled = self.finished

        if self.winning_line:
            for idx in self.winning_line:
                self.children[idx].style = discord.ButtonStyle.success

    async def process_click(self, interaction: discord.Interaction, index: int):
        if not self.message and interaction.message:
            self.message = interaction.message
        if self.finished:
            await interaction.response.send_message("⚠️ Esta partida ya ha concluido.", ephemeral=True)
            return

        if self.current_turn == "X":
            if interaction.user.id != self.player_x.id:
                await interaction.response.send_message(f"❌ No es tu turno. Le toca a {self.player_x.display_name} (❌).", ephemeral=True)
                return
        else:
            if self.is_pve:
                await interaction.response.send_message("❌ Es el turno del bot Asistente.", ephemeral=True)
                return
            if interaction.user.id != self.player_o.id:
                await interaction.response.send_message(f"❌ No es tu turno. Le toca a {self.player_o.display_name} (⭕).", ephemeral=True)
                return

        if self.board[index] != "":
            await interaction.response.send_message("❌ Esa casilla ya está ocupada.", ephemeral=True)
            return

        self.board[index] = self.current_turn
        win, line = check_ttt_winner_and_line(self.board)
        if win:
            self.finished = True
            self.winner = win
            self.winning_line = line
        elif "" not in self.board:
            self.finished = True
            self.winner = "tie"
        else:
            if self.current_turn == "X":
                self.current_turn = "O"
                if self.is_pve:
                    bot_move = get_tictactoe_bot_move(self.board)
                    if bot_move is not None:
                        self.board[bot_move] = "O"
                        bot_win, bot_line = check_ttt_winner_and_line(self.board)
                        if bot_win:
                            self.finished = True
                            self.winner = bot_win
                            self.winning_line = bot_line
                        elif "" not in self.board:
                            self.finished = True
                            self.winner = "tie"
                        else:
                            self.current_turn = "X"
            else:
                self.current_turn = "X"

        self.update_buttons()
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if not self.finished:
            self.finished = True
            self.winner = "timeout"
            for item in self.children:
                item.disabled = True
            embed = self.build_embed()
            embed.title = "⌛ Partida Cancelada por Inactividad"
            embed.description += "\n\n*Han transcurrido 2 minutos sin jugadas.*"
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    pass


# ==========================================
# MOTOR INTERACTIVO DE CONECTA 4
# ==========================================

def check_connect4_winner(board: list) -> tuple:
    """Comprueba 4 en raya (horizontal, vertical, diagonal) y devuelve (ganador, celdas_ganadoras)."""
    # Horizontal
    for r in range(6):
        for c in range(4):
            if board[r][c] != 0 and board[r][c] == board[r][c + 1] == board[r][c + 2] == board[r][c + 3]:
                return board[r][c], [(r, c), (r, c + 1), (r, c + 2), (r, c + 3)]
    # Vertical
    for r in range(3):
        for c in range(7):
            if board[r][c] != 0 and board[r][c] == board[r + 1][c] == board[r + 2][c] == board[r + 3][c]:
                return board[r][c], [(r, c), (r + 1, c), (r + 2, c), (r + 3, c)]
    # Diagonal \
    for r in range(3):
        for c in range(4):
            if board[r][c] != 0 and board[r][c] == board[r + 1][c + 1] == board[r + 2][c + 2] == board[r + 3][c + 3]:
                return board[r][c], [(r, c), (r + 1, c + 1), (r + 2, c + 2), (r + 3, c + 3)]
    # Diagonal /
    for r in range(3, 6):
        for c in range(4):
            if board[r][c] != 0 and board[r][c] == board[r - 1][c + 1] == board[r - 2][c + 2] == board[r - 3][c + 3]:
                return board[r][c], [(r, c), (r - 1, c + 1), (r - 2, c + 2), (r - 3, c + 3)]
    return 0, None


def drop_connect4_piece(board: list, col: int, player: int) -> int:
    """Deja caer una ficha en la columna indicada. Devuelve la fila ocupada o -1 si está llena."""
    if col < 0 or col >= 7 or board[0][col] != 0:
        return -1
    for r in range(5, -1, -1):
        if board[r][col] == 0:
            board[r][col] = player
            return r
    return -1


def get_connect4_bot_move(board: list, bot_player: int = 2, human_player: int = 1) -> int:
    """IA heurística estratégica para Conecta 4: victoria inmediata, bloqueo y ponderación central."""
    valid_cols = [c for c in range(7) if board[0][c] == 0]
    if not valid_cols:
        return -1

    # 1. Comprobar victoria inmediata del bot
    for c in valid_cols:
        r = drop_connect4_piece(board, c, bot_player)
        win, _ = check_connect4_winner(board)
        board[r][c] = 0
        if win == bot_player:
            return c

    # 2. Bloquear victoria inmediata del rival humano
    for c in valid_cols:
        r = drop_connect4_piece(board, c, human_player)
        win, _ = check_connect4_winner(board)
        board[r][c] = 0
        if win == human_player:
            return c

    # 3. Filtrar columnas donde poner ficha permita al rival ganar justo encima en su siguiente turno
    safe_cols = []
    for c in valid_cols:
        r = drop_connect4_piece(board, c, bot_player)
        rival_wins_above = False
        if r > 0:
            board[r - 1][c] = human_player
            w, _ = check_connect4_winner(board)
            if w == human_player:
                rival_wins_above = True
            board[r - 1][c] = 0
        board[r][c] = 0
        if not rival_wins_above:
            safe_cols.append(c)

    candidates = safe_cols if safe_cols else valid_cols

    # 4. Ponderación posicional y evaluación táctica de amenazas futuras
    col_weights = {3: 8, 2: 5, 4: 5, 1: 3, 5: 3, 0: 1, 6: 1}
    best_score = -1000
    best_c = candidates[0]
    for c in candidates:
        r = drop_connect4_piece(board, c, bot_player)
        score = col_weights.get(c, 0)
        # Bonificación si esta jugada crea una amenaza de 4 en raya para el bot en su siguiente turno
        threats = 0
        for next_c in [nc for nc in range(7) if board[0][nc] == 0]:
            nr = drop_connect4_piece(board, next_c, bot_player)
            w, _ = check_connect4_winner(board)
            board[nr][next_c] = 0
            if w == bot_player:
                threats += 1
        score += threats * 15
        board[r][c] = 0
        if score > best_score:
            best_score = score
            best_c = c
    return best_c


class Connect4Button(discord.ui.Button):
    def __init__(self, col: int, row_pos: int):
        super().__init__(style=discord.ButtonStyle.primary, label=f"{col+1}", row=row_pos)
        self.col = col

    async def callback(self, interaction: discord.Interaction):
        view: Connect4View = self.view
        await view.process_drop(interaction, self.col)


class Connect4View(discord.ui.View):
    """Botonera y tablero interactivo de Conecta 4 (6 filas x 7 columnas)."""

    def __init__(self, player_1: discord.User | discord.Member, player_2: discord.User | discord.Member | None):
        super().__init__(timeout=120)
        self.player_1 = player_1  # 🔴
        self.player_2 = player_2  # 🟡
        self.is_pve = player_2 is None
        self.board = [[0 for _ in range(7)] for _ in range(6)]
        self.current_turn = 1
        self.finished = False
        self.winner = 0
        self.winning_cells = None
        self.message: discord.Message = None

        for c in range(7):
            row_pos = 0 if c < 4 else 1
            self.add_item(Connect4Button(c, row_pos))

    def render_board_str(self) -> str:
        header = "1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣\n"
        symbols = {0: "⬛", 1: "🔴", 2: "🟡"}
        lines = []
        for r in range(6):
            row_str = ""
            for c in range(7):
                if self.winning_cells and (r, c) in self.winning_cells:
                    row_str += "⭐ "
                else:
                    row_str += f"{symbols[self.board[r][c]]} "
            lines.append(row_str.strip())
        return header + "\n".join(lines)

    def build_embed(self) -> discord.Embed:
        p2_name = "Asistente (IA)" if self.is_pve else self.player_2.display_name
        players_header = f"🔴 **{self.player_1.display_name}** vs 🟡 **{p2_name}**"

        if self.finished:
            if self.winner == 1:
                title = f"🏆 ¡Victoria de {self.player_1.display_name}!"
                desc = f"{players_header}\n\n{self.render_board_str()}\n\n🎉 ¡**{self.player_1.display_name}** (🔴) ha conectado 4 en raya!"
                color = 0xEF4444
            elif self.winner == 2:
                title = f"🏆 ¡Victoria de {p2_name}!"
                desc = f"{players_header}\n\n{self.render_board_str()}\n\n🎉 ¡**{p2_name}** (🟡) ha conectado 4 en raya!"
                color = 0xF59E0B
            elif self.winner == -1:
                title = "🤝 ¡Empate en Conecta 4!"
                desc = f"{players_header}\n\n{self.render_board_str()}\n\nTablero completamente lleno sin 4 en raya. ¡Partida muy reñida!"
                color = 0x3B82F6
            else:
                title = "⌛ Partida Finalizada"
                desc = f"{players_header}\n\n{self.render_board_str()}\n\nPartida terminada."
                color = 0x6B7280
        else:
            turn_name = self.player_1.display_name if self.current_turn == 1 else p2_name
            turn_sym = "🔴" if self.current_turn == 1 else "🟡"
            title = f"🔴🟡 Conecta 4 — Turno de {turn_sym} {turn_name}"
            desc = f"{players_header}\n\n{self.render_board_str()}\n\nTurno de **{turn_name}** ({turn_sym}). Pulsa el número de la columna para soltar la ficha."
            color = 0x8B5CF6

        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text="Conecta 4 interactivo • /conecta4 • 120s de inactividad")
        return embed

    def update_buttons(self):
        for item in self.children:
            if isinstance(item, Connect4Button):
                is_full = self.board[0][item.col] != 0
                item.disabled = self.finished or is_full

    async def process_drop(self, interaction: discord.Interaction, col: int):
        if not self.message and interaction.message:
            self.message = interaction.message
        if self.finished:
            await interaction.response.send_message("⚠️ Esta partida ya ha finalizado.", ephemeral=True)
            return

        if self.current_turn == 1:
            if interaction.user.id != self.player_1.id:
                await interaction.response.send_message(f"❌ No es tu turno. Le toca a {self.player_1.display_name} (🔴).", ephemeral=True)
                return
        else:
            if self.is_pve:
                await interaction.response.send_message("❌ Es el turno del bot Asistente.", ephemeral=True)
                return
            if interaction.user.id != self.player_2.id:
                await interaction.response.send_message(f"❌ No es tu turno. Le toca a {self.player_2.display_name} (🟡).", ephemeral=True)
                return

        r = drop_connect4_piece(self.board, col, self.current_turn)
        if r == -1:
            await interaction.response.send_message("❌ Esa columna ya está completa. Elige otra.", ephemeral=True)
            return

        winner, winning_cells = check_connect4_winner(self.board)
        if winner != 0:
            self.finished = True
            self.winner = winner
            self.winning_cells = winning_cells
        elif all(self.board[0][c] != 0 for c in range(7)):
            self.finished = True
            self.winner = -1
        else:
            if self.current_turn == 1:
                self.current_turn = 2
                if self.is_pve:
                    bot_col = get_connect4_bot_move(self.board, bot_player=2, human_player=1)
                    if bot_col != -1:
                        drop_connect4_piece(self.board, bot_col, 2)
                        b_winner, b_cells = check_connect4_winner(self.board)
                        if b_winner != 0:
                            self.finished = True
                            self.winner = b_winner
                            self.winning_cells = b_cells
                        elif all(self.board[0][c] != 0 for c in range(7)):
                            self.finished = True
                            self.winner = -1
                        else:
                            self.current_turn = 1
            else:
                self.current_turn = 1

        self.update_buttons()
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if not self.finished:
            self.finished = True
            self.winner = 0
            for item in self.children:
                item.disabled = True
            embed = self.build_embed()
            embed.title = "⌛ Partida Cancelada por Inactividad"
            embed.description += "\n\n*Han transcurrido 2 minutos sin jugadas.*"
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except Exception:
                    pass


# ==========================================
# AJEDREZ CONTRA ASISTENTE (python-chess + Stockfish)
# ==========================================

STOCKFISH_PATH = shutil.which("stockfish") or "/usr/games/stockfish"
# Partidas en memoria: user_id -> ChessGame (un reinicio del servicio las borra)
CHESS_GAMES = {}
CHESS_PIECE_NAMES = {1: "Peón", 2: "Caballo", 3: "Alfil", 4: "Torre", 5: "Dama", 6: "Rey"}
CHESS_ICONS_WHITE = {1: "♙", 2: "♘", 3: "♗", 4: "♖", 5: "♕", 6: "♔"}
CHESS_ICONS_BLACK = {1: "♟", 2: "♞", 3: "♝", 4: "♜", 5: "♛", 6: "♚"}
# Dificultades de Asistente: clave -> (etiqueta, ELO de Stockfish, segundos por jugada).
CHESS_LEVELS = {
    "facil": ("Fácil (~800 ELO, Gemini juega sola)", None, 0),
    "medio": ("Medio (1400 ELO)", 1400, 0.3),
    "dificil": ("Difícil (1900 ELO)", 1900, 0.5),
    "maximo": ("Máximo (3000+ ELO)", 0, 1.0),
}
CHESS_TYPED_MOVE_RE = re.compile(r"^[a-hRNBQKDTACOo0x=+#\-1-8]{2,7}$")
CHESS_SPANISH_PIECES = {"R": "K", "D": "Q", "T": "R", "A": "B", "C": "N"}


def chess_icon(piece) -> str:
    return (CHESS_ICONS_WHITE if piece.color else CHESS_ICONS_BLACK)[piece.piece_type]


def chess_board_url(board, player_white: bool) -> str:
    """Imagen del tablero servida por Lichess, orientada hacia el jugador y con la última jugada resaltada."""
    params = {"fen": board.fen(), "color": "white" if player_white else "black"}
    if board.move_stack:
        params["lastMove"] = board.move_stack[-1].uci()[:4]
    if board.is_check():
        params["check"] = chess.square_name(board.king(board.turn))
    return "https://lichess1.org/export/fen.gif?" + urllib.parse.urlencode(params)


def chess_parse_typed(board, text: str):
    """Interpreta una jugada escrita en el chat: notación algebraica (inglesa o española) o coordenadas (e2e4)."""
    txt = text.strip()
    if not CHESS_TYPED_MOVE_RE.match(txt):
        return None
    txt = txt.replace("0", "O").replace("o", "O")
    # Variante española: inicial de la pieza (Cf3) y pieza de coronación (a8=D)
    spanish = re.sub(r"=([DTAC])", lambda m: "=" + CHESS_SPANISH_PIECES[m.group(1)], txt)
    if spanish[0] in CHESS_SPANISH_PIECES:
        spanish = CHESS_SPANISH_PIECES[spanish[0]] + spanish[1:]
    candidates = [txt] if spanish == txt else [txt, spanish]
    for cand in candidates:
        try:
            return board.parse_san(cand)
        except Exception:
            pass
    try:
        low = text.strip().lower()
        move = chess.Move.from_uci(low)
        if move in board.legal_moves:
            return move
        # Coronación sin indicar pieza: dama por defecto
        queen = chess.Move.from_uci(low + "q")
        if queen in board.legal_moves:
            return queen
    except Exception:
        pass
    return None


def chess_piece_options(board) -> list:
    """Piezas del bando que mueve con alguna jugada legal: [(etiqueta, descripción, casilla)]."""
    counts = collections.OrderedDict()
    for mv in board.legal_moves:
        counts[mv.from_square] = counts.get(mv.from_square, 0) + 1
    opts = []
    for sq in sorted(counts, key=lambda s: (-board.piece_at(s).piece_type, s)):
        piece = board.piece_at(sq)
        n = counts[sq]
        opts.append(
            (
                f"{chess_icon(piece)} {CHESS_PIECE_NAMES[piece.piece_type]} {chess.square_name(sq)}",
                f"{n} jugada{'s' if n != 1 else ''}",
                chess.square_name(sq),
            )
        )
    return opts


def chess_dest_options(board, from_square: int) -> list:
    """Destinos legales de una pieza: [(etiqueta, uci)]."""
    opts = []
    piece = board.piece_at(from_square)
    for mv in board.legal_moves:
        if mv.from_square != from_square:
            continue
        if board.is_castling(mv):
            label = "Enroque corto" if board.is_kingside_castling(mv) else "Enroque largo"
        else:
            label = f"{chess_icon(piece)} → {chess.square_name(mv.to_square)}"
            if board.is_en_passant(mv):
                label += " ✕ Peón (al paso)"
            elif board.is_capture(mv):
                label += f" ✕ {CHESS_PIECE_NAMES[board.piece_at(mv.to_square).piece_type]}"
            if mv.promotion:
                label += f" = {CHESS_PIECE_NAMES[mv.promotion]}"
        if board.gives_check(mv):
            label += " (jaque)"
        opts.append((label, mv.uci()))
    return opts


def chess_moves_text(board, max_chars: int = 220) -> str:
    """Lista numerada de la partida, recortada a las últimas jugadas."""
    if not board.move_stack:
        return ""
    txt = chess.Board().variation_san(board.move_stack)
    if len(txt) > max_chars:
        txt = "… " + txt[-max_chars:].split(" ", 1)[-1]
    return txt


def chess_result_text(board, player_white: bool, player_name: str):
    """Texto de final de partida, o None si sigue en juego."""
    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        return None
    if outcome.winner is None:
        reasons = {
            chess.Termination.STALEMATE: "rey ahogado",
            chess.Termination.INSUFFICIENT_MATERIAL: "material insuficiente",
            chess.Termination.THREEFOLD_REPETITION: "triple repetición",
            chess.Termination.FIVEFOLD_REPETITION: "repetición",
            chess.Termination.FIFTY_MOVES: "regla de los 50 movimientos",
            chess.Termination.SEVENTYFIVE_MOVES: "regla de los 75 movimientos",
        }
        return f"🤝 **Tablas** por {reasons.get(outcome.termination, 'acuerdo')}."
    if outcome.winner == player_white:
        return f"🏆 **Jaque mate. Gana {player_name}.**"
    return "💀 **Jaque mate. Gana Asistente.**"


class ChessGame:
    def __init__(self, user_id: int, user_name: str, player_white: bool, rival: str):
        self.user_id = user_id
        self.user_name = user_name
        self.player_white = player_white
        self.rival = rival
        self.board = chess.Board()
        self.message = None
        self.comment = ""
        self.selected = None  # casilla de la pieza elegida en el menú
        self.busy = False
        self.finished = False
        self.result = ""
        self.lock = asyncio.Lock()


def chess_build_embed(game: "ChessGame") -> discord.Embed:
    board = game.board
    rival_label = "Asistente · " + CHESS_LEVELS[game.rival][0].split(" (")[0]
    lines = []
    if game.finished:
        lines.append(game.result)
    elif game.busy:
        lines.append("⏳ **Asistente está pensando...**")
    else:
        color = "blancas" if game.player_white else "negras"
        lines.append(f"🎯 **Te toca, {game.user_name}** (juegas con {color})" + (" — **estás en jaque**" if board.is_check() else ""))
    if game.comment:
        lines.append(f"💬 *{game.comment[:300]}*")
    moves = chess_moves_text(board)
    if moves:
        lines.append(f"`{moves}`")
    embed = discord.Embed(
        title=f"♟️ Ajedrez — {game.user_name} vs {rival_label}",
        description="\n\n".join(lines),
        color=0x57F287 if game.finished else 0x3B82F6,
    )
    embed.set_image(url=chess_board_url(board, game.player_white))
    if not game.finished:
        embed.set_footer(text="Elige pieza y destino en los menús, o escribe la jugada en este canal (e4, Cf3, e2e4)")
    return embed


class ChessView(discord.ui.View):
    """Menús de la partida: primero la pieza, después su destino."""

    def __init__(self, game: "ChessGame"):
        super().__init__(timeout=None)
        self.game = game
        board = game.board
        if game.busy:
            self.add_item(discord.ui.Button(label="Asistente está pensando...", style=discord.ButtonStyle.secondary, disabled=True))
            return
        if game.selected is None:
            select = discord.ui.Select(
                placeholder="1. Elige la pieza que quieres mover",
                options=[discord.SelectOption(label=l, description=d, value=v) for l, d, v in chess_piece_options(board)][:25],
            )
            select.callback = self.on_piece
            self.add_item(select)
        else:
            piece = board.piece_at(game.selected)
            dests = chess_dest_options(board, game.selected)
            for i in range(0, len(dests), 25):
                chunk = dests[i : i + 25]
                select = discord.ui.Select(
                    placeholder=f"2. ¿A dónde va {CHESS_PIECE_NAMES[piece.piece_type]} {chess.square_name(game.selected)}?" + (" (más)" if i else ""),
                    options=[discord.SelectOption(label=l, value=v) for l, v in chunk],
                )
                select.callback = self.on_dest
                self.add_item(select)
            back = discord.ui.Button(label="Cambiar pieza", style=discord.ButtonStyle.secondary, emoji="↩️")
            back.callback = self.on_back
            self.add_item(back)
        resign = discord.ui.Button(label="Rendirse", style=discord.ButtonStyle.danger, emoji="🏳️")
        resign.callback = self.on_resign
        self.add_item(resign)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.game.user_id:
            await interaction.response.send_message("⚠️ Esta partida no es tuya. Empieza la tuya con `/ajedrez`.", ephemeral=True)
            return False
        games_dict = getattr(_bs(), "CHESS_GAMES", CHESS_GAMES)
        if self.game.finished or games_dict.get(self.game.user_id) is not self.game:
            await interaction.response.send_message("ℹ️ Esta partida ya ha terminado.", ephemeral=True)
            return False
        return True

    async def on_piece(self, interaction: discord.Interaction):
        self.game.selected = chess.parse_square(interaction.data["values"][0])
        await interaction.response.edit_message(embed=chess_build_embed(self.game), view=ChessView(self.game))

    async def on_back(self, interaction: discord.Interaction):
        self.game.selected = None
        await interaction.response.edit_message(embed=chess_build_embed(self.game), view=ChessView(self.game))

    async def on_dest(self, interaction: discord.Interaction):
        move = chess.Move.from_uci(interaction.data["values"][0])
        if not await chess_play_player_move(self.game, move, interaction):
            if not interaction.response.is_done():
                self.game.selected = None
                await interaction.response.edit_message(embed=chess_build_embed(self.game), view=ChessView(self.game))

    async def on_resign(self, interaction: discord.Interaction):
        chess_finish(self.game, f"🏳️ **{self.game.user_name} se rinde. Gana Asistente.**")
        await interaction.response.edit_message(embed=chess_build_embed(self.game), view=None)


def chess_finish(game: "ChessGame", result: str):
    game.finished = True
    game.busy = False
    game.selected = None
    game.result = result
    games_dict = getattr(_bs(), "CHESS_GAMES", CHESS_GAMES)
    if games_dict.get(game.user_id) is game:
        games_dict.pop(game.user_id, None)


def chess_gemini_pick(fen: str, bot_color: str, legal_sans: list, history: str, user_name: str, played_san: str = None):
    """Pide a Gemini una jugada de la lista de legales y un comentario. Devuelve (san, comentario) o (None, '')."""
    if played_san:
        task = f"Acabas de jugar {played_san}. Repite esa jugada y añade un comentario breve "
    else:
        task = (
            f"Jugadas legales: {', '.join(legal_sans)}\n\n"
            f"Elige la mejor jugada, copiada EXACTAMENTE de la lista de jugadas legales, y añade un comentario breve "
        )
    prompt = (
        f"Eres 'Asistente', el bot colega de un servidor de Discord, jugando al ajedrez con {bot_color} contra {user_name}.\n"
        f"Posición (FEN): {fen}\n"
        f"Partida hasta ahora: {history or 'acaba de empezar'}\n"
        f"{task}"
        f"en español de España con pique sano de colegas (sin insultos, máximo 20 palabras).\n"
        f"Formato de salida estricto:\nJugada: <jugada>\nComentario: <comentario>"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.5, "maxOutputTokens": 120},
    }
    data = json.dumps(payload).encode("utf-8")
    bs = _bs()
    gemini_key = getattr(bs, "GEMINI_KEY", "")
    avail_fn = getattr(bs, "get_available_models", lambda: [])
    cooldown_fn = getattr(bs, "mark_model_cooldown", lambda m, s=60: None)

    for model_name in avail_fn()[:3]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode("utf-8"))
            text = res["candidates"][0]["content"]["parts"][0]["text"]
            m_move = re.search(r"Jugada:\s*([^\s]+)", text)
            m_comment = re.search(r"Comentario:\s*(.+)", text)
            if m_move:
                return m_move.group(1).strip().strip("*`."), (m_comment.group(1).strip() if m_comment else "")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                cooldown_fn(model_name, 60)
        except Exception as e:
            print(f"Aviso Gemini ajedrez ({model_name}): {e}")
    return None, ""


async def chess_stockfish_move(board, elo: int, seconds: float):
    """Jugada de Stockfish limitado al ELO indicado (0 = fuerza completa)."""
    sf_path = getattr(_bs(), "STOCKFISH_PATH", STOCKFISH_PATH)
    transport, engine = await chess.engine.popen_uci(sf_path)
    try:
        options = {"Threads": 1, "Hash": 16}
        if elo and "UCI_Elo" in engine.options:
            opt = engine.options["UCI_Elo"]
            options["UCI_LimitStrength"] = True
            options["UCI_Elo"] = max(opt.min, min(opt.max, elo))
        await engine.configure(options)
        result = await asyncio.wait_for(engine.play(board, chess.engine.Limit(time=seconds)), timeout=20)
        return result.move
    finally:
        try:
            await asyncio.wait_for(engine.quit(), timeout=5)
        except Exception:
            pass


async def chess_bot_move(game: "ChessGame"):
    """Devuelve (jugada, comentario) del rival configurado. Siempre devuelve una jugada legal."""
    board = game.board
    legal = list(board.legal_moves)
    _, elo, seconds = CHESS_LEVELS[game.rival]
    bot_color = "blancas" if board.turn else "negras"
    if elo is not None:
        try:
            move = await chess_stockfish_move(board, elo, seconds)
            if move in legal:
                _, comment = await asyncio.to_thread(
                    chess_gemini_pick, board.fen(), bot_color, [], chess_moves_text(board, 600), game.user_name, board.san(move)
                )
                return move, comment
        except Exception as e:
            _bot_log(f"Aviso Stockfish no disponible ({e}). Jugando con Gemini.")
    legal_sans = [board.san(m) for m in legal]
    san, comment = await asyncio.to_thread(
        chess_gemini_pick, board.fen(), bot_color, legal_sans, chess_moves_text(board, 600), game.user_name
    )
    if san:
        try:
            return board.parse_san(san), comment
        except Exception:
            pass
    return random.choice(legal), ""


async def chess_run_bot_turn(game: "ChessGame"):
    """Turno del rival: muestra 'pensando', juega y refresca el mensaje de la partida."""
    try:
        move, comment = await chess_bot_move(game)
        if game.finished:
            return
        game.board.push(move)
        game.comment = comment
    finally:
        game.busy = False
    result = chess_result_text(game.board, game.player_white, game.user_name)
    if result:
        chess_finish(game, result)
    await game.message.edit(embed=chess_build_embed(game), view=None if game.finished else ChessView(game))


async def chess_play_player_move(game: "ChessGame", move, interaction: discord.Interaction = None) -> bool:
    """Aplica la jugada del jugador (desde menú o escrita) y lanza la respuesta del rival."""
    async with game.lock:
        board = game.board
        if game.finished or game.busy or board.turn != game.player_white or move not in board.legal_moves:
            return False
        board.push(move)
        game.selected = None
        game.comment = ""
        result = chess_result_text(board, game.player_white, game.user_name)
        if result:
            chess_finish(game, result)
        else:
            game.busy = True
        embed = chess_build_embed(game)
        view = None if game.finished else ChessView(game)
        if interaction is not None:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await game.message.edit(embed=embed, view=view)
        if not game.finished:
            await chess_run_bot_turn(game)
        return True


async def chess_try_typed_move(message: discord.Message) -> bool:
    """Si el autor tiene partida en este canal y el mensaje es una jugada legal, la juega. Devuelve True si lo era."""
    games_dict = getattr(_bs(), "CHESS_GAMES", CHESS_GAMES)
    game = games_dict.get(message.author.id)
    if not game or game.finished or game.busy or not game.message or game.message.channel.id != message.channel.id:
        return False
    if game.board.turn != game.player_white:
        return False
    move = chess_parse_typed(game.board, message.content)
    if move is None:
        return False
    try:
        await message.delete()
    except Exception:
        pass
    return await chess_play_player_move(game, move)

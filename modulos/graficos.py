"""
Subsistema gráfico y multimodal para el bot 'Asistente':
- Extracción balanceada de bloques [ACTION_CODE], [ACTION_MATH], [ACTION_CHART], [ACTION_DIAGRAM], [ACTION_DRAW].
- Sanitización de expresiones LaTeX a texto Unicode legible en Discord (con protección de bloques de código).
- Generación de imágenes con FLUX.1 (Pollinations) y optimizador de prompts en inglés.
- Renderizado de tarjetas matemáticas (CodeCogs), gráficos estadísticos (QuickChart), diagramas (Mermaid) y tarjetas de código (Pillow).
"""

import asyncio
import base64
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import discord


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


def extract_action_block(text: str, tag_name: str):
    """
    Extrae bloques de acción [TAG_NAME: ...] soportando corchetes anidados
    (como arr[0] en código o [a, b] en fórmulas LaTeX y Mermaid) sin truncamientos accidentales.
    Delimita la búsqueda antes de cualquier acción posterior para evitar contaminación cruzada.
    Devuelve (full_match_str, content_str) o None si no existe la etiqueta.
    """
    prefix = f"[{tag_name.upper()}:"
    lower_text = text.lower()
    lower_prefix = prefix.lower()
    start_pos = lower_text.find(lower_prefix)
    if start_pos == -1:
        return None

    content_start = start_pos + len(prefix)

    # Buscar el inicio de cualquier acción posterior para no rebasarla nunca
    next_action_match = re.search(r"\[ACTION_[A-Z_]+:", text[content_start:], re.IGNORECASE)
    search_limit = content_start + next_action_match.start() if next_action_match else len(text)
    search_text = text[:search_limit]

    depth = 1
    end_pos = -1
    in_quote = None
    in_comment = False
    escaped = False
    is_code = tag_name.upper() in ("ACTION_CODE", "ACTION_CHART")

    idx = content_start
    while idx < search_limit:
        ch = search_text[idx]
        if escaped:
            escaped = False
            idx += 1
            continue
        if ch == "\\":
            escaped = True
            idx += 1
            continue

        if is_code:
            # Comentarios de código: ignorar caracteres y comillas hasta el fin de línea
            if in_comment:
                if ch == "\n":
                    in_comment = False
                idx += 1
                continue
            elif ch == "#" and in_quote is None:
                in_comment = True
                idx += 1
                continue

            # Strings literales en código
            if in_quote is not None:
                if len(in_quote) == 3:
                    if search_text.startswith(in_quote, idx):
                        idx += 3
                        in_quote = None
                        continue
                else:
                    if ch == in_quote:
                        in_quote = None
                    elif ch == "\n":
                        in_quote = None
                idx += 1
                continue
            else:
                if search_text.startswith('"""', idx):
                    in_quote = '"""'
                    idx += 3
                    continue
                elif search_text.startswith("'''", idx):
                    in_quote = "'''"
                    idx += 3
                    continue
                elif ch in ('"', "'"):
                    in_quote = ch
                    idx += 1
                    continue

        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end_pos = idx
                break
        idx += 1

    if end_pos != -1:
        return text[start_pos : end_pos + 1], text[content_start : end_pos]
    else:
        # Fallback acotado estrictamente antes de la siguiente acción
        last_bracket = text.rfind("]", content_start, search_limit)
        if last_bracket != -1:
            return text[start_pos : last_bracket + 1], text[content_start : last_bracket]
        else:
            return text[start_pos : search_limit], text[content_start : search_limit]


def generate_image_flux(prompt: str, width: int = 1024, height: int = 1024) -> bytes:
    """Genera una imagen en alta resolución usando el clúster libre de FLUX.1 / Stable Diffusion."""
    encoded_prompt = urllib.parse.quote(prompt.strip())
    seed = int(time.time() * 1000) % 1000000
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&model=flux&nologo=true&seed={seed}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=35) as resp:
        return resp.read()


def _parse_latex_braces(s: str, start: int):
    """Parsea llaves anidadas en LaTeX para extraer de forma segura numeradores y denominadores."""
    if start >= len(s) or s[start] != "{":
        return None, start
    depth = 0
    content = []
    i = start
    while i < len(s):
        if s[i] == "{":
            depth += 1
            if depth > 1:
                content.append("{")
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return "".join(content), i + 1
            else:
                content.append("}")
        else:
            content.append(s[i])
        i += 1
    return None, start


def replace_frac(text: str) -> str:
    """Convierte comandos \\frac{num}{den} en expresiones legibles (num)/(den)."""
    idx = 0
    while True:
        pos = text.find(r"\frac", idx)
        if pos == -1:
            break
        first_brace = text.find("{", pos)
        if first_brace == -1 or text[pos + 5 : first_brace].strip() != "":
            idx = pos + 5
            continue
        num, next_pos = _parse_latex_braces(text, first_brace)
        if num is None:
            idx = pos + 5
            continue
        while next_pos < len(text) and text[next_pos].isspace():
            next_pos += 1
        den, end_pos = _parse_latex_braces(text, next_pos)
        if den is None:
            idx = pos + 5
            continue
        replacement = f"({num.strip()})/({den.strip()})"
        text = text[:pos] + replacement + text[end_pos:]
        idx = pos + len(replacement)
    return text


def sanitize_discord_math_text(text: str) -> str:
    """Sustituye código LaTeX residual por símbolos legibles en Discord para evitar aspecto de 'chino'.
    Protege bloques de código (```...``` y `...`) para que el código fuente nunca sea alterado."""
    if not text:
        return text

    placeholders = []

    def repl_code(match):
        idx = len(placeholders)
        placeholders.append(match.group(0))
        return f"\x00CODE_BLOCK_{idx}\x00"

    protected_text = re.sub(r"```[\s\S]*?```|`[^`\n]+`", repl_code, text)

    replacements = [
        (r"\\cdot", "·"),
        (r"\\times", "×"),
        (r"\\div", "÷"),
        (r"\\pm", "±"),
        (r"\\mp", "∓"),
        (r"\\infty", "∞"),
        (r"\\neq", "≠"),
        (r"\\leq", "≤"),
        (r"\\geq", "≥"),
        (r"\\approx", "≈"),
        (r"\\in", "∈"),
        (r"\\notin", "∉"),
        (r"\\forall", "∀"),
        (r"\\exists", "∃"),
        (r"\\to", "→"),
        (r"\\rightarrow", "→"),
        (r"\\leftarrow", "←"),
        (r"\\Rightarrow", "⇒"),
        (r"\\Leftarrow", "⇐"),
        (r"\\iff", "⇔"),
        (r"\\alpha", "α"),
        (r"\\beta", "β"),
        (r"\\gamma", "γ"),
        (r"\\theta", "θ"),
        (r"\\pi", "π"),
        (r"\\sigma", "σ"),
        (r"\\lambda", "λ"),
        (r"\\Delta", "Δ"),
        (r"\\Omega", "Ω"),
    ]
    res = protected_text
    for pat, rep in replacements:
        res = re.sub(pat, rep, res)
    res = replace_frac(res)
    res = re.sub(r"\\sqrt\{([^{}]+)\}", r"√(\1)", res)
    res = re.sub(r"\\lim_\{([^{}]+)\}", r"lím(\1)", res)
    res = re.sub(r"\\text\{([^{}]+)\}", r"\1", res)
    res = re.sub(r"\{([^{}]+)\}", r"\1", res)
    res = re.sub(r"\$\$([^\$]+)\$\$", r"\1", res)
    res = re.sub(r"(?<!\w)\$([^\$\n]+)\$(?!\w)", r"\1", res)

    for idx, block in enumerate(placeholders):
        res = res.replace(f"\x00CODE_BLOCK_{idx}\x00", block)

    return res


def render_math_image(latex_code: str) -> bytes:
    """Convierte una fórmula LaTeX en una tarjeta gráfica PNG de alta resolución con fondo oscuro para Discord."""
    clean_latex = latex_code.strip().strip("$")
    encoded = urllib.parse.quote(clean_latex)
    # Renderizado 200 DPI con fondo Discord #1e1f22 y texto blanco nítido
    url = f"https://latex.codecogs.com/png.image?\\dpi{{200}}\\bg{{1e1f22}}\\color{{white}}{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def render_chart_image(chart_json_str: str) -> bytes:
    """Genera un gráfico estadístico o función matemática (líneas, barras, tarta) mediante QuickChart."""
    config = json.loads(chart_json_str) if isinstance(chart_json_str, str) else chart_json_str
    # Añadir estilo oscuro por defecto si no lo tiene
    if "options" not in config:
        config["options"] = {}
    config["options"]["legend"] = config["options"].get("legend", {})
    config["options"]["legend"]["labels"] = {"fontColor": "#ffffff"}

    url = "https://quickchart.io/chart"
    payload = {"chart": config, "backgroundColor": "#1e1f22", "width": 800, "height": 450}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def render_diagram_image(mermaid_code: str) -> bytes:
    """Genera un diagrama de flujo o esquema a partir de código Mermaid."""
    clean_code = mermaid_code.strip().replace("```mermaid", "").replace("```", "").strip()
    code_b64 = base64.b64encode(clean_code.encode("utf-8")).decode("ascii")
    url = f"https://mermaid.ink/img/{code_b64}?bgColor=1e1f22"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read()


def render_code_card_image(code_str: str) -> bytes:
    """Renderiza una tarjeta gráfica de código limpia estilo ventana terminal con Pillow."""
    from PIL import Image, ImageDraw

    lines = code_str.strip().replace("```", "").strip().split("\n")[:25]
    max_len = max(len(l) for l in lines) if lines else 20
    w = max(550, min(1000, 40 + max_len * 9))
    h = 45 + len(lines) * 22
    img = Image.new("RGB", (w, h), color="#1e1f22")
    draw = ImageDraw.Draw(img)
    # Botones terminal estilo macOS
    draw.ellipse((14, 12, 24, 22), fill="#ed6a5e")
    draw.ellipse((30, 12, 40, 22), fill="#f5bf4f")
    draw.ellipse((46, 12, 56, 22), fill="#62c554")
    draw.line([(0, 32), (w, 32)], fill="#2b2d31", width=1)

    y = 40
    for l in lines:
        draw.text((20, y), l, fill="#e0e0e0")
        y += 22
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def enhance_image_prompt(user_text: str, author_name: str = "") -> str:
    """Traduce y optimiza el prompt del usuario al inglés con detalles visuales cinematográficos."""
    clean = re.sub(
        r"\b(crea|genera|hazme|haz|dibuja|dibújame|dibujame|puedes|una|un|imagen|foto|dibujo|de|porfa|oye|asistente)\b",
        "",
        user_text,
        flags=re.IGNORECASE,
    ).strip()
    if not clean:
        clean = "cyberpunk anime warrior"

    if author_name:
        clean = re.sub(r"\b(yo|mí|mi)\b", author_name, clean, flags=re.IGNORECASE)

    prompt_enhancer = (
        f"You are an expert prompt engineer for FLUX.1 and Stable Diffusion image generation. "
        f"Convert this concept into a single, detailed, visually stunning English prompt (maximum 35 words). "
        f"Include art style, lighting, atmosphere, characters, actions and composition. "
        f"Return ONLY the final prompt text without quotes or explanations.\n"
        f"Concept: {clean}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt_enhancer}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 100},
    }
    data = json.dumps(payload).encode("utf-8")
    bs = _bs()
    gemini_key = getattr(bs, "GEMINI_KEY", "")
    avail_fn = getattr(bs, "get_available_models", lambda: [])
    cooldown_fn = getattr(bs, "mark_model_cooldown", lambda m, s=60: None)

    for model_name in avail_fn():
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        try:
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                candidates = res.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    enhanced = candidates[0]["content"]["parts"][0]["text"].strip()
                    if enhanced and len(enhanced) > 5:
                        return enhanced
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                cooldown_fn(model_name, 60)
            continue
        except Exception:
            continue

    if "vs" in clean.lower() or "contra" in clean.lower():
        return f"An epic 1v1 battle, {clean}, intense clash, glowing energy aura, dynamic action angle, detailed digital art, cinematic lighting"
    return f"{clean}, high quality digital art, detailed, dramatic lighting, cinematic 8k wallpaper"


class ImageActionView(discord.ui.View):
    """Botonera interactiva para creaciones de imágenes con FLUX.1."""

    def __init__(self, prompt: str, author_id: int):
        super().__init__(timeout=300)
        self.prompt = prompt
        self.author_id = author_id

    @discord.ui.button(label="Re-roll", style=discord.ButtonStyle.primary, emoji="🔄")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True)
        try:
            bs = _bs()
            flux_fn = getattr(bs, "generate_image_flux", generate_image_flux)
            img_bytes = await asyncio.to_thread(flux_fn, self.prompt)
            file = discord.File(io.BytesIO(img_bytes), filename="reroll_flux.png")
            new_view = ImageActionView(self.prompt, self.author_id)
            await interaction.followup.send(
                content=f"🔄 **Nueva versión (Re-roll) para {interaction.user.display_name}:**\n> *\"{self.prompt[:120]}\"*",
                file=file,
                view=new_view,
            )
        except Exception as e:
            await interaction.followup.send(f"⚠️ Error generando re-roll: {e}", ephemeral=True)

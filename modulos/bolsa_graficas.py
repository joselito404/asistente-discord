"""
Módulo de Renderizado Gráfico de Velas Japonesas (Bolsa Sanvi):
- Genera imágenes de cotización en formato PNG nativo para Discord vía Pillow (PIL).
- Estética y paleta institucional inspirada en Trading 212:
  - Fondo negro puro (#000000).
  - Velas alcistas en verde neón (#00E676) y bajistas en rojo intenso (#FF5252).
  - Subgráfico inferior de volumen con barras correlacionadas.
  - Línea horizontal de cotización actual en azul cian (#00A3FF) con badge flotante.
  - Grid lines tenues (#1E1E1E) y ejes de precios limpios.
"""

import io
import math
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from PIL import Image, ImageDraw, ImageFont


# Paleta de colores Trading 212
COLOR_BG = "#000000"
COLOR_GRID = "#1A1A1A"
COLOR_AXIS_TEXT = "#666666"
COLOR_WHITE = "#FFFFFF"
COLOR_MUTED = "#8E8E93"
COLOR_BULLISH = "#00E676"  # Verde Neón alcista
COLOR_BEARISH = "#FF5252"  # Rojo Vivo bajista
COLOR_CURRENT_LINE = "#00A3FF"  # Azul Cian cotización
COLOR_BADGE_BG = "#0077CC"
COLOR_VOLUME_BG = "#111111"


def _get_font(size: int, bold: bool = False):
    """Intenta cargar fuentes del sistema compatibles o recurre a la fuente por defecto."""
    font_names = ["segoeui.ttf", "arial.ttf", "consola.ttf", "DejaVuSans.ttf"]
    if bold:
        font_names = ["segoeuib.ttf", "arialbd.ttf", "consolab.ttf"] + font_names

    for fname in font_names:
        try:
            return ImageFont.truetype(fname, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _generate_synthetic_candles(
    base_price: float,
    count: int = 30,
    timeframe: str = "1D",
) -> List[Dict[str, Any]]:
    """Genera una serie de velas congruente con base_price cuando los datos son escasos."""
    candles = []
    curr = base_price * 0.94
    now = datetime.now(timezone.utc)

    for i in range(count):
        delta_pct = random.uniform(-0.025, 0.03)
        open_p = curr
        close_p = max(5.0, round(open_p * (1.0 + delta_pct), 2))
        high_p = max(open_p, close_p) + round(random.uniform(0.1, 0.8), 2)
        low_p = min(open_p, close_p) - round(random.uniform(0.1, 0.8), 2)
        vol = round(random.uniform(50, 450), 1)

        t_stamp = (now - timedelta(days=(count - i))).strftime("%d/%m")
        candles.append({
            "timestamp": t_stamp,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": vol,
        })
        curr = close_p

    # La última vela cierra exactamente en base_price
    candles[-1]["close"] = base_price
    candles[-1]["high"] = max(candles[-1]["high"], base_price)
    candles[-1]["low"] = min(candles[-1]["low"], base_price)

    return candles


def _normalize_or_generate_candles(
    history_candles: Optional[List[Dict[str, Any]]],
    current_price: float,
    timeframe: str = "1D",
    target_count: int = 30,
) -> List[Dict[str, Any]]:
    """
    Normaliza el historial de velas u órdenes para garantizar una serie OHLCV completa y consistente.
    Soporta:
    1. Lista previa de velas OHLCV (cada elemento con open, high, low, close).
    2. Lista de transacciones u órdenes (order_history de bolsa_mercado.json) con price, market_price, shares, timestamp.
    3. Lista vacía o insuficiente: genera serie sintética congruente con current_price.
    """
    c_price = current_price if (current_price is not None and current_price > 0) else 79.52

    if not history_candles:
        return _generate_synthetic_candles(base_price=c_price, count=target_count, timeframe=timeframe)

    # 1. Comprobar si ya son velas OHLCV válidas
    is_valid_candle_list = all(
        isinstance(c, dict) and "open" in c and "close" in c and "high" in c and "low" in c
        for c in history_candles
    )
    if is_valid_candle_list:
        candles = list(history_candles)
        if len(candles) < target_count:
            needed = target_count - len(candles)
            synth = _generate_synthetic_candles(base_price=candles[0]["open"], count=needed, timeframe=timeframe)
            candles = synth + candles
        candles[-1]["close"] = c_price
        candles[-1]["high"] = max(candles[-1]["high"], c_price)
        candles[-1]["low"] = min(candles[-1]["low"], c_price)
        return candles[-target_count:]

    # 2. Si son órdenes de mercado (order_history), convertirlas a velas
    trades = []
    for o in history_candles:
        if isinstance(o, dict):
            p = float(o.get("market_price") or o.get("price") or c_price)
            v = float(o.get("shares") or 10.0)
            ts = o.get("timestamp") or ""
            trades.append({"price": p, "shares": v, "timestamp": ts})

    if not trades:
        return _generate_synthetic_candles(base_price=c_price, count=target_count, timeframe=timeframe)

    num_buckets = min(len(trades), 20)
    chunk_size = len(trades) / num_buckets
    order_candles = []

    for i in range(num_buckets):
        start_idx = int(i * chunk_size)
        end_idx = int((i + 1) * chunk_size)
        if i == num_buckets - 1:
            end_idx = len(trades)
        bucket = trades[start_idx:end_idx]
        if not bucket:
            continue

        prices = [t["price"] for t in bucket]
        vols = [t["shares"] for t in bucket]
        o_p = prices[0]
        c_p = prices[-1]
        h_p = max(prices)
        l_p = min(prices)
        if h_p == l_p:
            h_p = round(h_p + max(0.1, o_p * 0.005), 2)
            l_p = round(max(0.01, l_p - max(0.1, o_p * 0.005)), 2)

        vol = sum(vols)
        ts_label = "Hoy"
        if bucket[-1]["timestamp"]:
            try:
                dt = datetime.fromisoformat(bucket[-1]["timestamp"].replace("Z", "+00:00"))
                ts_label = dt.strftime("%d/%m")
            except Exception:
                ts_label = "Hoy"

        order_candles.append({
            "timestamp": ts_label,
            "open": o_p,
            "high": h_p,
            "low": l_p,
            "close": c_p,
            "volume": vol,
        })

    # Rellenar con velas sintéticas previas para dar contexto temporal
    if len(order_candles) < target_count:
        needed = target_count - len(order_candles)
        first_open = order_candles[0]["open"]
        synth = _generate_synthetic_candles(base_price=first_open, count=needed, timeframe=timeframe)
        order_candles = synth + order_candles

    # Asegurar que la última vela refleja la cotización actual
    order_candles[-1]["close"] = c_price
    order_candles[-1]["high"] = max(order_candles[-1]["high"], c_price)
    order_candles[-1]["low"] = min(order_candles[-1]["low"], c_price)

    return order_candles[-target_count:]


def generate_candlestick_chart(
    ticker: str,
    history_candles: Optional[List[Dict[str, Any]]] = None,
    timeframe: str = "1D",
    current_price: Optional[float] = None,
    company_name: Optional[str] = None,
) -> io.BytesIO:
    """
    Renderiza un gráfico de velas japonesas de 800x450 píxeles.
    Devuelve un buffer BytesIO en formato PNG optimizado para discord.File.
    """
    WIDTH = 800
    HEIGHT = 450

    # Layout y márgenes
    HEADER_HEIGHT = 70
    FOOTER_MARGIN = 15
    PRICE_AXIS_WIDTH = 75
    LEFT = 20
    RIGHT = WIDTH - PRICE_AXIS_WIDTH
    TOP = HEADER_HEIGHT + 10
    BOTTOM = 345

    VOL_TOP = 360
    VOL_BOTTOM = HEIGHT - FOOTER_MARGIN

    # Normalizar velas u órdenes en serie OHLCV completa de 30 velas
    sym = ticker.upper().lstrip("$")
    c_price = current_price if (current_price is not None and current_price > 0) else 79.52
    candles = _normalize_or_generate_candles(
        history_candles=history_candles,
        current_price=c_price,
        timeframe=timeframe,
        target_count=30,
    )

    last_close = candles[-1]["close"]
    first_open = candles[0]["open"]
    pct_change = ((last_close - first_open) / first_open) * 100.0 if first_open > 0 else 0.0

    # Determinar rango de precios con margen
    all_highs = [c["high"] for c in candles]
    all_lows = [c["low"] for c in candles]
    min_price_raw = min(all_lows)
    max_price_raw = max(all_highs)

    price_range = max_price_raw - min_price_raw
    if price_range <= 0.01:
        price_range = max(1.0, min_price_raw * 0.1)

    padding = price_range * 0.08
    min_price = max(0.0, min_price_raw - padding)
    max_price = max_price_raw + padding
    eff_range = max_price - min_price

    # Rango de volumen
    max_vol = max([c.get("volume", 10.0) for c in candles] or [100.0])
    if max_vol <= 0:
        max_vol = 100.0

    # Inicializar lienzo Pillow
    image = Image.new("RGBA", (WIDTH, HEIGHT), COLOR_BG)
    draw = ImageDraw.Draw(image)

    # Fuentes
    font_title = _get_font(20, bold=True)
    font_price = _get_font(22, bold=True)
    font_badge = _get_font(12, bold=True)
    font_axis = _get_font(11, bold=False)
    font_small = _get_font(10, bold=False)

    # 1. Cabecera (Header)
    display_title = f"${sym}"
    if company_name:
        display_title += f" · {company_name}"
    draw.text((LEFT, 12), display_title, fill=COLOR_WHITE, font=font_title)

    # Precio actual y badge de variación
    price_str = f"{last_close:.2f} Porros"
    draw.text((LEFT, 38), price_str, fill=COLOR_WHITE, font=font_price)

    change_sign = "+" if pct_change >= 0 else ""
    change_str = f"{change_sign}{pct_change:.2f}%"
    change_color = COLOR_BULLISH if pct_change >= 0 else COLOR_BEARISH

    # Medir ancho para posicionar cambio porcentual
    price_bbox = draw.textbbox((LEFT, 38), price_str, font=font_price)
    change_x = price_bbox[2] + 14
    draw.text((change_x, 43), change_str, fill=change_color, font=font_badge)

    # Badge de timeframe en la esquina superior derecha
    tf_str = f"[ {timeframe.upper()} ]"
    draw.text((RIGHT - 20, 16), tf_str, fill=COLOR_MUTED, font=font_badge)

    # 2. Rejilla tenue (Grid) horizontal en el área de precios
    num_grid_lines = 5
    for i in range(num_grid_lines):
        ratio = i / (num_grid_lines - 1)
        grid_y = int(TOP + ratio * (BOTTOM - TOP))
        grid_price = max_price - ratio * eff_range

        # Línea de grid
        draw.line([(LEFT, grid_y), (RIGHT, grid_y)], fill=COLOR_GRID, width=1)
        # Etiqueta de precio en el eje derecho
        draw.text((RIGHT + 6, grid_y - 6), f"{grid_price:.2f}", fill=COLOR_AXIS_TEXT, font=font_axis)

    # Separador entre gráfico de precio y subgráfico de volumen
    draw.line([(LEFT, 352), (RIGHT, 352)], fill=COLOR_GRID, width=1)
    draw.text((LEFT + 2, 354), "VOLUMEN", fill=COLOR_AXIS_TEXT, font=font_small)

    # 3. Dibujo de Velas Japonesas y Barras de Volumen
    n_candles = len(candles)
    chart_width = RIGHT - LEFT
    slot_width = chart_width / n_candles
    candle_body_width = max(3, int(slot_width * 0.70))
    if candle_body_width % 2 == 0:
        candle_body_width += 1  # Mantener impar para centrado exacto con la mecha

    for i, candle in enumerate(candles):
        center_x = int(LEFT + (i + 0.5) * slot_width)
        o_val = candle["open"]
        c_val = candle["close"]
        h_val = candle["high"]
        l_val = candle["low"]
        vol_val = candle.get("volume", 0.0)

        is_bullish = c_val >= o_val
        candle_color = COLOR_BULLISH if is_bullish else COLOR_BEARISH

        # Coordenadas Y de precios
        y_high = int(TOP + (max_price - h_val) / eff_range * (BOTTOM - TOP))
        y_low = int(TOP + (max_price - l_val) / eff_range * (BOTTOM - TOP))
        y_open = int(TOP + (max_price - o_val) / eff_range * (BOTTOM - TOP))
        y_close = int(TOP + (max_price - c_val) / eff_range * (BOTTOM - TOP))

        # Clamp para asegurar que no se salgan de límites
        y_high = max(TOP, min(BOTTOM, y_high))
        y_low = max(TOP, min(BOTTOM, y_low))
        y_open = max(TOP, min(BOTTOM, y_open))
        y_close = max(TOP, min(BOTTOM, y_close))

        # Dibujar Mecha (Wick)
        draw.line([(center_x, y_high), (center_x, y_low)], fill=candle_color, width=1)

        # Dibujar Cuerpo (Body)
        body_top = min(y_open, y_close)
        body_bottom = max(y_open, y_close)
        if body_bottom - body_top < 2:
            body_bottom = body_top + 2  # Grosor mínimo visible

        half_w = candle_body_width // 2
        draw.rectangle(
            [(center_x - half_w, body_top), (center_x + half_w, body_bottom)],
            fill=candle_color,
            outline=candle_color,
        )

        # Subgráfico de Volumen
        vol_height = int((vol_val / max_vol) * (VOL_BOTTOM - VOL_TOP))
        vol_height = max(2, min(VOL_BOTTOM - VOL_TOP, vol_height))
        vol_y = VOL_BOTTOM - vol_height

        draw.rectangle(
            [(center_x - half_w, vol_y), (center_x + half_w, VOL_BOTTOM)],
            fill=candle_color,
            outline=None,
        )

    # 4. Línea de Cotización Actual con Badge Flotante
    curr_y = int(TOP + (max_price - last_close) / eff_range * (BOTTOM - TOP))
    curr_y = max(TOP, min(BOTTOM, curr_y))

    # Línea discontinua sutil o continua cian
    draw.line([(LEFT, curr_y), (RIGHT, curr_y)], fill=COLOR_CURRENT_LINE, width=1)

    # Badge en el eje de precios derecho
    badge_x1 = RIGHT + 3
    badge_y1 = curr_y - 9
    badge_x2 = WIDTH - 8
    badge_y2 = curr_y + 9
    draw.rounded_rectangle([(badge_x1, badge_y1), (badge_x2, badge_y2)], radius=3, fill=COLOR_BADGE_BG)

    badge_text = f"{last_close:.2f}"
    draw.text((badge_x1 + 6, badge_y1 + 2), badge_text, fill=COLOR_WHITE, font=font_axis)

    # 5. Exportación a BytesIO PNG
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer

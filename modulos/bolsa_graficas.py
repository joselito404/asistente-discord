"""
Módulo de Renderizado Gráfico de Velas Japonesas (Bolsa Sanvi):
- Genera imágenes de cotización en formato PNG nativo para Discord vía Pillow (PIL).
- Estética y paleta institucional inspirada en Trading 212:
  - Fondo negro puro (#000000).
  - Velas alcistas en verde neón (#00E676) y bajistas en rojo intenso (#FF5252).
  - Subgráfico inferior de volumen con barras correlacionadas.
  - Línea horizontal de cotización actual en azul cian (#00A3FF) con badge flotante.
  - Grid lines tenues (#1E1E1E) y ejes de precios limpios.
- Soporte para nuevas temporalidades intradía reales:
  - 'Trades' (o 'TICKS'): 1 vela por orden ejecutada (tick-by-tick real, con volumen de acciones operadas).
  - '15m': periodo 15 minutos, velas de 1 minuto (resolución 1m).
  - '1h': periodo 1 hora, velas de 2 minutos (resolución 2m).
  - '4h': periodo 4 horas, velas de 10 minutos (resolución 10m).
  - '1D': periodo 24 horas, velas de 30 minutos (resolución 30m).
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


# Configuración canónica de temporalidades
TIMEFRAME_CONFIG: Dict[str, Dict[str, Any]] = {
    "Trades": {
        "label": "TRADES · 1x orden",
        "resolution_seconds": None,
        "period_seconds": None,
        "default_count": 30,
        "resolution_label": "1 trade/vela",
    },
    "15m": {
        "label": "15m · velas 1m",
        "resolution_seconds": 60,
        "period_seconds": 15 * 60,
        "default_count": 15,
        "resolution_label": "1 minuto",
    },
    "1h": {
        "label": "1h · velas 2m",
        "resolution_seconds": 120,
        "period_seconds": 60 * 60,
        "default_count": 30,
        "resolution_label": "2 minutos",
    },
    "4h": {
        "label": "4h · velas 10m",
        "resolution_seconds": 600,
        "period_seconds": 4 * 3600,
        "default_count": 24,
        "resolution_label": "10 minutos",
    },
    "1D": {
        "label": "1D · velas 30m",
        "resolution_seconds": 1800,
        "period_seconds": 24 * 3600,
        "default_count": 48,
        "resolution_label": "30 minutos",
    },
}


def normalize_timeframe(timeframe: Optional[str]) -> str:
    """Normaliza y mapea el identificador de timeframe con soporte retrocompatible."""
    if not timeframe:
        return "1D"
    tf = str(timeframe).strip()
    mapping = {
        "trades": "Trades",
        "TRADES": "Trades",
        "Trades": "Trades",
        "ticks": "Trades",
        "TICKS": "Trades",
        "15m": "15m",
        "15M": "15m",
        "1h": "1h",
        "1H": "1h",
        "4h": "4h",
        "4H": "4h",
        "1d": "1D",
        "1D": "1D",
        "1s": "1D",
        "1S": "1D",
        "1m": "1D",
        "1M": "1D",
        "max": "1D",
        "MAX": "1D",
    }
    return mapping.get(tf, "1D")


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


def _parse_iso_to_datetime(ts_str: Optional[str], fallback_dt: datetime) -> datetime:
    """Convierte un timestamp ISO a datetime UTC con fallback determinista."""
    if not ts_str:
        return fallback_dt
    try:
        clean_ts = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return fallback_dt


def _generate_flat_candles(
    base_price: float,
    count: int = 30,
    start_dt: Optional[datetime] = None,
    step_seconds: int = 60,
    tf_key: str = "Trades",
) -> List[Dict[str, Any]]:
    """Genera una serie de velas planas para relleno suave hacia atrás sin patrones artificiales."""
    candles = []
    now = start_dt or datetime.now(timezone.utc)
    p = round(float(base_price), 2)

    for i in range(count):
        dt = now - timedelta(seconds=(count - i) * step_seconds)
        ts_label = dt.strftime("%H:%M:%S") if tf_key == "Trades" else dt.strftime("%H:%M")
        candles.append({
            "timestamp": ts_label,
            "time": int(dt.timestamp()),
            "open": p,
            "high": p,
            "low": p,
            "close": p,
            "volume": 0.0,
        })
    return candles


def _normalize_or_generate_candles(
    history_candles: Optional[List[Dict[str, Any]]],
    current_price: float,
    timeframe: str = "1D",
    target_count: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Normaliza el historial de velas u órdenes para garantizar una serie OHLCV completa y consistente.
    Soporta:
    1. Lista previa de velas OHLCV (cada elemento con open, high, low, close).
    2. 'Trades': 1 vela por cada orden real (con volumen = shares). Si hay pocas órdenes,
       rellena hacia atrás de forma plana con el precio de la primera orden/base (sin dientes de sierra).
    3. '15m', '1h', '4h', '1D': agrupa órdenes reales en cubetas temporales fijas.
       Si una cubeta no tuvo órdenes, mantiene el precio de cierre previo plano (volume=0).
    """
    c_price = current_price if (current_price is not None and current_price > 0) else 79.52
    c_price = round(float(c_price), 2)
    tf_key = normalize_timeframe(timeframe)
    cfg = TIMEFRAME_CONFIG.get(tf_key, TIMEFRAME_CONFIG["1D"])
    count = target_count or cfg.get("default_count", 30)

    now_utc = datetime.now(timezone.utc)

    # 1. Comprobar si ya son velas OHLCV válidas previas
    if history_candles:
        is_valid_candle_list = all(
            isinstance(c, dict) and "open" in c and "close" in c and "high" in c and "low" in c
            for c in history_candles
        )
        if is_valid_candle_list:
            candles = [dict(c) for c in history_candles]
            if len(candles) < count:
                needed = count - len(candles)
                first_open = candles[0].get("open", c_price)
                flat_prefix = _generate_flat_candles(
                    base_price=first_open,
                    count=needed,
                    start_dt=now_utc - timedelta(seconds=len(candles) * 60),
                    tf_key=tf_key,
                )
                candles = flat_prefix + candles
            candles[-1]["close"] = c_price
            candles[-1]["high"] = max(candles[-1]["high"], c_price)
            candles[-1]["low"] = min(candles[-1]["low"], c_price)
            return candles[-count:]

    # 2. Extraer lista de trades (órdenes de mercado)
    raw_trades = []
    if history_candles:
        for idx, o in enumerate(history_candles):
            if isinstance(o, dict):
                p = float(o.get("market_price") or o.get("price") or c_price)
                v = float(o.get("shares") or 10.0)
                ts_raw = o.get("timestamp")
                # Fallback retroactivo si no hay timestamp
                est_dt = now_utc - timedelta(seconds=(len(history_candles) - idx) * 30)
                dt = _parse_iso_to_datetime(ts_raw, fallback_dt=est_dt)
                raw_trades.append({"price": round(p, 2), "shares": round(v, 2), "dt": dt})

    # Ordenar trades por fecha cronológica ascendente
    raw_trades.sort(key=lambda x: x["dt"])

    # 3. Procesar según timeframe:
    # ----------------------------------------------------
    # Caso A: Trades (Tick-by-tick real, 1 orden por vela)
    # ----------------------------------------------------
    if tf_key == "Trades":
        trade_candles: List[Dict[str, Any]] = []
        for i, t in enumerate(raw_trades):
            p = t["price"]
            v = t["shares"]
            dt = t["dt"]
            trade_candles.append({
                "timestamp": dt.strftime("%H:%M:%S"),
                "time": int(dt.timestamp()) + i,  # Asegurar timestamps estrictamente crecientes
                "open": p,
                "high": p,
                "low": p,
                "close": p,
                "volume": v,
            })

        if not trade_candles:
            # Sin órdenes: generar serie plana con c_price
            trade_candles = _generate_flat_candles(
                base_price=c_price,
                count=count,
                start_dt=now_utc,
                step_seconds=30,
                tf_key="Trades",
            )
        elif len(trade_candles) < count:
            needed = count - len(trade_candles)
            first_p = trade_candles[0]["open"]
            first_dt = raw_trades[0]["dt"] if raw_trades else now_utc
            flat_prefix = _generate_flat_candles(
                base_price=first_p,
                count=needed,
                start_dt=first_dt,
                step_seconds=30,
                tf_key="Trades",
            )
            trade_candles = flat_prefix + trade_candles

        # Garantizar que la última vela cierre en la cotización actual
        trade_candles[-1]["close"] = c_price
        trade_candles[-1]["high"] = max(trade_candles[-1]["high"], c_price)
        trade_candles[-1]["low"] = min(trade_candles[-1]["low"], c_price)
        return trade_candles[-count:]

    # -----------------------------------------------------------------
    # Caso B: Cubetas temporales ('15m', '1h', '4h', '1D')
    # -----------------------------------------------------------------
    res_sec = cfg.get("resolution_seconds", 1800) or 1800
    period_sec = cfg.get("period_seconds", 24 * 3600) or (24 * 3600)
    num_buckets = count

    start_period = now_utc - timedelta(seconds=period_sec)

    # Determinar precio de cierre previo antes de que empiece la ventana
    prev_close = c_price
    prior_trades = [t for t in raw_trades if t["dt"] < start_period]
    if prior_trades:
        prev_close = prior_trades[-1]["price"]
    elif raw_trades:
        prev_close = raw_trades[0]["price"]

    bucket_candles: List[Dict[str, Any]] = []

    for i in range(num_buckets):
        b_start = start_period + timedelta(seconds=i * res_sec)
        b_end = b_start + timedelta(seconds=res_sec)

        b_trades = [t for t in raw_trades if b_start <= t["dt"] < b_end]

        if b_trades:
            prices = [t["price"] for t in b_trades]
            o_p = prices[0]
            c_p = prices[-1]
            h_p = max(prices)
            l_p = min(prices)
            vol = sum(t["shares"] for t in b_trades)
            prev_close = c_p
        else:
            # Cubeta sin órdenes: se mantiene el precio previo plano y volumen 0
            o_p = prev_close
            c_p = prev_close
            h_p = prev_close
            l_p = prev_close
            vol = 0.0

        ts_label = b_end.strftime("%H:%M") if tf_key != "1D" else b_end.strftime("%d/%m %H:%M")
        bucket_candles.append({
            "timestamp": ts_label,
            "time": int(b_end.timestamp()),
            "open": round(o_p, 2),
            "high": round(h_p, 2),
            "low": round(l_p, 2),
            "close": round(c_p, 2),
            "volume": round(vol, 2),
        })

    # Asegurar que la última vela refleje la cotización actual
    bucket_candles[-1]["close"] = c_price
    bucket_candles[-1]["high"] = max(bucket_candles[-1]["high"], c_price)
    bucket_candles[-1]["low"] = min(bucket_candles[-1]["low"], c_price)

    return bucket_candles[-count:]


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

    # Normalizar timeframe y velas
    tf_key = normalize_timeframe(timeframe)
    tf_cfg = TIMEFRAME_CONFIG.get(tf_key, TIMEFRAME_CONFIG["1D"])
    sym = ticker.upper().lstrip("$")
    c_price = current_price if (current_price is not None and current_price > 0) else 79.52

    candles = _normalize_or_generate_candles(
        history_candles=history_candles,
        current_price=c_price,
        timeframe=tf_key,
        target_count=tf_cfg.get("default_count", 30),
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
    max_vol = max([c.get("volume", 0.0) for c in candles] or [100.0])
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

    # Badge explícito de timeframe y resolución en la esquina superior derecha
    badge_label = tf_cfg.get("label", tf_key)
    tf_str = f"[ {badge_label} ]"
    tf_bbox = draw.textbbox((0, 0), tf_str, font=font_badge)
    tf_width = tf_bbox[2] - tf_bbox[0]
    draw.text((RIGHT - tf_width, 16), tf_str, fill=COLOR_MUTED, font=font_badge)

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

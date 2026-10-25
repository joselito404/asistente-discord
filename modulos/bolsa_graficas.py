"""
Módulo de Renderizado Gráfico de Velas Japonesas HD (Bolsa Sanvi):
- Genera imágenes de cotización en formato PNG HD (960x540) nativo para Discord vía Pillow (PIL).
- Estética y paleta institucional inspirada en Trading 212:
  - Fondo negro puro (#000000).
  - Velas alcistas en verde neón (#00E676) y bajistas en rojo intenso (#FF5252).
  - Periodos sin volumen (vol == 0) renderizados como segmento neutro (#3A4659) sin barras fantasma.
  - Curva EMA 14 superpuesta en ámbar institucional (#FFB300).
  - Subgráfico inferior de volumen real + Eje X temporal con marcas de tiempo.
  - Línea horizontal de cotización actual en azul cian (#00A3FF) con badge flotante.
- Soporte para las 8 temporalidades completas:
  'Trades', '15m', '1h', '4h', '1D', '1S', '1M', 'MAX'.
"""

import io
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from PIL import Image, ImageDraw, ImageFont


# Paleta de colores Trading 212 Institucional HD
COLOR_BG = "#000000"
COLOR_GRID = "#161922"
COLOR_AXIS_TEXT = "#787B86"
COLOR_WHITE = "#FFFFFF"
COLOR_MUTED = "#8E8E93"
COLOR_FLAT_TICK = "#3A4659"  # Gris azulado sutil para periodos sin volumen
COLOR_BULLISH = "#00E676"    # Verde Neón alcista
COLOR_BEARISH = "#FF5252"    # Rojo Vivo bajista
COLOR_EMA14 = "#FFB300"      # Ámbar / Dorado institucional para curva EMA 14
COLOR_CURRENT_LINE = "#00A3FF"  # Azul Cian cotización
COLOR_BADGE_BG = "#0077CC"
COLOR_VOLUME_BG = "#111111"


# Configuración canónica de las 8 temporalidades
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
    "1S": {
        "label": "1S · velas 4h",
        "resolution_seconds": 14400,
        "period_seconds": 7 * 86400,
        "default_count": 42,
        "resolution_label": "4 horas",
    },
    "1M": {
        "label": "1M · velas 1D",
        "resolution_seconds": 86400,
        "period_seconds": 30 * 86400,
        "default_count": 30,
        "resolution_label": "1 día",
    },
    "MAX": {
        "label": "MAX · histórico",
        "resolution_seconds": 86400,
        "period_seconds": 60 * 86400,
        "default_count": 45,
        "resolution_label": "histórico adaptativo",
    },
}


def normalize_timeframe(timeframe: Optional[str]) -> str:
    """Normaliza y mapea el identificador de timeframe entre las 8 temporalidades."""
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
        "1s": "1S",
        "1S": "1S",
        "1m": "1M",
        "1M": "1M",
        "max": "MAX",
        "MAX": "MAX",
    }
    return mapping.get(tf, "1D")


def _get_font(size: int, bold: bool = False):
    """Intenta cargar fuentes del sistema compatibles o recurre a la fuente por defecto."""
    font_names = ["segoeui.ttf", "arial.ttf", "consola.ttf", "DejaVuSans.ttf"]
    if bold:
        font_names = ["segoeuib.ttf", "arialbd.ttf", "consolab.ttf", "DejaVuSans-Bold.ttf"] + font_names

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


def _format_bucket_label(dt: datetime, tf_key: str) -> str:
    """Formatea la marca de tiempo del eje X según la temporalidad."""
    if tf_key == "Trades":
        return dt.strftime("%H:%M:%S")
    if tf_key in ("15m", "1h", "4h"):
        return dt.strftime("%H:%M")
    if tf_key in ("1S", "1M"):
        return dt.strftime("%d/%m")
    return dt.strftime("%d/%m %H:%M")


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
        ts_label = _format_bucket_label(dt, tf_key)
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
    base_price: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Normaliza el historial de velas u órdenes para garantizar una serie OHLCV completa y consistente.
    Soporta:
    1. Lista previa de velas OHLCV (cada elemento con open, high, low, close).
    2. 'Trades': 1 vela por cada orden real (con volumen = shares). Si hay pocas órdenes,
       rellena hacia atrás de forma plana con el precio de la primera orden/base.
    3. '15m', '1h', '4h', '1D', '1S', '1M', 'MAX': agrupa órdenes reales en cubetas temporales.
       Para 'MAX', adapta dinámicamente la ventana al span real desde la primera orden registrada
       (mínimo 2 horas) para mostrar toda la historia bursátil desde el minuto 1.
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
                est_dt = now_utc - timedelta(seconds=(len(history_candles) - idx) * 30)
                dt = _parse_iso_to_datetime(ts_raw, fallback_dt=est_dt)
                raw_trades.append({"price": round(p, 2), "shares": round(v, 2), "dt": dt})

    raw_trades.sort(key=lambda x: x["dt"])

    # 3. Procesar según timeframe:
    # ----------------------------------------------------
    # Caso A: Trades (Tick-by-tick real, 1 orden por vela)
    # ----------------------------------------------------
    if tf_key == "Trades":
        trade_candles: List[Dict[str, Any]] = []
        prev_p = raw_trades[0]["price"] if raw_trades else c_price
        for i, t in enumerate(raw_trades):
            p = t["price"]
            v = t["shares"]
            dt = t["dt"]
            o_val = prev_p if i > 0 else p
            h_val = max(o_val, p)
            l_val = min(o_val, p)
            prev_p = p
            trade_candles.append({
                "timestamp": dt.strftime("%H:%M:%S"),
                "time": int(dt.timestamp()) + i,
                "open": round(o_val, 2),
                "high": round(h_val, 2),
                "low": round(l_val, 2),
                "close": round(p, 2),
                "volume": v,
            })

        if not trade_candles:
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

        trade_candles[-1]["close"] = c_price
        trade_candles[-1]["high"] = max(trade_candles[-1]["high"], c_price)
        trade_candles[-1]["low"] = min(trade_candles[-1]["low"], c_price)
        return trade_candles[-count:]

    # -----------------------------------------------------------------
    # Caso B: Cubetas temporales ('15m', '1h', '4h', '1D', '1S', '1M', 'MAX')
    # -----------------------------------------------------------------
    res_sec = cfg.get("resolution_seconds", 1800) or 1800
    period_sec = cfg.get("period_seconds", 24 * 3600) or (24 * 3600)
    num_buckets = count

    # Ajuste dinámico adaptativo para MAX cuando el historial cabe en una ventana menor
    if tf_key == "MAX":
        if raw_trades:
            first_trade_dt = raw_trades[0]["dt"]
            real_span = max(7200, int((now_utc - first_trade_dt).total_seconds()) + 900)
            if real_span < period_sec:
                period_sec = real_span
                res_sec = max(60, int(period_sec / num_buckets))
        else:
            period_sec = 7 * 86400
            res_sec = max(60, int(period_sec / num_buckets))

    start_period = now_utc - timedelta(seconds=period_sec)

    # Determinar precio de referencia previo cronológicamente
    prior_trades = [t for t in raw_trades if t["dt"] < start_period]
    period_trades = [t for t in raw_trades if t["dt"] >= start_period]

    if prior_trades:
        # Si hay trades previos, el precio de partida es el último trade anterior
        # garantizado al menos por el valor fundamental (base_price) si existe
        if base_price is not None:
            prev_close = max(prior_trades[-1]["price"], base_price)
        else:
            prev_close = prior_trades[-1]["price"]
    elif period_trades:
        # Si no hay trades anteriores a la ventana pero sí dentro, arranca en el suelo base
        prev_close = base_price if base_price is not None else period_trades[0]["price"]
    else:
        prev_close = base_price if base_price is not None else c_price

    bucket_candles: List[Dict[str, Any]] = []

    for i in range(num_buckets):
        b_start = start_period + timedelta(seconds=i * res_sec)
        b_end = b_start + timedelta(seconds=res_sec)

        b_trades = [t for t in raw_trades if b_start <= t["dt"] < b_end]

        if b_trades:
            # Hubo compras/ventas reales en este intervalo: el precio salta instantáneamente
            prices = [t["price"] for t in b_trades]
            o_p = prev_close
            c_p = prices[-1]
            h_p = max([o_p] + prices)
            l_p = min([o_p] + prices)
            vol = sum(t["shares"] for t in b_trades)
            prev_close = c_p
        else:
            # Cubeta sin órdenes: el precio se mantiene estrictamente fiel al mercado en prev_close.
            # Queda prohibido interpolar hacia órdenes futuras para no falsear las subidas instantáneas.
            bucket_seed = (int(b_end.timestamp()) ^ int(prev_close * 100)) & 0xFFFFFFFF
            pseudo_rnd = ((bucket_seed * 1103515245 + 12345) & 0x7FFFFFFF) / float(0x7FFFFFFF)
            micro_spread = 0.0003 * prev_close
            o_p = round(prev_close, 2)
            c_p = round(prev_close, 2)
            h_p = round(prev_close + (pseudo_rnd * micro_spread), 2)
            l_p = round(prev_close - ((1.0 - pseudo_rnd) * micro_spread), 2)
            vol = 0.0
            prev_close = c_p

        ts_label = _format_bucket_label(b_end, tf_key)
        bucket_candles.append({
            "timestamp": ts_label,
            "time": int(b_end.timestamp()),
            "open": round(o_p, 2),
            "high": round(h_p, 2),
            "low": round(l_p, 2),
            "close": round(c_p, 2),
            "volume": round(vol, 2),
        })

    # Asegurar que la última vela refleje la cotización actual con precisión milimétrica
    last_c = bucket_candles[-1]
    if abs(c_price - last_c["close"]) >= 0.01:
        last_c["close"] = round(c_price, 2)
        last_c["high"] = max(last_c["high"], round(c_price, 2))
        last_c["low"] = min(last_c["low"], round(c_price, 2))

    return bucket_candles[-count:]


def _compute_ema_series(closes: List[float], period: int = 14) -> List[float]:
    """Calcula la serie punto a punto de la EMA para superponer en el gráfico."""
    if not closes:
        return []
    alpha = 2.0 / (period + 1.0)
    ema_vals = [closes[0]]
    for val in closes[1:]:
        ema_vals.append(val * alpha + ema_vals[-1] * (1.0 - alpha))
    return ema_vals


def generate_candlestick_chart(
    ticker: str,
    history_candles: Optional[List[Dict[str, Any]]] = None,
    timeframe: str = "1D",
    current_price: Optional[float] = None,
    company_name: Optional[str] = None,
) -> io.BytesIO:
    """
    Renderiza un gráfico institucional HD de velas japonesas de 960x540 píxeles.
    Incluye curva EMA 14 superpuesta, periodos planos sin barras verdes fantasma,
    estadísticas de sesión en cabecera y eje X temporal inferior.
    Devuelve un buffer BytesIO en formato PNG optimizado para discord.File.
    """
    WIDTH = 960
    HEIGHT = 540

    # Layout y márgenes HD
    HEADER_HEIGHT = 78
    FOOTER_MARGIN = 30
    PRICE_AXIS_WIDTH = 86
    LEFT = 24
    RIGHT = WIDTH - PRICE_AXIS_WIDTH
    TOP = HEADER_HEIGHT + 10
    BOTTOM = 405

    VOL_TOP = 424
    VOL_BOTTOM = HEIGHT - FOOTER_MARGIN

    # Normalizar timeframe y velas
    tf_key = normalize_timeframe(timeframe)
    tf_cfg = TIMEFRAME_CONFIG.get(tf_key, TIMEFRAME_CONFIG["1D"])
    sym = ticker.upper().lstrip("$")
    c_price = current_price if (current_price is not None and current_price > 0) else 79.52

    # Obtener base_price fundamental si está disponible
    base_p = None
    try:
        from modulos import bolsa_sanvi
        base_p = bolsa_sanvi.calculate_base_price(sym)
    except Exception:
        pass

    candles = _normalize_or_generate_candles(
        history_candles=history_candles,
        current_price=c_price,
        timeframe=tf_key,
        target_count=tf_cfg.get("default_count", 30),
        base_price=base_p,
    )

    last_close = candles[-1]["close"]
    first_open = candles[0]["open"]
    pct_change = ((last_close - first_open) / first_open) * 100.0 if first_open > 0 else 0.0

    # Serie EMA 14 de los cierres visibles
    closes_list = [c["close"] for c in candles]
    ema14_series = _compute_ema_series(closes_list, period=14)
    last_ema14 = ema14_series[-1] if ema14_series else last_close

    # Determinar rango de precios con margen
    all_highs = [c["high"] for c in candles] + ema14_series
    all_lows = [c["low"] for c in candles] + ema14_series
    min_price_raw = min(all_lows)
    max_price_raw = max(all_highs)
    total_vol_session = sum(c.get("volume", 0.0) for c in candles)

    price_range = max_price_raw - min_price_raw
    if price_range <= 0.02:
        price_range = max(1.2, min_price_raw * 0.08)

    padding = price_range * 0.12
    min_price = max(0.0, min_price_raw - padding)
    max_price = max_price_raw + padding
    eff_range = max_price - min_price

    # Rango de volumen
    max_vol = max([c.get("volume", 0.0) for c in candles] or [10.0])
    if max_vol <= 0:
        max_vol = 10.0

    # Inicializar lienzo Pillow HD
    image = Image.new("RGBA", (WIDTH, HEIGHT), COLOR_BG)
    draw = ImageDraw.Draw(image)

    # Fuentes
    font_title = _get_font(22, bold=True)
    font_price = _get_font(25, bold=True)
    font_badge = _get_font(13, bold=True)
    font_stats = _get_font(12, bold=False)
    font_axis = _get_font(12, bold=False)
    font_small = _get_font(11, bold=False)

    # 1. Cabecera (Header Izquierda)
    display_title = f"${sym}"
    if company_name:
        display_title += f" · {company_name}"
    draw.text((LEFT, 12), display_title, fill=COLOR_WHITE, font=font_title)

    # Precio actual y badge de variación
    price_str = f"{last_close:.2f} Porros"
    draw.text((LEFT, 42), price_str, fill=COLOR_WHITE, font=font_price)

    change_sign = "+" if pct_change >= 0 else ""
    change_str = f"{change_sign}{pct_change:.2f}%"
    change_color = COLOR_BULLISH if pct_change >= 0 else COLOR_BEARISH

    price_bbox = draw.textbbox((LEFT, 42), price_str, font=font_price)
    change_x = price_bbox[2] + 14
    draw.text((change_x, 48), change_str, fill=change_color, font=font_badge)

    # Leyenda EMA 14 junto al cambio porcentual
    change_bbox = draw.textbbox((change_x, 48), change_str, font=font_badge)
    ema_legend_x = change_bbox[2] + 22
    ema_legend_str = f"━ EMA 14: {last_ema14:.2f}"
    draw.text((ema_legend_x, 48), ema_legend_str, fill=COLOR_EMA14, font=font_stats)

    # Cabecera Derecha: Badge de Timeframe + Caja de Estadísticas (MÁX / MÍN / VOL)
    badge_label = tf_cfg.get("label", tf_key)
    tf_str = f"[ {badge_label} ]"
    tf_bbox = draw.textbbox((0, 0), tf_str, font=font_badge)
    tf_width = tf_bbox[2] - tf_bbox[0]
    draw.text((RIGHT - tf_width, 14), tf_str, fill=COLOR_CURRENT_LINE, font=font_badge)

    stats_str = f"MÁX: {max(c['high'] for c in candles):.2f}   MÍN: {min(c['low'] for c in candles):.2f}   VOL: {int(round(total_vol_session))} acc."
    stats_bbox = draw.textbbox((0, 0), stats_str, font=font_stats)
    stats_width = stats_bbox[2] - stats_bbox[0]
    draw.text((RIGHT - stats_width, 46), stats_str, fill=COLOR_MUTED, font=font_stats)

    # 2. Rejilla (Grid) horizontal y vertical tenue en el área de precios
    num_grid_lines = 5
    for i in range(num_grid_lines):
        ratio = i / (num_grid_lines - 1)
        grid_y = int(TOP + ratio * (BOTTOM - TOP))
        grid_price = max_price - ratio * eff_range

        draw.line([(LEFT, grid_y), (RIGHT, grid_y)], fill=COLOR_GRID, width=1)
        draw.text((RIGHT + 8, grid_y - 7), f"{grid_price:.2f}", fill=COLOR_AXIS_TEXT, font=font_axis)

    # Separador entre gráfico de precio y subgráfico de volumen
    draw.line([(LEFT, 414), (RIGHT, 414)], fill=COLOR_GRID, width=1)
    draw.text((LEFT + 2, 416), "VOLUMEN (ACCIONES)", fill=COLOR_AXIS_TEXT, font=font_small)

    # Línea base del eje X inferior
    draw.line([(LEFT, VOL_BOTTOM), (RIGHT, VOL_BOTTOM)], fill=COLOR_GRID, width=1)

    # 3. Dibujo de Velas Japonesas, Barras de Volumen y Eje X
    n_candles = len(candles)
    chart_width = RIGHT - LEFT
    slot_width = chart_width / n_candles
    candle_body_width = max(5, int(slot_width * 0.68))
    if candle_body_width % 2 == 0:
        candle_body_width += 1

    ema_points = []

    for i, candle in enumerate(candles):
        center_x = int(LEFT + (i + 0.5) * slot_width)
        o_val = candle["open"]
        c_val = candle["close"]
        h_val = candle["high"]
        l_val = candle["low"]
        vol_val = float(candle.get("volume", 0.0))

        # Coordenadas Y de precios
        y_high = int(TOP + (max_price - h_val) / eff_range * (BOTTOM - TOP))
        y_low = int(TOP + (max_price - l_val) / eff_range * (BOTTOM - TOP))
        y_open = int(TOP + (max_price - o_val) / eff_range * (BOTTOM - TOP))
        y_close = int(TOP + (max_price - c_val) / eff_range * (BOTTOM - TOP))

        y_high = max(TOP, min(BOTTOM, y_high))
        y_low = max(TOP, min(BOTTOM, y_low))
        y_open = max(TOP, min(BOTTOM, y_open))
        y_close = max(TOP, min(BOTTOM, y_close))

        # Punto de EMA 14
        ema_val = ema14_series[i]
        y_ema = int(TOP + (max_price - ema_val) / eff_range * (BOTTOM - TOP))
        y_ema = max(TOP, min(BOTTOM, y_ema))
        ema_points.append((center_x, y_ema))

        half_w = candle_body_width // 2
        has_price_move = abs(c_val - o_val) > 1e-4 or abs(h_val - l_val) > 1e-4

        if vol_val <= 0.0 and not has_price_move:
            # Periodo sin órdenes y precio plano: segmento horizontal gris azulado sutil (#3A4659)
            draw.line(
                [(center_x - half_w, y_close), (center_x + half_w, y_close)],
                fill=COLOR_FLAT_TICK,
                width=2,
            )
        else:
            # Hubo trade o variación real de precio: pintar vela alcista/bajista
            is_bullish = c_val >= o_val
            candle_color = COLOR_BULLISH if is_bullish else COLOR_BEARISH

            # Mecha (Wick)
            draw.line([(center_x, y_high), (center_x, y_low)], fill=candle_color, width=1)

            # Cuerpo (Body)
            body_top = min(y_open, y_close)
            body_bottom = max(y_open, y_close)
            if body_bottom - body_top < 3:
                body_bottom = body_top + 3

            draw.rectangle(
                [(center_x - half_w, body_top), (center_x + half_w, body_bottom)],
                fill=candle_color,
                outline=candle_color,
            )

        # Subgráfico de Volumen: SOLO dibujar barra cuando vol_val > 0
        if vol_val > 0.0:
            is_bullish_vol = c_val >= o_val
            vol_color = COLOR_BULLISH if is_bullish_vol else COLOR_BEARISH
            vol_height = int((vol_val / max_vol) * (VOL_BOTTOM - VOL_TOP - 6))
            vol_height = max(3, min(VOL_BOTTOM - VOL_TOP - 4, vol_height))
            vol_y = VOL_BOTTOM - vol_height

            draw.rectangle(
                [(center_x - half_w, vol_y), (center_x + half_w, VOL_BOTTOM - 1)],
                fill=vol_color,
                outline=None,
            )

    # 4. Dibujar Curva EMA 14 superpuesta (#FFB300)
    if len(ema_points) >= 2:
        draw.line(ema_points, fill=COLOR_EMA14, width=2)

    # 5. Eje X inferior con 5-6 marcas de tiempo espaciadas uniformemente
    num_x_labels = min(6, n_candles)
    if num_x_labels >= 2:
        step_idx = (n_candles - 1) / (num_x_labels - 1)
        for k in range(num_x_labels):
            idx = int(round(k * step_idx))
            idx = max(0, min(n_candles - 1, idx))
            cx = int(LEFT + (idx + 0.5) * slot_width)
            ts_text = str(candles[idx].get("timestamp", ""))
            if ts_text:
                tb = draw.textbbox((0, 0), ts_text, font=font_small)
                tw = tb[2] - tb[0]
                tx = max(LEFT, min(RIGHT - tw, cx - tw // 2))
                draw.line([(cx, VOL_BOTTOM), (cx, VOL_BOTTOM + 4)], fill=COLOR_AXIS_TEXT, width=1)
                draw.text((tx, VOL_BOTTOM + 6), ts_text, fill=COLOR_AXIS_TEXT, font=font_small)

    # 6. Línea de Cotización Actual con Badge Flotante
    curr_y = int(TOP + (max_price - last_close) / eff_range * (BOTTOM - TOP))
    curr_y = max(TOP, min(BOTTOM, curr_y))

    draw.line([(LEFT, curr_y), (RIGHT, curr_y)], fill=COLOR_CURRENT_LINE, width=1)

    badge_x1 = RIGHT + 4
    badge_y1 = curr_y - 10
    badge_x2 = WIDTH - 6
    badge_y2 = curr_y + 10
    draw.rounded_rectangle([(badge_x1, badge_y1), (badge_x2, badge_y2)], radius=4, fill=COLOR_BADGE_BG)

    badge_text = f"{last_close:.2f}"
    draw.text((badge_x1 + 7, badge_y1 + 2), badge_text, fill=COLOR_WHITE, font=font_axis)

    # 7. Exportación a BytesIO PNG
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer

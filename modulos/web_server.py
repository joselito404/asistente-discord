"""
Servidor HTTP de salud, estado en tiempo real, visor de logs, grabaciones y Web Terminal de la Bolsa Sanvi (Puerto 10000 en Render).
Endpoints:
- GET /status: Estado JSON del bot, conexiones de voz, protocolo DAVE E2EE y hora española.
- GET /logs: Últimas 200 líneas del buffer global de logs.
- GET /bolsa: Web Terminal interactiva institucional con TradingView Lightweight Charts.
- GET /api/bolsa/data: API JSON de cotizaciones, indicadores, dividend pool y velas OHLCV en vivo.
- GET /audios (o /grabaciones): Panel web reproductor de grabaciones de las últimas 24h.
- GET /audios/zip (o /grabaciones/zip): Descarga en paquete ZIP de todas las grabaciones activas y su metadata.
- GET /audios/file/<fname>: Streaming/descarga segura de un archivo .wav individual (protegido con os.path.basename).
- GET /api/audios: API JSON del registro de intervenciones de voz.
"""

from datetime import datetime, timezone
import html
import http.server
import io
import json
import os
import socketserver
import sys
import urllib.parse
import zipfile


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


def get_bolsa_api_payload():
    """Genera el payload JSON en tiempo real para la API bursátil y Web Terminal."""
    from modulos import bolsa_sanvi, bolsa_graficas
    mercado = bolsa_sanvi.load_market_data()
    pool_data = bolsa_sanvi.load_pool_data()
    tickers_dict = {}

    now_utc = datetime.now(timezone.utc)

    for ticker, info in bolsa_sanvi.TICKERS.items():
        t_data = mercado.get("tickers", {}).get(ticker, {})
        prices = bolsa_sanvi.get_bid_ask_prices(ticker)
        base_p = bolsa_sanvi.calculate_base_price(ticker)
        history = t_data.get("order_history", [])
        amm_shares = t_data.get("amm_shares", 9900)
        user_shares = 10000 - amm_shares
        float_pct = round((user_shares / 10000.0) * 100.0, 2)

        tech = bolsa_sanvi.get_ticker_technical_metrics(ticker)
        rsi = tech["rsi"]
        mas = tech["mas"]

        # Generar series OHLCV para las 8 temporalidades completas
        series = {}
        for tf in ["Trades", "15m", "1h", "4h", "1D", "1S", "1M", "MAX"]:
            candles = bolsa_graficas._normalize_or_generate_candles(
                history_candles=history,
                current_price=prices["market"],
                timeframe=tf,
                base_price=base_p,
            )
            formatted_candles = []
            formatted_volume = []
            last_t = 0
            for c in candles:
                c_time = c.get("time", int(now_utc.timestamp()))
                # Garantizar estricta monotonía creciente en timestamps para Lightweight Charts
                if c_time <= last_t:
                    c_time = last_t + 1
                last_t = c_time

                formatted_candles.append({
                    "time": c_time,
                    "open": float(c["open"]),
                    "high": float(c["high"]),
                    "low": float(c["low"]),
                    "close": float(c["close"]),
                    "timestamp": c.get("timestamp", ""),
                })
                formatted_volume.append({
                    "time": c_time,
                    "value": float(c.get("volume", 0.0)),
                    "color": "#00E67688" if c["close"] >= c["open"] else "#FF525288",
                })

            tf_pct = 0.0
            tf_diff = 0.0
            if formatted_candles:
                tf_first_open = formatted_candles[0]["open"]
                tf_last_close = formatted_candles[-1]["close"]
                if tf_first_open > 0:
                    tf_diff = round(tf_last_close - tf_first_open, 2)
                    tf_pct = round((tf_diff / tf_first_open) * 100.0, 2)

            series[tf] = {
                "candles": formatted_candles,
                "volume": formatted_volume,
                "pct_change": tf_pct,
                "diff": tf_diff,
            }

        # Calcular cambio porcentual respecto a la primera vela disponible en 1D
        d1_candles = series.get("1D", {}).get("candles", [])
        pct_change = 0.0
        if d1_candles:
            first_open = d1_candles[0]["open"]
            last_close = d1_candles[-1]["close"]
            if first_open > 0:
                pct_change = round(((last_close - first_open) / first_open) * 100.0, 2)

        tickers_dict[ticker] = {
            "symbol": ticker,
            "name": info.get("name", ticker),
            "description": info.get("description", ""),
            "avatar": info.get("avatar", ""),
            "current_price": prices["market"],
            "base_price": base_p,
            "pct_change": pct_change,
            "bid": prices["bid"],
            "ask": prices["ask"],
            "amm_shares": amm_shares,
            "user_shares": user_shares,
            "float_pct": float_pct,
            "rsi_14": round(rsi, 2),
            "mas": mas,
            "recent_trades": list(reversed(history[-25:])),
            "series": series,
        }

    return {
        "timestamp": now_utc.isoformat(),
        "is_halted": bolsa_sanvi.is_market_halted(),
        "halt_reason": bolsa_sanvi.get_market_halt_reason(),
        "pool": {
            "accumulated": round(pool_data.get("accumulated_pool", 0.0), 2),
            "total_distributed": round(pool_data.get("total_distributed", 0.0), 2),
            "next_distribution": pool_data.get("next_distribution_iso", "2026-11-01T00:00:00Z"),
        },
        "tickers": tickers_dict,
    }


def render_bolsa_html() -> str:
    """Devuelve la página HTML5 de la Web Terminal de la Bolsa Sanvi estilo Trading 212."""
    return """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bolsa Sanvi — Web Terminal 24/7 (Trading 212 Style)</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <!-- TradingView Lightweight Charts Standalone CDN -->
  <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    :root {
      --bg-dark: #000000;
      --bg-surface: #0c0d12;
      --bg-card: #14161f;
      --bg-card-hover: #1a1d29;
      --border-color: #212433;
      --text-main: #FFFFFF;
      --text-muted: #8E8E93;
      --bullish: #00E676;
      --bullish-glow: rgba(0, 230, 118, 0.25);
      --bearish: #FF5252;
      --bearish-glow: rgba(255, 82, 82, 0.25);
      --cian-accent: #00A3FF;
      --cian-glow: rgba(0, 163, 255, 0.2);
      --font-ui: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: var(--font-ui);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
    }

    /* Top Navigation Bar */
    header {
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-color);
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      position: sticky;
      top: 0;
      z-index: 50;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-icon {
      font-size: 24px;
      background: linear-gradient(135deg, #00A3FF, #00E676);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .brand-title {
      font-size: 18px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: var(--text-main);
    }
    .market-badge {
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 12px;
      background: rgba(0, 230, 118, 0.12);
      color: var(--bullish);
      border: 1px solid rgba(0, 230, 118, 0.3);
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }
    .market-badge.halted {
      background: rgba(255, 82, 82, 0.15);
      color: var(--bearish);
      border-color: rgba(255, 82, 82, 0.35);
    }
    .pulse-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 0 0 8px currentColor;
    }

    /* Ticker Selector in Header */
    .ticker-bar {
      display: flex;
      gap: 8px;
      background: #08090d;
      padding: 4px;
      border-radius: 10px;
      border: 1px solid var(--border-color);
    }
    .ticker-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }
    .ticker-btn:hover {
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.05);
    }
    .ticker-btn.active {
      background: var(--cian-accent);
      color: #FFFFFF;
      box-shadow: 0 2px 10px var(--cian-glow);
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .pool-badge {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      background: var(--bg-card);
      padding: 6px 14px;
      border-radius: 8px;
      border: 1px solid var(--border-color);
    }
    .pool-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }
    .pool-val { font-size: 13px; font-weight: 700; color: #FFD54F; font-family: var(--font-mono); }

    /* Main Container */
    main {
      flex: 1;
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
      padding: 20px 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    /* Sub-header: Asset Info & Controls */
    .asset-header {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 18px 24px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    .asset-info {
      display: flex;
      align-items: baseline;
      gap: 16px;
      flex-wrap: wrap;
    }
    .asset-title {
      font-size: 24px;
      font-weight: 800;
      color: var(--text-main);
    }
    .asset-name {
      font-size: 14px;
      color: var(--text-muted);
      font-weight: 500;
    }
    .asset-price-box {
      display: flex;
      align-items: baseline;
      gap: 12px;
    }
    .asset-price {
      font-size: 32px;
      font-weight: 800;
      font-family: var(--font-mono);
      letter-spacing: -1px;
    }
    .asset-change {
      font-size: 14px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 6px;
      font-family: var(--font-mono);
    }
    .asset-change.bull { background: rgba(0, 230, 118, 0.15); color: var(--bullish); }
    .asset-change.bear { background: rgba(255, 82, 82, 0.15); color: var(--bearish); }

    .bid-ask-pills {
      display: flex;
      gap: 8px;
      font-family: var(--font-mono);
      font-size: 12px;
    }
    .pill {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      padding: 6px 12px;
      border-radius: 6px;
    }
    .pill span { color: var(--text-muted); font-weight: 500; }

    /* Timeframe Selector */
    .timeframe-bar {
      display: flex;
      gap: 6px;
      background: #08090d;
      padding: 4px;
      border-radius: 8px;
      border: 1px solid var(--border-color);
    }
    .tf-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .tf-btn:hover {
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.05);
    }
    .tf-btn.active {
      background: #2a2e3d;
      color: var(--text-main);
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
    }

    /* Chart Section */
    .chart-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      overflow: hidden;
      position: relative;
      display: flex;
      flex-direction: column;
    }
    .chart-container-wrapper {
      width: 100%;
      height: 480px;
      position: relative;
      background: #000000;
    }
    #tv-chart {
      width: 100%;
      height: 100%;
    }
    .chart-legend {
      position: absolute;
      top: 12px;
      left: 16px;
      z-index: 10;
      display: flex;
      gap: 12px;
      font-size: 11px;
      font-family: var(--font-mono);
      color: var(--text-muted);
      pointer-events: none;
      background: rgba(0, 0, 0, 0.6);
      padding: 4px 10px;
      border-radius: 6px;
      backdrop-filter: blur(4px);
    }
    .chart-legend span b { color: var(--text-main); font-weight: 600; }

    /* Metrics Grid */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
    }
    .metric-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
      border-color: #2e3447;
      transform: translateY(-2px);
    }
    .metric-title {
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .metric-value {
      font-size: 20px;
      font-weight: 800;
      font-family: var(--font-mono);
      color: var(--text-main);
    }
    .metric-sub {
      font-size: 11px;
      color: var(--text-muted);
    }
    .progress-bar-bg {
      width: 100%;
      height: 6px;
      background: #1c1f2e;
      border-radius: 3px;
      overflow: hidden;
      margin-top: 4px;
    }
    .progress-bar-fill {
      height: 100%;
      background: linear-gradient(90deg, #00A3FF, #00E676);
      border-radius: 3px;
      transition: width 0.4s ease;
    }

    /* Bottom Split Panels */
    .bottom-grid {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 20px;
    }
    @media (max-width: 960px) {
      .bottom-grid { grid-template-columns: 1fr; }
    }

    .panel-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .panel-title {
      font-size: 15px;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    /* Trades Table */
    .trades-table-wrap {
      overflow-x: auto;
      max-height: 280px;
      overflow-y: auto;
    }
    table.trades-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      font-family: var(--font-mono);
    }
    table.trades-table th {
      text-align: left;
      padding: 8px 10px;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-color);
      font-weight: 600;
      font-size: 11px;
      text-transform: uppercase;
      position: sticky;
      top: 0;
      background: var(--bg-surface);
    }
    table.trades-table td {
      padding: 8px 10px;
      border-bottom: 1px solid #141722;
      color: #D1D4DC;
    }
    .trade-type-buy { color: var(--bullish); font-weight: 700; }
    .trade-type-sell { color: var(--bearish); font-weight: 700; }

    /* Yield Pool Info List */
    .pool-features {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 10px;
      font-size: 12px;
      color: var(--text-muted);
    }
    .pool-features li {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      line-height: 1.4;
    }
    .pool-features strong { color: var(--text-main); }

    /* Footer */
    footer {
      border-top: 1px solid var(--border-color);
      padding: 16px 24px;
      text-align: center;
      font-size: 12px;
      color: var(--text-muted);
      background: var(--bg-surface);
      margin-top: auto;
    }
    footer a { color: var(--cian-accent); text-decoration: none; }
  </style>
</head>
<body>

  <!-- Top Navigation Header -->
  <header>
    <div class="brand">
      <div class="brand-icon">📈</div>
      <div>
        <div class="brand-title">SANVI EXCHANGE</div>
        <div id="market-status-badge" class="market-badge">
          <span class="pulse-dot"></span> 24/7 AMM Activo
        </div>
      </div>
    </div>

    <!-- Ticker Selectors -->
    <div class="ticker-bar" id="ticker-bar">
      <button class="ticker-btn active" onclick="setTicker('JOSE')">$JOSE</button>
      <button class="ticker-btn" onclick="setTicker('TERRE')">$TERRE</button>
      <button class="ticker-btn" onclick="setTicker('OMEN')">$OMEN</button>
      <button class="ticker-btn" onclick="setTicker('RACER')">$RACER</button>
    </div>

    <!-- Yield Pool Live Badge -->
    <div class="header-actions">
      <div class="pool-badge">
        <span class="pool-label">🏆 Bote Dividendos</span>
        <span id="pool-accumulated-val" class="pool-val">-- Porros</span>
      </div>
    </div>
  </header>

  <!-- Main Trading Dashboard -->
  <main>
    <!-- Asset Summary Header -->
    <div class="asset-header">
      <div class="asset-info">
        <div>
          <div class="asset-title" id="asset-symbol-title">$JOSE</div>
          <div class="asset-name" id="asset-company-name">Joselito</div>
        </div>
        <div class="asset-price-box">
          <div class="asset-price" id="asset-current-price">-- Porros</div>
          <div class="asset-change bull" id="asset-change-badge">+0.00%</div>
        </div>
      </div>

      <div style="display:flex; align-items:center; gap: 14px; flex-wrap: wrap;">
        <div class="bid-ask-pills">
          <div class="pill"><span>Ask:</span> <b id="asset-ask-val" style="color:var(--bullish);">--</b></div>
          <div class="pill"><span>Bid:</span> <b id="asset-bid-val" style="color:var(--bearish);">--</b></div>
        </div>

        <!-- Timeframe Toolbar -->
        <div class="timeframe-bar" id="timeframe-bar">
          <button class="tf-btn" onclick="setTimeframe('Trades')">Trades</button>
          <button class="tf-btn" onclick="setTimeframe('15m')">15m</button>
          <button class="tf-btn" onclick="setTimeframe('1h')">1h</button>
          <button class="tf-btn" onclick="setTimeframe('4h')">4h</button>
          <button class="tf-btn active" onclick="setTimeframe('1D')">1D</button>
          <button class="tf-btn" onclick="setTimeframe('1S')">1S</button>
          <button class="tf-btn" onclick="setTimeframe('1M')">1M</button>
          <button class="tf-btn" onclick="setTimeframe('MAX')">MAX</button>
        </div>
      </div>
    </div>

    <!-- TradingView Lightweight Chart Container -->
    <div class="chart-card">
      <div class="chart-legend" id="chart-legend">
        <span>O: <b id="leg-open">--</b></span>
        <span>H: <b id="leg-high">--</b></span>
        <span>L: <b id="leg-low">--</b></span>
        <span>C: <b id="leg-close">--</b></span>
        <span>Vol: <b id="leg-vol">--</b></span>
      </div>
      <div class="chart-container-wrapper">
        <div id="tv-chart"></div>
      </div>
    </div>

    <!-- Metrics Grid -->
    <div class="metrics-grid">
      <!-- Fundamental Value -->
      <div class="metric-card">
        <div class="metric-title">🏛️ Valor Fundamental (Aura)</div>
        <div class="metric-value" id="val-fundamental">-- Porros</div>
        <div class="metric-sub">Suelo garantizado por Book Value + E30d</div>
      </div>

      <!-- Technical RSI -->
      <div class="metric-card">
        <div class="metric-title">📊 RSI (14 periodos)</div>
        <div class="metric-value" id="val-rsi">--</div>
        <div class="metric-sub" id="sub-rsi">Momentum Cuantitativo</div>
      </div>

      <!-- Float Circulation -->
      <div class="metric-card">
        <div class="metric-title">📜 Float en Cartera vs AMM</div>
        <div class="metric-value" id="val-float">-- / 10.000</div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" id="float-progress-fill" style="width: 1%;"></div>
        </div>
        <div class="metric-sub" id="sub-float-pct">0.00% en manos de usuarios</div>
      </div>

      <!-- Moving Averages -->
      <div class="metric-card">
        <div class="metric-title">📈 Medias Móviles & Cruces</div>
        <div class="metric-value" id="val-mas">EMA 14: --</div>
        <div class="metric-sub" id="sub-mas-signal">SMA 50: -- • Tendencia Estable</div>
      </div>
    </div>

    <!-- Bottom Panels: Trades & Yield Pool -->
    <div class="bottom-grid">
      <!-- Order History -->
      <div class="panel-card">
        <div class="panel-title">
          <span>🧾 Historial de Órdenes Ejecutadas</span>
          <span style="font-size:12px; color:var(--text-muted); font-weight:500;">En tiempo real</span>
        </div>
        <div class="trades-table-wrap">
          <table class="trades-table">
            <thead>
              <tr>
                <th>Hora</th>
                <th>Operación</th>
                <th>Acciones</th>
                <th>Precio</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody id="trades-table-body">
              <tr><td colspan="5" style="text-align:center; color:var(--text-muted);">Cargando historial...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Yield Pool & Rules -->
      <div class="panel-card">
        <div class="panel-title">
          <span>🏆 Yield Pool de Dividendos</span>
          <span style="font-size:11px; background:#FFD54F20; color:#FFD54F; padding:2px 8px; border-radius:4px;">1er día/mes</span>
        </div>
        <ul class="pool-features">
          <li>
            <span>💎</span>
            <div><strong>Comisión Retenida (0.5%):</strong> Cada compra y venta nutre automáticamente el bote acumulado.</div>
          </li>
          <li>
            <span>🔥</span>
            <div><strong>Quema Deflacionaria (0.5%):</strong> Cada orden destruye masa monetaria de Porros protegiendo el poder adquisitivo.</div>
          </li>
          <li>
            <span>💰</span>
            <div><strong>Reparto Pro-rata:</strong> El Yield Pool se abona en cuenta a todos los accionistas de la Bolsa Sanvi según sus participaciones.</div>
          </li>
          <li>
            <span>⚡</span>
            <div><strong>Sinergia de Cartera:</strong> Mantener acciones activas otorga un multiplicador de hasta +25% en <code>/trabajar</code>.</div>
          </li>
        </ul>
      </div>
    </div>
  </main>

  <footer>
    Bolsa Sanvi 24/7 • Automated Market Maker (K=2000) • Integración nativa con <a href="https://discord.com" target="_blank">Discord Bot</a>
  </footer>

  <!-- Interactive Terminal Logic -->
  <script>
    let bolsaData = null;
    let selectedTicker = 'JOSE';
    let selectedTf = '1D';

    let tvChart = null;
    let candleSeries = null;
    let volumeSeries = null;

    // Inicializar Lightweight Charts
    function initChart() {
      const chartContainer = document.getElementById('tv-chart');
      if (!chartContainer) return;
      chartContainer.innerHTML = '';

      if (typeof LightweightCharts === 'undefined') {
        chartContainer.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#8E8E93;font-size:14px;">Error cargando librería gráfica TradingView. Revisa tu conexión.</div>';
        return;
      }

      tvChart = LightweightCharts.createChart(chartContainer, {
        layout: {
          background: { type: 'solid', color: '#000000' },
          textColor: '#8E8E93',
          fontFamily: "'JetBrains Mono', monospace",
        },
        grid: {
          vertLines: { color: '#161922' },
          horzLines: { color: '#161922' },
        },
        crosshair: {
          mode: LightweightCharts.CrosshairMode.Normal,
          vertLine: { color: '#00A3FF', width: 1, style: 2 },
          horzLine: { color: '#00A3FF', width: 1, style: 2 },
        },
        rightPriceScale: {
          borderColor: '#212433',
          scaleMargins: { top: 0.1, bottom: 0.25 },
        },
        timeScale: {
          borderColor: '#212433',
          timeVisible: true,
          secondsVisible: true,
        },
      });

      // Serie de Velas Japonesas Trading 212
      candleSeries = tvChart.addCandlestickSeries({
        upColor: '#00E676',
        downColor: '#FF5252',
        borderVisible: false,
        wickUpColor: '#00E676',
        wickDownColor: '#FF5252',
      });

      // Subgráfico de Volumen
      volumeSeries = tvChart.addHistogramSeries({
        priceFormat: { type: 'volume' },
        priceScaleId: '',
      });
      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.82, bottom: 0 },
      });

      // Responsive Resize
      const resizeObserver = new ResizeObserver(entries => {
        if (!entries || !entries[0] || !tvChart) return;
        const { width, height } = entries[0].contentRect;
        tvChart.applyOptions({ width, height });
      });
      resizeObserver.observe(chartContainer);

      // Crosshair Tooltip interactivo con precio y % dinámicos según vela inspeccionada
      tvChart.subscribeCrosshairMove(param => {
        if (!param || !param.seriesData || !param.seriesData.get(candleSeries)) {
          updateLegendFromCurrent();
          updatePriceAndChange(null);
          return;
        }
        const data = param.seriesData.get(candleSeries);
        const vol = param.seriesData.get(volumeSeries);
        if (data) {
          document.getElementById('leg-open').textContent = data.open.toFixed(2);
          document.getElementById('leg-high').textContent = data.high.toFixed(2);
          document.getElementById('leg-low').textContent = data.low.toFixed(2);
          document.getElementById('leg-close').textContent = data.close.toFixed(2);
          document.getElementById('leg-vol').textContent = vol ? vol.value.toFixed(1) : '0.0';
          updatePriceAndChange(data);
        }
      });
    }

    function updateLegendFromCurrent() {
      if (!bolsaData || !bolsaData.tickers || !bolsaData.tickers[selectedTicker]) return;
      const t = bolsaData.tickers[selectedTicker];
      const seriesObj = t.series && t.series[selectedTf];
      if (seriesObj && seriesObj.candles && seriesObj.candles.length > 0) {
        const last = seriesObj.candles[seriesObj.candles.length - 1];
        const lastVol = seriesObj.volume && seriesObj.volume.length > 0 ? seriesObj.volume[seriesObj.volume.length - 1].value : 0;
        document.getElementById('leg-open').textContent = last.open.toFixed(2);
        document.getElementById('leg-high').textContent = last.high.toFixed(2);
        document.getElementById('leg-low').textContent = last.low.toFixed(2);
        document.getElementById('leg-close').textContent = last.close.toFixed(2);
        document.getElementById('leg-vol').textContent = lastVol.toFixed(1);
      }
    }

    function updatePriceAndChange(hoverCandle = null) {
      if (!bolsaData || !bolsaData.tickers) return;
      const t = bolsaData.tickers[selectedTicker];
      if (!t) return;

      const s = t.series && t.series[selectedTf];
      const candles = (s && s.candles) || [];

      let currentP = t.current_price;
      let baseOpen = currentP;

      if (candles.length > 0) {
        baseOpen = candles[0].open;
        if (hoverCandle) {
          currentP = hoverCandle.close;
        } else {
          currentP = candles[candles.length - 1].close || t.current_price;
        }
      }

      const diff = currentP - baseOpen;
      const pct = baseOpen > 0 ? (diff / baseOpen) * 100.0 : 0.0;

      // Actualizar Precio mostrado
      document.getElementById('asset-current-price').textContent = currentP.toFixed(2) + ' Porros';

      // Actualizar Badge de % dinámico según las velas
      const changeElem = document.getElementById('asset-change-badge');
      const sign = pct > 0 ? '+' : '';
      changeElem.textContent = sign + pct.toFixed(2) + '%';
      if (pct > 0) {
        changeElem.className = 'asset-change bull';
      } else if (pct < 0) {
        changeElem.className = 'asset-change bear';
      } else {
        changeElem.className = 'asset-change';
      }
    }

    function renderActiveData() {
      if (!bolsaData || !bolsaData.tickers) return;
      const t = bolsaData.tickers[selectedTicker];
      if (!t) return;

      // Actualizar Encabezado del Activo
      document.getElementById('asset-symbol-title').textContent = '$' + t.symbol;
      document.getElementById('asset-company-name').textContent = t.name;
      document.getElementById('asset-ask-val').textContent = t.ask.toFixed(2);
      document.getElementById('asset-bid-val').textContent = t.bid.toFixed(2);

      // Variación % y Precio dinámico según las velas del timeframe activo
      updatePriceAndChange(null);

      // Métricas Fundamentales
      document.getElementById('val-fundamental').textContent = t.base_price.toFixed(2) + ' Porros';

      // RSI
      const rsiElem = document.getElementById('val-rsi');
      rsiElem.textContent = t.rsi_14.toFixed(1);
      const subRsi = document.getElementById('sub-rsi');
      if (t.rsi_14 >= 70) {
        rsiElem.style.color = '#FF5252';
        subRsi.textContent = 'Sobrecompra Cuantitativa';
      } else if (t.rsi_14 <= 30) {
        rsiElem.style.color = '#AB47BC';
        subRsi.textContent = 'Sobreventa Cuantitativa';
      } else {
        rsiElem.style.color = '#00E676';
        subRsi.textContent = 'Rango Neutral Saludable';
      }

      // Float
      document.getElementById('val-float').textContent = t.user_shares.toLocaleString() + ' / 10.000';
      document.getElementById('float-progress-fill').style.width = Math.min(100, Math.max(1, t.float_pct)) + '%';
      document.getElementById('sub-float-pct').textContent = t.float_pct.toFixed(2) + '% en manos de usuarios';

      // MAs
      if (t.mas) {
        const ema14 = t.mas.ema_14 ? t.mas.ema_14.toFixed(2) : '--';
        const sma50 = t.mas.sma_50 ? t.mas.sma_50.toFixed(2) : '--';
        document.getElementById('val-mas').textContent = 'EMA 14: ' + ema14;
        document.getElementById('sub-mas-signal').textContent = 'SMA 50: ' + sma50;
      }

      // Gráfica de Velas y Volumen
      if (candleSeries && volumeSeries && t.series && t.series[selectedTf]) {
        const s = t.series[selectedTf];
        candleSeries.setData(s.candles || []);
        volumeSeries.setData(s.volume || []);
        tvChart.timeScale().fitContent();
        updateLegendFromCurrent();
      }

      // Tabla de Órdenes
      const tbody = document.getElementById('trades-table-body');
      if (tbody) {
        const trades = t.recent_trades || [];
        if (trades.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">Sin órdenes registradas recientemente.</td></tr>';
        } else {
          tbody.innerHTML = trades.map(tr => {
            const isBuy = (tr.type || 'BUY').toUpperCase() === 'BUY';
            const typeClass = isBuy ? 'trade-type-buy' : 'trade-type-sell';
            const typeLabel = isBuy ? 'Compra' : 'Venta';
            const price = (tr.price || tr.market_price || 0).toFixed(2);
            const total = (tr.total_cost || (tr.shares * price) || 0).toFixed(2);
            let timeStr = tr.timestamp || '';
            if (timeStr.includes('T')) {
              try { timeStr = new Date(timeStr).toLocaleTimeString(); } catch(e){}
            }
            return `<tr>
              <td>${timeStr || 'Hoy'}</td>
              <td class="${typeClass}">${typeLabel}</td>
              <td>${tr.shares || 0}</td>
              <td>${price}</td>
              <td>${total} P</td>
            </tr>`;
          }).join('');
        }
      }

      // Yield Pool
      if (bolsaData.pool) {
        document.getElementById('pool-accumulated-val').textContent = bolsaData.pool.accumulated.toFixed(2) + ' Porros';
      }

      // Estado de parada
      const haltBadge = document.getElementById('market-status-badge');
      if (bolsaData.is_halted) {
        haltBadge.className = 'market-badge halted';
        haltBadge.innerHTML = '<span class="pulse-dot"></span> Paro de Emergencia';
      } else {
        haltBadge.className = 'market-badge';
        haltBadge.innerHTML = '<span class="pulse-dot"></span> 24/7 AMM Activo';
      }
    }

    function setTicker(ticker) {
      selectedTicker = ticker;
      document.querySelectorAll('#ticker-bar .ticker-btn').forEach(btn => {
        if (btn.textContent.includes(ticker)) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });
      renderActiveData();
    }

    function setTimeframe(tf) {
      selectedTf = tf;
      document.querySelectorAll('#timeframe-bar .tf-btn').forEach(btn => {
        if (btn.textContent === tf) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });
      renderActiveData();
    }

    function fetchMarketData() {
      fetch('/api/bolsa/data')
        .then(res => res.json())
        .then(data => {
          bolsaData = data;
          renderActiveData();
        })
        .catch(err => {
          console.error("Error al obtener cotizaciones de /api/bolsa/data:", err);
        });
    }

    // Inicialización al cargar la página
    window.addEventListener('DOMContentLoaded', () => {
      initChart();
      fetchMarketData();
      // Auto-refresco cada 10 segundos
      setInterval(fetchMarketData, 10000);
    });
  </script>
</body>
</html>
"""


class ReusableTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_health_check_server():
    port = int(os.getenv("PORT", 10000))

    class HealthHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            bs = _bs()
            bot = getattr(bs, "bot", None)
            log_buf = getattr(bs, "GLOBAL_LOG_BUFFER", [])
            recordings_dir = getattr(bs, "RECORDINGS_DIR", "recordings")
            metadata_file = getattr(bs, "METADATA_FILE", os.path.join(recordings_dir, "recordings_metadata.json"))
            voice_lock = getattr(bs, "VOICE_TURNS_LOCK", None)
            voice_log = getattr(bs, "VOICE_TURNS_LOG", [])
            spain_now_fn = getattr(bs, "get_spain_now_str", lambda: "")

            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/logs":
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.end_headers()
                content = "\n".join(log_buf) if log_buf else "Sin logs registrados aún."
                self.wfile.write(content.encode("utf-8"))
            elif parsed.path == "/status":
                try:
                    voice_data = []
                    for vc in list(getattr(bot, "voice_clients", [])):
                        conn = getattr(vc, "_connection", None)
                        dave = getattr(conn, "dave_session", None)
                        dave_info = {
                            "protocol_version": getattr(conn, "dave_protocol_version", 0),
                            "ready": getattr(dave, "ready", False) if dave else False,
                            "user_ids": dave.get_user_ids() if dave and hasattr(dave, "get_user_ids") else [],
                        }
                        voice_data.append(
                            {
                                "guild": str(vc.guild.name) if vc.guild else None,
                                "channel": str(getattr(vc.channel, "name", "desconocido")),
                                "is_connected": bool(vc.is_connected()),
                                "is_listening": bool(vc.is_listening()) if hasattr(vc, "is_listening") else False,
                                "is_playing": bool(vc.is_playing()) if hasattr(vc, "is_playing") else False,
                                "dave": dave_info,
                                "members": [m.display_name for m in getattr(vc.channel, "members", []) if not m.bot],
                            }
                        )
                    economy_bot = getattr(bs, "economy_bot", None)
                    payload = {
                        "bot_ready": bot.is_ready() if bot else False,
                        "bot_user": str(bot.user) if (bot and bot.user) else None,
                        "economy_bot_ready": economy_bot.is_ready() if economy_bot else False,
                        "economy_bot_user": str(economy_bot.user) if (economy_bot and economy_bot.user) else None,
                        "voice_clients": voice_data,
                        "server_time": spain_now_fn(),
                    }
                    data_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-type", "application/json; charset=utf-8")
                    self.send_header("Content-length", str(len(data_bytes)))
                    self.end_headers()
                    self.wfile.write(data_bytes)
                except Exception as ex:
                    err_bytes = json.dumps({"error": str(ex)}).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-type", "application/json; charset=utf-8")
                    self.send_header("Content-length", str(len(err_bytes)))
                    self.end_headers()
                    self.wfile.write(err_bytes)
            elif parsed.path in ["/audios/zip", "/grabaciones/zip"]:
                try:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                        if os.path.exists(metadata_file):
                            zf.write(metadata_file, arcname="recordings_metadata.json")
                        if os.path.exists(recordings_dir):
                            for fname in os.listdir(recordings_dir):
                                if fname.endswith(".wav"):
                                    fpath = os.path.join(recordings_dir, fname)
                                    if os.path.isfile(fpath):
                                        zf.write(fpath, arcname=fname)
                    zip_data = zip_buffer.getvalue()
                    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    zip_filename = f"grabaciones_{now_str}.zip"
                    self.send_response(200)
                    self.send_header("Content-type", "application/zip")
                    self.send_header("Content-Disposition", f'attachment; filename="{zip_filename}"')
                    self.send_header("Content-length", str(len(zip_data)))
                    self.end_headers()
                    self.wfile.write(zip_data)
                except Exception as ex_zip:
                    err_b = f"Error generando ZIP: {ex_zip}".encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(err_b)
            elif parsed.path in ["/audios", "/grabaciones"]:
                try:
                    if voice_lock:
                        with voice_lock:
                            turns = list(reversed(voice_log))
                    else:
                        turns = list(reversed(voice_log))

                    cards_html = []
                    for t in turns:
                        status_cls = t.get("status", "procesando")
                        u_name = html.escape(str(t.get("user", "Usuario")))
                        t_time = html.escape(str(t.get("timestamp", "")))
                        dur = t.get("duration_s", 0.0)
                        fname = html.escape(str(t.get("filename", "")))
                        trans = html.escape(str(t.get("transcription", "")))
                        reply = html.escape(str(t.get("bot_reply", "")))
                        file_url = f"/audios/file/{fname}"

                        card = f"""
                        <div class="card {status_cls}">
                          <div class="card-header">
                            <span class="user-badge">{u_name}</span>
                            <span class="time-tag">⏱️ {dur}s &nbsp;|&nbsp; 🕒 {t_time}</span>
                          </div>
                          <div class="speech-bubble user">
                            <div class="bubble-label">👤 Usuario ({u_name}):</div>
                            <div>"{trans or '(audio procesado)'}"</div>
                          </div>
                        """
                        if reply and reply not in ["[IGNORAR]", "IGNORAR"]:
                            card += f"""
                          <div class="speech-bubble bot">
                            <div class="bubble-label">🤖 Asistente:</div>
                            <div>"{reply}"</div>
                          </div>
                        """
                        card += f"""
                          <div class="player-container">
                            <audio controls preload="none" src="{file_url}"></audio>
                            <a href="{file_url}" download="{fname}" class="btn btn-secondary">📥 Descargar WAV</a>
                          </div>
                        </div>
                        """
                        cards_html.append(card)

                    body_content = (
                        "\n".join(cards_html)
                        if cards_html
                        else '<div class="empty-state"><h3>Aún no hay grabaciones en esta sesión</h3><p>Cuando alguien hable en la llamada de Discord, sus intervenciones aparecerán aquí con su reproductor de audio y transcripción.</p></div>'
                    )

                    html_page = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Grabaciones en Vivo - Asistente Discord</title>
<style>
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #1e1f22; color: #dbdee1; margin: 0; padding: 20px; }}
.container {{ max-width: 920px; margin: 0 auto; }}
header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #3f4147; padding-bottom: 16px; margin-bottom: 20px; flex-wrap: wrap; gap: 10px; }}
.title-group h1 {{ margin: 0; font-size: 22px; color: #fff; }}
.title-group p {{ margin: 4px 0 0 0; color: #949ba4; font-size: 13px; }}
.actions {{ display: flex; gap: 8px; align-items: center; }}
.btn {{ background: #5865f2; color: #fff; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }}
.btn:hover {{ background: #4752c4; }}
.btn-secondary {{ background: #35373c; color: #dbdee1; font-size: 12px; padding: 6px 12px; }}
.btn-secondary:hover {{ background: #3b3e45; color: #fff; }}
.card {{ background: #2b2d31; border-radius: 8px; padding: 16px; margin-bottom: 14px; border-left: 4px solid #5865f2; box-shadow: 0 2px 6px rgba(0,0,0,0.25); }}
.card.respondido {{ border-left-color: #57f287; }}
.card.ignorado {{ border-left-color: #80848e; opacity: 0.85; }}
.card.silenciado {{ border-left-color: #f23f43; }}
.card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 13px; }}
.user-badge {{ font-weight: 700; color: #fff; background: #5865f2; padding: 3px 10px; border-radius: 12px; font-size: 13px; }}
.time-tag {{ color: #949ba4; font-size: 12px; }}
.speech-bubble {{ background: #313338; border-radius: 6px; padding: 10px 14px; margin: 8px 0; font-size: 14px; }}
.speech-bubble.user {{ border-left: 3px solid #5865f2; color: #f2f3f5; }}
.speech-bubble.bot {{ border-left: 3px solid #57f287; background: #232428; color: #57f287; }}
.bubble-label {{ font-size: 11px; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 4px; color: #949ba4; }}
.player-container {{ display: flex; align-items: center; gap: 10px; margin-top: 10px; background: #1e1f22; padding: 8px 12px; border-radius: 6px; flex-wrap: wrap; }}
audio {{ flex: 1; height: 36px; min-width: 220px; }}
.empty-state {{ text-align: center; padding: 60px 20px; background: #2b2d31; border-radius: 8px; color: #949ba4; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="title-group">
      <h1>🎙️ Grabaciones de Voz - Asistente Discord</h1>
      <p>Escucha las intervenciones de los usuarios y las respuestas del Asistente en tiempo real. <span style="background: rgba(87, 242, 135, 0.15); color: #57f287; border: 1px solid rgba(87, 242, 135, 0.3); border-radius: 4px; padding: 2px 6px; font-weight: 600; font-size: 11px; margin-left: 6px;">🕒 Retención: Permanente (Protegida por Cuota)</span></p>
    </div>
    <div class="actions">
      <a href="/audios/zip" class="btn" style="background:#23a55a;">📦 Descargar Todo (ZIP)</a>
      <a href="/audios" class="btn">🔄 Refrescar</a>
      <a href="/status" class="btn btn-secondary">📊 Estado</a>
      <a href="/logs" class="btn btn-secondary">📜 Logs</a>
    </div>
  </header>
  <div class="content">
    {body_content}
  </div>
</div>
</body>
</html>"""
                    out_bytes = html_page.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.send_header("Content-length", str(len(out_bytes)))
                    self.end_headers()
                    self.wfile.write(out_bytes)
                except Exception as e_page:
                    err_b = f"Error generando página: {e_page}".encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(err_b)
            elif parsed.path.startswith("/audios/file/"):
                fname = os.path.basename(parsed.path)
                fpath = os.path.join(recordings_dir, fname)
                if os.path.exists(fpath):
                    try:
                        with open(fpath, "rb") as f_a:
                            audio_b = f_a.read()
                        self.send_response(200)
                        self.send_header("Content-type", "audio/wav")
                        self.send_header("Content-length", str(len(audio_b)))
                        self.send_header("Content-Disposition", f'inline; filename="{fname}"')
                        self.end_headers()
                        self.wfile.write(audio_b)
                    except Exception:
                        self.send_response(500)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()
            elif parsed.path == "/bolsa":
                try:
                    b_html = render_bolsa_html().encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.send_header("Content-length", str(len(b_html)))
                    self.end_headers()
                    self.wfile.write(b_html)
                except Exception as ex_html:
                    err_b = f"Error cargando Bolsa Web Terminal: {ex_html}".encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(err_b)
            elif parsed.path == "/api/bolsa/data":
                try:
                    payload = get_bolsa_api_payload()
                    d_b = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-type", "application/json; charset=utf-8")
                    self.send_header("Content-length", str(len(d_b)))
                    self.end_headers()
                    self.wfile.write(d_b)
                except Exception as ex_api:
                    err_b = json.dumps({"error": str(ex_api)}).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-type", "application/json; charset=utf-8")
                    self.send_header("Content-length", str(len(err_b)))
                    self.end_headers()
                    self.wfile.write(err_b)
            elif parsed.path == "/api/audios":
                if voice_lock:
                    with voice_lock:
                        turns = list(reversed(voice_log))
                else:
                    turns = list(reversed(voice_log))
                d_b = json.dumps(turns, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.send_header("Content-length", str(len(d_b)))
                self.end_headers()
                self.wfile.write(d_b)
            else:
                is_rdy = bot.is_ready() if bot else False
                status = (
                    "OK - Asistente Bot Activo (Discord: Conectado)"
                    if is_rdy
                    else "OK - Asistente Bot Activo (Discord: Conectando...)"
                )
                status_bytes = status.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.send_header("Connection", "close")
                self.send_header("Content-length", str(len(status_bytes)))
                self.end_headers()
                self.wfile.write(status_bytes)

        def do_HEAD(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.send_header("Connection", "close")
            self.end_headers()

        def log_message(self, format, *args):
            pass

    log_fn = getattr(_bs(), "bot_log", print)
    try:
        with ReusableTCPServer(("", port), HealthHandler) as httpd:
            log_fn(f"Servidor de salud y logs HTTP activo en puerto {port} para Render")
            httpd.serve_forever()
    except Exception as e:
        log_fn(f"Aviso servidor salud: {e}")

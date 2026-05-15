"""
StockVision Pro - Global Stock Market Intelligence Platform
Main Flask Application Entry Point — with caching for fast loads
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
import os
import time
import threading
from api.market_data import MarketDataAPI
from api.analysis import StockAnalysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

market_api = MarketDataAPI()
analyzer   = StockAnalysis()


# ─── Simple In-Memory Cache ───────────────────────────────────────────────────

class Cache:
    def __init__(self):
        self._store = {}
        self._lock  = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._store.get(key)
            if item and time.time() < item["expires"]:
                return item["data"]
            return None

    def set(self, key, data, ttl=300):  # default TTL = 5 minutes
        with self._lock:
            self._store[key] = {
                "data":    data,
                "expires": time.time() + ttl,
            }

    def clear(self):
        with self._lock:
            self._store.clear()


cache = Cache()


# ─── Background Prefetch ──────────────────────────────────────────────────────

def prefetch_data():
    """
    Runs in a background thread immediately on startup.
    Warms the cache so the very first visitor doesn't wait.
    """
    logger.info("Background prefetch started...")

    try:
        data = market_api.get_global_indices()
        cache.set("markets_overview", data, ttl=300)
        # Also build the by-country view from the same data
        by_country = market_api.get_markets_by_country()
        cache.set("markets_by_country", by_country, ttl=300)
        logger.info(f"Prefetch: {len(data)} indices cached")
    except Exception as e:
        logger.error(f"Prefetch (indices) error: {e}")

    try:
        data = market_api.get_sector_performance()
        cache.set("sector_heatmap", data, ttl=300)
        logger.info("Prefetch: sectors cached")
    except Exception as e:
        logger.error(f"Prefetch (sectors) error: {e}")

    try:
        data = market_api.get_top_performers()
        cache.set("top_performers", data, ttl=300)
        logger.info("Prefetch: top performers cached")
    except Exception as e:
        logger.error(f"Prefetch (performers) error: {e}")

    logger.info("Background prefetch complete.")


# Fire prefetch as soon as the app boots
threading.Thread(target=prefetch_data, daemon=True).start()


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/markets/overview")
def markets_overview():
    """Global market indices — cached 5 min"""
    cached = cache.get("markets_overview")
    if cached:
        logger.info("Cache hit: markets_overview")
        return jsonify({"status": "success", "data": cached})
    try:
        data = market_api.get_global_indices()
        cache.set("markets_overview", data, ttl=300)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Markets overview error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/markets/by-country")
def markets_by_country():
    """Markets grouped by country — cached 5 min"""
    cached = cache.get("markets_by_country")
    if cached:
        logger.info("Cache hit: markets_by_country")
        return jsonify({"status": "success", "data": cached})
    try:
        data = market_api.get_markets_by_country()
        cache.set("markets_by_country", data, ttl=300)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Markets by country error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/stock/<ticker>")
def stock_detail(ticker):
    """Detailed stock info — cached 10 min per ticker+period"""
    ticker = ticker.upper()
    period = request.args.get("period", "1y")
    key    = f"stock_detail_{ticker}_{period}"

    cached = cache.get(key)
    if cached:
        logger.info(f"Cache hit: {key}")
        return jsonify({"status": "success", "data": cached})
    try:
        data = market_api.get_stock_detail(ticker, period)
        cache.set(key, data, ttl=600)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Stock detail error for {ticker}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/stock/<ticker>/analysis")
def stock_analysis(ticker):
    """Stock analysis — cached 10 min per ticker"""
    ticker = ticker.upper()
    key    = f"stock_analysis_{ticker}"

    cached = cache.get(key)
    if cached:
        logger.info(f"Cache hit: {key}")
        return jsonify({"status": "success", "data": cached})
    try:
        data = analyzer.analyze_stock(ticker)
        cache.set(key, data, ttl=600)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Stock analysis error for {ticker}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/markets/top-performers")
def top_performers():
    """Top gainers and losers — cached 5 min"""
    cached = cache.get("top_performers")
    if cached:
        logger.info("Cache hit: top_performers")
        return jsonify({"status": "success", "data": cached})
    try:
        data = market_api.get_top_performers()
        cache.set("top_performers", data, ttl=300)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Top performers error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/markets/sector-heatmap")
def sector_heatmap():
    """Sector heatmap — cached 5 min"""
    cached = cache.get("sector_heatmap")
    if cached:
        logger.info("Cache hit: sector_heatmap")
        return jsonify({"status": "success", "data": cached})
    try:
        data = market_api.get_sector_performance()
        cache.set("sector_heatmap", data, ttl=300)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Sector heatmap error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/search")
def search_stocks():
    """Search stocks by ticker — cached 2 min"""
    query = request.args.get("q", "").strip()
    if len(query) < 1:
        return jsonify({"status": "success", "data": []})

    key    = f"search_{query.upper()}"
    cached = cache.get(key)
    if cached:
        return jsonify({"status": "success", "data": cached})
    try:
        data = market_api.search_stocks(query)
        cache.set(key, data, ttl=120)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Search error for '{query}': {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/watchlist/validate", methods=["POST"])
def validate_tickers():
    """Validate a list of ticker symbols"""
    tickers = request.json.get("tickers", [])
    results = {}
    for t in tickers[:20]:
        try:
            info       = yf.Ticker(t).info
            results[t] = bool(
                info.get("regularMarketPrice") or info.get("currentPrice")
            )
        except Exception:
            results[t] = False
    return jsonify({"status": "success", "data": results})


@app.route("/api/cache/clear")
def clear_cache():
    """Force-clear all cached data and re-prefetch"""
    cache.clear()
    threading.Thread(target=prefetch_data, daemon=True).start()
    return jsonify({"status": "success", "message": "Cache cleared and prefetch restarted"})


@app.route("/health")
def health():
    """Health check — used by Render and UptimeRobot"""
    return jsonify({
        "status":      "ok",
        "cached_keys": len(cache._store),
        "timestamp":   datetime.utcnow().isoformat(),
    })


# ─── Main Entry ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
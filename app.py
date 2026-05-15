"""
StockVision Pro - Global Stock Market Intelligence Platform
Main Flask Application Entry Point
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
from api.market_data import MarketDataAPI
from api.analysis import StockAnalysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

market_api = MarketDataAPI()
analyzer = StockAnalysis()


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/markets/overview")
def markets_overview():
    """Global market indices overview"""
    try:
        data = market_api.get_global_indices()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Markets overview error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/markets/by-country")
def markets_by_country():
    """All markets organized by country/region"""
    try:
        data = market_api.get_markets_by_country()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Markets by country error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/stock/<ticker>")
def stock_detail(ticker):
    """Detailed stock information"""
    try:
        period = request.args.get("period", "1y")
        data = market_api.get_stock_detail(ticker.upper(), period)
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Stock detail error for {ticker}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/stock/<ticker>/analysis")
def stock_analysis(ticker):
    """AI-powered stock analysis"""
    try:
        data = analyzer.analyze_stock(ticker.upper())
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Stock analysis error for {ticker}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/markets/top-performers")
def top_performers():
    """Top gaining and losing stocks globally"""
    try:
        data = market_api.get_top_performers()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Top performers error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/markets/sector-heatmap")
def sector_heatmap():
    """Sector performance heatmap data"""
    try:
        data = market_api.get_sector_performance()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        logger.error(f"Sector heatmap error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/search")
def search_stocks():
    """Search stocks by name or ticker"""
    query = request.args.get("q", "").strip()
    if len(query) < 1:
        return jsonify({"status": "success", "data": []})
    try:
        data = market_api.search_stocks(query)
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
            info = yf.Ticker(t).info
            results[t] = bool(
                info.get("regularMarketPrice") or
                info.get("currentPrice")
            )
        except Exception:
            results[t] = False
    return jsonify({"status": "success", "data": results})


# ─── Main Entry ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
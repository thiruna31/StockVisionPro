"""
Stock Analysis Engine
Technical + Fundamental scoring, buy/sell signals, and investment recommendations
"""

import yfinance as yf
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class StockAnalysis:

    def analyze_stock(self, ticker: str) -> dict:
        """
        Full analysis pipeline:
        - Technical signals (RSI, MACD, MA crossovers, Bollinger Bands)
        - Fundamental scoring (PE, PB, profit margin, ROE)
        - Overall investment score (0–100)
        - Verdict: Strong Buy / Buy / Hold / Sell / Strong Sell
        """
        stock = yf.Ticker(ticker)
        info  = stock.info or {}
        hist  = stock.history(period="1y", auto_adjust=True)

        if hist.empty:
            raise ValueError(f"No historical data for {ticker}")

        closes  = hist["Close"]
        volumes = hist["Volume"] if "Volume" in hist.columns else pd.Series([0]*len(hist))

        # ── Technical Indicators ─────────────────────────────────────────────
        sma20  = closes.rolling(20).mean()
        sma50  = closes.rolling(50).mean()
        sma200 = closes.rolling(200).mean()

        delta  = closes.diff()
        gain   = delta.clip(lower=0).rolling(14).mean()
        loss   = (-delta.clip(upper=0)).rolling(14).mean()
        rs     = gain / loss.replace(0, np.nan)
        rsi    = 100 - (100 / (1 + rs))

        ema12  = closes.ewm(span=12, adjust=False).mean()
        ema26  = closes.ewm(span=26, adjust=False).mean()
        macd   = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()

        bb_mid   = closes.rolling(20).mean()
        bb_std   = closes.rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std

        curr_price  = float(closes.iloc[-1])
        curr_rsi    = float(rsi.iloc[-1])   if not rsi.empty else 50.0
        curr_macd   = float(macd.iloc[-1])  if not macd.empty else 0.0
        curr_signal = float(signal.iloc[-1]) if not signal.empty else 0.0
        curr_sma20  = float(sma20.iloc[-1]) if not sma20.empty else curr_price
        curr_sma50  = float(sma50.iloc[-1]) if not sma50.empty else curr_price
        curr_sma200 = float(sma200.iloc[-1]) if not sma200.empty else curr_price
        curr_bb_u   = float(bb_upper.iloc[-1]) if not bb_upper.empty else curr_price * 1.05
        curr_bb_l   = float(bb_lower.iloc[-1]) if not bb_lower.empty else curr_price * 0.95

        # ── Technical Signals ────────────────────────────────────────────────
        tech_signals = []
        tech_score   = 0

        # RSI
        if curr_rsi < 30:
            tech_signals.append({"indicator": "RSI", "value": round(curr_rsi, 1),
                                  "signal": "Strong Buy", "weight": 3,
                                  "note": "Oversold territory — potential reversal"})
            tech_score += 3
        elif curr_rsi < 45:
            tech_signals.append({"indicator": "RSI", "value": round(curr_rsi, 1),
                                  "signal": "Buy", "weight": 2,
                                  "note": "Below midline — building momentum"})
            tech_score += 2
        elif curr_rsi < 55:
            tech_signals.append({"indicator": "RSI", "value": round(curr_rsi, 1),
                                  "signal": "Neutral", "weight": 0,
                                  "note": "Neutral zone"})
        elif curr_rsi < 70:
            tech_signals.append({"indicator": "RSI", "value": round(curr_rsi, 1),
                                  "signal": "Sell", "weight": -2,
                                  "note": "Above midline — momentum fading"})
            tech_score -= 2
        else:
            tech_signals.append({"indicator": "RSI", "value": round(curr_rsi, 1),
                                  "signal": "Strong Sell", "weight": -3,
                                  "note": "Overbought — correction risk"})
            tech_score -= 3

        # MACD
        if curr_macd > curr_signal:
            tech_signals.append({"indicator": "MACD", "value": round(curr_macd, 4),
                                  "signal": "Buy", "weight": 2,
                                  "note": "MACD above signal line — bullish crossover"})
            tech_score += 2
        else:
            tech_signals.append({"indicator": "MACD", "value": round(curr_macd, 4),
                                  "signal": "Sell", "weight": -2,
                                  "note": "MACD below signal line — bearish crossover"})
            tech_score -= 2

        # Moving Averages
        if curr_price > curr_sma20 > curr_sma50 > curr_sma200:
            tech_signals.append({"indicator": "Moving Averages", "value": round(curr_sma50, 2),
                                  "signal": "Strong Buy", "weight": 3,
                                  "note": "Price above all MAs — strong uptrend"})
            tech_score += 3
        elif curr_price > curr_sma50:
            tech_signals.append({"indicator": "Moving Averages", "value": round(curr_sma50, 2),
                                  "signal": "Buy", "weight": 2,
                                  "note": "Above 50-day MA — positive momentum"})
            tech_score += 2
        elif curr_price < curr_sma200:
            tech_signals.append({"indicator": "Moving Averages", "value": round(curr_sma200, 2),
                                  "signal": "Strong Sell", "weight": -3,
                                  "note": "Below 200-day MA — long-term downtrend"})
            tech_score -= 3
        else:
            tech_signals.append({"indicator": "Moving Averages", "value": round(curr_sma50, 2),
                                  "signal": "Sell", "weight": -1,
                                  "note": "Below 50-day MA — weakening trend"})
            tech_score -= 1

        # Bollinger Bands
        bb_pct = (curr_price - curr_bb_l) / (curr_bb_u - curr_bb_l) if (curr_bb_u - curr_bb_l) != 0 else 0.5
        if bb_pct < 0.2:
            tech_signals.append({"indicator": "Bollinger Bands", "value": round(bb_pct, 2),
                                  "signal": "Buy", "weight": 2,
                                  "note": "Price near lower band — potential bounce"})
            tech_score += 2
        elif bb_pct > 0.8:
            tech_signals.append({"indicator": "Bollinger Bands", "value": round(bb_pct, 2),
                                  "signal": "Sell", "weight": -2,
                                  "note": "Price near upper band — potential pullback"})
            tech_score -= 2
        else:
            tech_signals.append({"indicator": "Bollinger Bands", "value": round(bb_pct, 2),
                                  "signal": "Neutral", "weight": 0,
                                  "note": "Price within normal range"})

        # Volume trend
        avg_vol   = float(volumes.rolling(20).mean().iloc[-1])
        curr_vol  = float(volumes.iloc[-1])
        vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
        if vol_ratio > 1.5:
            tech_signals.append({"indicator": "Volume", "value": round(vol_ratio, 2),
                                  "signal": "Strong", "weight": 1,
                                  "note": f"Volume {round(vol_ratio,1)}x above average — high conviction"})
            tech_score += 1

        # ── Fundamental Scoring ───────────────────────────────────────────────
        fund_signals = []
        fund_score   = 0

        pe = info.get("trailingPE")
        if pe:
            if pe < 15:
                fund_signals.append({"metric": "P/E Ratio", "value": round(pe, 1),
                                      "signal": "Undervalued", "note": "Low PE — potential value play"})
                fund_score += 3
            elif pe < 25:
                fund_signals.append({"metric": "P/E Ratio", "value": round(pe, 1),
                                      "signal": "Fair Value", "note": "Reasonable valuation"})
                fund_score += 1
            elif pe < 40:
                fund_signals.append({"metric": "P/E Ratio", "value": round(pe, 1),
                                      "signal": "Elevated", "note": "Above average — growth priced in"})
                fund_score -= 1
            else:
                fund_signals.append({"metric": "P/E Ratio", "value": round(pe, 1),
                                      "signal": "Overvalued", "note": "Very high PE — significant premium"})
                fund_score -= 2

        margin = info.get("profitMargins")
        if margin:
            pct = margin * 100
            if pct > 20:
                fund_signals.append({"metric": "Profit Margin", "value": round(pct, 1),
                                      "signal": "Excellent", "note": "Strong profitability"})
                fund_score += 3
            elif pct > 10:
                fund_signals.append({"metric": "Profit Margin", "value": round(pct, 1),
                                      "signal": "Good", "note": "Healthy margins"})
                fund_score += 2
            elif pct > 0:
                fund_signals.append({"metric": "Profit Margin", "value": round(pct, 1),
                                      "signal": "Thin", "note": "Low margins — watch costs"})
                fund_score += 1
            else:
                fund_signals.append({"metric": "Profit Margin", "value": round(pct, 1),
                                      "signal": "Unprofitable", "note": "Negative margins"})
                fund_score -= 2

        roe = info.get("returnOnEquity")
        if roe:
            pct = roe * 100
            if pct > 20:
                fund_signals.append({"metric": "ROE", "value": round(pct, 1),
                                      "signal": "Excellent", "note": "Very efficient capital use"})
                fund_score += 3
            elif pct > 10:
                fund_signals.append({"metric": "ROE", "value": round(pct, 1),
                                      "signal": "Good", "note": "Decent returns on equity"})
                fund_score += 1
            else:
                fund_signals.append({"metric": "ROE", "value": round(pct, 1),
                                      "signal": "Weak", "note": "Below-average equity returns"})
                fund_score -= 1

        beta = info.get("beta")
        if beta:
            if beta < 0.8:
                fund_signals.append({"metric": "Beta (Risk)", "value": round(beta, 2),
                                      "signal": "Low Risk", "note": "Less volatile than market"})
            elif beta < 1.3:
                fund_signals.append({"metric": "Beta (Risk)", "value": round(beta, 2),
                                      "signal": "Moderate", "note": "Moves with the market"})
            else:
                fund_signals.append({"metric": "Beta (Risk)", "value": round(beta, 2),
                                      "signal": "High Risk", "note": "More volatile than market"})
                fund_score -= 1

        # ── Overall Score ─────────────────────────────────────────────────────
        raw_score    = tech_score + fund_score
        clamped      = max(-12, min(12, raw_score))
        overall_score = int(((clamped + 12) / 24) * 100)

        if overall_score >= 75:
            verdict = "Strong Buy"
        elif overall_score >= 60:
            verdict = "Buy"
        elif overall_score >= 40:
            verdict = "Hold"
        elif overall_score >= 25:
            verdict = "Sell"
        else:
            verdict = "Strong Sell"

        # 52-week position
        high52 = float(closes.max())
        low52  = float(closes.min())
        pos52  = ((curr_price - low52) / (high52 - low52)) * 100 if (high52 - low52) > 0 else 50

        return {
            "ticker":          ticker,
            "overall_score":   overall_score,
            "verdict":         verdict,
            "tech_score":      tech_score,
            "fund_score":      fund_score,
            "tech_signals":    tech_signals,
            "fund_signals":    fund_signals,
            "price_targets": {
                "current":     round(curr_price, 2),
                "support":     round(curr_bb_l, 2),
                "resistance":  round(curr_bb_u, 2),
                "sma50_target":round(curr_sma50, 2),
                "position_52w":round(pos52, 1),
            },
            "risk_level": self._risk_level(beta, info.get("trailingPE"), margin),
        }

    def _risk_level(self, beta, pe, margin):
        score = 0
        if beta:
            score += min(3, int(beta * 2))
        if pe and pe > 40:
            score += 2
        if margin is not None and margin < 0:
            score += 3
        if score <= 2:
            return "Low"
        elif score <= 5:
            return "Medium"
        else:
            return "High"

"""
Market Data API Module
Fetches real-time and historical data from Yahoo Finance
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# ─── Global Market Indices by Country/Region ─────────────────────────────────

GLOBAL_INDICES = {
    "United States": [
        {"symbol": "^GSPC",  "name": "S&P 500",         "exchange": "NYSE"},
        {"symbol": "^DJI",   "name": "Dow Jones",        "exchange": "NYSE"},
        {"symbol": "^IXIC",  "name": "NASDAQ Composite", "exchange": "NASDAQ"},
        {"symbol": "^RUT",   "name": "Russell 2000",     "exchange": "NYSE"},
    ],
    "United Kingdom": [
        {"symbol": "^FTSE",  "name": "FTSE 100",         "exchange": "LSE"},
        {"symbol": "^FTMC",  "name": "FTSE 250",         "exchange": "LSE"},
    ],
    "Germany": [
        {"symbol": "^GDAXI", "name": "DAX 40",           "exchange": "Frankfurt"},
        {"symbol": "^MDAXI", "name": "MDAX",             "exchange": "Frankfurt"},
    ],
    "Japan": [
        {"symbol": "^N225",  "name": "Nikkei 225",       "exchange": "TSE"},
        {"symbol": "^N300",  "name": "Nikkei 300",       "exchange": "TSE"},
    ],
    "China": [
        {"symbol": "000001.SS", "name": "Shanghai Composite", "exchange": "SSE"},
        {"symbol": "399001.SZ", "name": "Shenzhen Component", "exchange": "SZSE"},
        {"symbol": "^HSI",      "name": "Hang Seng",          "exchange": "HKEX"},
    ],
    "India": [
        {"symbol": "^BSESN", "name": "BSE Sensex",       "exchange": "BSE"},
        {"symbol": "^NSEI",  "name": "NSE Nifty 50",     "exchange": "NSE"},
    ],
    "France": [
        {"symbol": "^FCHI",  "name": "CAC 40",           "exchange": "Euronext"},
    ],
    "Canada": [
        {"symbol": "^GSPTSE", "name": "TSX Composite",   "exchange": "TSX"},
    ],
    "Australia": [
        {"symbol": "^AXJO",  "name": "ASX 200",          "exchange": "ASX"},
        {"symbol": "^AORD",  "name": "All Ordinaries",   "exchange": "ASX"},
    ],
    "Brazil": [
        {"symbol": "^BVSP",  "name": "Bovespa",          "exchange": "B3"},
    ],
    "South Korea": [
        {"symbol": "^KS11",  "name": "KOSPI",            "exchange": "KRX"},
        {"symbol": "^KQ11",  "name": "KOSDAQ",           "exchange": "KRX"},
    ],
    "Singapore": [
        {"symbol": "^STI",   "name": "Straits Times",    "exchange": "SGX"},
    ],
    "Switzerland": [
        {"symbol": "^SSMI",  "name": "SMI",              "exchange": "SIX"},
    ],
    "Italy": [
        {"symbol": "FTSEMIB.MI", "name": "FTSE MIB",    "exchange": "Borsa Italiana"},
    ],
    "Spain": [
        {"symbol": "^IBEX",  "name": "IBEX 35",          "exchange": "BME"},
    ],
    "Netherlands": [
        {"symbol": "^AEX",   "name": "AEX",              "exchange": "Euronext Amsterdam"},
    ],
    "Saudi Arabia": [
        {"symbol": "^TASI.SR", "name": "Tadawul (TASI)", "exchange": "Tadawul"},
    ],
    # Russia removed — MOEX (IMOEX.ME) blocked on Yahoo Finance since 2022 sanctions
    "Mexico": [
        {"symbol": "^MXX",   "name": "IPC Mexico",       "exchange": "BMV"},
    ],
    "South Africa": [
        {"symbol": "^J203.JO", "name": "JSE All Share",  "exchange": "JSE"},
    ],
}


# ─── Curated stock lists per region for top performers ────────────────────────

REGION_STOCKS = {
    "US": [
        "AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","BRK-B","JPM","JNJ",
        "V","PG","UNH","HD","MA","MRK","ABBV","PFE","KO","PEP","AVGO","COST",
        "WMT","DIS","BAC","XOM","CVX","LLY","TMO","MCD",
    ],
    "UK":   ["SHEL.L","AZN.L","HSBA.L","ULVR.L","BP.L","GSK.L","RIO.L","AAL.L"],
    # LVMH.PA fixed → MC.PA (correct Yahoo Finance ticker for LVMH)
    "EU":   ["ASML.AS","SAP.DE","MC.PA","TTE.PA","SIE.DE","ALV.DE","AIR.PA"],
    "ASIA": ["9988.HK","0700.HK","005930.KS","2330.TW","TCS.NS","INFY.NS","RELIANCE.NS"],
    # PETRO.SA removed (not on Yahoo); replaced with ITUB4.SA (Itaú Unibanco)
    "OTHER": ["SHOP.TO","WES.AX","CBA.AX","VALE3.SA","ITUB4.SA"],
}


# ─── Sector definitions ───────────────────────────────────────────────────────

SECTORS = {
    "Technology":    ["AAPL","MSFT","NVDA","GOOGL","META","AVGO","CRM","ORCL","AMD","INTC"],
    "Healthcare":    ["UNH","JNJ","LLY","ABBV","MRK","TMO","ABT","DHR","BMY","AMGN"],
    "Financials":    ["BRK-B","JPM","BAC","WFC","GS","MS","C","BLK","AXP","USB"],
    "Consumer":      ["AMZN","TSLA","HD","MCD","NKE","SBUX","TGT","LOW","TJX","BKNG"],
    "Energy":        ["XOM","CVX","COP","EOG","PXD","MPC","VLO","PSX","OXY","SLB"],
    "Industrials":   ["HON","UPS","CAT","DE","BA","LMT","RTX","GE","MMM","FDX"],
    "Communication": ["META","GOOGL","DIS","NFLX","CMCSA","T","VZ","CHTR","TMUS","ATVI"],
    "Real Estate":   ["AMT","PLD","CCI","EQIX","PSA","WELL","O","SPG","DLR","AVB"],
    "Utilities":     ["NEE","DUK","SO","AEP","EXC","XEL","PCG","SRE","D","ED"],
    "Materials":     ["LIN","APD","ECL","SHW","FCX","NEM","CTVA","DOW","DD","PPG"],
    "Staples":       ["PG","KO","PEP","WMT","COST","MDLZ","CL","KHC","GIS","HSY"],
}


class MarketDataAPI:

    def get_global_indices(self):
        """Fetch all global indices with current data"""
        results    = []
        all_symbols = []
        symbol_meta = {}

        for country, indices in GLOBAL_INDICES.items():
            for idx in indices:
                all_symbols.append(idx["symbol"])
                symbol_meta[idx["symbol"]] = {**idx, "country": country}

        # Batch download — 5d period to get prev close for % change
        try:
            raw = yf.download(
                all_symbols, period="5d", interval="1d",
                group_by="ticker", auto_adjust=True, progress=False
            )
        except Exception as e:
            logger.error(f"Batch download failed: {e}")
            raw = None

        for sym in all_symbols:
            meta = symbol_meta[sym]
            try:
                if raw is not None and len(all_symbols) > 1:
                    df = raw[sym].dropna()
                else:
                    df = yf.Ticker(sym).history(period="5d")

                if df is None or len(df) < 2:
                    continue

                prev_close = float(df["Close"].iloc[-2])
                curr_close = float(df["Close"].iloc[-1])
                chg        = curr_close - prev_close
                chg_pct    = (chg / prev_close) * 100

                results.append({
                    "symbol":     sym,
                    "name":       meta["name"],
                    "country":    meta["country"],
                    "exchange":   meta["exchange"],
                    "price":      round(curr_close, 2),
                    "change":     round(chg, 2),
                    "change_pct": round(chg_pct, 2),
                    "prev_close": round(prev_close, 2),
                    "volume":     int(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0,
                    "trend":      "up" if chg >= 0 else "down",
                    "sparkline":  [round(float(x), 2) for x in df["Close"].tail(5).tolist()],
                })
            except Exception as e:
                logger.warning(f"Skipping {sym}: {e}")
                continue

        return results

    def get_markets_by_country(self):
        """Return indices grouped by country with performance stats"""
        indices    = self.get_global_indices()
        by_country = {}
        for item in indices:
            c = item["country"]
            if c not in by_country:
                by_country[c] = []
            by_country[c].append(item)
        return by_country

    def get_stock_detail(self, ticker: str, period: str = "1y"):
        """Full detail for a single stock"""
        stock = yf.Ticker(ticker)
        info  = stock.info or {}
        hist  = stock.history(period=period, auto_adjust=True)

        if hist.empty:
            raise ValueError(f"No data found for {ticker}")

        closes  = hist["Close"]
        volumes = hist["Volume"] if "Volume" in hist.columns else pd.Series([0] * len(hist))

        # ── Technical indicators ──────────────────────────────────────────────
        sma20  = closes.rolling(20).mean()
        sma50  = closes.rolling(50).mean()
        sma200 = closes.rolling(200).mean()

        # RSI
        delta = closes.diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, np.nan)
        rsi   = 100 - (100 / (1 + rs))

        # MACD
        ema12  = closes.ewm(span=12, adjust=False).mean()
        ema26  = closes.ewm(span=26, adjust=False).mean()
        macd   = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()

        # Bollinger Bands
        bb_mid   = closes.rolling(20).mean()
        bb_std   = closes.rolling(20).std()
        bb_upper = bb_mid + 2 * bb_std
        bb_lower = bb_mid - 2 * bb_std

        total_return = ((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0]) * 100
        dates        = hist.index.strftime("%Y-%m-%d").tolist()

        def safe_list(series):
            return [round(float(x), 4) if not np.isnan(x) else None for x in series]

        return {
            "ticker":   ticker,
            "name":     info.get("longName") or info.get("shortName", ticker),
            "sector":   info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "country":  info.get("country", "N/A"),
            "exchange": info.get("exchange", "N/A"),
            "currency": info.get("currency", "USD"),
            "website":  info.get("website", ""),
            "description": info.get("longBusinessSummary", ""),
            "fundamentals": {
                "market_cap":     info.get("marketCap"),
                "pe_ratio":       info.get("trailingPE"),
                "forward_pe":     info.get("forwardPE"),
                "pb_ratio":       info.get("priceToBook"),
                "ps_ratio":       info.get("priceToSalesTrailing12Months"),
                "eps":            info.get("trailingEps"),
                "dividend_yield": info.get("dividendYield"),
                "beta":           info.get("beta"),
                "52w_high":       info.get("fiftyTwoWeekHigh"),
                "52w_low":        info.get("fiftyTwoWeekLow"),
                "avg_volume":     info.get("averageVolume"),
                "revenue":        info.get("totalRevenue"),
                "profit_margin":  info.get("profitMargins"),
                "roe":            info.get("returnOnEquity"),
                "debt_to_equity": info.get("debtToEquity"),
            },
            "price_data": {
                "dates":       dates,
                "open":        safe_list(hist["Open"]),
                "high":        safe_list(hist["High"]),
                "low":         safe_list(hist["Low"]),
                "close":       safe_list(closes),
                "volume":      [int(x) for x in volumes.tolist()],
                "sma20":       safe_list(sma20),
                "sma50":       safe_list(sma50),
                "sma200":      safe_list(sma200),
                "rsi":         safe_list(rsi),
                "macd":        safe_list(macd),
                "macd_signal": safe_list(signal),
                "bb_upper":    safe_list(bb_upper),
                "bb_lower":    safe_list(bb_lower),
                "bb_mid":      safe_list(bb_mid),
            },
            "stats": {
                "current_price": round(float(closes.iloc[-1]), 2),
                "total_return":  round(float(total_return), 2),
                "volatility":    round(float(closes.pct_change().std() * np.sqrt(252) * 100), 2),
                "sharpe_ratio":  self._sharpe(closes),
                "max_drawdown":  self._max_drawdown(closes),
                "current_rsi":   round(float(rsi.iloc[-1]), 2) if not np.isnan(rsi.iloc[-1]) else None,
            },
        }

    def get_top_performers(self):
        """Fetch top gainers and losers across regions"""
        all_stocks = []
        for region_stocks in REGION_STOCKS.values():
            all_stocks.extend(region_stocks)

        try:
            raw = yf.download(
                all_stocks, period="5d", interval="1d",
                group_by="ticker", auto_adjust=True, progress=False
            )
        except Exception as e:
            logger.error(f"Top performers download error: {e}")
            return {"gainers": [], "losers": []}

        performers = []
        for sym in all_stocks:
            try:
                df = raw[sym].dropna() if len(all_stocks) > 1 else raw.dropna()
                if len(df) < 2:
                    continue
                prev    = float(df["Close"].iloc[-2])
                curr    = float(df["Close"].iloc[-1])
                chg_pct = ((curr - prev) / prev) * 100
                performers.append({
                    "symbol":     sym,
                    "price":      round(curr, 2),
                    "change_pct": round(chg_pct, 2),
                    "change":     round(curr - prev, 2),
                    "volume":     int(df["Volume"].iloc[-1]) if "Volume" in df.columns else 0,
                    "sparkline":  [round(float(x), 2) for x in df["Close"].tail(5).tolist()],
                })
            except Exception:
                continue

        performers.sort(key=lambda x: x["change_pct"], reverse=True)
        return {
            "gainers": performers[:10],
            "losers":  list(reversed(performers[-10:])),
        }

    def get_sector_performance(self):
        """ETF-based sector performance"""
        sector_etfs = {
            "Technology":    "XLK",
            "Healthcare":    "XLV",
            "Financials":    "XLF",
            "Consumer Disc": "XLY",
            "Energy":        "XLE",
            "Industrials":   "XLI",
            "Communication": "XLC",
            "Real Estate":   "XLRE",
            "Utilities":     "XLU",
            "Materials":     "XLB",
            "Staples":       "XLP",
        }
        symbols = list(sector_etfs.values())
        results = []

        try:
            raw = yf.download(
                symbols, period="1mo", interval="1d",
                group_by="ticker", auto_adjust=True, progress=False
            )
        except Exception as e:
            logger.error(f"Sector ETF download error: {e}")
            return results

        for sector, sym in sector_etfs.items():
            try:
                df = raw[sym].dropna() if len(symbols) > 1 else raw.dropna()
                if len(df) < 2:
                    continue
                day_chg   = ((float(df["Close"].iloc[-1]) - float(df["Close"].iloc[-2]))
                             / float(df["Close"].iloc[-2])) * 100
                month_chg = ((float(df["Close"].iloc[-1]) - float(df["Close"].iloc[0]))
                             / float(df["Close"].iloc[0])) * 100
                results.append({
                    "sector":       sector,
                    "etf":          sym,
                    "day_change":   round(day_chg, 2),
                    "month_change": round(month_chg, 2),
                    "price":        round(float(df["Close"].iloc[-1]), 2),
                    "sparkline":    [round(float(x), 2) for x in df["Close"].tail(10).tolist()],
                })
            except Exception:
                continue

        return results

    def search_stocks(self, query: str):
        """Basic search using yfinance"""
        try:
            ticker = yf.Ticker(query.upper())
            info   = ticker.info
            if info and (info.get("regularMarketPrice") or info.get("currentPrice")):
                price = info.get("regularMarketPrice") or info.get("currentPrice", 0)
                return [{
                    "symbol":   query.upper(),
                    "name":     info.get("longName") or info.get("shortName", query.upper()),
                    "price":    round(float(price), 2),
                    "sector":   info.get("sector", ""),
                    "country":  info.get("country", ""),
                    "exchange": info.get("exchange", ""),
                }]
        except Exception:
            pass
        return []

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _sharpe(self, prices: pd.Series, risk_free: float = 0.045) -> float:
        try:
            rets   = prices.pct_change().dropna()
            excess = rets.mean() * 252 - risk_free
            vol    = rets.std() * np.sqrt(252)
            return round(float(excess / vol), 3) if vol != 0 else 0.0
        except Exception:
            return 0.0

    def _max_drawdown(self, prices: pd.Series) -> float:
        try:
            roll_max = prices.cummax()
            drawdown = (prices - roll_max) / roll_max
            return round(float(drawdown.min() * 100), 2)
        except Exception:
            return 0.0
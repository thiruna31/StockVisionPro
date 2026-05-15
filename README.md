# StockVision Pro 📈

**Global Stock Market Intelligence Platform** — Real-time data, technical & fundamental analysis, investment scoring across 20+ countries.

---

## Features

- 🌍 **20+ Country Markets** — Indices from US, UK, Germany, Japan, China, India, Brazil, and more
- 📊 **Live Price Charts** — Interactive candlestick/line charts with SMA 20/50/200 overlays
- 🔥 **Sector Heatmap** — Color-coded sector performance (day + 1-month)
- 🏆 **Top Gainers & Losers** — Real-time across US, UK, EU, Asia, and other regions
- 🔬 **AI-Powered Analysis** — Technical signals (RSI, MACD, Bollinger Bands, Moving Averages) + Fundamental scoring
- 🎯 **Investment Verdict** — Strong Buy / Buy / Hold / Sell / Strong Sell with 0–100 score
- 🔎 **Stock Screener** — Analyze any global ticker (e.g. `AAPL`, `RELIANCE.NS`, `9988.HK`)
- 📡 **Ticker Tape** — Scrolling live market data
- 🌐 **Price Targets** — Support, resistance, 52-week position

---

## Quick Start

### 1. Clone / Download

```bash
git clone https://github.com/yourname/stockvision-pro.git
cd stockvision-pro
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
python app.py
```

Then open **http://localhost:5000** in your browser.

---

## Production Deployment

```bash
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

Or with Docker:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```

---

## Project Structure

```
stockvision/
├── app.py                  # Flask entry point
├── requirements.txt
├── README.md
├── api/
│   ├── __init__.py
│   ├── market_data.py      # Data fetching (yfinance)
│   └── analysis.py         # Technical + fundamental analysis engine
├── templates/
│   └── index.html          # Main SPA template
└── static/
    ├── css/
    │   └── main.css        # Professional dark theme
    └── js/
        └── app.js          # Frontend application
```

---

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/markets/overview` | All global indices with price/change |
| `GET /api/markets/by-country` | Indices grouped by country |
| `GET /api/markets/top-performers` | Top 10 gainers and losers |
| `GET /api/markets/sector-heatmap` | 11 sector ETF performance |
| `GET /api/stock/<TICKER>` | Full stock detail + price history |
| `GET /api/stock/<TICKER>/analysis` | Technical & fundamental analysis + verdict |
| `GET /api/search?q=<query>` | Search stocks by ticker |

---

## Data Source

All data is fetched via **Yahoo Finance** (`yfinance`) — free, no API key required.

> ⚠️ Data is for informational purposes only and not financial advice.

---

## Tech Stack

- **Backend**: Python 3.11, Flask, yfinance, pandas, numpy
- **Frontend**: Vanilla JS, Chart.js, CSS custom properties
- **Fonts**: Syne (display), Space Mono (monospace), Inter (body)
- **No external dependencies** beyond requirements.txt

---

## License

MIT

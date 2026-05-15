/* ── StockVision Pro — Main Application JS ───────────────────────────────── */

"use strict";

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  currentView: "dashboard",
  indices: [],
  performers: { gainers: [], losers: [] },
  sectors: [],
  countryMarkets: {},
  currentChart: null,
  searchTimer: null,
};

// ── Utilities ─────────────────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function fmt(n, decimals = 2) {
  if (n == null || isNaN(n)) return "—";
  return Number(n).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
function fmtBig(n) {
  if (n == null) return "—";
  if (n >= 1e12) return "$" + (n / 1e12).toFixed(2) + "T";
  if (n >= 1e9)  return "$" + (n / 1e9).toFixed(2) + "B";
  if (n >= 1e6)  return "$" + (n / 1e6).toFixed(2) + "M";
  return "$" + fmt(n);
}
function fmtPct(n) {
  if (n == null || isNaN(n)) return "—";
  return (n >= 0 ? "+" : "") + fmt(n) + "%";
}
function colorClass(n) { return n >= 0 ? "up" : "down"; }

async function api(path) {
  const res = await fetch(path);
  const json = await res.json();
  if (json.status !== "success") throw new Error(json.message || "API error");
  return json.data;
}

// Sparkline via Chart.js
function drawSparkline(canvas, data, isUp) {
  if (!canvas || !data || data.length < 2) return;
  const ctx = canvas.getContext("2d");
  const color = isUp ? "#10d98b" : "#ff4d6d";
  new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map((_, i) => i),
      datasets: [{ data, borderColor: color, borderWidth: 1.5,
        pointRadius: 0, tension: 0.4,
        fill: true,
        backgroundColor: isUp
          ? "rgba(16,217,139,0.1)"
          : "rgba(255,77,109,0.1)",
      }],
    },
    options: {
      responsive: false, animation: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: { x: { display: false }, y: { display: false } },
    },
  });
}

// ── Navigation ─────────────────────────────────────────────────────────────────
function switchView(viewId) {
  $$(".view").forEach(v => v.classList.remove("active"));
  $$(".nav-link").forEach(l => l.classList.remove("active"));
  const el = $(`#view-${viewId}`);
  const link = $(`[data-view="${viewId}"]`);
  if (el) el.classList.add("active");
  if (link) link.classList.add("active");
  state.currentView = viewId;

  if (viewId === "markets" && !Object.keys(state.countryMarkets).length) {
    loadCountryMarkets();
  }
  if (viewId === "sectors" && !state.sectors.length) {
    loadSectors();
  }
}

$$(".nav-link").forEach(link => {
  link.addEventListener("click", e => {
    e.preventDefault();
    switchView(link.dataset.view);
  });
});

// ── Loading ────────────────────────────────────────────────────────────────────
function showLoading()  { $("#loadingOverlay").classList.remove("hidden"); }
function hideLoading()  { $("#loadingOverlay").classList.add("hidden"); }

// ── Dashboard ─────────────────────────────────────────────────────────────────
async function loadDashboard() {
  showLoading();
  try {
    const [indices, performers, sectors] = await Promise.all([
      api("/api/markets/overview"),
      api("/api/markets/top-performers"),
      api("/api/markets/sector-heatmap"),
    ]);
    state.indices    = indices;
    state.performers = performers;
    state.sectors    = sectors;

    renderStatsBar(indices);
    renderWorldIndices(indices);
    renderPerformers(performers.gainers, "topGainers");
    renderPerformers(performers.losers,  "topLosers");
    renderSectorHeatmap(sectors);
    buildTickerTape(indices);
  } catch (err) {
    console.error("Dashboard load error:", err);
  } finally {
    hideLoading();
  }
}

function renderStatsBar(indices) {
  const up   = indices.filter(i => i.change_pct >= 0);
  const down  = indices.filter(i => i.change_pct < 0);
  const best  = [...indices].sort((a, b) => b.change_pct - a.change_pct)[0];
  const worst = [...indices].sort((a, b) => a.change_pct - b.change_pct)[0];

  $("#marketsUp").textContent    = up.length;
  $("#marketsDown").textContent  = down.length;
  $("#totalMarkets").textContent = indices.length;
  if (best)  $("#bestMarket").textContent  = `${best.name} ${fmtPct(best.change_pct)}`;
  if (worst) $("#worstMarket").textContent = `${worst.name} ${fmtPct(worst.change_pct)}`;
}

function renderWorldIndices(indices, filter = "all") {
  const grid = $("#worldIndices");
  grid.innerHTML = "";
  const filtered = filter === "all" ? indices
    : filter === "up"   ? indices.filter(i => i.change_pct >= 0)
    : indices.filter(i => i.change_pct < 0);

  filtered.forEach(idx => {
    const tile = document.createElement("div");
    tile.className = "index-tile";
    tile.innerHTML = `
      <div class="index-country">${idx.country}</div>
      <div class="index-name">${idx.name}</div>
      <div class="index-sym">${idx.symbol}</div>
      <div class="index-price">${fmt(idx.price)}</div>
      <div class="index-change ${colorClass(idx.change_pct)}">
        ${fmtPct(idx.change_pct)} &nbsp;${idx.change >= 0 ? "▲" : "▼"} ${fmt(Math.abs(idx.change))}
      </div>
      <div class="sparkline-wrap">
        <canvas width="160" height="32"></canvas>
      </div>`;
    grid.appendChild(tile);
    const canvas = tile.querySelector("canvas");
    if (idx.sparkline) drawSparkline(canvas, idx.sparkline, idx.change_pct >= 0);
    tile.addEventListener("click", () => openStockModal(idx.symbol, idx.name));
  });
}

// Filter chips
$$("#worldIndices").length; // ensure DOM ready
document.addEventListener("click", e => {
  if (e.target.matches(".chip[data-filter]")) {
    $$(".chip[data-filter]").forEach(c => c.classList.remove("active"));
    e.target.classList.add("active");
    renderWorldIndices(state.indices, e.target.dataset.filter);
  }
});

function renderPerformers(list, containerId) {
  const container = $(`#${containerId}`);
  if (!container) return;
  container.innerHTML = "";
  if (!list.length) {
    container.innerHTML = '<div class="empty-state">No data available</div>';
    return;
  }
  list.forEach(item => {
    const div = document.createElement("div");
    div.className = "performer-item";
    const isUp = item.change_pct >= 0;
    div.innerHTML = `
      <div class="perf-left">
        <div class="perf-sym">${item.symbol}</div>
        <div class="perf-vol">Vol: ${item.volume ? Number(item.volume).toLocaleString() : "—"}</div>
      </div>
      <div class="perf-right">
        <div class="perf-price">$${fmt(item.price)}</div>
        <div class="perf-pct ${isUp ? "up" : "down"}">${fmtPct(item.change_pct)}</div>
      </div>`;
    div.addEventListener("click", () => openStockModal(item.symbol));
    container.appendChild(div);
  });
}

function renderSectorHeatmap(sectors) {
  const container = $("#sectorHeatmap");
  if (!container) return;
  container.innerHTML = "";

  const maxAbs = Math.max(...sectors.map(s => Math.abs(s.day_change)), 1);

  sectors.forEach(sec => {
    const tile = document.createElement("div");
    tile.className = "sector-tile";
    const pct  = sec.day_change;
    const intensity = Math.min(Math.abs(pct) / maxAbs, 1);
    const alpha = 0.08 + intensity * 0.55;
    const bg = pct >= 0
      ? `rgba(16,217,139,${alpha})`
      : `rgba(255,77,109,${alpha})`;
    tile.style.background = bg;
    tile.innerHTML = `
      <div class="sector-name">${sec.sector}</div>
      <div class="sector-etf">${sec.etf}</div>
      <div class="sector-day ${colorClass(pct)}">${fmtPct(pct)}</div>
      <div class="sector-month">1M: ${fmtPct(sec.month_change)}</div>`;
    tile.addEventListener("click", () => openStockModal(sec.etf, sec.sector + " ETF"));
    container.appendChild(tile);
  });
}

function buildTickerTape(indices) {
  const inner = $("#tapeInner");
  if (!inner || !indices.length) return;
  const html = [...indices, ...indices]
    .map(idx => `
      <span class="tape-item">
        <span class="t-sym">${idx.name.slice(0, 12)}</span>
        <span>${fmt(idx.price)}</span>
        <span class="${idx.change_pct >= 0 ? "t-up" : "t-down"}">
          ${fmtPct(idx.change_pct)}
        </span>
      </span>`)
    .join("");
  inner.innerHTML = html;
}

// ── Country Markets ────────────────────────────────────────────────────────────
async function loadCountryMarkets() {
  try {
    const data = await api("/api/markets/by-country");
    state.countryMarkets = data;
    renderCountryMarkets(data);
  } catch (err) {
    console.error("Country markets error:", err);
  }
}

function renderCountryMarkets(data) {
  const grid = $("#countryMarketsGrid");
  if (!grid) return;
  grid.innerHTML = "";

  const flags = {
    "United States":"🇺🇸","United Kingdom":"🇬🇧","Germany":"🇩🇪",
    "Japan":"🇯🇵","China":"🇨🇳","India":"🇮🇳","France":"🇫🇷",
    "Canada":"🇨🇦","Australia":"🇦🇺","Brazil":"🇧🇷","South Korea":"🇰🇷",
    "Singapore":"🇸🇬","Switzerland":"🇨🇭","Italy":"🇮🇹","Spain":"🇪🇸",
    "Netherlands":"🇳🇱","Saudi Arabia":"🇸🇦","Russia":"🇷🇺",
    "Mexico":"🇲🇽","South Africa":"🇿🇦",
  };

  Object.entries(data).forEach(([country, indices]) => {
    const card = document.createElement("div");
    card.className = "country-card";
    const rowsHTML = indices.map(idx => `
      <div class="country-index-row" data-sym="${idx.symbol}">
        <div>
          <div class="cir-name">${idx.name}</div>
          <div class="cir-sym">${idx.symbol} · ${idx.exchange}</div>
        </div>
        <div class="cir-right">
          <div class="cir-price">${fmt(idx.price)}</div>
          <div class="cir-chg ${colorClass(idx.change_pct)}">${fmtPct(idx.change_pct)}</div>
        </div>
      </div>`).join("");

    card.innerHTML = `
      <div class="country-card-header">
        <span>${flags[country] || "🌐"}</span>
        <span>${country}</span>
      </div>
      <div class="country-indices">${rowsHTML}</div>`;

    card.querySelectorAll(".country-index-row").forEach(row => {
      row.addEventListener("click", () => {
        const idx = indices.find(i => i.symbol === row.dataset.sym);
        openStockModal(row.dataset.sym, idx ? idx.name : row.dataset.sym);
      });
    });
    grid.appendChild(card);
  });
}

// ── Sectors View ───────────────────────────────────────────────────────────────
async function loadSectors() {
  const data = state.sectors.length ? state.sectors : await api("/api/markets/sector-heatmap");
  state.sectors = data;
  const wrap = $("#sectorsContent");
  if (!wrap) return;
  wrap.innerHTML = "";

  data.forEach(sec => {
    const card = document.createElement("div");
    card.className = "sector-detail-card";
    card.innerHTML = `
      <div class="sdcard-header">
        <div class="sdcard-name">${sec.sector}</div>
        <div class="sdcard-perf">
          <div class="sdcard-stat">
            <div class="label">Day</div>
            <div class="value ${colorClass(sec.day_change)}">${fmtPct(sec.day_change)}</div>
          </div>
          <div class="sdcard-stat">
            <div class="label">1 Month</div>
            <div class="value ${colorClass(sec.month_change)}">${fmtPct(sec.month_change)}</div>
          </div>
          <div class="sdcard-stat">
            <div class="label">ETF Price</div>
            <div class="value">$${fmt(sec.price)}</div>
          </div>
        </div>
      </div>`;
    card.style.cursor = "pointer";
    card.addEventListener("click", () => openStockModal(sec.etf, sec.sector + " Sector ETF"));
    wrap.appendChild(card);
  });
}

// ── Stock Modal ────────────────────────────────────────────────────────────────
async function openStockModal(ticker, displayName) {
  const modal = $("#stockModal");
  const content = $("#modalContent");
  modal.classList.remove("hidden");
  content.innerHTML = `<div class="empty-state">Loading ${ticker}…</div>`;

  try {
    const [detail, analysis] = await Promise.all([
      api(`/api/stock/${ticker}`),
      api(`/api/stock/${ticker}/analysis`),
    ]);
    renderModalContent(detail, analysis);
  } catch (err) {
    content.innerHTML = `<div class="empty-state">⚠ ${err.message}</div>`;
  }
}

function renderModalContent(detail, analysis) {
  const content = $("#modalContent");
  const d = detail;
  const a = analysis;
  const f = d.fundamentals;
  const s = d.stats;
  const pt = a.price_targets;

  // Verdict class
  const verdictClass = a.verdict.toLowerCase().replace(" ", "-");

  // Score ring SVG
  const pct = a.overall_score;
  const r = 68, cx = 80, cy = 80;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const scoreColor = pct >= 70 ? "#10d98b" : pct >= 45 ? "#fbbf24" : "#ff4d6d";

  // Tech signals
  const techHTML = a.tech_signals.map(sig => `
    <div class="signal-row">
      <div>
        <div class="sig-indicator">${sig.indicator}</div>
        <div class="sig-note">${sig.note}</div>
      </div>
      <span class="sig-badge ${sig.signal.toLowerCase().replace(" ", "-")}">${sig.signal}</span>
    </div>`).join("");

  // Fund signals
  const fundHTML = a.fund_signals.map(sig => `
    <div class="signal-row">
      <div>
        <div class="sig-indicator">${sig.metric}</div>
        <div class="sig-note">${sig.note}</div>
      </div>
      <span class="sig-badge ${sig.signal.toLowerCase().replace(" ", "-")}">${sig.signal}</span>
    </div>`).join("");

  // Fundamentals rows
  const fundRows = [
    ["Market Cap",    fmtBig(f.market_cap)],
    ["P/E Ratio",     f.pe_ratio ? fmt(f.pe_ratio) : "—"],
    ["Forward P/E",   f.forward_pe ? fmt(f.forward_pe) : "—"],
    ["EPS",           f.eps ? "$" + fmt(f.eps) : "—"],
    ["Div Yield",     f.dividend_yield ? fmt(f.dividend_yield * 100) + "%" : "—"],
    ["Beta",          f.beta ? fmt(f.beta) : "—"],
    ["52W High",      f.range_high ? fmt(f["52w_high"]) : "—"],
    ["52W Low",       f.range_low ? fmt(f["52w_low"]) : "—"],
    ["Profit Margin", f.profit_margin ? fmt(f.profit_margin * 100) + "%" : "—"],
    ["ROE",           f.roe ? fmt(f.roe * 100) + "%" : "—"],
    ["Debt/Equity",   f.debt_to_equity ? fmt(f.debt_to_equity) : "—"],
    ["Revenue",       fmtBig(f.revenue)],
  ].map(([k, v]) => `
    <div class="fund-row">
      <span class="fund-key">${k}</span>
      <span class="fund-val">${v}</span>
    </div>`).join("");

  content.innerHTML = `
    <div style="margin-bottom:1.5rem">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;flex-wrap:wrap">
        <div>
          <h1 style="font-family:var(--font-display);font-size:1.8rem;font-weight:800;letter-spacing:-0.03em">${d.name}</h1>
          <div style="color:var(--text2);margin-top:0.2rem;display:flex;gap:1rem;font-size:0.8rem;flex-wrap:wrap">
            <span class="mono">${d.ticker}</span>
            <span>${d.exchange}</span>
            <span>${d.sector || "—"}</span>
            <span>${d.country || "—"}</span>
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-family:var(--font-mono);font-size:2rem;font-weight:700">${d.currency} ${fmt(s.current_price)}</div>
          <div style="font-size:0.82rem;color:var(--text2)">Volatility: ${s.volatility}% &nbsp;|&nbsp; Sharpe: ${s.sharpe_ratio}</div>
        </div>
      </div>
    </div>

    <div class="analysis-wrap">
      <!-- Score Panel -->
      <div class="score-panel">
        <div class="score-ring-wrap">
          <svg viewBox="0 0 160 160">
            <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--bg2)" stroke-width="10"/>
            <circle cx="${cx}" cy="${cy}" r="${r}" fill="none"
              stroke="${scoreColor}" stroke-width="10"
              stroke-dasharray="${dash} ${circ}" stroke-dashoffset="${circ / 4}"
              stroke-linecap="round" style="transition:stroke-dasharray 0.8s ease"/>
            <text x="${cx}" y="${cy - 6}" text-anchor="middle" class="score-number" style="font-family:var(--font-display);font-size:2.2rem;font-weight:800;fill:var(--text)">${pct}</text>
            <text x="${cx}" y="${cy + 16}" text-anchor="middle" class="score-label" style="fill:var(--text3);font-size:0.7rem">SCORE</text>
          </svg>
        </div>

        <div class="verdict-badge">
          <span class="verdict-pill ${verdictClass}">${a.verdict}</span>
        </div>

        <div class="risk-bar-wrap">
          <div class="risk-label">Risk Level: ${a.risk_level}</div>
          <div class="risk-bar"><div class="risk-fill ${a.risk_level}"></div></div>
        </div>

        <div style="margin-top:1.2rem">
          <div style="font-size:0.7rem;color:var(--text3);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:0.5rem">52-Week Position</div>
          <div class="pos52-bar">
            <div class="pos52-dot" style="left:${pt.position_52w}%"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:0.65rem;color:var(--text3);margin-top:0.4rem">
            <span>Low</span><span>${pt.position_52w}%</span><span>High</span>
          </div>
        </div>

        <div style="margin-top:1.5rem">
          <div class="signals-section">
            <h3>Technical Signals</h3>
            ${techHTML}
          </div>
          <div class="signals-section" style="margin-top:1rem">
            <h3>Fundamental Signals</h3>
            ${fundHTML || "<div class='empty-state' style='padding:0.5rem'>No fundamental data</div>"}
          </div>
        </div>
      </div>

      <!-- Chart Panel -->
      <div class="chart-panel">
        <div class="chart-panel-header">
          <h2>${d.name} — Price Chart</h2>
          <div class="period-tabs" id="periodTabs">
            <button class="period-tab" data-period="1mo">1M</button>
            <button class="period-tab active" data-period="6mo">6M</button>
            <button class="period-tab" data-period="1y">1Y</button>
            <button class="period-tab" data-period="2y">2Y</button>
          </div>
        </div>
        <div class="chart-container">
          <canvas id="priceChart"></canvas>
        </div>

        <div class="targets-row">
          <div class="target-item">
            <div class="target-label">Current</div>
            <div class="target-value">${fmt(pt.current)}</div>
          </div>
          <div class="target-item">
            <div class="target-label">Support</div>
            <div class="target-value red">${fmt(pt.support)}</div>
          </div>
          <div class="target-item">
            <div class="target-label">Resistance</div>
            <div class="target-value green">${fmt(pt.resistance)}</div>
          </div>
          <div class="target-item">
            <div class="target-label">50D MA</div>
            <div class="target-value">${fmt(pt.sma50_target)}</div>
          </div>
          <div class="target-item">
            <div class="target-label">Return (period)</div>
            <div class="target-value ${s.total_return >= 0 ? "green" : "red"}">${fmtPct(s.total_return)}</div>
          </div>
          <div class="target-item">
            <div class="target-label">Max Drawdown</div>
            <div class="target-value red">${s.max_drawdown}%</div>
          </div>
        </div>

        <div style="margin-top:1.5rem">
          <div style="font-family:var(--font-display);font-size:0.85rem;font-weight:700;margin-bottom:0.75rem">Key Fundamentals</div>
          <div class="fundamentals-grid">${fundRows}</div>
        </div>

        ${d.description ? `
          <div style="margin-top:1.5rem;padding-top:1.5rem;border-top:1px solid var(--border)">
            <div style="font-family:var(--font-display);font-size:0.85rem;font-weight:700;margin-bottom:0.5rem">About</div>
            <div style="color:var(--text2);font-size:0.78rem;line-height:1.7">${d.description.slice(0, 500)}${d.description.length > 500 ? "…" : ""}</div>
          </div>` : ""}
      </div>
    </div>`;

  // Render chart
  renderPriceChart(d.price_data);

  // Period tab switching (re-fetch)
  $$("#periodTabs .period-tab").forEach(tab => {
    tab.addEventListener("click", async () => {
      $$("#periodTabs .period-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      try {
        const newDetail = await api(`/api/stock/${d.ticker}?period=${tab.dataset.period}`);
        renderPriceChart(newDetail.price_data);
      } catch (e) { console.error(e); }
    });
  });
}

function renderPriceChart(priceData) {
  const canvas = $("#priceChart");
  if (!canvas) return;
  if (state.currentChart) { state.currentChart.destroy(); state.currentChart = null; }

  const labels = priceData.dates;
  const closes = priceData.close;

  const ctx = canvas.getContext("2d");
  const gradient = ctx.createLinearGradient(0, 0, 0, 320);
  gradient.addColorStop(0, "rgba(0,212,255,0.25)");
  gradient.addColorStop(1, "rgba(0,212,255,0)");

  state.currentChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Price", data: closes, borderColor: "#00d4ff",
          borderWidth: 2, pointRadius: 0, tension: 0.3,
          fill: true, backgroundColor: gradient, yAxisID: "y",
        },
        {
          label: "SMA 50", data: priceData.sma50, borderColor: "#fbbf24",
          borderWidth: 1.5, pointRadius: 0, tension: 0.3,
          fill: false, yAxisID: "y", borderDash: [4, 4],
        },
        {
          label: "SMA 200", data: priceData.sma200, borderColor: "#7c3aed",
          borderWidth: 1.5, pointRadius: 0, tension: 0.3,
          fill: false, yAxisID: "y", borderDash: [8, 4],
        },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: true,
          labels: { color: "#8b98b5", font: { size: 11 }, boxWidth: 20 },
        },
        tooltip: {
          backgroundColor: "#141c2e", borderColor: "#1a2440",
          borderWidth: 1, titleColor: "#e8edf5", bodyColor: "#8b98b5",
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y != null ? fmt(ctx.parsed.y) : "—"}`,
          },
        },
      },
      scales: {
        x: {
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: { color: "#4a5875", maxTicksLimit: 8, font: { size: 10 } },
        },
        y: {
          grid: { color: "rgba(255,255,255,0.04)" },
          ticks: { color: "#4a5875", font: { size: 10 } },
          position: "right",
        },
      },
    },
  });
}

// Modal close
$("#stockModal .modal-backdrop").addEventListener("click", closeModal);
$(".modal-close").addEventListener("click", closeModal);
document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });
function closeModal() {
  $("#stockModal").classList.add("hidden");
  if (state.currentChart) { state.currentChart.destroy(); state.currentChart = null; }
}

// ── Screener ───────────────────────────────────────────────────────────────────
$("#screenerBtn").addEventListener("click", () => {
  const ticker = $("#screenerInput").value.trim().toUpperCase();
  if (!ticker) return;
  openScreenerResult(ticker);
});
$("#screenerInput").addEventListener("keydown", e => {
  if (e.key === "Enter") $("#screenerBtn").click();
});

async function openScreenerResult(ticker) {
  const result = $("#screenerResult");
  result.innerHTML = `<div class="empty-state">Analyzing ${ticker}…</div>`;
  try {
    const [detail, analysis] = await Promise.all([
      api(`/api/stock/${ticker}`),
      api(`/api/stock/${ticker}/analysis`),
    ]);
    // Reuse modal render logic but inline
    const fakeContent = document.createElement("div");
    fakeContent.id = "modalContent";
    result.innerHTML = "";
    result.appendChild(fakeContent);
    // Temporarily swap modal content target
    const orig = $("#modalContent");
    fakeContent.innerHTML = "";
    renderScreenerInline(detail, analysis, fakeContent);
  } catch (err) {
    result.innerHTML = `<div class="empty-state">⚠ ${err.message || "Stock not found"}</div>`;
  }
}

function renderScreenerInline(detail, analysis, container) {
  // Same as modal but renders in-page
  const d = detail, a = analysis, f = d.fundamentals, s = d.stats, pt = a.price_targets;
  const verdictClass = a.verdict.toLowerCase().replace(" ", "-");
  const pct = a.overall_score;
  const r = 68, cx = 80, cy = 80;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const scoreColor = pct >= 70 ? "#10d98b" : pct >= 45 ? "#fbbf24" : "#ff4d6d";

  const techHTML = a.tech_signals.map(sig => `
    <div class="signal-row">
      <div><div class="sig-indicator">${sig.indicator}</div><div class="sig-note">${sig.note}</div></div>
      <span class="sig-badge ${sig.signal.toLowerCase().replace(" ", "-")}">${sig.signal}</span>
    </div>`).join("");

  const fundHTML = a.fund_signals.map(sig => `
    <div class="signal-row">
      <div><div class="sig-indicator">${sig.metric}</div><div class="sig-note">${sig.note}</div></div>
      <span class="sig-badge ${sig.signal.toLowerCase().replace(" ", "-")}">${sig.signal}</span>
    </div>`).join("");

  const fundRows = [
    ["Market Cap", fmtBig(f.market_cap)], ["P/E", f.pe_ratio ? fmt(f.pe_ratio) : "—"],
    ["EPS", f.eps ? "$" + fmt(f.eps) : "—"], ["Beta", f.beta ? fmt(f.beta) : "—"],
    ["Profit Margin", f.profit_margin ? fmt(f.profit_margin * 100) + "%" : "—"],
    ["ROE", f.roe ? fmt(f.roe * 100) + "%" : "—"],
  ].map(([k, v]) => `<div class="fund-row"><span class="fund-key">${k}</span><span class="fund-val">${v}</span></div>`).join("");

  container.innerHTML = `
    <div style="background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:2rem;margin-bottom:1.5rem">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:1.5rem;flex-wrap:wrap;gap:1rem">
        <div>
          <h2 style="font-family:var(--font-display);font-size:1.6rem;font-weight:800">${d.name}</h2>
          <div style="color:var(--text2);font-size:0.8rem;display:flex;gap:1rem;margin-top:0.3rem;flex-wrap:wrap">
            <span class="mono">${d.ticker}</span><span>${d.exchange}</span>
            <span>${d.sector || "—"}</span><span>${d.country || "—"}</span>
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-family:var(--font-mono);font-size:2rem;font-weight:700">${d.currency} ${fmt(s.current_price)}</div>
          <div style="color:var(--text2);font-size:0.8rem">Volatility: ${s.volatility}% | Sharpe: ${s.sharpe_ratio}</div>
        </div>
      </div>
      <div class="analysis-wrap">
        <div class="score-panel">
          <div class="score-ring-wrap">
            <svg viewBox="0 0 160 160">
              <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--bg2)" stroke-width="10"/>
              <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${scoreColor}" stroke-width="10"
                stroke-dasharray="${dash} ${circ}" stroke-dashoffset="${circ/4}" stroke-linecap="round"/>
              <text x="${cx}" y="${cy-6}" text-anchor="middle" style="font-family:var(--font-display);font-size:2.2rem;font-weight:800;fill:var(--text)">${pct}</text>
              <text x="${cx}" y="${cy+16}" text-anchor="middle" style="fill:var(--text3);font-size:0.7rem">SCORE</text>
            </svg>
          </div>
          <div class="verdict-badge"><span class="verdict-pill ${verdictClass}">${a.verdict}</span></div>
          <div class="risk-bar-wrap">
            <div class="risk-label">Risk: ${a.risk_level}</div>
            <div class="risk-bar"><div class="risk-fill ${a.risk_level}"></div></div>
          </div>
          <div class="signals-section" style="margin-top:1rem"><h3>Technical</h3>${techHTML}</div>
          <div class="signals-section" style="margin-top:1rem"><h3>Fundamentals</h3>${fundHTML}</div>
        </div>
        <div class="chart-panel">
          <div class="chart-panel-header"><h2>Price Chart</h2></div>
          <div class="chart-container"><canvas id="screenerChart"></canvas></div>
          <div class="targets-row">
            <div class="target-item"><div class="target-label">Support</div><div class="target-value red">${fmt(pt.support)}</div></div>
            <div class="target-item"><div class="target-label">Resistance</div><div class="target-value green">${fmt(pt.resistance)}</div></div>
            <div class="target-item"><div class="target-label">Return</div><div class="target-value ${s.total_return>=0?"green":"red"}">${fmtPct(s.total_return)}</div></div>
            <div class="target-item"><div class="target-label">Max Drawdown</div><div class="target-value red">${s.max_drawdown}%</div></div>
          </div>
          <div class="fundamentals-grid" style="margin-top:1rem">${fundRows}</div>
        </div>
      </div>
    </div>`;

  // Render screener chart
  const canvas = container.querySelector("#screenerChart");
  if (canvas) {
    const ctx = canvas.getContext("2d");
    const gradient = ctx.createLinearGradient(0, 0, 0, 320);
    gradient.addColorStop(0, "rgba(0,212,255,0.25)");
    gradient.addColorStop(1, "rgba(0,212,255,0)");
    new Chart(ctx, {
      type: "line",
      data: {
        labels: d.price_data.dates,
        datasets: [{
          label: "Price", data: d.price_data.close, borderColor: "#00d4ff",
          borderWidth: 2, pointRadius: 0, tension: 0.3, fill: true, backgroundColor: gradient,
        }, {
          label: "SMA 50", data: d.price_data.sma50, borderColor: "#fbbf24",
          borderWidth: 1.5, pointRadius: 0, fill: false, borderDash: [4,4],
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: true, labels: { color: "#8b98b5", font: { size: 11 }, boxWidth: 20 } },
          tooltip: { backgroundColor: "#141c2e", borderColor: "#1a2440", borderWidth: 1 } },
        scales: {
          x: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#4a5875", maxTicksLimit: 8, font:{size:10} } },
          y: { grid: { color: "rgba(255,255,255,0.04)" }, ticks: { color: "#4a5875", font:{size:10} }, position: "right" },
        },
      },
    });
  }
}

// ── Global Search ──────────────────────────────────────────────────────────────
const searchInput = $("#globalSearch");
const searchDropdown = $("#searchDropdown");

searchInput.addEventListener("input", () => {
  clearTimeout(state.searchTimer);
  const q = searchInput.value.trim();
  if (q.length < 1) { searchDropdown.classList.add("hidden"); return; }
  state.searchTimer = setTimeout(() => doSearch(q), 350);
});

async function doSearch(q) {
  try {
    const results = await api(`/api/search?q=${encodeURIComponent(q)}`);
    if (!results.length) { searchDropdown.classList.add("hidden"); return; }
    searchDropdown.innerHTML = results.map(r => `
      <div class="search-item" data-sym="${r.symbol}">
        <div>
          <div class="s-name">${r.name || r.symbol}</div>
          <div style="font-size:0.68rem;color:var(--text3)">${r.sector || ""} ${r.country || ""}</div>
        </div>
        <span class="s-sym">${r.symbol}</span>
      </div>`).join("");
    searchDropdown.classList.remove("hidden");
    searchDropdown.querySelectorAll(".search-item").forEach(item => {
      item.addEventListener("click", () => {
        searchDropdown.classList.add("hidden");
        searchInput.value = "";
        openStockModal(item.dataset.sym);
      });
    });
  } catch (e) {
    searchDropdown.classList.add("hidden");
  }
}

document.addEventListener("click", e => {
  if (!e.target.closest(".search-wrap")) searchDropdown.classList.add("hidden");
});

// ── Boot ───────────────────────────────────────────────────────────────────────
loadDashboard();

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

async function getJSON(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`failed to load ${path}`);
  return res.json();
}

function fmt(n, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return Number(n).toLocaleString("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function pctBadgeClass(v) {
  if (v === null || v === undefined) return "badge-neutral";
  return v >= 0 ? "badge-positive" : "badge-negative";
}

function signalBadgeClass(signal) {
  return { Bullish: "badge-bullish", Bearish: "badge-bearish" }[signal] || "badge-neutral";
}

function actionBadgeClass(action) {
  return { BUY: "badge-bullish", SELL: "badge-bearish" }[action] || "badge-neutral";
}

function setupTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    });
  });
}

let analysisChart, backtestChart;

function renderSignals(quotesDoc, analysisDoc, fundamentalsDoc) {
  const quotes = quotesDoc.quotes;
  const analysis = analysisDoc.analysis;
  const fundamentals = fundamentalsDoc.fundamentals || {};
  const symbols = Object.keys(quotes).sort((a, b) => {
    const order = { BUY: 0, HOLD: 1, SELL: 2 };
    return (order[analysis[a]?.action] ?? 1) - (order[analysis[b]?.action] ?? 1);
  });

  const tbody = document.querySelector("#signals-table tbody");
  tbody.innerHTML = symbols.map((sym) => {
    const q = quotes[sym];
    const a = analysis[sym] || {};
    const f = fundamentals[sym] || {};
    return `<tr>
      <td>${q.name}<br><span class="hint">${sym}</span></td>
      <td>${fmt(q.price)}</td>
      <td>${f.pe_ratio !== null && f.pe_ratio !== undefined ? fmt(f.pe_ratio, 1) : "—"}</td>
      <td><span class="badge ${actionBadgeClass(a.action)}">${a.action || "—"}</span></td>
      <td class="wrap">${a.action_reason || "—"}</td>
      <td class="wrap">${a.exit_rule || "—"}</td>
    </tr>`;
  }).join("");
}

function renderAnalysis(quotesDoc, analysisDoc, fundamentalsDoc, newsDoc) {
  const quotes = quotesDoc.quotes;
  const analysis = analysisDoc.analysis;
  const fundamentals = fundamentalsDoc.fundamentals || {};
  const news = newsDoc.news || {};
  const symbols = Object.keys(quotes).sort();

  const tbody = document.querySelector("#analysis-table tbody");
  tbody.innerHTML = symbols.map((sym) => {
    const q = quotes[sym];
    const a = analysis[sym] || {};
    return `<tr>
      <td>${q.name}<br><span class="hint">${sym}</span></td>
      <td>${fmt(q.price)}</td>
      <td><span class="badge ${pctBadgeClass(q.pct_change)}">${q.pct_change >= 0 ? "+" : ""}${fmt(q.pct_change)}%</span></td>
      <td>${fmt(a.sma20)}</td>
      <td>${fmt(a.sma50)}</td>
      <td>${fmt(a.rsi14)}</td>
      <td><span class="badge ${signalBadgeClass(a.signal)}">${a.signal || "—"}</span></td>
    </tr>`;
  }).join("");

  const select = document.getElementById("analysis-symbol-select");
  select.innerHTML = symbols.map((s) => `<option value="${s}">${quotes[s].name} (${s})</option>`).join("");
  const showDetail = (sym) => {
    drawAnalysisChart(analysis, sym);
    renderFundamentals(fundamentals[sym]);
    renderNews(news[sym]);
  };
  select.addEventListener("change", () => showDetail(select.value));
  if (symbols.length) showDetail(symbols[0]);
}

function renderFundamentals(f) {
  const grid = document.getElementById("fundamentals-grid");
  if (!f) {
    grid.innerHTML = `<div class="hint">No fundamentals data yet.</div>`;
    return;
  }
  const rows = [
    ["Market cap", f.market_cap_cr ? `₹${fmt(f.market_cap_cr, 0)} Cr` : "—"],
    ["P/E (trailing)", f.pe_ratio ?? "—"],
    ["P/E (forward)", f.forward_pe ?? "—"],
    ["EPS", f.eps ? fmt(f.eps) : "—"],
    ["Dividend yield", f.dividend_yield_pct ? `${fmt(f.dividend_yield_pct)}%` : "—"],
    ["ROE", f.roe_pct ? `${fmt(f.roe_pct)}%` : "—"],
    ["Beta", f.beta ?? "—"],
    ["52w range", f.week52_low && f.week52_high ? `${fmt(f.week52_low)} – ${fmt(f.week52_high)}` : "—"],
    ["Sector", f.sector || "—"],
    ["Industry", f.industry || "—"],
  ];
  grid.innerHTML = rows.map(([label, value]) => `
    <div class="fund-item"><div class="fund-label">${label}</div><div class="fund-value">${value}</div></div>
  `).join("");
}

function renderNews(items) {
  const list = document.getElementById("news-list");
  if (!items || !items.length) {
    list.innerHTML = `<li class="hint">No recent news found.</li>`;
    return;
  }
  list.innerHTML = items.map((n) => {
    const date = n.published ? new Date(n.published).toLocaleDateString("en-IN", { day: "numeric", month: "short" }) : "";
    return `<li>
      <a href="${n.url}" target="_blank" rel="noopener noreferrer">${n.title}</a>
      <div class="hint">${n.publisher || ""}${date ? " · " + date : ""}</div>
    </li>`;
  }).join("");
}

function drawAnalysisChart(analysis, symbol) {
  const a = analysis[symbol];
  if (!a) return;
  const labels = a.history.map((h) => h.date);
  const close = a.history.map((h) => h.close);
  const sma20 = a.history.map((h) => h.sma20);
  const sma50 = a.history.map((h) => h.sma50);

  if (analysisChart) analysisChart.destroy();
  analysisChart = new Chart(document.getElementById("analysis-chart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "Close", data: close, borderColor: css("--accent"), borderWidth: 2, pointRadius: 0 },
        { label: "SMA20", data: sma20, borderColor: css("--green"), borderWidth: 1.5, pointRadius: 0 },
        { label: "SMA50", data: sma50, borderColor: css("--red"), borderWidth: 1.5, pointRadius: 0 },
      ],
    },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { ticks: { color: css("--text-muted"), maxTicksLimit: 8 }, grid: { display: false } },
        y: { ticks: { color: css("--text-muted") }, grid: { color: css("--border") } },
      },
      plugins: { legend: { labels: { color: css("--text") } } },
    },
  });
}

function renderPortfolio(doc) {
  const { positions, totals } = doc;
  const statRow = document.getElementById("portfolio-stats");
  statRow.innerHTML = `
    <div class="stat-card"><div class="label">Invested</div><div class="value">₹${fmt(totals.invested)}</div></div>
    <div class="stat-card"><div class="label">Current value</div><div class="value">₹${fmt(totals.current_value)}</div></div>
    <div class="stat-card"><div class="label">P&amp;L</div><div class="value ${totals.pnl_abs >= 0 ? "up" : "down"}">₹${fmt(totals.pnl_abs)}</div></div>
    <div class="stat-card"><div class="label">P&amp;L %</div><div class="value ${totals.pnl_pct >= 0 ? "up" : "down"}">${totals.pnl_pct >= 0 ? "+" : ""}${fmt(totals.pnl_pct)}%</div></div>
  `;

  const tbody = document.querySelector("#portfolio-table tbody");
  tbody.innerHTML = positions.map((p) => `<tr>
    <td>${p.name}<br><span class="hint">${p.symbol}</span></td>
    <td>${fmt(p.qty)}</td>
    <td>${fmt(p.buy_price)}</td>
    <td>${fmt(p.current_price)}</td>
    <td>${fmt(p.invested)}</td>
    <td>${fmt(p.current_value)}</td>
    <td class="${p.pnl_abs >= 0 ? "up" : "down"}">${fmt(p.pnl_abs)}</td>
    <td class="${p.pnl_pct >= 0 ? "up" : "down"}">${p.pnl_pct !== null ? (p.pnl_pct >= 0 ? "+" : "") + fmt(p.pnl_pct) + "%" : "—"}</td>
  </tr>`).join("");

  document.getElementById("portfolio-empty").hidden = positions.length > 0;
}

function renderAlerts(doc) {
  const { rules } = doc;
  const tbody = document.querySelector("#alerts-table tbody");
  const statusClass = { new: "badge-negative", active: "badge-negative", cleared: "badge-neutral", inactive: "badge-inactive" };
  const statusLabel = { new: "NEW", active: "ACTIVE", cleared: "CLEARED", inactive: "—" };

  tbody.innerHTML = rules.map((r) => `<tr>
    <td><span class="badge ${statusClass[r.status] || "badge-neutral"}">${statusLabel[r.status] || r.status}</span></td>
    <td>${r.label}</td>
    <td>${r.symbol}</td>
    <td>${r.condition} ${r.value}</td>
    <td>${fmt(r.current_price)} (${r.current_pct_change >= 0 ? "+" : ""}${fmt(r.current_pct_change)}%)</td>
  </tr>`).join("");

  document.getElementById("alerts-empty").hidden = rules.length > 0;
}

function renderBacktest(doc) {
  const results = doc.results;
  const symbols = Object.keys(results).sort();

  const tbody = document.querySelector("#backtest-table tbody");
  tbody.innerHTML = symbols.map((sym) => {
    const r = results[sym];
    return `<tr>
      <td>${sym}</td>
      <td class="${r.strategy_return_pct >= 0 ? "up" : "down"}">${r.strategy_return_pct >= 0 ? "+" : ""}${fmt(r.strategy_return_pct)}%</td>
      <td class="${r.buyhold_return_pct >= 0 ? "up" : "down"}">${r.buyhold_return_pct >= 0 ? "+" : ""}${fmt(r.buyhold_return_pct)}%</td>
      <td>${r.num_trades}</td>
      <td>${r.win_rate_pct !== null ? fmt(r.win_rate_pct) + "%" : "—"}</td>
    </tr>`;
  }).join("");

  const select = document.getElementById("backtest-symbol-select");
  select.innerHTML = symbols.map((s) => `<option value="${s}">${s}</option>`).join("");
  select.addEventListener("change", () => drawBacktestChart(results, select.value));
  if (symbols.length) drawBacktestChart(results, symbols[0]);
}

function drawBacktestChart(results, symbol) {
  const r = results[symbol];
  if (!r) return;
  const labels = r.equity_curve.strategy.map((p) => p.date);
  const strategy = r.equity_curve.strategy.map((p) => p.value);
  const buyhold = r.equity_curve.buyhold.map((p) => p.value);

  if (backtestChart) backtestChart.destroy();
  backtestChart = new Chart(document.getElementById("backtest-chart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        { label: "SMA crossover strategy", data: strategy, borderColor: css("--accent"), borderWidth: 2, pointRadius: 0 },
        { label: "Buy & hold", data: buyhold, borderColor: css("--neutral"), borderWidth: 1.5, pointRadius: 0, borderDash: [4, 3] },
      ],
    },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { ticks: { color: css("--text-muted"), maxTicksLimit: 8 }, grid: { display: false } },
        y: { ticks: { color: css("--text-muted") }, grid: { color: css("--border") } },
      },
      plugins: { legend: { labels: { color: css("--text") } } },
    },
  });
}

async function main() {
  setupTabs();
  try {
    const [quotes, analysis, portfolio, alerts, backtest, fundamentals, news] = await Promise.all([
      getJSON("data/quotes.json"),
      getJSON("data/analysis.json"),
      getJSON("data/portfolio.json"),
      getJSON("data/alerts.json"),
      getJSON("data/backtest.json"),
      getJSON("data/fundamentals.json"),
      getJSON("data/news.json"),
    ]);

    document.getElementById("last-updated").textContent =
      "Last updated: " + new Date(quotes.updated).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });

    renderSignals(quotes, analysis, fundamentals);
    renderAnalysis(quotes, analysis, fundamentals, news);
    renderPortfolio(portfolio);
    renderAlerts(alerts);
    renderBacktest(backtest);
  } catch (err) {
    document.getElementById("last-updated").textContent = "Failed to load data";
    console.error(err);
  }
}

main();

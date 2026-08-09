# Nifty50 Agent

A personal share-market agent for the top 20 Nifty 50 companies (by index weight):
research/analysis, a portfolio tracker, price alerts, and a strategy backtester.
No API keys anywhere — data comes from free public Yahoo Finance quotes via
[`yfinance`](https://pypi.org/project/yfinance/), and the site is a static page
on GitHub Pages that a scheduled GitHub Action keeps up to date.

Not financial advice. The backtester is a historical simulation only — nothing
here places or suggests live trades.

## How it works

- `config/watchlist.json` — the 20 symbols tracked (edit to add/remove)
- `config/holdings.json` — your portfolio positions (edit to add what you own)
- `config/alert_rules.json` — price/percent-change rules to watch (edit to add rules)
- `.github/workflows/update.yml` — runs on a schedule (weekdays 15:35 IST, shortly
  after NSE close) and on-demand, via **Actions → Update market data → Run workflow**
- `scripts/*.py` — fetch quotes, compute indicators, portfolio P&L, alert status,
  and the backtest; each writes JSON into `docs/data/`
- `docs/` — the static site (GitHub Pages serves this folder), reads the JSON at
  page load, no build step

## One-time setup

1. **Enable GitHub Pages**: repo Settings → Pages → Source: "Deploy from a branch"
   → Branch: `main`, folder: `/docs` → Save. Or via CLI:
   ```bash
   gh api repos/d4kverma/nifty50-agent/pages -X POST -f "source[branch]=main" -f "source[path]=/docs"
   ```
2. That's it — no secrets, no tokens to configure. The workflow uses the default
   `GITHUB_TOKEN` GitHub Actions already provides to commit updated data back.

## Editing your watchlist / holdings / alerts

Just edit the JSON files in `config/` and push. The next scheduled run (or a manual
`workflow_dispatch`) picks up the changes automatically.

**Alert conditions**: `price_above`, `price_below`, `pct_change_above`, `pct_change_below`.
Example:
```json
{ "symbol": "TCS.NS", "condition": "price_below", "value": 3500, "label": "TCS below 3500" }
```
Alerts show up on the Alerts tab with a status badge — `NEW` the run it first fires,
`ACTIVE` while still true, `CLEARED` the run after it stops being true. There's no
external push (no email/Telegram/etc.) — check the page to see current alerts.

## Running locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python scripts/fetch_and_analyze.py
.venv/bin/python scripts/portfolio.py
.venv/bin/python scripts/alerts.py
.venv/bin/python scripts/backtest.py
python3 -m http.server 8000 --directory docs   # then open http://localhost:8000
```

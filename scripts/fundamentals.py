"""Fetch company fundamentals per watchlist symbol via yfinance (no API key).

Gives BUY/SELL signals some context beyond pure price patterns: valuation
(P/E), size (market cap), profitability (ROE), and where price sits in its
52-week range. Writes docs/data/fundamentals.json.
"""
import sys
import time

import yfinance as yf

from common import DATA_DIR, load_watchlist, save_json, utcnow_iso


def crores(value):
    return round(value / 1e7, 1) if value is not None else None


def main():
    watchlist = load_watchlist()
    if not watchlist:
        print("watchlist is empty, nothing to fetch", file=sys.stderr)
        return

    fundamentals = {}
    for w in watchlist:
        symbol = w["symbol"]
        try:
            info = yf.Ticker(symbol).info
        except Exception as e:
            print(f"failed to fetch fundamentals for {symbol}: {e}", file=sys.stderr)
            continue

        fundamentals[symbol] = {
            "market_cap_cr": crores(info.get("marketCap")),
            "pe_ratio": round(info["trailingPE"], 1) if info.get("trailingPE") else None,
            "forward_pe": round(info["forwardPE"], 1) if info.get("forwardPE") else None,
            "eps": info.get("trailingEps"),
            "dividend_yield_pct": info.get("dividendYield"),
            "week52_high": info.get("fiftyTwoWeekHigh"),
            "week52_low": info.get("fiftyTwoWeekLow"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "roe_pct": round(info["returnOnEquity"] * 100, 1) if info.get("returnOnEquity") is not None else None,
            "beta": info.get("beta"),
        }
        time.sleep(0.3)  # be polite to the free endpoint

    save_json(DATA_DIR / "fundamentals.json", {"updated": utcnow_iso(), "fundamentals": fundamentals})
    print(f"wrote fundamentals.json for {len(fundamentals)} symbols")


if __name__ == "__main__":
    main()

"""Fetch quotes + history for the watchlist and compute technical indicators.

Writes docs/data/quotes.json and docs/data/analysis.json. No API key required
(yfinance pulls public Yahoo Finance data).
"""
import sys

import pandas as pd
import yfinance as yf

from common import DATA_DIR, load_watchlist, save_json, utcnow_iso

HISTORY_PERIOD = "2y"
CHART_DAYS = 180


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def macd(close: pd.Series):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line, signal_line


def classify_signal(sma20, sma50, rsi14):
    if sma20 is None or sma50 is None or rsi14 is None:
        return "Neutral"
    if sma20 > sma50 and rsi14 < 70:
        return "Bullish"
    if sma20 < sma50 and rsi14 > 30:
        return "Bearish"
    return "Neutral"


def main():
    watchlist = load_watchlist()
    if not watchlist:
        print("watchlist is empty, nothing to fetch", file=sys.stderr)
        return

    symbols = [w["symbol"] for w in watchlist]
    names = {w["symbol"]: w["name"] for w in watchlist}

    raw = yf.download(
        tickers=symbols,
        period=HISTORY_PERIOD,
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )

    quotes = {}
    analysis = {}

    for symbol in symbols:
        try:
            df = raw[symbol].dropna(how="all") if len(symbols) > 1 else raw.dropna(how="all")
        except KeyError:
            print(f"no data for {symbol}, skipping", file=sys.stderr)
            continue
        if df.empty or len(df) < 5:
            print(f"insufficient data for {symbol}, skipping", file=sys.stderr)
            continue

        close = df["Close"].dropna()
        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()
        rsi14 = rsi(close, 14)
        macd_line, macd_signal = macd(close)

        last = df.iloc[-1]
        prev_close = close.iloc[-2] if len(close) > 1 else last["Close"]
        price = float(last["Close"])
        change = price - float(prev_close)
        pct_change = (change / float(prev_close) * 100) if prev_close else 0.0

        quotes[symbol] = {
            "name": names.get(symbol, symbol),
            "price": round(price, 2),
            "prev_close": round(float(prev_close), 2),
            "change": round(change, 2),
            "pct_change": round(pct_change, 2),
            "day_high": round(float(last["High"]), 2),
            "day_low": round(float(last["Low"]), 2),
            "volume": int(last["Volume"]) if pd.notna(last["Volume"]) else None,
            "date": close.index[-1].strftime("%Y-%m-%d"),
        }

        latest_sma20 = float(sma20.iloc[-1]) if pd.notna(sma20.iloc[-1]) else None
        latest_sma50 = float(sma50.iloc[-1]) if pd.notna(sma50.iloc[-1]) else None
        latest_rsi = float(rsi14.iloc[-1]) if pd.notna(rsi14.iloc[-1]) else None

        chart = close.tail(CHART_DAYS)
        chart_sma20 = sma20.tail(CHART_DAYS)
        chart_sma50 = sma50.tail(CHART_DAYS)

        analysis[symbol] = {
            "sma20": round(latest_sma20, 2) if latest_sma20 else None,
            "sma50": round(latest_sma50, 2) if latest_sma50 else None,
            "rsi14": round(latest_rsi, 2) if latest_rsi else None,
            "macd": round(float(macd_line.iloc[-1]), 2) if pd.notna(macd_line.iloc[-1]) else None,
            "macd_signal": round(float(macd_signal.iloc[-1]), 2) if pd.notna(macd_signal.iloc[-1]) else None,
            "signal": classify_signal(latest_sma20, latest_sma50, latest_rsi),
            "history": [
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "close": round(float(c), 2) if pd.notna(c) else None,
                    "sma20": round(float(s20), 2) if pd.notna(s20) else None,
                    "sma50": round(float(s50), 2) if pd.notna(s50) else None,
                }
                for d, c, s20, s50 in zip(chart.index, chart, chart_sma20, chart_sma50)
            ],
        }

    save_json(DATA_DIR / "quotes.json", {"updated": utcnow_iso(), "quotes": quotes})
    save_json(DATA_DIR / "analysis.json", {"updated": utcnow_iso(), "analysis": analysis})
    print(f"wrote quotes + analysis for {len(quotes)} symbols")


if __name__ == "__main__":
    main()

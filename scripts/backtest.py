"""Backtest a simple SMA(20/50) crossover strategy per watchlist symbol vs.
buy-and-hold, over ~2 years of daily history. Historical simulation only —
this does not place or suggest live trades.

Writes docs/data/backtest.json.
"""
import sys

import pandas as pd
import yfinance as yf

from common import DATA_DIR, load_watchlist, save_json, utcnow_iso

HISTORY_PERIOD = "2y"
INITIAL_CAPITAL = 100_000.0
CURVE_POINTS = 120


def downsample(dates, values, n):
    if len(dates) <= n:
        return list(zip(dates, values))
    step = len(dates) / n
    idxs = sorted({int(i * step) for i in range(n)} | {len(dates) - 1})
    return [(dates[i], values[i]) for i in idxs]


def backtest_symbol(df: pd.DataFrame):
    close = df["Close"].dropna()
    if len(close) < 60:
        return None

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()

    # position for day t decided using SMA relationship as of t-1 (no lookahead)
    raw_position = (sma20 > sma50).astype(int)
    position = raw_position.shift(1).fillna(0)

    daily_return = close.pct_change().fillna(0)
    strategy_return = daily_return * position
    buyhold_return = daily_return

    strategy_equity = INITIAL_CAPITAL * (1 + strategy_return).cumprod()
    buyhold_equity = INITIAL_CAPITAL * (1 + buyhold_return).cumprod()

    trade_changes = position.diff().fillna(0)
    entries = trade_changes[trade_changes == 1].index
    exits = trade_changes[trade_changes == -1].index

    trade_returns = []
    for entry in entries:
        later_exits = exits[exits > entry]
        exit_ = later_exits[0] if len(later_exits) else close.index[-1]
        entry_price = close.loc[entry]
        exit_price = close.loc[exit_]
        trade_returns.append((exit_price - entry_price) / entry_price)

    num_trades = len(trade_returns)
    wins = sum(1 for r in trade_returns if r > 0)
    win_rate = (wins / num_trades * 100) if num_trades else None

    strategy_total_return = (strategy_equity.iloc[-1] / INITIAL_CAPITAL - 1) * 100
    buyhold_total_return = (buyhold_equity.iloc[-1] / INITIAL_CAPITAL - 1) * 100

    dates = [d.strftime("%Y-%m-%d") for d in close.index]
    strategy_points = downsample(dates, strategy_equity.round(2).tolist(), CURVE_POINTS)
    buyhold_points = downsample(dates, buyhold_equity.round(2).tolist(), CURVE_POINTS)

    return {
        "strategy_return_pct": round(float(strategy_total_return), 2),
        "buyhold_return_pct": round(float(buyhold_total_return), 2),
        "num_trades": num_trades,
        "win_rate_pct": round(win_rate, 2) if win_rate is not None else None,
        "equity_curve": {
            "strategy": [{"date": d, "value": v} for d, v in strategy_points],
            "buyhold": [{"date": d, "value": v} for d, v in buyhold_points],
        },
    }


def main():
    watchlist = load_watchlist()
    if not watchlist:
        print("watchlist is empty, nothing to backtest", file=sys.stderr)
        return

    symbols = [w["symbol"] for w in watchlist]
    raw = yf.download(
        tickers=symbols,
        period=HISTORY_PERIOD,
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )

    results = {}
    for symbol in symbols:
        try:
            df = raw[symbol].dropna(how="all") if len(symbols) > 1 else raw.dropna(how="all")
        except KeyError:
            continue
        result = backtest_symbol(df)
        if result:
            results[symbol] = result

    save_json(DATA_DIR / "backtest.json", {
        "updated": utcnow_iso(),
        "strategy": "SMA20/50 crossover (long-only)",
        "initial_capital": INITIAL_CAPITAL,
        "results": results,
    })
    print(f"wrote backtest.json for {len(results)} symbols")


if __name__ == "__main__":
    main()

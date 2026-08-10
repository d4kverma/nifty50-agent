"""Fetch recent news headlines per watchlist symbol via yfinance (no API key).

Gives BUY/SELL signals some context beyond price patterns — what's actually
being reported about the company. Writes docs/data/news.json.
"""
import sys
import time

import yfinance as yf

from common import DATA_DIR, load_watchlist, save_json, utcnow_iso

MAX_ITEMS_PER_SYMBOL = 5


def main():
    watchlist = load_watchlist()
    if not watchlist:
        print("watchlist is empty, nothing to fetch", file=sys.stderr)
        return

    news = {}
    for w in watchlist:
        symbol = w["symbol"]
        try:
            items = yf.Ticker(symbol).news or []
        except Exception as e:
            print(f"failed to fetch news for {symbol}: {e}", file=sys.stderr)
            continue

        parsed = []
        for item in items[:MAX_ITEMS_PER_SYMBOL]:
            content = item.get("content", {})
            url = (content.get("clickThroughUrl") or content.get("canonicalUrl") or {}).get("url")
            title = content.get("title")
            if not title or not url:
                continue
            parsed.append({
                "title": title,
                "publisher": (content.get("provider") or {}).get("displayName"),
                "url": url,
                "published": content.get("pubDate"),
            })

        news[symbol] = parsed
        time.sleep(0.3)  # be polite to the free endpoint

    save_json(DATA_DIR / "news.json", {"updated": utcnow_iso(), "news": news})
    total = sum(len(v) for v in news.values())
    print(f"wrote news.json: {total} headlines across {len(news)} symbols")


if __name__ == "__main__":
    main()

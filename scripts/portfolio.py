"""Compute portfolio P&L from config/holdings.json against the latest quotes.

Must run after fetch_and_analyze.py. Writes docs/data/portfolio.json.
"""
from common import CONFIG_DIR, DATA_DIR, load_json, save_json, utcnow_iso


def main():
    holdings_cfg = load_json(CONFIG_DIR / "holdings.json", {"holdings": []})
    quotes_doc = load_json(DATA_DIR / "quotes.json", {"quotes": {}})
    quotes = quotes_doc.get("quotes", {})

    positions = []
    total_invested = 0.0
    total_value = 0.0

    for h in holdings_cfg.get("holdings", []):
        symbol = h["symbol"]
        qty = float(h["qty"])
        buy_price = float(h["buy_price"])
        invested = qty * buy_price

        quote = quotes.get(symbol)
        price = quote["price"] if quote else None
        value = qty * price if price is not None else None
        pnl_abs = (value - invested) if value is not None else None
        pnl_pct = (pnl_abs / invested * 100) if pnl_abs is not None and invested else None

        total_invested += invested
        if value is not None:
            total_value += value

        positions.append({
            "symbol": symbol,
            "name": quote["name"] if quote else symbol,
            "qty": qty,
            "buy_price": buy_price,
            "buy_date": h.get("buy_date"),
            "current_price": price,
            "invested": round(invested, 2),
            "current_value": round(value, 2) if value is not None else None,
            "pnl_abs": round(pnl_abs, 2) if pnl_abs is not None else None,
            "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
        })

    total_pnl_abs = total_value - total_invested if positions else 0.0
    total_pnl_pct = (total_pnl_abs / total_invested * 100) if total_invested else 0.0

    save_json(DATA_DIR / "portfolio.json", {
        "updated": utcnow_iso(),
        "positions": positions,
        "totals": {
            "invested": round(total_invested, 2),
            "current_value": round(total_value, 2),
            "pnl_abs": round(total_pnl_abs, 2),
            "pnl_pct": round(total_pnl_pct, 2),
        },
    })
    print(f"wrote portfolio.json for {len(positions)} positions")


if __name__ == "__main__":
    main()

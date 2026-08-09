"""Evaluate config/alert_rules.json against the latest quotes.

Must run after fetch_and_analyze.py. On-page only — no external notifications,
no API keys. Tracks edge-triggered status (new / active / cleared) by comparing
against the previous docs/data/alerts.json so the UI can distinguish a rule that
just fired from one that's been active for a while.
"""
from common import CONFIG_DIR, DATA_DIR, load_json, save_json, utcnow_iso

CONDITIONS = {
    "price_above": lambda price, pct, value: price is not None and price > value,
    "price_below": lambda price, pct, value: price is not None and price < value,
    "pct_change_above": lambda price, pct, value: pct is not None and pct > value,
    "pct_change_below": lambda price, pct, value: pct is not None and pct < value,
}


def main():
    rules_cfg = load_json(CONFIG_DIR / "alert_rules.json", {"rules": []})
    quotes_doc = load_json(DATA_DIR / "quotes.json", {"quotes": {}})
    quotes = quotes_doc.get("quotes", {})
    prev_doc = load_json(DATA_DIR / "alerts.json", {"rules": []})
    prev_status = {r.get("id"): r for r in prev_doc.get("rules", [])}

    results = []
    now = utcnow_iso()

    for i, rule in enumerate(rules_cfg.get("rules", [])):
        rule_id = rule.get("label") or f"{rule['symbol']}-{rule['condition']}-{rule['value']}-{i}"
        symbol = rule["symbol"]
        condition = rule["condition"]
        value = rule["value"]

        quote = quotes.get(symbol)
        price = quote["price"] if quote else None
        pct = quote["pct_change"] if quote else None

        check = CONDITIONS.get(condition)
        triggered = bool(check(price, pct, value)) if check else False

        was = prev_status.get(rule_id)
        was_triggered = bool(was and was.get("triggered"))

        if triggered and not was_triggered:
            status = "new"
            since = now
        elif triggered and was_triggered:
            status = "active"
            since = was.get("since", now)
        elif not triggered and was_triggered:
            status = "cleared"
            since = now
        else:
            status = "inactive"
            since = None

        results.append({
            "id": rule_id,
            "label": rule.get("label", rule_id),
            "symbol": symbol,
            "condition": condition,
            "value": value,
            "current_price": price,
            "current_pct_change": pct,
            "triggered": triggered,
            "status": status,
            "since": since,
        })

    save_json(DATA_DIR / "alerts.json", {"updated": now, "rules": results})
    triggered_count = sum(1 for r in results if r["triggered"])
    print(f"wrote alerts.json: {triggered_count}/{len(results)} rules triggered")


if __name__ == "__main__":
    main()

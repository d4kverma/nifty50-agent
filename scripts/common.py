import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "docs" / "data"


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    with open(path) as f:
        return json.load(f)


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)


def load_watchlist():
    cfg = load_json(CONFIG_DIR / "watchlist.json", {"symbols": []})
    return cfg["symbols"]


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

import json, os
from datetime import datetime

class WatchlistManager:
    def __init__(self, path="watchlist.json"):
        self.path = path
        if not os.path.exists(path):
            with open(path,"w") as f: json.dump({"stocks":[]}, f)

    def _load(self):
        with open(self.path) as f: return json.load(f)
    def _save(self, d):
        with open(self.path,"w") as f: json.dump(d, f, indent=2, default=str)

    def add(self, symbol):
        sym = symbol.upper()
        if not sym.endswith(".NS"): sym += ".NS"
        d = self._load()
        if sym not in [s["symbol"] for s in d["stocks"]]:
            d["stocks"].append({"symbol":sym,
                "added":datetime.now().isoformat(),"last_trend":None})
            self._save(d); return f"Added {sym} to watchlist"
        return f"{sym} already on watchlist"

    def remove(self, symbol):
        sym = symbol.upper()
        if not sym.endswith(".NS"): sym += ".NS"
        d = self._load()
        d["stocks"] = [s for s in d["stocks"] if s["symbol"]!=sym]
        self._save(d); return f"Removed {sym}"

    def get_all(self): return self._load()["stocks"]

    def update_trend(self, symbol, new_trend):
        d = self._load()
        for s in d["stocks"]:
            if s["symbol"] == symbol:
                old = s.get("last_trend")
                s["last_trend"]    = new_trend
                s["trend_updated"] = datetime.now().isoformat()
                self._save(d)
                return old != new_trend and old is not None
        return False

    def list_formatted(self):
        stocks = self.get_all()
        if not stocks: return "Watchlist empty. Use /addwatch SYMBOL"
        lines = [f"WATCHLIST - {len(stocks)} stocks","---"]
        for s in stocks:
            t = s.get("last_trend") or "pending"
            e = "(+)" if "BULL" in t.upper() else "(-)" if "BEAR" in t.upper() else "(~)"
            lines.append(f"{e} {s['symbol']}  [{t}]")
        return "\n".join(lines)

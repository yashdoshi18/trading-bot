import json, os, uuid
from datetime import datetime

class TradeTracker:
    def __init__(self, path="trades.json"):
        self.path = path
        if not os.path.exists(path):
            self._save({"signals":[], "trades":[]})

    def _load(self):
        with open(self.path) as f: return json.load(f)
    def _save(self, d):
        with open(self.path,"w") as f: json.dump(d, f, indent=2, default=str)

    def log_signal(self, signal):
        d = self._load()
        signal.update({"id": str(uuid.uuid4())[:8],
                        "logged_at": datetime.now().isoformat()})
        d["signals"].append(signal)
        self._save(d)
        return signal["id"]

    def get_open_trades(self):
        return [t for t in self._load()["trades"] if t.get("status")=="ENTERED"]

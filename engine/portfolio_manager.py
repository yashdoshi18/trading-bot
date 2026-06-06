import json, os, logging
from datetime import datetime
log = logging.getLogger(__name__)

class PortfolioManager:
    def __init__(self, path="portfolio.json"):
        self.path = path
        if not os.path.exists(path):
            self._save({"holdings":[], "closed":[]})

    def _load(self):
        with open(self.path) as f: return json.load(f)
    def _save(self, d):
        with open(self.path,"w") as f: json.dump(d, f, indent=2, default=str)

    def add_holding(self, symbol, qty, price, targets=None, stoploss=None):
        sym = symbol.upper()
        if not sym.endswith(".NS"): sym += ".NS"
        d = self._load()
        h = {"symbol":sym, "qty":qty, "buy_price":float(price),
             "invested":round(qty*float(price),2),
             "bought_at":datetime.now().isoformat(),
             "targets":targets or [], "stoploss":stoploss,
             "t1_hit":False,"t2_hit":False,"t3_hit":False,"sl_hit":False,
             "current_price":float(price),"pnl_pct":0.0,
             "days_held":0,"status":"OPEN"}
        d["holdings"].append(h); self._save(d); return h

    def close_holding(self, symbol, qty, price):
        sym = symbol.upper()
        if not sym.endswith(".NS"): sym += ".NS"
        d = self._load()
        for h in d["holdings"]:
            if h["symbol"]==sym and h["status"]=="OPEN":
                h.update({"status":"CLOSED","exit_price":float(price),
                    "closed_at":datetime.now().isoformat(),
                    "final_pnl":round((float(price)-h["buy_price"])/h["buy_price"]*100,2)})
                break
        self._save(d)

    def check_portfolio(self, fetcher, ai_engine):
        d = self._load()
        for h in [x for x in d["holdings"] if x["status"]=="OPEN"]:
            try:
                df  = fetcher.get_daily(h["symbol"],"1mo")
                if df is None: continue
                cur = float(df["Close"].iloc[-1])
                buy = h["buy_price"]
                pnl = round((cur-buy)/buy*100,2)
                h.update({"current_price":round(cur,2),"pnl_pct":pnl,
                    "pnl_rs":round((cur-buy)*h["qty"],0),
                    "days_held":(datetime.now()-datetime.fromisoformat(h["bought_at"])).days})
                msg = None
                if h.get("stoploss") and cur<=h["stoploss"] and not h["sl_hit"]:
                    h["sl_hit"] = True
                    msg = (f"STOP LOSS HIT - {h['symbol']}\n"
                           f"SL: Rs.{h['stoploss']} | Now: Rs.{cur:.2f}\n"
                           f"Loss: {pnl:.1f}% | EXIT NOW")
                for i, tgt in enumerate(h.get("targets",[]), 1):
                    if not h.get(f"t{i}_hit") and cur>=tgt:
                        h[f"t{i}_hit"] = True
                        msg = (f"TARGET T{i} HIT - {h['symbol']}\n"
                               f"T{i}: Rs.{tgt} | Now: Rs.{cur:.2f}\n"
                               f"P&L: +{pnl:.1f}%")
                if not msg:
                    ev = ai_engine.evaluate_holding(h, cur)
                    if ev.get("action") in ["SELL","BOOK_PARTIAL"]:
                        msg = (f"AI ALERT - {h['symbol']}\n"
                               f"Action: {ev['action']}\n"
                               f"P&L: {pnl:+.1f}%\n"
                               f"Reason: {ev.get('reason','')}")
                if msg:
                    from engine.notifier import TelegramNotifier
                    from config import Config
                    TelegramNotifier(Config.TELEGRAM_TOKEN,
                                     Config.TELEGRAM_CHAT_ID).send_message(msg)
            except Exception as e:
                log.error(f"Portfolio {h['symbol']}: {e}")
        self._save(d)

    def get_holdings(self):
        return [h for h in self._load()["holdings"] if h["status"]=="OPEN"]

    def get_summary(self):
        hh = self.get_holdings()
        if not hh: return "No open positions.\nUse /bought SYMBOL QTY PRICE"
        inv = sum(h["invested"] for h in hh)
        cur = sum(h.get("current_price",h["buy_price"])*h["qty"] for h in hh)
        pnl = cur - inv
        lines = ["PORTFOLIO SUMMARY",
                 f"Positions : {len(hh)}",
                 f"Invested  : Rs.{inv:,.0f}",
                 f"Current   : Rs.{cur:,.0f}",
                 f"Total P&L : Rs.{pnl:+,.0f} ({pnl/inv*100:+.1f}%)", "---"]
        for h in hh:
            p = h.get("pnl_pct",0)
            lines.append(f"{'(+)' if p>=0 else '(-)'} {h['symbol']} "
                         f"{h['qty']}sh @ Rs.{h['buy_price']} "
                         f"Now Rs.{h.get('current_price','?')} {p:+.1f}%")
        return "\n".join(lines)

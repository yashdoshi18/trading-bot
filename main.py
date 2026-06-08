#!/usr/bin/env python3
"""
AI Trading Engine v4.0
KEY CHANGE: Always picks top 8 stocks every scan and sends
to Claude for BUY/SELL/HOLD - no more "no signals" problem.
"""
import schedule, time, logging, threading
from datetime import datetime
from engine.data_fetcher import DataFetcher
from engine.news_fetcher import NewsFetcher
from engine.technical_analyzer import TechnicalAnalyzer
from engine.candlestick_analyzer import CandlestickAnalyzer
from engine.fundamental_analyzer import FundamentalAnalyzer
from engine.ai_engine import AIEngine
from engine.trade_tracker import TradeTracker
from engine.portfolio_manager import PortfolioManager
from engine.watchlist_manager import WatchlistManager
from engine.morning_analysis import MorningAnalysis
from engine.notifier import TelegramNotifier
from telegram_bot import TelegramCommandBot
from config import Config

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()])
log = logging.getLogger(__name__)

class AITradingEngine:
    def __init__(self):
        cfg = Config()
        self.fetcher   = DataFetcher()
        self.news      = NewsFetcher()
        self.tech      = TechnicalAnalyzer()
        self.candle    = CandlestickAnalyzer()
        self.fundam    = FundamentalAnalyzer()
        self.ai        = AIEngine(cfg.ANTHROPIC_API_KEY)
        self.tracker   = TradeTracker("trades.json")
        self.portfolio = PortfolioManager("portfolio.json")
        self.watchlist = WatchlistManager("watchlist.json")
        self.morning   = MorningAnalysis()
        self.notifier  = TelegramNotifier(cfg.TELEGRAM_TOKEN, cfg.TELEGRAM_CHAT_ID)
        self.cfg       = cfg

    def _get_nifty_trend(self):
        try: return self.news.fetch_nifty_trend()
        except: return "NEUTRAL"

    def scan_tier(self, tier_name, symbols):
        log.info(f"=== {tier_name} SCAN ({len(symbols)} stocks) ===")
        ts          = datetime.now().strftime("%d %b %Y, %I:%M %p")
        nifty       = self._get_nifty_trend()
        user_syms   = [s["symbol"] for s in self.watchlist.get_all()]
        all_syms    = list(set(symbols + user_syms))

        # Step 1: Score ALL stocks
        scored = []
        for sym in all_syms:
            try:
                df15 = self.fetcher.get_intraday(sym, "15m", "5d")
                df1d = self.fetcher.get_daily(sym, "1y")
                df1w = self.fetcher.get_weekly(sym, "3y")
                if df1d is None: continue
                ti = self.tech.analyze(df15, "intraday") if df15 is not None else {}
                ts_sw = self.tech.analyze(df1d, "swing")
                tl = self.tech.analyze(df1w, "longterm") if df1w is not None else {}
                cd = self.candle.analyze(df1d)
                sc = (ti.get("score",0)*0.25 +
                      ts_sw.get("score",0)*0.45 +
                      tl.get("score",0)*0.30)
                scored.append({
                    "symbol": sym, "score": sc,
                    "ti": ti, "ts": ts_sw, "tl": tl, "cd": cd
                })
                log.info(f"{sym}: {sc:.1f}")
            except Exception as e:
                log.error(f"Score {sym}: {e}")

        if not scored:
            self.notifier.send_message(f"Scan error - no data fetched. {ts}")
            return []

        # Step 2: Always pick TOP 6 bullish + TOP 2 bearish
        scored.sort(key=lambda x: x["score"], reverse=True)
        bullish = [s for s in scored if s["score"] > 0][:6]
        bearish = [s for s in scored if s["score"] < 0][-2:]
        candidates = bullish + bearish
        if not candidates:
            candidates = scored[:8]  # fallback: just take top 8

        log.info(f"Sending {len(candidates)} stocks to AI analysis")

        # Step 3: Send ALL candidates to Claude AI
        results = []
        for item in candidates:
            try:
                sym    = item["symbol"]
                news   = self.news.fetch(sym)
                fundam = self.fundam.get(sym)
                result = self.ai.full_analysis(
                    sym, item["ti"], item["ts"], item["tl"],
                    item["cd"], fundam, news, item["score"], nifty)
                if result:
                    result["raw_score"] = round(item["score"], 1)
                    results.append(result)
                    if result.get("action") != "HOLD":
                        self.tracker.log_signal(result)
            except Exception as e:
                log.error(f"AI {item['symbol']}: {e}")

        # Step 4: Check watchlist trend changes
        for s in self.watchlist.get_all():
            try:
                df  = self.fetcher.get_daily(s["symbol"], "3mo")
                if df is None: continue
                sig = self.tech.analyze(df, "swing")
                if self.watchlist.update_trend(s["symbol"], sig.get("trend","")):
                    self.notifier.send_message(
                        f"WATCHLIST ALERT\n"
                        f"{s['symbol']} trend changed to {sig.get('trend')}")
            except: pass

        # Step 5: Portfolio check
        self.portfolio.check_portfolio(self.fetcher, self.ai)

        # Step 6: Always send full report - no hiding
        ts_now = datetime.now().strftime("%d %b %Y, %I:%M %p")
        self.notifier.send_full_report(results, ts_now, tier_name, nifty,
                                        len(all_syms))
        log.info(f"{tier_name} done. {len(results)} stocks analysed.")
        return results

    def tier1_scan(self): self.scan_tier("TIER1", self.cfg.TIER1)
    def tier2_scan(self): self.scan_tier("TIER2", self.cfg.TIER2)
    def tier3_scan(self): self.scan_tier("TIER3", self.cfg.TIER3)

    def start(self):
        log.info("v4.0 starting...")
        self.notifier.send_message(
            "AI TRADING BOT v4.0 ONLINE\n"
            "Every scan now gives TOP stock picks\n"
            "No more no-signal messages!\n"
            "Morning briefing: 9:15 AM IST\n"
            "Tier 1 scan: every 2.5h\n"
            "Tier 2 scan: 4 PM daily\n"
            "News alerts: every 30 min\n"
            "Send /help for commands")

        bot = TelegramCommandBot(
            self.ai, self.portfolio,
            self.watchlist, self.notifier, self.morning)
        threading.Thread(target=bot.start_polling, daemon=True).start()

        schedule.every().day.at("09:15").do(self.morning.run)
        schedule.every(150).minutes.do(self.tier1_scan)
        schedule.every().day.at("16:00").do(self.tier2_scan)
        schedule.every().friday.at("16:30").do(self.tier3_scan)

        self.tier1_scan()

        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    AITradingEngine().start()

#!/usr/bin/env python3
# AI Trading Engine v5.0 - Complete
import schedule, time, logging, threading
from datetime import datetime
from engine.data_fetcher import DataFetcher
from engine.news_fetcher import NewsFetcher
from engine.news_scanner import NewsScanner
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
        self.news_scan = NewsScanner(portfolio_manager=self.portfolio)
        self.cfg       = cfg

    def _nifty(self):
        try: return self.news.fetch_nifty_trend()
        except: return "NEUTRAL"

    def _analyze_stock(self, symbol, nifty="NEUTRAL"):
        df15 = self.fetcher.get_intraday(symbol, "15m", "5d")
        df1d = self.fetcher.get_daily(symbol, "1y")
        df1w = self.fetcher.get_weekly(symbol, "3y")
        if df1d is None: return None, 0
        ti = self.tech.analyze(df15, "intraday") if df15 is not None else {}
        ts = self.tech.analyze(df1d, "swing")
        tl = self.tech.analyze(df1w, "longterm") if df1w is not None else {}
        cd = self.candle.analyze(df1d)
        sc = ti.get("score",0)*0.25 + ts.get("score",0)*0.45 + tl.get("score",0)*0.30
        news   = self.news.fetch(symbol)
        fundam = self.fundam.get(symbol)
        result = self.ai.full_analysis(symbol, ti, ts, tl, cd, fundam, news, sc, nifty)
        if result: result["raw_score"] = round(sc, 1)
        return result, sc

    def scan_tier(self, tier_name, symbols):
        log.info(f"=== {tier_name} ({len(symbols)} stocks) ===")
        nifty     = self._nifty()
        user_syms = [s["symbol"] for s in self.watchlist.get_all()]
        all_syms  = list(set(symbols + user_syms))
        scored    = []

        for sym in all_syms:
            try:
                df15 = self.fetcher.get_intraday(sym, "15m", "5d")
                df1d = self.fetcher.get_daily(sym, "1y")
                df1w = self.fetcher.get_weekly(sym, "3y")
                if df1d is None: continue
                ti   = self.tech.analyze(df15, "intraday") if df15 is not None else {}
                tsw  = self.tech.analyze(df1d, "swing")
                tl   = self.tech.analyze(df1w, "longterm") if df1w is not None else {}
                cd   = self.candle.analyze(df1d)
                sc   = ti.get("score",0)*0.25 + tsw.get("score",0)*0.45 + tl.get("score",0)*0.30
                scored.append({"symbol":sym,"score":sc,"ti":ti,"ts":tsw,"tl":tl,"cd":cd})
                log.info(f"{sym}: {sc:.1f} | {cd.get('bias','?')} | patterns: {cd.get('count',0)}")
            except Exception as e:
                log.error(f"Score {sym}: {e}")

        scored.sort(key=lambda x: x["score"], reverse=True)
        bullish = [s for s in scored if s["score"] > 0][:6]
        bearish = [s for s in scored if s["score"] < 0][-2:]
        cands   = bullish + bearish
        if not cands: cands = scored[:8]

        results = []
        for item in cands:
            try:
                sym    = item["symbol"]
                news   = self.news.fetch(sym)
                fundam = self.fundam.get(sym)
                r = self.ai.full_analysis(
                    sym, item["ti"], item["ts"], item["tl"],
                    item["cd"], fundam, news, item["score"], nifty)
                if r:
                    r["raw_score"] = round(item["score"], 1)
                    results.append(r)
                    if r.get("action") != "HOLD":
                        self.tracker.log_signal(r)
            except Exception as e:
                log.error(f"AI {item['symbol']}: {e}")

        for s in self.watchlist.get_all():
            try:
                df = self.fetcher.get_daily(s["symbol"], "3mo")
                if df is None: continue
                sig = self.tech.analyze(df, "swing")
                if self.watchlist.update_trend(s["symbol"], sig.get("trend","")):
                    self.notifier.send_message(
                        f"WATCHLIST TREND CHANGE\n{s['symbol']}: now {sig.get('trend')}")
            except: pass

        self.portfolio.check_portfolio(self.fetcher, self.ai)
        ts = datetime.now().strftime("%d %b %Y, %I:%M %p")
        self.notifier.send_full_report(results, ts, tier_name, nifty, len(all_syms))
        return results

    def news_alert_scan(self):
        log.info("News alert scan...")
        nifty     = self._nifty()
        triggered = self.news_scan.scan_and_get_triggers()
        if not triggered:
            log.info("No news triggers"); return
        for symbol, triggers in triggered.items():
            try:
                price = self.news_scan._get_current_price(symbol)
                if not price: continue
                result, sc = self._analyze_stock(symbol, nifty)
                if self.news_scan.is_in_portfolio(symbol):
                    if result and result.get("action") == "BUY":
                        result["action"] = "HOLD"
                        result["reasoning"] = "You own this. " + result.get("reasoning","")
                msg = self.news_scan.format_news_alert(symbol, triggers, result, price)
                self.notifier.send_message(msg)
            except Exception as e:
                log.error(f"News alert {symbol}: {e}")

    def tier1_scan(self): self.scan_tier("TIER1", self.cfg.TIER1)
    def tier2_scan(self): self.scan_tier("TIER2", self.cfg.TIER2)
    def tier3_scan(self): self.scan_tier("TIER3", self.cfg.TIER3)

    def start(self):
        log.info("v5.0 starting...")
        self.notifier.send_message(
            "AI TRADING BOT v5.0 ONLINE\n"
            "14 technical indicators\n"
            "25+ candlestick patterns\n"
            "15 news sources every 30 min\n"
            "150+ NSE companies tracked\n"
            "Morning briefing: 9:15 AM IST")
        bot = TelegramCommandBot(
            self.ai, self.portfolio, self.watchlist, self.notifier, self.morning)
        threading.Thread(target=bot.start_polling, daemon=True).start()
        schedule.every().day.at("09:15").do(self.morning.run)
        schedule.every(150).minutes.do(self.tier1_scan)
        schedule.every().day.at("16:00").do(self.tier2_scan)
        schedule.every().tuesday.at("16:30").do(self.tier3_scan)
        schedule.every().thursday.at("16:30").do(self.tier3_scan)
        schedule.every(30).minutes.do(self.news_alert_scan)
        self.tier1_scan()
        self.news_alert_scan()
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    AITradingEngine().start()

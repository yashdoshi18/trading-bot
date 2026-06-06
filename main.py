#!/usr/bin/env python3
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

    def full_scan(self):
        ts = datetime.now().strftime("%d %b %Y, %I:%M %p")
        self.portfolio.check_portfolio(self.fetcher, self.ai)
        all_syms = list(set(self.cfg.WATCHLIST +
                            [s["symbol"] for s in self.watchlist.get_all()]))
        signals = []
        for sym in all_syms:
            try:
                r = self._analyze(sym)
                if r and r.get("action") != "HOLD":
                    signals.append(r)
                    self.tracker.log_signal(r)
            except Exception as e:
                log.error(f"{sym}: {e}")
        for s in self.watchlist.get_all():
            try:
                df  = self.fetcher.get_daily(s["symbol"], "3mo")
                sig = self.tech.analyze(df, "swing")
                if self.watchlist.update_trend(s["symbol"], sig.get("trend", "")):
                    self.notifier.send_message(
                        f"WATCHLIST ALERT\n{s['symbol']} trend: {sig.get('trend')}")
            except:
                pass
        if signals:
            self.notifier.send_scan_summary(signals, ts)
        else:
            self.notifier.send_message(f"Scan done - {ts}\nNo strong signals.")
        log.info(f"Scan done. {len(signals)} signals.")

    def _analyze(self, symbol):
        df15 = self.fetcher.get_intraday(symbol, "15m", "5d")
        df1d = self.fetcher.get_daily(symbol, "1y")
        df1w = self.fetcher.get_weekly(symbol, "3y")
        if df1d is None:
            return None
        ti = self.tech.analyze(df15, "intraday") if df15 is not None else {}
        ts = self.tech.analyze(df1d, "swing")
        tl = self.tech.analyze(df1w, "longterm") if df1w is not None else {}
        cd = self.candle.analyze(df1d)
        sc = (ti.get("score",0)*0.25 + ts.get("score",0)*0.45
              + tl.get("score",0)*0.30)
        if abs(sc) < self.cfg.MIN_SCORE:
            return None
        return self.ai.full_analysis(symbol, ti, ts, tl, cd,
                                     self.fundam.get(symbol),
                                     self.news.fetch(symbol), sc)

    def start(self):
        self.notifier.send_message(
            "AI TRADING BOT v3 ONLINE\n"
            "Morning briefing: 9:15 AM daily\n"
            "Full scans: every 2.5 hours\n"
            "Send /help for all commands")
        bot = TelegramCommandBot(self.ai, self.portfolio,
                                  self.watchlist, self.notifier, self.morning)
        threading.Thread(target=bot.start_polling, daemon=True).start()
        schedule.every().day.at("09:15").do(self.morning.run)
        schedule.every(150).minutes.do(self.full_scan)
        schedule.every().day.at("16:30").do(self.full_scan)
        self.full_scan()
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    AITradingEngine().start()

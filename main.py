#!/usr/bin/env python3
"""
AI Trading Engine v3.1
Tiered scanning: 200+ NSE stocks
Tier 1 (top 80): every 2.5h
Tier 2 (mid caps 100+): daily EOD
Tier 3 (small caps): weekly Sunday
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
        """Market filter — only go long if Nifty is not strongly bearish"""
        try:
            return self.news.fetch_nifty_trend()
        except:
            return "NEUTRAL"

    def scan_tier(self, tier_name, symbols, notify_summary=True):
        """Scan a list of symbols and return signals"""
        log.info(f"=== SCANNING {tier_name} ({len(symbols)} stocks) ===")

        # Market filter
        nifty_trend = self._get_nifty_trend()
        log.info(f"Nifty trend: {nifty_trend}")

        # Also include user watchlist in every scan
        user_watchlist = [s["symbol"] for s in self.watchlist.get_all()]
        all_syms = list(set(symbols + user_watchlist))

        signals = []
        for sym in all_syms:
            try:
                result = self._analyze(sym, nifty_trend)
                if result and result.get("action") != "HOLD":
                    signals.append(result)
                    self.tracker.log_signal(result)
            except Exception as e:
                log.error(f"{sym}: {e}")

        # Check watchlist trend changes
        for s in self.watchlist.get_all():
            try:
                df  = self.fetcher.get_daily(s["symbol"], "3mo")
                if df is None: continue
                sig = self.tech.analyze(df, "swing")
                if self.watchlist.update_trend(s["symbol"], sig.get("trend","")):
                    self.notifier.send_message(
                        f"WATCHLIST ALERT\n"
                        f"{s['symbol']} trend changed to {sig.get('trend')}")
            except:
                pass

        # Check portfolio
        self.portfolio.check_portfolio(self.fetcher, self.ai)

        ts = datetime.now().strftime("%d %b %Y, %I:%M %p")
        if notify_summary:
            if signals:
                self.notifier.send_scan_summary(signals, ts, tier_name)
            else:
                self.notifier.send_message(
                    f"Scan done ({tier_name}) - {ts}\n"
                    f"Scanned {len(all_syms)} stocks\n"
                    f"Nifty: {nifty_trend}\n"
                    f"No strong signals.")

        log.info(f"{tier_name} done. {len(signals)} signals from {len(all_syms)} stocks.")
        return signals

    def tier1_scan(self):
        """Top 80 stocks — runs every 2.5 hours"""
        self.scan_tier("TIER1 (Top Stocks)", self.cfg.TIER1)

    def tier2_scan(self):
        """Mid cap 100+ stocks — runs daily at 4 PM"""
        self.scan_tier("TIER2 (Mid Caps)", self.cfg.TIER2)

    def tier3_scan(self):
        """Small caps — runs weekly Sunday 8 PM"""
        self.scan_tier("TIER3 (Small Caps)", self.cfg.TIER3, notify_summary=True)

    def full_market_scan(self):
        """Full scan of all tiers — runs Sunday evening"""
        log.info("=== FULL MARKET SCAN ALL TIERS ===")
        all_signals = []
        all_signals += self.scan_tier("TIER1", self.cfg.TIER1, notify_summary=False)
        all_signals += self.scan_tier("TIER2", self.cfg.TIER2, notify_summary=False)
        all_signals += self.scan_tier("TIER3", self.cfg.TIER3, notify_summary=False)

        ts = datetime.now().strftime("%d %b %Y, %I:%M %p")
        total = len(self.cfg.get_all_stocks())
        self.notifier.send_message(
            f"FULL MARKET SCAN COMPLETE\n"
            f"{ts}\n"
            f"Scanned {total}+ NSE stocks\n"
            f"Total signals: {len(all_signals)}")

        if all_signals:
            self.notifier.send_scan_summary(all_signals, ts, "FULL MARKET")

    def _analyze(self, symbol, nifty_trend="NEUTRAL"):
        df15 = self.fetcher.get_intraday(symbol, "15m", "5d")
        df1d = self.fetcher.get_daily(symbol, "1y")
        df1w = self.fetcher.get_weekly(symbol, "3y")
        if df1d is None:
            return None

        ti = self.tech.analyze(df15, "intraday") if df15 is not None else {}
        ts = self.tech.analyze(df1d, "swing")
        tl = self.tech.analyze(df1w, "longterm") if df1w is not None else {}
        cd = self.candle.analyze(df1d)

        sc = (ti.get("score",0)*0.25 +
              ts.get("score",0)*0.45 +
              tl.get("score",0)*0.30)

        # Market filter: if Nifty strongly bearish, raise threshold for BUY signals
        threshold = self.cfg.MIN_SCORE
        if nifty_trend == "BEARISH":
            threshold = self.cfg.MIN_SCORE + 1.5
            log.info(f"Nifty bearish — raising threshold to {threshold}")

        if abs(sc) < threshold:
            return None

        return self.ai.full_analysis(
            symbol, ti, ts, tl, cd,
            self.fundam.get(symbol),
            self.news.fetch(symbol),
            sc, nifty_trend
        )

    def start(self):
        log.info("AI Trading Engine v3.1 starting...")
        self.notifier.send_message(
            "AI TRADING BOT v3.1 ONLINE\n"
            "Scanning 200+ NSE stocks\n"
            "Tier 1 (80 top stocks): every 2.5h\n"
            "Tier 2 (100 mid caps): daily 4 PM\n"
            "Tier 3 (small caps): weekly Sunday\n"
            "Morning briefing: 9:15 AM daily IST\n"
            "Send /help for all commands")

        # Start Telegram command bot in background thread
        bot = TelegramCommandBot(
            self.ai, self.portfolio,
            self.watchlist, self.notifier, self.morning)
        threading.Thread(target=bot.start_polling, daemon=True).start()
        log.info("Telegram command bot started")

        # 9:15 AM IST = 03:45 UTC
        schedule.every().day.at("09:15").do(self.morning.run)

        # Tier 1: every 2.5 hours
        schedule.every(150).minutes.do(self.tier1_scan)

        # Tier 2: daily EOD 4 PM IST = 10:30 UTC
        schedule.every().day.at("16:00").do(self.tier2_scan)

        # Tier 3 + Full scan: Sunday 8 PM IST = 14:30 UTC
        schedule.every().sunday.at("20:00").do(self.full_market_scan)

        # Run Tier 1 immediately on startup
        self.tier1_scan()

        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    AITradingEngine().start()

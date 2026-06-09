#!/usr/bin/env python3
"""
AI Trading Engine v5.0
Complete signal flow:
1. Volume spike + candle trigger → news check → full analysis → signal
2. News trigger → stock extraction → full analysis → buy/sell/hold
3. Portfolio monitoring → sell/hold signals when targets/SL hit
4. Regular tier scans → always top N signals
"""
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

    def _get_nifty_trend(self):
        try: return self.news.fetch_nifty_trend()
        except: return "NEUTRAL"

    def _analyze_stock(self, symbol, nifty_trend="NEUTRAL"):
        """Full analysis pipeline for one stock"""
        df15 = self.fetcher.get_intraday(symbol,"15m","5d")
        df1d = self.fetcher.get_daily(symbol,"1y")
        df1w = self.fetcher.get_weekly(symbol,"3y")
        if df1d is None: return None, 0

        ti = self.tech.analyze(df15,"intraday") if df15 is not None else {}
        ts = self.tech.analyze(df1d,"swing")
        tl = self.tech.analyze(df1w,"longterm") if df1w is not None else {}
        cd = self.candle.analyze(df1d)
        sc = (ti.get("score",0)*0.25 +
              ts.get("score",0)*0.45 +
              tl.get("score",0)*0.30)

        news   = self.news.fetch(symbol)
        fundam = self.fundam.get(symbol)
        result = self.ai.full_analysis(
            symbol,ti,ts,tl,cd,fundam,news,sc,nifty_trend)
        if result:
            result["raw_score"] = round(sc,1)
        return result, sc

    def scan_tier(self, tier_name, symbols):
        """Main tier scan - always returns top signals"""
        log.info(f"=== {tier_name} ({len(symbols)} stocks) ===")
        ts    = datetime.now().strftime("%d %b %Y, %I:%M %p")
        nifty = self._get_nifty_trend()

        user_syms = [s["symbol"] for s in self.watchlist.get_all()]
        all_syms  = list(set(symbols + user_syms))

        # Score all stocks first (fast - no AI)
        scored = []
        for sym in all_syms:
            try:
                df15 = self.fetcher.get_intraday(sym,"15m","5d")
                df1d = self.fetcher.get_daily(sym,"1y")
                df1w = self.fetcher.get_weekly(sym,"3y")
                if df1d is None: continue
                ti = self.tech.analyze(df15,"intraday") if df15 is not None else {}
                ts_sw = self.tech.analyze(df1d,"swing")
                tl = self.tech.analyze(df1w,"longterm") if df1w is not None else {}
                cd = self.candle.analyze(df1d)
                sc = (ti.get("score",0)*0.25 +
                      ts_sw.get("score",0)*0.45 +
                      tl.get("score",0)*0.30)
                scored.append({
                    "symbol":sym,"score":sc,
                    "ti":ti,"ts":ts_sw,"tl":tl,"cd":cd
                })
                log.info(f"{sym}: {sc:.1f} | candle: {cd.get('bias','?')} | "
                         f"patterns: {cd.get('count',0)}")
            except Exception as e:
                log.error(f"Score {sym}: {e}")

        # Always pick top 6 bullish + top 2 bearish
        scored.sort(key=lambda x: x["score"], reverse=True)
        bullish = [s for s in scored if s["score"]>0][:6]
        bearish = [s for s in scored if s["score"]<0][-2:]
        cands   = bullish + bearish
        if not cands: cands = scored[:8]

        # Full AI analysis for all candidates
        results = []
        for item in cands:
            try:
                sym    = item["symbol"]
                news   = self.news.fetch(sym)
                fundam = self.fundam.get(sym)
                result = self.ai.full_analysis(
                    sym,item["ti"],item["ts"],item["tl"],
                    item["cd"],fundam,news,item["score"],nifty)
                if result:
                    result["raw_score"] = round(item["score"],1)
                    results.append(result)
                    if result.get("action") != "HOLD":
                        self.tracker.log_signal(result)
            except Exception as e:
                log.error(f"AI {item['symbol']}: {e}")

        # Watchlist trend changes
        for s in self.watchlist.get_all():
            try:
                df  = self.fetcher.get_daily(s["symbol"],"3mo")
                if df is None: continue
                sig = self.tech.analyze(df,"swing")
                if self.watchlist.update_trend(s["symbol"],sig.get("trend","")):
                    self.notifier.send_message(
                        f"WATCHLIST TREND CHANGE\n"
                        f"{s['symbol']}: now {sig.get('trend')}")
            except: pass

        # Portfolio monitoring
        self.portfolio.check_portfolio(self.fetcher, self.ai)

        # Send full report
        ts_now = datetime.now().strftime("%d %b %Y, %I:%M %p")
        self.notifier.send_full_report(
            results, ts_now, tier_name, nifty, len(all_syms))
        return results

    def news_alert_scan(self):
        """
        News-triggered scan:
        1. Scan all news sources
        2. Extract triggered stocks (any NSE company)
        3. Full analysis on each
        4. Portfolio check: if owned → SELL/HOLD only
        5. Send alerts
        """
        log.info("News alert scan running...")
        nifty    = self._get_nifty_trend()
        triggered = self.news_scan.scan_and_get_triggers()

        if not triggered:
            log.info("No news triggers found")
            return

        for symbol, triggers in triggered.items():
            try:
                # Get current price
                price = self.news_scan._get_current_price(symbol)
                if not price:
                    log.warning(f"No price for {symbol}")
                    continue

                # Full technical + AI analysis
                result, sc = self._analyze_stock(symbol, nifty)

                # If in portfolio and AI says BUY → change to HOLD
                if self.news_scan.is_in_portfolio(symbol):
                    if result and result.get("action") == "BUY":
                        result["action"] = "HOLD"
                        result["reasoning"] = (
                            "You already own this stock. "
                            + result.get("reasoning",""))

                # Format and send alert
                alert_msg = self.news_scan.format_news_alert(
                    symbol, triggers, result, price)
                self.notifier.send_message(alert_msg)
                log.info(f"News alert sent: {symbol}")

            except Exception as e:
                log.error(f"News alert {symbol}: {e}")

    def tier1_scan(self): self.scan_tier("TIER1", self.cfg.TIER1)
    def tier2_scan(self): self.scan_tier("TIER2", self.cfg.TIER2)
    def tier3_scan(self): self.scan_tier("TIER3", self.cfg.TIER3)

    def start(self):
        log.info("AI Trading Engine v5.0 starting...")
        self.notifier.send_message(
            "AI TRADING BOT v5.0 ONLINE\n"
            "Full signal flow active:\n"
            "- Volume + candle triggers\n"
            "- News from 15 sources every 30 min\n"
            "- 150+ NSE companies tracked\n"
            "- Buy signals for new stocks\n"
            "- Hold/Sell for portfolio stocks\n"
            "- 25+ candlestick patterns\n"
            "Morning briefing: 9:15 AM IST")

        bot = TelegramCommandBot(
            self.ai, self.portfolio,
            self.watchlist, self.notifier, self.morning)
        threading.Thread(target=bot.start_polling, daemon=True).start()

        # Schedules (all IST - TZ=Asia/Kolkata in Railway)
        schedule.every().day.at("09:15").do(self.morning.run)
        schedule.every(150).minutes.do(self.tier1_scan)
        schedule.every().day.at("16:00").do(self.tier2_scan)
        schedule.every().friday.at("16:30").do(self.tier3_scan)
        schedule.every(30).minutes.do(self.news_alert_scan)

        # Run immediately
        self.tier1_scan()
        self.news_alert_scan()

        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    AITradingEngine().start()

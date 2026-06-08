import logging
from datetime import datetime
from engine.data_fetcher import DataFetcher
from engine.news_fetcher import NewsFetcher
from engine.technical_analyzer import TechnicalAnalyzer
from engine.candlestick_analyzer import CandlestickAnalyzer
from engine.ai_engine import AIEngine
from engine.notifier import TelegramNotifier
from config import Config

log = logging.getLogger(__name__)

class MorningAnalysis:
    def __init__(self):
        cfg = Config()
        self.fetcher  = DataFetcher()
        self.news     = NewsFetcher()
        self.tech     = TechnicalAnalyzer()
        self.candle   = CandlestickAnalyzer()
        self.ai       = AIEngine(cfg.ANTHROPIC_API_KEY)
        self.notifier = TelegramNotifier(cfg.TELEGRAM_TOKEN, cfg.TELEGRAM_CHAT_ID)
        self.cfg      = cfg

    def run(self):
        ds          = datetime.now().strftime("%d %b %Y")
        nifty_trend = self.news.fetch_nifty_trend()
        log.info(f"Morning analysis: {ds} | Nifty: {nifty_trend}")

        self.notifier.send_message(
            f"MORNING BRIEFING - {ds}\n"
            f"Nifty trend: {nifty_trend}\n"
            "Analysing top 30 stocks...\n"
            "Results in 5-8 minutes")

        mkt      = self.news.fetch_market_sentiment()
        intraday = []
        swing    = []
        longterm = []
        scanned  = 0
        scored   = []

        # Score all stocks first
        for sym in self.cfg.TIER1[:30]:
            try:
                df15 = self.fetcher.get_intraday(sym, "15m", "2d")
                df1d = self.fetcher.get_daily(sym, "3mo")
                if df1d is None: continue
                tech   = self.tech.analyze(df1d, "swing")
                candle = self.candle.analyze(df1d)
                news   = self.news.fetch(sym)
                gap    = 0.0
                if df15 is not None and len(df15)>0 and len(df1d)>1:
                    gap = round(
                        (float(df15["Open"].iloc[0])-float(df1d["Close"].iloc[-2]))
                        /float(df1d["Close"].iloc[-2])*100, 2)
                sc = tech.get("score",0)
                scored.append({
                    "symbol":sym,"score":sc,"tech":tech,
                    "candle":candle,"news":news,"gap":gap
                })
                scanned += 1
            except Exception as e:
                log.error(f"Morning score {sym}: {e}")

        # Always take top 8 by absolute score
        scored.sort(key=lambda x: abs(x["score"]), reverse=True)
        top_stocks = scored[:8]

        # Get AI picks for all top stocks
        for item in top_stocks:
            try:
                pick = self.ai.morning_pick({
                    "symbol":      item["symbol"],
                    "tech":        item["tech"],
                    "candle":      item["candle"],
                    "news":        item["news"],
                    "gap_pct":     item["gap"],
                    "nifty_trend": nifty_trend
                })
                if pick.get("action","SKIP") == "SKIP":
                    continue
                tt = pick.get("trade_type","SWING")
                if   tt=="INTRADAY": intraday.append(pick)
                elif tt=="SWING":    swing.append(pick)
                else:                longterm.append(pick)
            except Exception as e:
                log.error(f"Morning pick {item['symbol']}: {e}")

        intraday.sort(key=lambda x: x.get("conviction",0), reverse=True)
        swing.sort(   key=lambda x: x.get("conviction",0), reverse=True)

        total = len(intraday)+len(swing)+len(longterm)

        # Always send full report
        self.notifier.send_morning_report(
            intraday[:3], swing[:3], longterm[:2], mkt, ds)

        # Summary
        self.notifier.send_message(
            f"MORNING BRIEFING COMPLETE - {ds}\n"
            f"Scanned: {scanned} stocks | Nifty: {nifty_trend}\n"
            f"Intraday picks: {len(intraday)}\n"
            f"Swing picks: {len(swing)}\n"
            f"Longterm picks: {len(longterm)}\n"
            f"Total picks: {total}\n"
            f"Good trading today!")

        log.info(f"Morning done. {total} picks from {scanned} stocks.")

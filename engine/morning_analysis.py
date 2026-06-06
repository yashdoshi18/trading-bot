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
        ds = datetime.now().strftime("%d %b %Y")
        self.notifier.send_message(
            f"MORNING BRIEFING - {ds}\n"
            "Scanning candles, technicals and news...\n"
            "Results in 2 minutes")
        mkt = self.news.fetch_market_sentiment()
        intraday, swing, longterm = [], [], []
        for sym in self.cfg.WATCHLIST[:25]:
            try:
                df15 = self.fetcher.get_intraday(sym,"15m","2d")
                df1d = self.fetcher.get_daily(sym,"3mo")
                if df1d is None: continue
                tech   = self.tech.analyze(df1d,"swing")
                candle = self.candle.analyze(df1d)
                news   = self.news.fetch(sym)
                gap    = 0.0
                if df15 is not None and len(df15)>0 and len(df1d)>1:
                    gap = round((float(df15["Open"].iloc[0])
                                 - float(df1d["Close"].iloc[-2]))
                                / float(df1d["Close"].iloc[-2])*100, 2)
                pick = self.ai.morning_pick(
                    {"symbol":sym,"tech":tech,"candle":candle,
                     "news":news,"gap_pct":gap})
                if pick.get("action","SKIP") == "SKIP": continue
                tt = pick.get("trade_type","SWING")
                if   tt=="INTRADAY": intraday.append(pick)
                elif tt=="SWING":    swing.append(pick)
                else:                longterm.append(pick)
            except Exception as e:
                log.error(f"Morning {sym}: {e}")
        intraday.sort(key=lambda x: x.get("conviction",0), reverse=True)
        swing.sort(   key=lambda x: x.get("conviction",0), reverse=True)
        self.notifier.send_morning_report(
            intraday[:3], swing[:3], longterm[:2], mkt, ds)

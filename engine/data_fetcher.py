import yfinance as yf, logging
log = logging.getLogger(__name__)

class DataFetcher:
    def get_intraday(self, s, i="15m", p="5d"): return self._f(s, p, i)
    def get_daily(self, s, p="1y"):              return self._f(s, p, "1d")
    def get_weekly(self, s, p="3y"):             return self._f(s, p, "1wk")
    def _f(self, s, p, i):
        try:
            df = yf.Ticker(s).history(period=p, interval=i)
            df.dropna(inplace=True)
            return df if len(df) > 5 else None
        except Exception as e:
            log.error(f"Fetch {s}: {e}")
            return None

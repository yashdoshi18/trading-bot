import yfinance as yf, logging
log = logging.getLogger(__name__)

class FundamentalAnalyzer:
    def get(self, symbol):
        try:
            info = yf.Ticker(symbol).info
            cur  = info.get("currentPrice", 0)
            wh   = info.get("fiftyTwoWeekHigh")
            wl   = info.get("fiftyTwoWeekLow")
            return {
                "pe":      round(info.get("trailingPE",0) or 0, 1),
                "pb":      round(info.get("priceToBook",0) or 0, 2),
                "roe":     f"{round((info.get('returnOnEquity') or 0)*100,1)}%",
                "de":      round(info.get("debtToEquity",0) or 0, 2),
                "eps_g":   f"{round((info.get('earningsGrowth') or 0)*100,1)}%",
                "sector":  info.get("sector",""),
                "mktcap":  info.get("marketCap",0),
                "from_52h":f"{round((cur-wh)/wh*100,1)}%" if wh and cur else None,
                "from_52l":f"{round((cur-wl)/wl*100,1)}%" if wl and cur else None,
                "52h":     round(wh,2) if wh else None,
                "52l":     round(wl,2) if wl else None,
            }
        except Exception as e:
            log.warning(f"Fundamentals {symbol}: {e}")
            return {}

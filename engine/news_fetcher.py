import feedparser
import requests
from datetime import datetime, timedelta
import logging
log = logging.getLogger(__name__)

# 100% India-focused news feeds
INDIA_FEEDS = {
    "moneycontrol":   "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "mc_markets":     "https://www.moneycontrol.com/rss/marketreports.xml",
    "mc_results":     "https://www.moneycontrol.com/rss/results.xml",
    "economictimes":  "https://economictimes.indiatimes.com/markets/stocks/rss.cms",
    "et_markets":     "https://economictimes.indiatimes.com/markets/rss.cms",
    "et_results":     "https://economictimes.indiatimes.com/news/earnings/rss.cms",
    "livemint":       "https://www.livemint.com/rss/markets",
    "livemint_comp":  "https://www.livemint.com/rss/companies",
    "bizstandard":    "https://www.business-standard.com/rss/markets-106.rss",
    "bs_companies":   "https://www.business-standard.com/rss/companies-101.rss",
    "financialexp":   "https://www.financialexpress.com/market/feed/",
    "cnbctv18":       "https://www.cnbctv18.com/commonfeeds/v1/eng/rss/market.xml",
    "thehindubl":     "https://www.thehindubusinessline.com/markets/?service=rss",
}

# Indian market keywords to identify relevant news
INDIA_KEYWORDS = [
    "nifty", "sensex", "bse", "nse", "sebi", "rbi", "india",
    "rupee", "inr", "dalal street", "mumbai", "narendra modi",
    "budget", "gst", "fii", "dii", "ipo", "nse listed",
    "quarterly results", "q1", "q2", "q3", "q4", "earnings"
]

# Map ticker to common company name variations for better matching
COMPANY_NAMES = {
    "HDFCBANK": ["hdfc bank", "hdfcbank"],
    "ICICIBANK": ["icici bank", "icicibank"],
    "RELIANCE": ["reliance industries", "ril", "reliance"],
    "TCS": ["tata consultancy", "tcs"],
    "INFY": ["infosys", "infy"],
    "WIPRO": ["wipro"],
    "SBIN": ["sbi", "state bank", "sbi life"],
    "AXISBANK": ["axis bank", "axisbank"],
    "KOTAKBANK": ["kotak bank", "kotak mahindra bank"],
    "BAJFINANCE": ["bajaj finance", "bajaj fin"],
    "BAJAJFINSV": ["bajaj finserv"],
    "HINDUNILVR": ["hindustan unilever", "hul"],
    "ITC": ["itc limited", "itc ltd"],
    "BHARTIARTL": ["airtel", "bharti airtel"],
    "MARUTI": ["maruti suzuki", "maruti"],
    "SUNPHARMA": ["sun pharma", "sun pharmaceutical"],
    "DRREDDY": ["dr reddy", "dr. reddy"],
    "ADANIPORTS": ["adani ports", "adani"],
    "ADANIENT": ["adani enterprises", "adani group"],
    "TATASTEEL": ["tata steel"],
    "LARSEN": ["larsen & toubro", "l&t", "larsen"],
    "NTPC": ["ntpc", "national thermal"],
    "POWERGRID": ["power grid", "powergrid"],
    "ONGC": ["ongc", "oil and natural gas"],
    "COALINDIA": ["coal india", "coalindia"],
    "ZOMATO": ["zomato"],
    "DMART": ["dmart", "avenue supermarts", "d-mart"],
    "TITAN": ["titan company", "titan"],
    "ASIANPAINT": ["asian paints", "asian paint"],
    "ULTRACEMCO": ["ultratech cement", "ultratech"],
    "BAJAJ-AUTO": ["bajaj auto"],
    "EICHERMOT": ["eicher motors", "royal enfield"],
    "HEROMOTOCO": ["hero moto", "hero motocorp"],
}

class NewsFetcher:
    def __init__(self, max_age_h=10):
        self.max_age = timedelta(hours=max_age_h)

    def fetch(self, symbol, max_age_h=10):
        """Fetch India-specific news for a stock symbol"""
        # Get ticker without exchange suffix
        ticker = symbol.replace(".NS","").replace(".BO","").upper()

        # Build search terms
        search_terms = [ticker.lower()]
        if ticker in COMPANY_NAMES:
            search_terms.extend(COMPANY_NAMES[ticker])
        else:
            # fallback: lowercase ticker
            search_terms.append(ticker.lower().replace("-",""))

        cutoff = datetime.utcnow() - timedelta(hours=max_age_h)
        items  = []

        for src, url in INDIA_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for e in feed.entries[:40]:
                    title   = e.get("title","").lower()
                    summary = e.get("summary","").lower()
                    content = title + " " + summary

                    # Must match company name
                    if not any(term in content for term in search_terms):
                        continue

                    # Check age
                    pp = e.get("published_parsed")
                    if pp:
                        pub_dt = datetime(*pp[:6])
                        if pub_dt < cutoff:
                            continue

                    items.append({
                        "source":  src,
                        "title":   e.get("title",""),
                        "summary": e.get("summary","")[:250],
                        "url":     e.get("link",""),
                        "published": e.get("published","")
                    })
            except Exception as ex:
                log.warning(f"News fetch {src}: {ex}")

        # Deduplicate by title
        seen   = set()
        unique = []
        for item in items:
            t = item["title"][:60]
            if t not in seen:
                seen.add(t)
                unique.append(item)

        return unique[:8]

    def fetch_market_sentiment(self):
        """Fetch Indian market-wide sentiment — Nifty, Sensex, RBI, SEBI news"""
        headlines   = []
        nifty_news  = []
        result_news = []

        for src, url in INDIA_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for e in feed.entries[:15]:
                    title = e.get("title","")
                    tl    = title.lower()

                    # Market index news
                    if any(k in tl for k in ["nifty","sensex","bse","nse","market"]):
                        nifty_news.append(title)

                    # Results season news
                    if any(k in tl for k in ["results","earnings","quarterly","q1","q2","q3","q4","profit","revenue"]):
                        result_news.append(title)

                    # General India market
                    if any(k in tl for k in INDIA_KEYWORDS):
                        headlines.append(title)

            except Exception as ex:
                log.warning(f"Sentiment fetch {src}: {ex}")

        # Deduplicate
        def dedup(lst):
            seen = set(); out = []
            for x in lst:
                if x[:50] not in seen:
                    seen.add(x[:50]); out.append(x)
            return out

        return {
            "headlines":    dedup(headlines)[:6],
            "nifty_news":   dedup(nifty_news)[:4],
            "result_news":  dedup(result_news)[:4],
        }

    def fetch_nifty_trend(self):
        """Get Nifty 50 current trend as market filter"""
        try:
            import yfinance as yf
            nifty = yf.Ticker("^NSEI")
            df    = nifty.history(period="5d", interval="1d")
            if df is None or len(df) < 2:
                return "NEUTRAL"
            prev  = float(df["Close"].iloc[-2])
            curr  = float(df["Close"].iloc[-1])
            chg   = (curr - prev) / prev * 100
            if chg > 0.5:    return "BULLISH"
            elif chg < -0.5: return "BEARISH"
            else:            return "NEUTRAL"
        except Exception as e:
            log.warning(f"Nifty trend: {e}")
            return "NEUTRAL"


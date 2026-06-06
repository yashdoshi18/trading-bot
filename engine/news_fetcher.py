import feedparser
from datetime import datetime, timedelta
import logging
log = logging.getLogger(__name__)

FEEDS = {
    "moneycontrol": "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "economictimes": "https://economictimes.indiatimes.com/markets/stocks/rss.cms",
    "livemint":      "https://www.livemint.com/rss/markets",
    "bizstandard":   "https://www.business-standard.com/rss/markets-106.rss",
}

class NewsFetcher:
    def fetch(self, symbol, max_age_h=8):
        name   = symbol.replace(".NS","").replace(".BO","").lower()
        cutoff = datetime.utcnow() - timedelta(hours=max_age_h)
        items  = []
        for src, url in FEEDS.items():
            try:
                for e in feedparser.parse(url).entries[:30]:
                    title = e.get("title","")
                    if name not in title.lower(): continue
                    pp = e.get("published_parsed")
                    if pp and datetime(*pp[:6]) < cutoff: continue
                    items.append({"source":src,"title":title,
                        "url":e.get("link","")})
            except:
                pass
        return items[:8]

    def fetch_market_sentiment(self):
        kw = ["nifty","sensex","market","bse","nse"]
        hl = []
        for _, url in FEEDS.items():
            try:
                for e in feedparser.parse(url).entries[:10]:
                    if any(k in e.get("title","").lower() for k in kw):
                        hl.append(e.get("title",""))
            except:
                pass
        return {"headlines": hl[:6]}

"""
News Scanner Engine - Complete Rebuild
Flow:
1. Scans 15+ news sources every 30 min
2. Extracts stock names from any NSE/BSE company
3. Does full analysis on those stocks (not just top 50)
4. If stock in portfolio → only SELL/HOLD signals
5. If stock not in portfolio → BUY signals
6. Sends rich Telegram alert with full details
"""
import feedparser, logging, json, os, re
from datetime import datetime, timedelta
import yfinance as yf

log = logging.getLogger(__name__)

# ============================================================
# 15+ NEWS SOURCES
# ============================================================
NEWS_SOURCES = {
    "mc_top":       "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "mc_markets":   "https://www.moneycontrol.com/rss/marketreports.xml",
    "mc_results":   "https://www.moneycontrol.com/rss/results.xml",
    "mc_biz":       "https://www.moneycontrol.com/rss/business.xml",
    "et_markets":   "https://economictimes.indiatimes.com/markets/stocks/rss.cms",
    "et_earnings":  "https://economictimes.indiatimes.com/news/earnings/rss.cms",
    "et_industry":  "https://economictimes.indiatimes.com/industry/rss.cms",
    "et_economy":   "https://economictimes.indiatimes.com/news/economy/rss.cms",
    "livemint_mkt": "https://www.livemint.com/rss/markets",
    "livemint_co":  "https://www.livemint.com/rss/companies",
    "bs_markets":   "https://www.business-standard.com/rss/markets-106.rss",
    "bs_companies": "https://www.business-standard.com/rss/companies-101.rss",
    "bs_finance":   "https://www.business-standard.com/rss/finance-102.rss",
    "finexp":       "https://www.financialexpress.com/market/feed/",
    "cnbctv18":     "https://www.cnbctv18.com/commonfeeds/v1/eng/rss/market.xml",
}

# ============================================================
# TRIGGER CATEGORIES WITH KEYWORDS
# ============================================================
TRIGGERS = {
    "QUARTERLY_RESULTS": {
        "keywords": ["quarterly results","q1 results","q2 results","q3 results",
                     "q4 results","fy26 results","fy25 results","net profit",
                     "revenue up","revenue jumps","profit up","profit jumps",
                     "ebitda","earnings","beats estimate","misses estimate",
                     "record profit","all time high profit","strong results"],
        "strength": 5,
        "default_action": "BUY_OR_SELL"
    },
    "MERGER_ACQUISITION": {
        "keywords": ["merger","acquisition","acquires","takeover","amalgamation",
                     "buyout","strategic acquisition","open offer","delisting",
                     "all-stock deal","demerger","spin-off","splits"],
        "strength": 5,
        "default_action": "BUY"
    },
    "ORDER_WIN": {
        "keywords": ["order win","wins order","bagged order","receives order",
                     "work order","contract win","awarded contract","supply order",
                     "export order","defence order","railway order","government order",
                     "letter of intent","loi received","rs crore order","crore contract"],
        "strength": 5,
        "default_action": "BUY"
    },
    "BUYBACK": {
        "keywords": ["buyback","buy back","share repurchase","board approves buyback",
                     "buyback offer","open offer buyback"],
        "strength": 4,
        "default_action": "BUY"
    },
    "DIVIDEND": {
        "keywords": ["dividend declared","special dividend","interim dividend",
                     "final dividend","rs per share dividend","dividend announced"],
        "strength": 3,
        "default_action": "BUY"
    },
    "FII_DII_BUYING": {
        "keywords": ["fii buys","fii increases","promoter buys","promoter increases",
                     "bulk deal","block deal","institutional buying","lic buys",
                     "mutual fund buys","insider buying","promoter stake"],
        "strength": 4,
        "default_action": "BUY"
    },
    "52_WEEK_HIGH": {
        "keywords": ["52-week high","52 week high","all-time high","lifetime high",
                     "record high","new high","multi-year high"],
        "strength": 3,
        "default_action": "BUY"
    },
    "PRICE_TARGET_UPGRADE": {
        "keywords": ["target price raised","target upgraded","analyst upgrade",
                     "rating upgrade","overweight","strong buy recommendation",
                     "price target increased"],
        "strength": 3,
        "default_action": "BUY"
    },
    "NEGATIVE_NEWS": {
        "keywords": ["profit falls","profit drops","revenue falls","loss reported",
                     "fii sells","promoter sells","rating downgrade","target cut",
                     "debt concern","default","fraud","sebi notice","regulatory action",
                     "plant shutdown","strike","recall","penalty"],
        "strength": 4,
        "default_action": "SELL"
    },
    "EXPANSION_CAPEX": {
        "keywords": ["new plant","capacity expansion","capex","greenfield",
                     "new facility","expansion plan","investment plan",
                     "opens new","launches new product"],
        "strength": 3,
        "default_action": "BUY"
    },
    "FUNDRAISING": {
        "keywords": ["qip","rights issue","fpo","fundraise","raises funds",
                     "private placement","venture capital","series a","series b",
                     "ipo listing","gmp","grey market premium"],
        "strength": 3,
        "default_action": "BUY"
    },
}

# ============================================================
# COMPREHENSIVE NSE COMPANY MAP
# Company name variations → NSE symbol
# ============================================================
COMPANY_MAP = {
    # Banking
    "HDFCBANK.NS":   ["hdfc bank","hdfcbank","hdfc bank ltd"],
    "ICICIBANK.NS":  ["icici bank","icicibank"],
    "SBIN.NS":       ["state bank","sbi","sbi bank","state bank of india"],
    "AXISBANK.NS":   ["axis bank","axisbank"],
    "KOTAKBANK.NS":  ["kotak bank","kotak mahindra","kotak"],
    "INDUSINDBK.NS": ["indusind bank","indusind"],
    "BANDHANBNK.NS": ["bandhan bank","bandhan"],
    "FEDERALBNK.NS": ["federal bank","federalbank"],
    "IDFCFIRSTB.NS": ["idfc first","idfc bank"],
    "PNB.NS":        ["punjab national bank","pnb bank","pnb"],
    "BANKBARODA.NS": ["bank of baroda","bob bank"],
    "CANBK.NS":      ["canara bank","canara"],
    "AUBANK.NS":     ["au small finance","au bank","au sfb"],
    "RBLBANK.NS":    ["rbl bank","rbl"],
    # Finance
    "BAJFINANCE.NS": ["bajaj finance","bajaj fin"],
    "BAJAJFINSV.NS": ["bajaj finserv"],
    "HDFCLIFE.NS":   ["hdfc life","hdfc life insurance"],
    "SBILIFE.NS":    ["sbi life","sbi life insurance"],
    "CHOLAFIN.NS":   ["chola","cholamandalam"],
    "MUTHOOTFIN.NS": ["muthoot finance","muthoot"],
    "MANAPPURAM.NS": ["manappuram finance","manappuram"],
    # IT
    "TCS.NS":        ["tata consultancy","tcs","tata consulting"],
    "INFY.NS":       ["infosys","infy"],
    "WIPRO.NS":      ["wipro"],
    "HCLTECH.NS":    ["hcl tech","hcltech","hcl technologies"],
    "TECHM.NS":      ["tech mahindra","techm"],
    "LTIM.NS":       ["ltimindtree","lti mindtree","larsen toubro infotech"],
    "MPHASIS.NS":    ["mphasis"],
    "PERSISTENT.NS": ["persistent systems","persistent"],
    "COFORGE.NS":    ["coforge","niit technologies"],
    "TATAELXSI.NS":  ["tata elxsi"],
    "OFSS.NS":       ["oracle financial","ofss","oracle finserv"],
    "KPITTECH.NS":   ["kpit technologies","kpit"],
    # Auto
    "MARUTI.NS":     ["maruti suzuki","maruti","suzuki india"],
    "BAJAJ-AUTO.NS": ["bajaj auto","bajaj automobiles"],
    "EICHERMOT.NS":  ["eicher motors","royal enfield","eicher"],
    "HEROMOTOCO.NS": ["hero motocorp","hero honda","hero moto"],
    "M&M.NS":        ["mahindra","m&m","mahindra and mahindra"],
    "TVSMOTOR.NS":   ["tvs motor","tvs motors"],
    "ASHOKLEY.NS":   ["ashok leyland","ashokleyland"],
    # FMCG
    "HINDUNILVR.NS": ["hindustan unilever","hul","unilever india"],
    "ITC.NS":        ["itc ltd","itc limited","itc cigarettes"],
    "NESTLEIND.NS":  ["nestle india","nestle"],
    "BRITANNIA.NS":  ["britannia industries","britannia"],
    "DABUR.NS":      ["dabur india","dabur"],
    "MARICO.NS":     ["marico"],
    "GODREJCP.NS":   ["godrej consumer","godrej cp"],
    "COLPAL.NS":     ["colgate palmolive","colgate"],
    "TATACONSUM.NS": ["tata consumer","tata consumer products","tata tea"],
    # Pharma
    "SUNPHARMA.NS":  ["sun pharma","sun pharmaceutical"],
    "DRREDDY.NS":    ["dr reddy","dr. reddy","dr reddys"],
    "CIPLA.NS":      ["cipla"],
    "DIVISLAB.NS":   ["divi laboratories","divi labs","divislab"],
    "AUROPHARMA.NS": ["aurobindo pharma","aurobindo"],
    "TORNTPHARM.NS": ["torrent pharma","torrent pharmaceuticals"],
    "LUPIN.NS":      ["lupin limited","lupin pharma"],
    "ALKEM.NS":      ["alkem laboratories","alkem labs"],
    "BIOCON.NS":     ["biocon"],
    "GLENMARK.NS":   ["glenmark pharmaceuticals","glenmark"],
    "LAURUS.NS":     ["laurus labs","laurus laboratories"],
    "GRANULES.NS":   ["granules india","granules"],
    "IPCALAB.NS":    ["ipca laboratories","ipca labs"],
    # Energy & Oil
    "RELIANCE.NS":   ["reliance industries","ril","reliance jio","jio platforms"],
    "ONGC.NS":       ["ongc","oil and natural gas","oil natural gas"],
    "BPCL.NS":       ["bpcl","bharat petroleum"],
    "IOC.NS":        ["indian oil","ioc","indian oil corporation"],
    "GAIL.NS":       ["gail india","gail gas"],
    "HINDPETRO.NS":  ["hindustan petroleum","hpcl","hindpetro"],
    "IGL.NS":        ["indraprastha gas","igl"],
    "MGL.NS":        ["mahanagar gas","mgl"],
    "PETRONET.NS":   ["petronet lng","petronet"],
    # Metals & Mining
    "TATASTEEL.NS":  ["tata steel"],
    "JSWSTEEL.NS":   ["jsw steel","jsw"],
    "HINDALCO.NS":   ["hindalco","hindalco industries"],
    "VEDL.NS":       ["vedanta","vedl"],
    "COALINDIA.NS":  ["coal india","coalindia"],
    "NMDC.NS":       ["nmdc","national mineral"],
    "SAIL.NS":       ["sail","steel authority","steel authority india"],
    "JINDALSTEL.NS": ["jindal steel","jspl","jindal steel power"],
    # Infra & Construction
    "LARSEN.NS":     ["larsen toubro","l&t","larsen and toubro"],
    "ULTRACEMCO.NS": ["ultratech cement","ultratech"],
    "GRASIM.NS":     ["grasim industries","grasim"],
    "ACC.NS":        ["acc cement","acc ltd"],
    "AMBUJACEMENT.NS":["ambuja cements","ambuja cement"],
    "SHREECEM.NS":   ["shree cement","shree cements"],
    "DLF.NS":        ["dlf limited","dlf realty"],
    "GODREJPROP.NS": ["godrej properties","godrej prop"],
    "PRESTIGE.NS":   ["prestige estates","prestige group"],
    # Power & Utilities
    "NTPC.NS":       ["ntpc","national thermal power"],
    "POWERGRID.NS":  ["power grid","powergrid corporation"],
    "TATAPOWER.NS":  ["tata power","tata power company"],
    "ADANIPOWER.NS": ["adani power"],
    "TORNTPOWER.NS": ["torrent power"],
    # Conglomerates
    "ADANIENT.NS":   ["adani enterprises","adani group","adani"],
    "ADANIPORTS.NS": ["adani ports","adani port"],
    "ADANIGREEN.NS": ["adani green","adani renewables"],
    # Consumer & Retail
    "TITAN.NS":      ["titan company","titan watches","tanishq"],
    "ASIANPAINT.NS": ["asian paints","asian paint"],
    "DMART.NS":      ["dmart","avenue supermarts","d-mart"],
    "TRENT.NS":      ["trent","westside zudio"],
    "ZOMATO.NS":     ["zomato"],
    "NYKAA.NS":      ["nykaa","fsg nykaa"],
    "PAYTM.NS":      ["paytm","one97 communications"],
    # Defence & PSU
    "HAL.NS":        ["hindustan aeronautics","hal"],
    "BEL.NS":        ["bharat electronics","bel"],
    "BHEL.NS":       ["bhel","bharat heavy electricals"],
    "MAZAGON.NS":    ["mazagon dock","mazagondock"],
    "COCHINSHIP.NS": ["cochin shipyard","cochin ship"],
    "GRSE.NS":       ["garden reach","grse"],
    "RVNL.NS":       ["rail vikas","rvnl","rail vikas nigam"],
    "IRFC.NS":       ["irfc","indian railway finance"],
    "IRCON.NS":      ["ircon","ircon international"],
    "IRCTC.NS":      ["irctc","indian railway catering"],
    "CONCOR.NS":     ["concor","container corporation"],
    # Healthcare
    "APOLLOHOSP.NS": ["apollo hospitals","apollo hospital"],
    "FORTIS.NS":     ["fortis healthcare","fortis hospital"],
    "MAXHEALTH.NS":  ["max healthcare","max hospital"],
    "LALPATHLAB.NS": ["dr lal pathlab","dr lal","lal pathlab"],
    "METROPOLIS.NS": ["metropolis healthcare","metropolis lab"],
    # Telecom
    "BHARTIARTL.NS": ["airtel","bharti airtel","bharti telecom"],
    # Specialty
    "POLYCAB.NS":    ["polycab","polycab india"],
    "HAVELLS.NS":    ["havells india","havells"],
    "DIXON.NS":      ["dixon technologies","dixon tech"],
    "PIDILITIND.NS": ["pidilite industries","pidilite","fevicol"],
    # Mid-cap additions
    "SIEMENS.NS":    ["siemens india","siemens ltd"],
    "ABB.NS":        ["abb india","abb ltd"],
    "CUMMINSIND.NS": ["cummins india","cummins"],
    "THERMAX.NS":    ["thermax limited","thermax"],
    "VOLTAS.NS":     ["voltas","voltas limited"],
    "APOLLOTYRE.NS": ["apollo tyres","apollo tyre"],
    "BALKRISIND.NS": ["balkrishna industries","bkt tyres","bki"],
    "BOSCHLTD.NS":   ["bosch india","bosch ltd"],
    "DEEPAKNTR.NS":  ["deepak nitrite","deepak nitrate"],
    "AARTI.NS":      ["aarti industries","aarti ind"],
}

class NewsScanner:
    def __init__(self, portfolio_manager=None):
        self.portfolio = portfolio_manager
        self.alerted_path = "news_alerted.json"
        self.alerted = self._load_alerted()

    def _load_alerted(self):
        if os.path.exists(self.alerted_path):
            try:
                with open(self.alerted_path) as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_alerted(self):
        with open(self.alerted_path,"w") as f:
            json.dump(self.alerted, f, default=str)

    def _already_alerted(self, key):
        k = key[:80].lower().replace(" ","")
        if k in self.alerted:
            return True
        self.alerted[k] = datetime.now().isoformat()
        # Clean alerts older than 12 hours
        cutoff = datetime.now() - timedelta(hours=12)
        self.alerted = {
            kk:v for kk,v in self.alerted.items()
            if datetime.fromisoformat(v) > cutoff
        }
        self._save_alerted()
        return False

    def _find_trigger(self, text):
        tl = text.lower()
        best_trigger = None
        best_strength = 0
        for ttype, tdata in TRIGGERS.items():
            for kw in tdata["keywords"]:
                if kw in tl:
                    if tdata["strength"] > best_strength:
                        best_trigger = (ttype, kw, tdata)
                        best_strength = tdata["strength"]
        return best_trigger

    def _find_stocks(self, text):
        """Find all stocks mentioned in news"""
        tl  = text.lower()
        found = []
        for symbol, names in COMPANY_MAP.items():
            for name in names:
                if name in tl:
                    found.append(symbol)
                    break
        return list(set(found))

    def _get_current_price(self, symbol):
        try:
            df = yf.Ticker(symbol).history(period="2d",interval="1d")
            if df is not None and len(df)>0:
                return float(df["Close"].iloc[-1])
        except: pass
        return None

    def fetch_all_news(self, max_age_mins=35):
        """Fetch all fresh news from all sources"""
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_mins)
        all_items = []
        for source, url in NEWS_SOURCES.items():
            try:
                feed = feedparser.parse(url)
                for e in feed.entries[:40]:
                    title   = e.get("title","")
                    summary = e.get("summary","")
                    if not title: continue
                    pp = e.get("published_parsed")
                    if pp:
                        pub_dt = datetime(*pp[:6])
                        if pub_dt < cutoff: continue
                    all_items.append({
                        "source":  source,
                        "title":   title,
                        "summary": summary[:300],
                        "url":     e.get("link",""),
                        "full":    (title + " " + summary).lower()
                    })
            except Exception as e:
                log.warning(f"News fetch {source}: {e}")
        log.info(f"Fetched {len(all_items)} fresh news items")
        return all_items

    def scan_and_get_triggers(self):
        """
        Main scan function.
        Returns list of triggered stocks with their news context.
        """
        news_items = self.fetch_all_news()
        triggered  = {}  # symbol -> {trigger, news_title, trigger_type}

        for item in news_items:
            trigger = self._find_trigger(item["full"])
            if not trigger: continue

            stocks = self._find_stocks(item["full"])
            if not stocks: continue

            trigger_type, keyword, trigger_data = trigger

            for sym in stocks:
                key = f"{sym}_{item['title'][:40]}"
                if self._already_alerted(key): continue

                if sym not in triggered:
                    triggered[sym] = []
                triggered[sym].append({
                    "trigger_type":    trigger_type,
                    "keyword":         keyword,
                    "default_action":  trigger_data["default_action"],
                    "strength":        trigger_data["strength"],
                    "title":           item["title"],
                    "source":          item["source"],
                    "summary":         item["summary"],
                })

        log.info(f"News scan: {len(triggered)} stocks triggered")
        return triggered

    def is_in_portfolio(self, symbol):
        if not self.portfolio: return False
        holdings = self.portfolio.get_holdings()
        return any(h["symbol"]==symbol for h in holdings)

    def format_news_alert(self, symbol, triggers, analysis, current_price):
        """Format the complete news alert message"""
        in_portfolio = self.is_in_portfolio(symbol)
        top_trigger  = max(triggers, key=lambda x: x["strength"])
        action       = analysis.get("action","HOLD") if analysis else "HOLD"

        # If in portfolio, override to only show HOLD/SELL
        if in_portfolio and action == "BUY":
            action = "HOLD"

        lines = [
            f"NEWS ALERT - {symbol}",
            f"Trigger: {top_trigger['trigger_type'].replace('_',' ')}",
            f"News: {top_trigger['title'][:120]}",
            f"Source: {top_trigger['source']}",
            "---",
        ]

        if in_portfolio:
            lines.append("(You OWN this stock)")

        if analysis and action != "HOLD":
            ez  = analysis.get("entry_zone",{})
            sl  = analysis.get("stoploss",{})
            rr  = analysis.get("risk_reward","?")
            conv= analysis.get("conviction","?")
            lines += [
                f"AI CALL: {action}",
                f"Conviction: {conv}/10",
                f"Trade: {analysis.get('trade_type','')} | {analysis.get('time_horizon','')}",
                "---",
                f"Entry: Rs.{ez.get('low','?')} to Rs.{ez.get('high','?')}",
            ]
            for t in analysis.get("targets",[]):
                lines.append(f"{t.get('label','')}: Rs.{t.get('level','?')} (+{t.get('return_pct','?')}%)")
            lines += [
                f"Stop Loss: Rs.{sl.get('price','?')} (-{sl.get('pct','?')}%)",
                f"R:R = 1:{rr}",
                "---",
                f"Analysis: {analysis.get('reasoning','')}",
                f"Enter when: {analysis.get('entry_condition','')}",
            ]
        else:
            lines += [
                f"Verdict: {action}",
                f"Current price: Rs.{current_price}",
                "Technicals neutral - monitor this stock.",
                "Wait for price movement to confirm news."
            ]

        return "\n".join(lines)


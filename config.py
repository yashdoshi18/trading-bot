import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID")
    MIN_SCORE         = 4.0

    # TIER 1 — Nifty 50 + top liquid stocks — scanned every 2.5 hours
    TIER1 = [
        # Banking
        "HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","AXISBANK.NS","KOTAKBANK.NS",
        "INDUSINDBK.NS","BANDHANBNK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","PNB.NS",
        # Finance
        "BAJFINANCE.NS","BAJAJFINSV.NS","HDFCLIFE.NS","SBILIFE.NS","CHOLAFIN.NS",
        # IT
        "TCS.NS","INFY.NS","WIPRO.NS","HCLTECH.NS","TECHM.NS",
        "LTIM.NS","MPHASIS.NS","PERSISTENT.NS","COFORGE.NS","LTTS.NS",
        # Auto
        "MARUTI.NS","BAJAJ-AUTO.NS","EICHERMOT.NS","HEROMOTOCO.NS","M&M.NS",
        "TVSMOTOR.NS","ASHOKLEY.NS","MOTHERSON.NS",
        # FMCG
        "HINDUNILVR.NS","ITC.NS","NESTLEIND.NS","BRITANNIA.NS","DABUR.NS",
        "MARICO.NS","GODREJCP.NS","COLPAL.NS","TATACONSUM.NS","EMAMILTD.NS",
        # Pharma
        "SUNPHARMA.NS","DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","AUROPHARMA.NS",
        "TORNTPHARM.NS","LUPIN.NS","ALKEM.NS",
        # Energy
        "RELIANCE.NS","ONGC.NS","BPCL.NS","IOC.NS","GAIL.NS",
        "HINDPETRO.NS","IGL.NS","MGL.NS","PETRONET.NS",
        # Metals
        "TATASTEEL.NS","JSWSTEEL.NS","HINDALCO.NS","VEDL.NS","COALINDIA.NS",
        "NMDC.NS","SAIL.NS","JINDALSTEL.NS",
        # Infra & Cement
        "LARSEN.NS","ULTRACEMCO.NS","GRASIM.NS","ACC.NS","AMBUJACEMENT.NS",
        "SHREECEM.NS",
        # Power
        "NTPC.NS","POWERGRID.NS","TATAPOWER.NS","ADANIPOWER.NS","TORNTPOWER.NS",
        # Conglomerate & Others
        "ADANIPORTS.NS","ADANIENT.NS","TITAN.NS","ASIANPAINT.NS","PIDILITIND.NS",
        "HAVELLS.NS","POLYCAB.NS","DIXON.NS",
        # Telecom & Consumer
        "BHARTIARTL.NS","DMART.NS","TRENT.NS","ZOMATO.NS","NYKAA.NS",
    ]

    # TIER 2 — Mid caps — scanned once daily at 4 PM
    TIER2 = [
        # Banking & Finance
        "BANKBARODA.NS","CANBK.NS","AUBANK.NS","RBLBANK.NS","ICICIPRULI.NS",
        "MUTHOOTFIN.NS","MANAPPURAM.NS","SBICARD.NS","JMFINANCIL.NS","IIFL.NS",
        # IT Mid-cap
        "TATAELXSI.NS","OFSS.NS","KPITTECH.NS","CYIENT.NS","HEXAWARE.NS",
        "MASTEK.NS","NIIT.NS","ZENSAR.NS","BIRLASOFT.NS","SONATSOFTW.NS",
        # Auto Ancillary
        "BOSCHLTD.NS","APOLLOTYRE.NS","BALKRISIND.NS","EXIDEIND.NS","AMARAJABAT.NS",
        "SUNDRMFAST.NS","ENDURANCE.NS","SUPRAJIT.NS",
        # Pharma Mid-cap
        "BIOCON.NS","ABBOTINDIA.NS","PFIZER.NS","GLAXO.NS","SANOFI.NS",
        "IPCALAB.NS","NATCOPHARM.NS","GRANULES.NS","LAURUS.NS","GLENMARK.NS",
        # Real Estate
        "DLF.NS","GODREJPROP.NS","PRESTIGE.NS","OBEROIRLTY.NS","PHOENIXLTD.NS",
        "BRIGADE.NS","SOBHA.NS","MAHLIFE.NS",
        # Capital Goods
        "BHEL.NS","SIEMENS.NS","ABB.NS","CUMMINSIND.NS","THERMAX.NS",
        "VOLTAS.NS","WHIRLPOOL.NS","BLUESTAR.NS","KAJARIACER.NS","ORIENTBELL.NS",
        # Defence & PSU
        "HAL.NS","BEL.NS","MAZAGON.NS","COCHINSHIP.NS","GRSE.NS",
        "IRFC.NS","RVNL.NS","IRCON.NS","IRCTC.NS","CONCOR.NS",
        # Healthcare
        "APOLLOHOSP.NS","FORTIS.NS","MAXHEALTH.NS","LALPATHLAB.NS","METROPOLIS.NS",
        "HEALTHIUM.NS","MEDANTA.NS",
        # Specialty Chemicals
        "PIDILITIND.NS","AARTI.NS","DEEPAKNTR.NS","NAVINFLUOR.NS","CLEAN.NS",
        "ALKYLAMINE.NS","ROSSARI.NS","SUDARSCHEM.NS",
        # Consumer
        "PAGEIND.NS","VGUARD.NS","SYMPHONY.NS","BAJAJELEC.NS","CROMPTON.NS",
        "AMBER.NS","HAVELLS.NS","KEI.NS","FINOLEX.NS","POLYCAB.NS",
    ]

    # TIER 3 — Small caps & sector plays — scanned weekly Sunday
    TIER3 = [
        # Emerging tech
        "ZOMATO.NS","PAYTM.NS","POLICYBZR.NS","CARTRADE.NS","EASEMYTRIP.NS",
        # Textile
        "PAGEIND.NS","KPRMILL.NS","WELSPUNIND.NS","VARDHMANTEXT.NS","TRIDENT.NS",
        # Agri & Fertiliser
        "UPL.NS","COROMANDEL.NS","CHAMBLFERT.NS","GNFC.NS","RCF.NS",
        # Media
        "ZEEL.NS","SUNTV.NS","PVRINOX.NS","INOXWIND.NS",
        # Logistics
        "BLUEDART.NS","GATI.NS","TCI.NS","MAHLOG.NS","DELHIVERY.NS",
        # Hotels & Tourism
        "INDHOTEL.NS","EIHOTEL.NS","LEMONTREE.NS","CHALET.NS",
        # Paper & Packaging
        "TNPL.NS","WESTERNINDIA.NS","HUHTAMAKI.NS","MOLD-TEK.NS",
        # Retail
        "ABFRL.NS","SHOPERSTOP.NS","VMART.NS","METROBRANDS.NS","BATA.NS",
    ]

    # All tiers combined for reference
    @classmethod
    def get_all_stocks(cls):
        return list(set(cls.TIER1 + cls.TIER2 + cls.TIER3))

    # Nifty 50 index for market sentiment filter
    NIFTY_SYMBOL = "^NSEI"
    SENSEX_SYMBOL = "^BSESN"
    BANKNIFTY_SYMBOL = "^NSEBANK"

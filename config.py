import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID")
    MIN_SCORE         = 2.5  # Lowered from 4.0 for more signals

    # TIER 1 - Nifty 50 + top liquid stocks - scanned every 2.5 hours
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

    # TIER 2 - Mid caps - scanned daily at 4 PM IST
    TIER2 = [
        # Banking & Finance
        "BANKBARODA.NS","CANBK.NS","AUBANK.NS","RBLBANK.NS","ICICIPRULI.NS",
        "MUTHOOTFIN.NS","MANAPPURAM.NS","SBICARD.NS",
        # IT Mid-cap
        "TATAELXSI.NS","OFSS.NS","KPITTECH.NS","CYIENT.NS",
        "MASTEK.NS","BIRLASOFT.NS","SONATSOFTW.NS",
        # Auto Ancillary
        "BOSCHLTD.NS","APOLLOTYRE.NS","BALKRISIND.NS","EXIDEIND.NS",
        "SUNDRMFAST.NS","ENDURANCE.NS",
        # Pharma Mid-cap
        "BIOCON.NS","ABBOTINDIA.NS","IPCALAB.NS","NATCOPHARM.NS",
        "GRANULES.NS","LAURUS.NS","GLENMARK.NS",
        # Real Estate
        "DLF.NS","GODREJPROP.NS","PRESTIGE.NS","OBEROIRLTY.NS",
        "PHOENIXLTD.NS","BRIGADE.NS","SOBHA.NS",
        # Capital Goods
        "BHEL.NS","SIEMENS.NS","ABB.NS","CUMMINSIND.NS","THERMAX.NS",
        "VOLTAS.NS","BLUESTAR.NS",
        # Defence & PSU
        "HAL.NS","BEL.NS","MAZAGON.NS","COCHINSHIP.NS","GRSE.NS",
        "IRFC.NS","RVNL.NS","IRCON.NS","IRCTC.NS","CONCOR.NS",
        # Healthcare
        "APOLLOHOSP.NS","FORTIS.NS","MAXHEALTH.NS","LALPATHLAB.NS","METROPOLIS.NS",
        # Specialty Chemicals
        "AARTI.NS","DEEPAKNTR.NS","NAVINFLUOR.NS","ALKYLAMINE.NS",
        # Consumer
        "PAGEIND.NS","VGUARD.NS","CROMPTON.NS","AMBER.NS","KEI.NS",
    ]

    # TIER 3 - Small caps - scanned every Friday 4:30 PM IST
    TIER3 = [
        "ZOMATO.NS","PAYTM.NS","POLICYBZR.NS","EASEMYTRIP.NS",
        "KPRMILL.NS","WELSPUNIND.NS","TRIDENT.NS",
        "UPL.NS","COROMANDEL.NS","CHAMBLFERT.NS","GNFC.NS",
        "ZEEL.NS","SUNTV.NS","PVRINOX.NS",
        "BLUEDART.NS","DELHIVERY.NS",
        "INDHOTEL.NS","EIHOTEL.NS","LEMONTREE.NS",
        "ABFRL.NS","METROBRANDS.NS","BATA.NS","VMART.NS",
    ]

    @classmethod
    def get_all_stocks(cls):
        return list(set(cls.TIER1 + cls.TIER2 + cls.TIER3))

    NIFTY_SYMBOL    = "^NSEI"
    SENSEX_SYMBOL   = "^BSESN"
    BANKNIFTY_SYMBOL= "^NSEBANK"

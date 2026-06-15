import pandas_ta as ta
import logging
log = logging.getLogger(__name__)

class TechnicalAnalyzer:
    def analyze(self, df, mode):
        if df is None or len(df) < 30:
            return {"score":0, "mode":mode}

        c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
        price = float(c.iloc[-1])
        score = 0.0
        sig   = {"mode":mode, "price":round(price,2)}

        # ── EMA TREND ──────────────────────────────────────────
        e20  = ta.ema(c,20).iloc[-1]
        e50  = ta.ema(c,50).iloc[-1]
        e200 = ta.ema(c,200).iloc[-1] if len(df)>=200 else None
        if e200:
            if price>e50>e200:    sig["trend"]="STRONG_BULL"; score+=3
            elif price>e50:       sig["trend"]="BULL";        score+=1.5
            elif price<e50<e200:  sig["trend"]="STRONG_BEAR"; score-=3
            else:                 sig["trend"]="BEAR";        score-=1.5
        else:
            sig["trend"] = "BULL" if price>e50 else "BEAR"
            score += 1 if price>e50 else -1
        sig["ema20"]=round(e20,2); sig["ema50"]=round(e50,2)

        # ── RSI ────────────────────────────────────────────────
        rsi = ta.rsi(c,14).iloc[-1]
        sig["rsi"] = round(rsi,1)
        if   rsi<30: score+=2.5   # oversold
        elif rsi<40: score+=1.0
        elif rsi>75: score-=2.5   # overbought
        elif rsi>65: score-=1.0

        # ── STOCHASTIC RSI (more sensitive) ───────────────────
        try:
            stoch = ta.stochrsi(c, length=14)
            k_col = [x for x in stoch.columns if "STOCHRSIk" in x]
            d_col = [x for x in stoch.columns if "STOCHRSId" in x]
            if k_col and d_col:
                sk = stoch[k_col[0]].iloc[-1]
                sd = stoch[d_col[0]].iloc[-1]
                sig["stoch_rsi"] = round(sk,1)
                if sk<20 and sk>sd:  score+=1.5  # oversold + turning up
                elif sk>80 and sk<sd: score-=1.5 # overbought + turning down
        except: pass

        # ── MFI (Money Flow Index - RSI with volume) ──────────
        # Better than RSI because it confirms with actual money flow
        try:
            mfi = ta.mfi(h, l, c, v, length=14).iloc[-1]
            sig["mfi"] = round(mfi,1)
            if   mfi<20: score+=2.0   # oversold with volume confirmation
            elif mfi<30: score+=1.0
            elif mfi>80: score-=2.0   # overbought with volume
            elif mfi>70: score-=1.0
        except: pass

        # ── CCI (Commodity Channel Index) ─────────────────────
        # Good for spotting new trends beginning
        try:
            cci = ta.cci(h, l, c, length=20).iloc[-1]
            sig["cci"] = round(cci,1)
            if   cci < -100: score+=1.5  # oversold
            elif cci > +100: score-=1.5  # overbought
            elif cci > 0 and cci < 100: score+=0.5   # bullish zone
            elif cci < 0 and cci > -100: score-=0.5  # bearish zone
        except: pass

        # ── WILLIAMS %R ───────────────────────────────────────
        # Confirms RSI oversold/overbought signals
        try:
            willr = ta.willr(h, l, c, length=14).iloc[-1]
            sig["williams_r"] = round(willr,1)
            if   willr < -80: score+=1.0   # oversold
            elif willr > -20: score-=1.0   # overbought
        except: pass

        # ── ROC (Rate of Change - price momentum) ─────────────
        # Measures speed of price change
        try:
            roc = ta.roc(c, length=10).iloc[-1]
            sig["roc"] = round(roc,2)
            if   roc > 5:  score+=1.5   # strong upward momentum
            elif roc > 2:  score+=0.5
            elif roc < -5: score-=1.5   # strong downward momentum
            elif roc < -2: score-=0.5
        except: pass

        # ── MACD ──────────────────────────────────────────────
        mx = ta.macd(c)
        ml = mx["MACD_12_26_9"]; ms = mx["MACDs_12_26_9"]
        if ml.iloc[-2]<ms.iloc[-2] and ml.iloc[-1]>ms.iloc[-1]:
            sig["macd"]="BULL_CROSS"; score+=3
        elif ml.iloc[-2]>ms.iloc[-2] and ml.iloc[-1]<ms.iloc[-1]:
            sig["macd"]="BEAR_CROSS"; score-=3
        else:
            sig["macd"] = "ABOVE" if ml.iloc[-1]>ms.iloc[-1] else "BELOW"
            score += 0.5 if ml.iloc[-1]>ms.iloc[-1] else -0.5

        # ── BOLLINGER BANDS ───────────────────────────────────
        try:
            bb    = ta.bbands(c,20)
            bcols = bb.columns.tolist()
            bbu   = bb[[x for x in bcols if "BBU" in x][0]].iloc[-1]
            bbl   = bb[[x for x in bcols if "BBL" in x][0]].iloc[-1]
            pct   = (price-bbl)/(bbu-bbl) if (bbu-bbl)>0 else 0.5
            sig["bb_pct"] = round(pct,2)
            if   pct<0.10: score+=2.0  # very near lower band
            elif pct<0.20: score+=1.0
            elif pct>0.90: score-=2.0  # very near upper band
            elif pct>0.80: score-=1.0
        except: sig["bb_pct"]=0.5

        # ── VWAP ──────────────────────────────────────────────
        try:
            vwap = (c*v).cumsum() / v.cumsum()
            sig["vwap"] = round(float(vwap.iloc[-1]),2)
            sig["above_vwap"] = price > float(vwap.iloc[-1])
            score += 1.5 if price > float(vwap.iloc[-1]) else -1.5
        except: pass

        # ── PIVOT POINTS ──────────────────────────────────────
        try:
            ph = float(h.iloc[-2]); pl = float(l.iloc[-2]); pc = float(c.iloc[-2])
            pp = (ph+pl+pc)/3
            r1 = 2*pp-pl; r2 = pp+(ph-pl)
            s1 = 2*pp-ph; s2 = pp-(ph-pl)
            sig.update({"pivot":round(pp,2),"r1":round(r1,2),"r2":round(r2,2),
                        "s1":round(s1,2),"s2":round(s2,2)})
            if abs(price-s1)/price < 0.01: score+=1.0
            if abs(price-s2)/price < 0.01: score+=1.5
            if abs(price-r1)/price < 0.01: score-=1.0
        except: pass

        # ── FIBONACCI RETRACEMENT ─────────────────────────────
        try:
            ph50 = float(h.rolling(50).max().iloc[-1])
            pl50 = float(l.rolling(50).min().iloc[-1])
            fr   = ph50-pl50
            f382 = ph50-0.382*fr; f500 = ph50-0.500*fr; f618 = ph50-0.618*fr
            sig.update({"fib_382":round(f382,2),"fib_500":round(f500,2),
                        "fib_618":round(f618,2)})
            for fib in [f382,f500,f618]:
                if abs(price-fib)/price < 0.015:
                    score+=1.0; sig["near_fib"]=True
        except: pass

        # ── OBV (On Balance Volume) ───────────────────────────
        try:
            obv     = ta.obv(c,v)
            obv_ema = ta.ema(obv,20)
            sig["obv_trend"] = "UP" if obv.iloc[-1]>obv_ema.iloc[-1] else "DOWN"
            score += 1.0 if obv.iloc[-1]>obv_ema.iloc[-1] else -0.5
        except: pass

        # ── ATR (for stop loss sizing) ────────────────────────
        try:
            atr = ta.atr(h,l,c,length=14).iloc[-1]
            sig["atr"]    = round(float(atr),2)
            sig["atr_sl"] = round(price-2*float(atr),2)
        except: pass

        # ── SUPERTREND ────────────────────────────────────────
        try:
            st  = ta.supertrend(h,l,c,length=10,multiplier=3)
            col = [x for x in st.columns if "SUPERTd" in x]
            if col:
                d = st[col[0]].iloc[-1]
                sig["supertrend"] = "BUY" if d==1 else "SELL"
                score += 2 if d==1 else -2
        except: pass

        # ── ADX (Trend Strength) ──────────────────────────────
        try:
            adx = ta.adx(h,l,c,14)["ADX_14"].iloc[-1]
            sig["adx"] = round(adx,1)
            if adx>25: score+=1.0   # strong trend confirmed
            if adx>40: score+=0.5   # very strong trend
        except: pass

        # ── PARABOLIC SAR ─────────────────────────────────────
        try:
            psar = ta.psar(h,l,c)
            psar_cols = psar.columns.tolist()
            psar_long = [x for x in psar_cols if "PSARl" in x]
            psar_short= [x for x in psar_cols if "PSARs" in x]
            if psar_long and not str(psar[psar_long[0]].iloc[-1])=="nan":
                sig["psar"] = "BUY"
                score += 1.0
            elif psar_short and not str(psar[psar_short[0]].iloc[-1])=="nan":
                sig["psar"] = "SELL"
                score -= 1.0
        except: pass

        # ── ICHIMOKU CLOUD ────────────────────────────────────
        # Price above cloud = bullish, below = bearish
        try:
            ich = ta.ichimoku(h,l,c)
            if ich and len(ich)>0:
                ikh = ich[0]
                span_a_col = [x for x in ikh.columns if "ISA" in x]
                span_b_col = [x for x in ikh.columns if "ISB" in x]
                if span_a_col and span_b_col:
                    span_a = ikh[span_a_col[0]].iloc[-1]
                    span_b = ikh[span_b_col[0]].iloc[-1]
                    cloud_top = max(span_a, span_b)
                    cloud_bot = min(span_a, span_b)
                    if price > cloud_top:
                        sig["ichimoku"] = "ABOVE_CLOUD"; score+=2.0
                    elif price < cloud_bot:
                        sig["ichimoku"] = "BELOW_CLOUD"; score-=2.0
                    else:
                        sig["ichimoku"] = "IN_CLOUD"
        except: pass

        # ── VOLUME ANALYSIS ───────────────────────────────────
        avg_v = v.rolling(20).mean().iloc[-1]
        vr    = float(v.iloc[-1])/avg_v if avg_v>0 else 1
        sig["volume_ratio"] = round(vr,2)
        if   vr>3.0: score+=3.0   # massive volume spike
        elif vr>2.0: score+=2.0
        elif vr>1.5: score+=1.0
        # Volume drying up on downtrend = reversal signal
        if vr<0.5 and sig.get("trend","") in ["BEAR","STRONG_BEAR"]:
            score+=0.5

        sig["support"]    = round(float(l.rolling(20).min().iloc[-1]),2)
        sig["resistance"] = round(float(h.rolling(20).max().iloc[-1]),2)
        sig["score"]      = round(score,1)
        return sig

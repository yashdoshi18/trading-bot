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

        # === EMAs ===
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

        # === RSI ===
        rsi = ta.rsi(c,14).iloc[-1]
        sig["rsi"] = round(rsi,1)
        if   rsi<30: score+=2.5
        elif rsi<40: score+=1.0
        elif rsi>75: score-=2.5
        elif rsi>65: score-=1.0

        # === Stochastic RSI (more sensitive than RSI) ===
        try:
            stoch = ta.stochrsi(c, length=14)
            k_col = [x for x in stoch.columns if "STOCHRSIk" in x]
            d_col = [x for x in stoch.columns if "STOCHRSId" in x]
            if k_col and d_col:
                sk = stoch[k_col[0]].iloc[-1]
                sd = stoch[d_col[0]].iloc[-1]
                sig["stoch_rsi"] = round(sk,1)
                if sk<20 and sk>sd:  score+=1.5  # oversold + turning up
                elif sk>80 and sk<sd: score-=1.5  # overbought + turning down
        except: pass

        # === MACD ===
        mx = ta.macd(c)
        ml = mx["MACD_12_26_9"]; ms = mx["MACDs_12_26_9"]
        if ml.iloc[-2]<ms.iloc[-2] and ml.iloc[-1]>ms.iloc[-1]:
            sig["macd"]="BULL_CROSS"; score+=3
        elif ml.iloc[-2]>ms.iloc[-2] and ml.iloc[-1]<ms.iloc[-1]:
            sig["macd"]="BEAR_CROSS"; score-=3
        else:
            sig["macd"] = "ABOVE" if ml.iloc[-1]>ms.iloc[-1] else "BELOW"

        # === Bollinger Bands ===
        try:
            bb    = ta.bbands(c,20)
            bcols = bb.columns.tolist()
            bbu   = bb[[x for x in bcols if "BBU" in x][0]].iloc[-1]
            bbl   = bb[[x for x in bcols if "BBL" in x][0]].iloc[-1]
            pct   = (price-bbl)/(bbu-bbl) if (bbu-bbl)>0 else 0.5
            sig["bb_pct"] = round(pct,2)
            if pct<0.15:  score+=1.5
            elif pct>0.85: score-=1.5
        except: sig["bb_pct"]=0.5

        # === VWAP (Volume Weighted Avg Price) ===
        # Critical for intraday - where institutions buy/sell
        try:
            vwap = (c*v).cumsum() / v.cumsum()
            sig["vwap"] = round(float(vwap.iloc[-1]),2)
            sig["above_vwap"] = price > float(vwap.iloc[-1])
            if price > float(vwap.iloc[-1]): score+=1.5
            else: score-=1.5
        except: pass

        # === Pivot Points (Daily Support/Resistance) ===
        try:
            ph = float(h.iloc[-2]); pl = float(l.iloc[-2]); pc = float(c.iloc[-2])
            pp = (ph+pl+pc)/3
            r1 = 2*pp-pl; r2 = pp+(ph-pl)
            s1 = 2*pp-ph; s2 = pp-(ph-pl)
            sig["pivot"]=round(pp,2); sig["r1"]=round(r1,2); sig["r2"]=round(r2,2)
            sig["s1"]=round(s1,2);   sig["s2"]=round(s2,2)
            if abs(price-s1)/price < 0.01: score+=1.0  # near S1 support = buy zone
            if abs(price-s2)/price < 0.01: score+=1.5  # near S2 strong support
            if abs(price-r1)/price < 0.01: score-=1.0  # near R1 resistance = caution
        except: pass

        # === Fibonacci Retracement (50-day) ===
        try:
            ph50 = float(h.rolling(50).max().iloc[-1])
            pl50 = float(l.rolling(50).min().iloc[-1])
            frange = ph50-pl50
            fib382 = ph50 - 0.382*frange
            fib500 = ph50 - 0.500*frange
            fib618 = ph50 - 0.618*frange
            sig["fib_382"]=round(fib382,2)
            sig["fib_500"]=round(fib500,2)
            sig["fib_618"]=round(fib618,2)
            for fib in [fib382, fib500, fib618]:
                if abs(price-fib)/price < 0.015:
                    score+=1.0; sig["near_fib"]=True
        except: pass

        # === OBV (On Balance Volume - confirms trend with volume) ===
        try:
            obv     = ta.obv(c,v)
            obv_ema = ta.ema(obv,20)
            sig["obv_trend"] = "UP" if obv.iloc[-1]>obv_ema.iloc[-1] else "DOWN"
            if obv.iloc[-1]>obv_ema.iloc[-1]: score+=1.0  # accumulation
            else: score-=0.5  # distribution
        except: pass

        # === ATR (Average True Range - for stop loss sizing) ===
        try:
            atr = ta.atr(h,l,c,length=14).iloc[-1]
            sig["atr"]    = round(float(atr),2)
            sig["atr_sl"] = round(price - 2*float(atr),2)  # 2x ATR stop loss
        except: pass

        # === SuperTrend ===
        try:
            st  = ta.supertrend(h,l,c,length=10,multiplier=3)
            col = [x for x in st.columns if "SUPERTd" in x]
            if col:
                d = st[col[0]].iloc[-1]
                sig["supertrend"] = "BUY" if d==1 else "SELL"
                score += 2 if d==1 else -2
        except: pass

        # === ADX (Trend Strength) ===
        try:
            adx = ta.adx(h,l,c,14)["ADX_14"].iloc[-1]
            sig["adx"] = round(adx,1)
            if adx>25: score+=1
        except: pass

        # === Volume ===
        avg_v = v.rolling(20).mean().iloc[-1]
        vr    = float(v.iloc[-1])/avg_v if avg_v>0 else 1
        sig["volume_ratio"] = round(vr,2)
        if vr>2.0: score+=2
        elif vr>1.5: score+=1

        sig["support"]    = round(float(l.rolling(20).min().iloc[-1]),2)
        sig["resistance"] = round(float(h.rolling(20).max().iloc[-1]),2)
        sig["score"]      = round(score,1)
        return sig


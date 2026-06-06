import pandas_ta as ta

class TechnicalAnalyzer:
    def analyze(self, df, mode):
        if df is None or len(df) < 30:
            return {"score":0, "mode":mode}
        c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
        price = float(c.iloc[-1])
        score = 0.0
        sig   = {"mode":mode, "price":round(price,2)}
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
        rsi = ta.rsi(c,14).iloc[-1]; sig["rsi"]=round(rsi,1)
        if   rsi < 30: score+=2.5
        elif rsi < 40: score+=1.0
        elif rsi > 75: score-=2.5
        elif rsi > 65: score-=1.0
        mx = ta.macd(c)
        ml, ms = mx["MACD_12_26_9"], mx["MACDs_12_26_9"]
        if ml.iloc[-2]<ms.iloc[-2] and ml.iloc[-1]>ms.iloc[-1]:
            sig["macd"]="BULL_CROSS"; score+=3
        elif ml.iloc[-2]>ms.iloc[-2] and ml.iloc[-1]<ms.iloc[-1]:
            sig["macd"]="BEAR_CROSS"; score-=3
        else:
            sig["macd"] = "ABOVE" if ml.iloc[-1]>ms.iloc[-1] else "BELOW"
        bb  = ta.bbands(c,20)
        bbu = bb["BBU_20_2.0"].iloc[-1]; bbl = bb["BBL_20_2.0"].iloc[-1]
        pct = (price-bbl)/(bbu-bbl) if (bbu-bbl)>0 else 0.5
        sig["bb_pct"] = round(pct,2)
        if pct<0.15: score+=1.5
        elif pct>0.85: score-=1.5
        try:
            st  = ta.supertrend(h,l,c,length=10,multiplier=3)
            col = [x for x in st.columns if "SUPERTd" in x]
            if col:
                d = st[col[0]].iloc[-1]
                sig["supertrend"] = "BUY" if d==1 else "SELL"
                score += 2 if d==1 else -2
        except: pass
        try:
            adx = ta.adx(h,l,c,14)["ADX_14"].iloc[-1]
            sig["adx"] = round(adx,1)
            if adx>25: score+=1
        except: pass
        avg_v = v.rolling(20).mean().iloc[-1]
        vr    = float(v.iloc[-1])/avg_v if avg_v>0 else 1
        sig["volume_ratio"] = round(vr,2)
        if vr>2.0: score+=2
        elif vr>1.5: score+=1
        sig["support"]    = round(float(l.rolling(20).min().iloc[-1]),2)
        sig["resistance"] = round(float(h.rolling(20).max().iloc[-1]),2)
        sig["score"]      = round(score,1)
        return sig

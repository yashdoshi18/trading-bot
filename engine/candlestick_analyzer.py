class CandlestickAnalyzer:
    def analyze(self, df):
        if df is None or len(df) < 5:
            return {"patterns":[], "bias":"NEUTRAL", "score":0}
        o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
        o0,o1,o2 = o.iloc[-1],o.iloc[-2],o.iloc[-3]
        h0 = h.iloc[-1]; l0 = l.iloc[-1]
        c0,c1,c2 = c.iloc[-1],c.iloc[-2],c.iloc[-3]
        body0  = abs(c0-o0)
        avg_b  = abs(c-o).rolling(10).mean().iloc[-1]
        lo_sh  = min(o0,c0) - l0
        up_sh  = h0 - max(o0,c0)
        patterns = []; score = 0

        if body0 < avg_b*0.15:
            patterns.append({"name":"Doji","type":"NEUTRAL",
                "desc":"Indecision - watch next candle"})
        if lo_sh>body0*2 and up_sh<body0*0.5 and c1<o1:
            patterns.append({"name":"Hammer","type":"BULLISH",
                "desc":"Bullish reversal"}); score+=2
        if up_sh>body0*2 and lo_sh<body0*0.5 and c1>o1:
            patterns.append({"name":"Shooting Star","type":"BEARISH",
                "desc":"Bearish reversal"}); score-=2
        if c1<o1 and c0>o0 and c0>o1 and o0<c1:
            patterns.append({"name":"Bullish Engulfing","type":"BULLISH",
                "desc":"Bulls overwhelm bears"}); score+=3
        if c1>o1 and c0<o0 and c0<o1 and o0>c1:
            patterns.append({"name":"Bearish Engulfing","type":"BEARISH",
                "desc":"Bears overwhelm bulls"}); score-=3
        if c2<o2 and abs(c1-o1)<avg_b*0.3 and c0>o0 and c0>(o2+c2)/2:
            patterns.append({"name":"Morning Star","type":"BULLISH",
                "desc":"3-candle bottom reversal"}); score+=4
        if c2>o2 and abs(c1-o1)<avg_b*0.3 and c0<o0 and c0<(o2+c2)/2:
            patterns.append({"name":"Evening Star","type":"BEARISH",
                "desc":"3-candle top reversal"}); score-=4
        if body0>avg_b*2 and up_sh<body0*0.05 and lo_sh<body0*0.05:
            if c0>o0:
                patterns.append({"name":"Bullish Marubozu","type":"BULLISH",
                    "desc":"Strong buying pressure"}); score+=3
            else:
                patterns.append({"name":"Bearish Marubozu","type":"BEARISH",
                    "desc":"Strong selling pressure"}); score-=3
        if all(c.iloc[-i]>o.iloc[-i] for i in range(1,4)) and c0>c1>c2:
            patterns.append({"name":"Three White Soldiers","type":"BULLISH",
                "desc":"Strong 3-day uptrend"}); score+=4
        if all(c.iloc[-i]<o.iloc[-i] for i in range(1,4)) and c0<c1<c2:
            patterns.append({"name":"Three Black Crows","type":"BEARISH",
                "desc":"Strong 3-day downtrend"}); score-=4

        bias = "BULLISH" if score>1 else "BEARISH" if score<-1 else "NEUTRAL"
        return {"patterns":patterns, "bias":bias, "score":score, "count":len(patterns)}

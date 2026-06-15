"""
Enhanced Candlestick Analyzer
25+ patterns with strength, interpretation and trading implication.
Each pattern explains WHAT it means and HOW to trade it.
"""

CANDLE_GUIDE = {
    "Doji":               {"type":"NEUTRAL","strength":2,"meaning":"Buyers and sellers equal. Market at crossroads. Next candle decides direction.","trade":"Wait for confirmation candle before entering."},
    "Long-legged Doji":   {"type":"NEUTRAL","strength":3,"meaning":"Extreme indecision. Big swings both ways but closed flat. High volatility warning.","trade":"Avoid entry. Wait for clear direction."},
    "Gravestone Doji":    {"type":"BEARISH","strength":4,"meaning":"Bulls pushed price up but bears slammed it back down. Strong rejection of highs.","trade":"Short below low. SL above high."},
    "Dragonfly Doji":     {"type":"BULLISH","strength":4,"meaning":"Bears pushed price down but bulls recovered all losses. Strong rejection of lows.","trade":"Buy above high. SL below low."},
    "Hammer":             {"type":"BULLISH","strength":4,"meaning":"Bears tried hard to push down but buyers stepped in aggressively. Reversal signal.","trade":"Buy above hammer high. SL below hammer low."},
    "Inverted Hammer":    {"type":"BULLISH","strength":3,"meaning":"Buyers tried to push up, some selling but bulls still show strength. Potential reversal.","trade":"Buy on next green candle confirmation."},
    "Hanging Man":        {"type":"BEARISH","strength":4,"meaning":"Same shape as hammer but at TOP means bears testing. Warning of reversal down.","trade":"Short below hanging man low. SL above high."},
    "Shooting Star":      {"type":"BEARISH","strength":4,"meaning":"Bulls pushed high but bears crushed them. Strong rejection of price highs.","trade":"Short below shooting star low. SL above high."},
    "Bullish Marubozu":   {"type":"BULLISH","strength":5,"meaning":"Bulls in complete control. Opened at low, closed at high. No hesitation. Pure buying.","trade":"Buy immediately. Strong trend continuation. Wider SL."},
    "Bearish Marubozu":   {"type":"BEARISH","strength":5,"meaning":"Bears in complete control. Opened at high, closed at low. Pure selling pressure.","trade":"Short immediately. Strong trend continuation. Wider SL."},
    "Spinning Top":       {"type":"NEUTRAL","strength":1,"meaning":"Neither bulls nor bears winning. Market consolidating. Small body, equal shadows.","trade":"No trade. Wait for breakout from consolidation."},
    "Bullish Engulfing":  {"type":"BULLISH","strength":5,"meaning":"Bulls completely swallowed previous bearish candle. Powerful reversal. Institutional buying.","trade":"Buy above engulfing candle. Strong signal. Good R:R."},
    "Bearish Engulfing":  {"type":"BEARISH","strength":5,"meaning":"Bears completely swallowed previous bullish candle. Institutional selling. Reversal.","trade":"Short below engulfing candle. Strong signal."},
    "Bullish Harami":     {"type":"BULLISH","strength":3,"meaning":"Small candle inside previous large bear candle. Bears losing momentum. Reversal possible.","trade":"Buy on breakout above harami high."},
    "Bearish Harami":     {"type":"BEARISH","strength":3,"meaning":"Small candle inside previous large bull candle. Bulls losing momentum. Reversal possible.","trade":"Short on breakdown below harami low."},
    "Piercing Pattern":   {"type":"BULLISH","strength":4,"meaning":"Bull candle pierces more than 50% into previous bear candle. Strong buying emerged.","trade":"Buy above piercing candle high."},
    "Dark Cloud Cover":   {"type":"BEARISH","strength":4,"meaning":"Bear candle covers more than 50% of previous bull candle. Strong selling emerged.","trade":"Short below dark cloud low."},
    "Morning Star":       {"type":"BULLISH","strength":5,"meaning":"3-candle reversal. Indecision then strong bull candle. Institutional accumulation.","trade":"Buy above morning star third candle. Reliable pattern."},
    "Evening Star":       {"type":"BEARISH","strength":5,"meaning":"3-candle reversal at top. Indecision then strong bear candle. Distribution.","trade":"Short below evening star third candle."},
    "Morning Doji Star":  {"type":"BULLISH","strength":5,"meaning":"Like morning star but with doji. Even stronger reversal signal. Very reliable.","trade":"Strong buy signal. Enter above third candle."},
    "Evening Doji Star":  {"type":"BEARISH","strength":5,"meaning":"Like evening star but with doji. Even stronger reversal signal at top.","trade":"Strong short signal. Enter below third candle."},
    "Three White Soldiers":{"type":"BULLISH","strength":5,"meaning":"3 consecutive bull candles each closing higher. Sustained institutional buying.","trade":"Strong trend beginning. Buy with confidence. Trail SL."},
    "Three Black Crows":  {"type":"BEARISH","strength":5,"meaning":"3 consecutive bear candles each closing lower. Sustained institutional selling.","trade":"Strong downtrend. Short with confidence. Trail SL."},
    "Three Inside Up":    {"type":"BULLISH","strength":4,"meaning":"Harami followed by confirmation bull candle. Reversal confirmed by buyers.","trade":"Reliable buy signal. Enter on third candle close."},
    "Three Inside Down":  {"type":"BEARISH","strength":4,"meaning":"Bearish harami followed by confirmation bear candle. Reversal confirmed by sellers.","trade":"Reliable short signal. Enter on third candle close."},
    "Tweezer Bottom":     {"type":"BULLISH","strength":3,"meaning":"Two candles with same low. Bears couldn't push lower twice. Support confirmed.","trade":"Buy above tweezer high. SL below the double low."},
    "Tweezer Top":        {"type":"BEARISH","strength":3,"meaning":"Two candles with same high. Bulls couldn't push higher twice. Resistance confirmed.","trade":"Short below tweezer low. SL above the double high."},
    "Abandoned Baby Bull":{"type":"BULLISH","strength":5,"meaning":"Gap down doji then gap up candle. Extremely rare. Powerful reversal. Smart money buying.","trade":"Very strong buy. Can enter aggressively."},
    "Abandoned Baby Bear":{"type":"BEARISH","strength":5,"meaning":"Gap up doji then gap down candle. Extremely rare. Powerful reversal. Smart money selling.","trade":"Very strong short. Can enter aggressively."},
}

class CandlestickAnalyzer:
    def analyze(self, df):
        if df is None or len(df) < 5:
            return {"patterns":[],"bias":"NEUTRAL","score":0,"interpretation":"Insufficient data"}

        o = df["Open"]; h = df["High"]; l = df["Low"]; c = df["Close"]
        o0,o1,o2 = o.iloc[-1],o.iloc[-2],o.iloc[-3]
        h0,h1    = h.iloc[-1],h.iloc[-2]
        l0,l1    = l.iloc[-1],l.iloc[-2]
        c0,c1,c2 = c.iloc[-1],c.iloc[-2],c.iloc[-3]

        body0    = abs(c0-o0); body1 = abs(c1-o1); body2 = abs(c2-o2)
        avg_body = abs(c-o).rolling(10).mean().iloc[-1]
        lo_sh0   = min(o0,c0)-l0; up_sh0 = h0-max(o0,c0)
        lo_sh1   = min(o1,c1)-l1; up_sh1 = h1-max(o1,c1)
        rng0     = h0-l0

        patterns = []
        score    = 0

        # ===== SINGLE CANDLE PATTERNS =====

        # Doji family
        if body0 < avg_body * 0.1 and rng0 > 0:
            if up_sh0 < rng0*0.1:
                patterns.append("Dragonfly Doji"); score += 3
            elif lo_sh0 < rng0*0.1:
                patterns.append("Gravestone Doji"); score -= 3
            elif up_sh0 > avg_body and lo_sh0 > avg_body:
                patterns.append("Long-legged Doji")
            else:
                patterns.append("Doji")

        # Hammer (at downtrend bottom)
        elif lo_sh0 > body0*2.5 and up_sh0 < body0*0.5 and c1<o1:
            patterns.append("Hammer"); score += 3

        # Inverted Hammer
        elif up_sh0 > body0*2.5 and lo_sh0 < body0*0.5 and c1<o1:
            patterns.append("Inverted Hammer"); score += 2

        # Hanging Man (at uptrend top)
        elif lo_sh0 > body0*2.5 and up_sh0 < body0*0.5 and c1>o1:
            patterns.append("Hanging Man"); score -= 3

        # Shooting Star (at uptrend top)
        elif up_sh0 > body0*2.5 and lo_sh0 < body0*0.5 and c1>o1:
            patterns.append("Shooting Star"); score -= 3

        # Marubozu (strong trend candle)
        if body0 > avg_body*2.2 and up_sh0 < body0*0.05 and lo_sh0 < body0*0.05:
            if c0>o0:
                patterns.append("Bullish Marubozu"); score += 4
            else:
                patterns.append("Bearish Marubozu"); score -= 4

        # Spinning Top
        elif (body0 < avg_body*0.4 and
              up_sh0 > body0 and lo_sh0 > body0 and
              "Doji" not in " ".join(patterns)):
            patterns.append("Spinning Top")

        # ===== TWO CANDLE PATTERNS =====

        # Bullish Engulfing
        if c1<o1 and c0>o0 and c0>o1 and o0<c1 and body0>body1*1.2:
            patterns.append("Bullish Engulfing"); score += 4

        # Bearish Engulfing
        if c1>o1 and c0<o0 and c0<o1 and o0>c1 and body0>body1*1.2:
            patterns.append("Bearish Engulfing"); score -= 4

        # Bullish Harami
        if c1<o1 and c0>o0 and c0<o1 and o0>c1 and body0<body1*0.6:
            patterns.append("Bullish Harami"); score += 2

        # Bearish Harami
        if c1>o1 and c0<o0 and c0>o1 and o0<c1 and body0<body1*0.6:
            patterns.append("Bearish Harami"); score -= 2

        # Piercing Pattern
        if (c1<o1 and c0>o0 and
            o0 < l1 and
            c0 > (o1+c1)/2 and c0 < o1):
            patterns.append("Piercing Pattern"); score += 3

        # Dark Cloud Cover
        if (c1>o1 and c0<o0 and
            o0 > h1 and
            c0 < (o1+c1)/2 and c0 > c1):
            patterns.append("Dark Cloud Cover"); score -= 3

        # Tweezer Bottom
        if abs(l0-l1)/max(l0,l1) < 0.002 and c1<o1 and c0>o0:
            patterns.append("Tweezer Bottom"); score += 2

        # Tweezer Top
        if abs(h0-h1)/max(h0,h1) < 0.002 and c1>o1 and c0<o0:
            patterns.append("Tweezer Top"); score -= 2

        # ===== THREE CANDLE PATTERNS =====

        # Morning Star
        if (c2<o2 and body2>avg_body*0.8 and
            body1<avg_body*0.4 and
            c0>o0 and c0>(o2+c2)/2):
            patterns.append("Morning Star"); score += 4

        # Evening Star
        if (c2>o2 and body2>avg_body*0.8 and
            body1<avg_body*0.4 and
            c0<o0 and c0<(o2+c2)/2):
            patterns.append("Evening Star"); score -= 4

        # Morning Doji Star
        if (c2<o2 and body2>avg_body*0.8 and
            body1<avg_body*0.1 and
            c0>o0 and c0>(o2+c2)/2):
            patterns.append("Morning Doji Star"); score += 5

        # Evening Doji Star
        if (c2>o2 and body2>avg_body*0.8 and
            body1<avg_body*0.1 and
            c0<o0 and c0<(o2+c2)/2):
            patterns.append("Evening Doji Star"); score -= 5

        # Three White Soldiers
        if (all(c.iloc[-i]>o.iloc[-i] for i in range(1,4)) and
            c0>c1>c2 and
            all(abs(c.iloc[-i]-o.iloc[-i])>avg_body*0.7 for i in range(1,4))):
            patterns.append("Three White Soldiers"); score += 5

        # Three Black Crows
        if (all(c.iloc[-i]<o.iloc[-i] for i in range(1,4)) and
            c0<c1<c2 and
            all(abs(c.iloc[-i]-o.iloc[-i])>avg_body*0.7 for i in range(1,4))):
            patterns.append("Three Black Crows"); score -= 5

        # Three Inside Up
        if (c2<o2 and body1<body2*0.6 and
            c1>c2 and c0>o0 and c0>max(o2,c2)):
            patterns.append("Three Inside Up"); score += 3

        # Three Inside Down
        if (c2>o2 and body1<body2*0.6 and
            c1<c2 and c0<o0 and c0<min(o2,c2)):
            patterns.append("Three Inside Down"); score -= 3

        # Abandoned Baby (gaps needed - approximate check)
        try:
            if (c.iloc[-4]<o.iloc[-4] and
                body1<avg_body*0.1 and
                l1>h.iloc[-4] and
                c0>o0 and l0>h1):
                patterns.append("Abandoned Baby Bull"); score += 5
        except: pass

        # Remove duplicates
        patterns = list(dict.fromkeys(patterns))

        # Build interpretation
        bias = "BULLISH" if score>1 else "BEARISH" if score<-1 else "NEUTRAL"
        strength = min(5, abs(score)//2 + 1) if score != 0 else 0

        # Get guide info for detected patterns
        pattern_details = []
        for p in patterns:
            if p in CANDLE_GUIDE:
                g = CANDLE_GUIDE[p]
                pattern_details.append({
                    "name": p,
                    "type": g["type"],
                    "strength": g["strength"],
                    "meaning": g["meaning"],
                    "trade_action": g["trade"]
                })
            else:
                pattern_details.append({
                    "name": p,
                    "type": bias,
                    "strength": strength,
                    "meaning": f"{bias} signal detected",
                    "trade_action": "Monitor for confirmation"
                })

        # Overall interpretation
        if not patterns:
            interpretation = "No clear pattern. Market moving without a strong candle signal. Use technical indicators only."
        elif bias == "BULLISH":
            top = max(pattern_details, key=lambda x: x["strength"])
            interpretation = (f"{top['name']} detected — {top['meaning']} "
                              f"Trade action: {top['trade_action']}")
        else:
            top = max(pattern_details, key=lambda x: x["strength"])
            interpretation = (f"{top['name']} detected — {top['meaning']} "
                              f"Trade action: {top['trade_action']}")

        return {
            "patterns": pattern_details,
            "pattern_names": [p["name"] for p in pattern_details],
            "bias": bias,
            "score": round(score,1),
            "strength": strength,
            "count": len(pattern_details),
            "interpretation": interpretation,
            "top_pattern": pattern_details[0] if pattern_details else None
        }


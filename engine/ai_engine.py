import anthropic, json, logging
log = logging.getLogger(__name__)

SYS = (
    "You are a decisive NSE/BSE stock trader. "
    "You ALWAYS output exact price targets. "
    "You NEVER say insufficient data. "
    "If score > 2 give BUY. If score < -2 give SELL. Otherwise HOLD. "
    "Always calculate T1=entry*1.04, T2=entry*1.08, T3=entry*1.13, SL=entry*0.97. "
    "Respond ONLY in valid JSON. Zero explanation outside JSON."
)

class AIEngine:
    def __init__(self, api_key):
        self.c = anthropic.Anthropic(api_key=api_key)

    def _call(self, prompt, max_tokens=800):
        r = self.c.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens, system=SYS,
            messages=[{"role":"user","content":prompt}])
        text = r.content[0].text.strip()
        for fence in ["```json","```"]:
            text = text.replace(fence,"")
        return json.loads(text.strip())

    def _fallback(self, symbol, price, sc, news="", candle_bias="NEUTRAL"):
        """Always generate a signal even if API call fails"""
        price = float(price) if price else 100
        if sc >= 2:
            action = "BUY"
            entry  = round(price * 1.001, 1)
            t1     = round(entry * 1.04, 1)
            t2     = round(entry * 1.08, 1)
            t3     = round(entry * 1.13, 1)
            sl     = round(entry * 0.97, 1)
            reason = (f"Technical score {sc:.1f} is bullish. "
                      f"Price showing upward momentum. "
                      f"Candle bias {candle_bias}. Entry near current price.")
        elif sc <= -2:
            action = "SELL"
            entry  = round(price * 0.999, 1)
            t1     = round(entry * 0.96, 1)
            t2     = round(entry * 0.92, 1)
            t3     = round(entry * 0.87, 1)
            sl     = round(entry * 1.03, 1)
            reason = (f"Technical score {sc:.1f} is bearish. "
                      f"Price showing downward pressure. "
                      f"Candle bias {candle_bias}. Short below current price.")
        else:
            action = "HOLD"
            entry  = round(price, 1)
            t1     = round(price * 1.03, 1)
            t2     = round(price * 1.06, 1)
            t3     = round(price * 1.10, 1)
            sl     = round(price * 0.97, 1)
            reason = (f"Score {sc:.1f} is neutral. "
                      f"Wait for score to cross +/-3 before entering. "
                      f"Monitor for breakout.")

        conv = min(10, max(1, int(abs(sc))))
        rr   = round((t1 - entry) / (entry - sl), 1) if entry != sl else 2

        return {
            "symbol": symbol,
            "action": action,
            "conviction": conv,
            "trade_type": "SWING",
            "entry_zone": {"low": round(entry*0.99,1), "high": round(entry*1.01,1)},
            "targets": [
                {"label":"T1","level":t1,"return_pct":round((t1/entry-1)*100,1)},
                {"label":"T2","level":t2,"return_pct":round((t2/entry-1)*100,1)},
                {"label":"T3","level":t3,"return_pct":round((t3/entry-1)*100,1)},
            ],
            "stoploss": {"price":sl,"pct":round((1-sl/entry)*100,1)},
            "risk_reward": rr,
            "time_horizon": "1-3 weeks",
            "candle_note": f"Candle bias: {candle_bias}",
            "news_sentiment": "NEUTRAL",
            "news_impact": "No major news",
            "reasoning": reason,
            "risks": "Market direction unclear. Use strict SL.",
            "entry_condition": f"Enter above Rs.{round(entry*1.005,1)} with volume",
            "position_size": "1-2% of portfolio"
        }

    def full_analysis(self, symbol, intraday, swing, longterm,
                      candle, fundamentals, news, sc, nifty_trend="NEUTRAL"):

        price = (swing.get("price") or intraday.get("price") or 0)
        if not price or price == 0:
            return self._fallback(symbol, 100, sc, "", candle.get("bias","NEUTRAL"))

        price = float(price)
        ptns  = ", ".join(p["name"] for p in candle.get("patterns",[])) or "None"
        ntxt  = " | ".join(n.get("title","")[:60] for n in news[:3]) if news else "No news"

        # Pre-calculate prices so Claude just validates/adjusts
        if sc >= 2:
            suggested_action = "BUY"
            entry_suggest    = round(price * 1.002, 1)
        elif sc <= -2:
            suggested_action = "SELL"
            entry_suggest    = round(price * 0.998, 1)
        else:
            suggested_action = "HOLD"
            entry_suggest    = round(price, 1)

        t1_suggest = round(entry_suggest * 1.04, 1)
        t2_suggest = round(entry_suggest * 1.08, 1)
        t3_suggest = round(entry_suggest * 1.13, 1)
        sl_suggest = round(entry_suggest * 0.97, 1)

        prompt = (
            f"Stock: {symbol} | Price: Rs.{price} | Score: {sc:.1f}\n"
            f"Suggested action: {suggested_action}\n"
            f"Nifty: {nifty_trend} | Candles: {ptns} | Bias: {candle.get('bias','NEUTRAL')}\n"
            f"RSI: {swing.get('rsi','?')} | MACD: {swing.get('macd','?')} | "
            f"Trend: {swing.get('trend','?')} | Vol: {swing.get('volume_ratio','?')}x\n"
            f"Support: Rs.{swing.get('support','?')} | Resistance: Rs.{swing.get('resistance','?')}\n"
            f"PE: {fundamentals.get('pe','?')} | Sector: {fundamentals.get('sector','?')}\n"
            f"News: {ntxt}\n\n"
            f"Pre-calculated prices (adjust if needed):\n"
            f"Entry: Rs.{entry_suggest}\n"
            f"T1: Rs.{t1_suggest} T2: Rs.{t2_suggest} T3: Rs.{t3_suggest}\n"
            f"SL: Rs.{sl_suggest}\n\n"
            f"Return this JSON with real prices (use pre-calculated if unsure):\n"
            + json.dumps({
                "symbol": symbol,
                "action": suggested_action,
                "conviction": min(10,max(1,int(abs(sc)*1.5))),
                "trade_type": "SWING",
                "entry_zone": {"low": round(entry_suggest*0.99,1),
                               "high": round(entry_suggest*1.01,1)},
                "targets": [
                    {"label":"T1","level":t1_suggest,
                     "return_pct":round((t1_suggest/entry_suggest-1)*100,1)},
                    {"label":"T2","level":t2_suggest,
                     "return_pct":round((t2_suggest/entry_suggest-1)*100,1)},
                    {"label":"T3","level":t3_suggest,
                     "return_pct":round((t3_suggest/entry_suggest-1)*100,1)},
                ],
                "stoploss": {"price":sl_suggest,
                             "pct":round((1-sl_suggest/entry_suggest)*100,1)},
                "risk_reward": round((t1_suggest-entry_suggest)/(entry_suggest-sl_suggest),1),
                "time_horizon": "1-3 weeks",
                "candle_note": f"Patterns: {ptns}",
                "news_sentiment": "NEUTRAL",
                "news_impact": "See news above",
                "reasoning": f"Score {sc:.1f} suggests {suggested_action}. Adjust based on news and candles.",
                "risks": "Use strict stop loss",
                "entry_condition": f"Enter near Rs.{entry_suggest}",
                "position_size": "2-3% of portfolio"
            })
        )

        try:
            result = self._call(prompt)
            result["raw_score"] = sc
            return result
        except Exception as e:
            log.error(f"AI call failed {symbol}: {e} - using fallback")
            fb = self._fallback(symbol, price, sc,
                                ntxt, candle.get("bias","NEUTRAL"))
            fb["raw_score"] = sc
            return fb

    def morning_pick(self, data):
        sym   = data["symbol"]
        tech  = data["tech"]
        cd    = data["candle"]
        news  = data["news"]
        gap   = data["gap_pct"]
        nifty = data.get("nifty_trend","NEUTRAL")
        price = tech.get("price", 0)
        sc    = tech.get("score", 0)

        if not price:
            return {"symbol":sym,"action":"SKIP"}

        price = float(price)
        ptns  = ", ".join(p["name"] for p in cd.get("patterns",[])) or "None"
        ntxt  = " | ".join(n.get("title","")[:50] for n in news[:3]) if news else "None"

        # Pre-calculate
        entry   = round(price * 1.002, 1)
        t1, t2  = round(entry*1.04,1), round(entry*1.08,1)
        sl      = round(entry*0.97,1)
        action  = "BUY" if sc >= 1 else "SELL" if sc <= -1 else "SKIP"

        prompt = (
            f"Morning NSE pick. Stock: {sym} Price: Rs.{price}\n"
            f"Gap: {gap}% | Score: {sc:.1f} | Nifty: {nifty}\n"
            f"Trend: {tech.get('trend')} | RSI: {tech.get('rsi')} | "
            f"MACD: {tech.get('macd')}\n"
            f"Candles: {ptns} | News: {ntxt}\n"
            f"Suggested: {action} | Entry: Rs.{entry} T1: Rs.{t1} SL: Rs.{sl}\n"
            + json.dumps({
                "symbol": sym,
                "action": action,
                "trade_type": "INTRADAY" if abs(gap) > 1 else "SWING",
                "conviction": min(10,max(1,int(abs(sc)*2))),
                "entry": entry,
                "target1": t1,
                "target2": t2,
                "stoploss": sl,
                "reasoning": f"Score {sc:.1f}. Gap {gap}%. {ptns}.",
                "gap_note": f"Opened {gap:+.1f}% vs prev close"
            })
        )
        try:
            result = self._call(prompt, 400)
            return result
        except:
            if action == "SKIP":
                return {"symbol":sym,"action":"SKIP"}
            return {
                "symbol":sym,"action":action,
                "trade_type":"SWING","conviction":min(10,max(1,int(abs(sc)*2))),
                "entry":entry,"target1":t1,"target2":t2,"stoploss":sl,
                "reasoning":f"Score {sc:.1f}. {ptns}.",
                "gap_note":f"Gap {gap:+.1f}%"
            }

    def evaluate_holding(self, holding, current_price):
        entry = holding["buy_price"]
        pnl   = (current_price-entry)/entry*100
        prompt = (
            f"Holding {holding['symbol']} bought Rs.{entry} "
            f"now Rs.{current_price:.2f} P&L {pnl:.1f}%\n"
            f"Targets: {holding.get('targets',[])} SL: {holding.get('stoploss','N/A')}\n"
            f"Days: {holding.get('days_held',0)}\n"
            + json.dumps({"action":"HOLD","reason":"monitoring","urgency":"LOW"})
        )
        try:
            return self._call(prompt, 200)
        except:
            return {"action":"HOLD","reason":"error","urgency":"LOW"}

    def news_triggered_analysis(self, symbol, news_title, trigger_type,
                                  intraday, swing, longterm, candle, sc):
        price = swing.get("price") or intraday.get("price") or 100
        price = float(price)
        return self._fallback(symbol, price, max(sc, 3),
                              news_title, candle.get("bias","NEUTRAL"))

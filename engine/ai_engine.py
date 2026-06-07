import anthropic, json, logging
log = logging.getLogger(__name__)

SYS = ("You are an elite NSE/BSE Indian stock market analyst with 20 years experience. "
       "You specialize in Indian markets, understand SEBI regulations, Indian economic cycles, "
       "FII/DII flows, RBI policy impact, and Indian corporate fundamentals. "
       "Respond ONLY in valid JSON. No markdown. No preamble.")

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

    def full_analysis(self, symbol, intraday, swing, longterm,
                      candle, fundamentals, news, sc, nifty_trend="NEUTRAL"):
        ptns = ", ".join(p["name"] for p in candle.get("patterns",[])) or "None"
        ntxt = "\n".join(f"- [{n['source']}] {n['title']}"
                         for n in news[:6]) if news else "No recent Indian news"
        prompt = (
            f"Analyze this NSE/BSE Indian stock comprehensively.\n\n"
            f"SYMBOL: {symbol}\n"
            f"NIFTY 50 TREND: {nifty_trend} (use as market filter)\n"
            f"COMBINED SCORE: {sc:.1f} (range -10 to +10)\n\n"
            f"INTRADAY (15m): {json.dumps(intraday)}\n"
            f"SWING (Daily): {json.dumps(swing)}\n"
            f"LONGTERM (Weekly): {json.dumps(longterm)}\n\n"
            f"CANDLESTICK PATTERNS: {ptns}\n"
            f"CANDLE BIAS: {candle.get('bias','NEUTRAL')} (score {candle.get('score',0)})\n\n"
            f"FUNDAMENTALS: {json.dumps(fundamentals)}\n\n"
            f"RECENT INDIAN NEWS:\n{ntxt}\n\n"
            "Consider: multi-timeframe confluence, Indian market hours (9:15AM-3:30PM IST), "
            "FII/DII sentiment from news, RBI/SEBI impact, sector rotation in Indian market.\n\n"
            'Return ONLY this JSON:\n'
            '{"symbol":"str","action":"BUY|SELL|HOLD","conviction":1-10,'
            '"trade_type":"INTRADAY|SWING|LONGTERM|MULTI",'
            '"entry_zone":{"low":0,"high":0},'
            '"targets":['
            '{"label":"T1","level":0,"return_pct":0},'
            '{"label":"T2","level":0,"return_pct":0},'
            '{"label":"T3","level":0,"return_pct":0}],'
            '"stoploss":{"price":0,"pct":0},'
            '"risk_reward":0,"time_horizon":"str",'
            '"candle_note":"str",'
            '"news_sentiment":"POSITIVE|NEGATIVE|NEUTRAL",'
            '"news_impact":"str",'
            '"nifty_filter_note":"how nifty trend affects this trade",'
            '"reasoning":"3 sentence Indian market context analysis",'
            '"risks":"str","entry_condition":"str"}'
        )
        try:
            return self._call(prompt)
        except Exception as e:
            log.error(f"full_analysis {symbol}: {e}")
            return {"symbol":symbol,"action":"HOLD"}

    def morning_pick(self, data):
        sym  = data["symbol"]
        tech = data["tech"]
        cd   = data["candle"]
        news = data["news"]
        gap  = data["gap_pct"]
        nifty= data.get("nifty_trend","NEUTRAL")
        ptns = ", ".join(p["name"] for p in cd.get("patterns",[])) or "None"
        ntxt = "\n".join(f"- {n['title']}" for n in news[:4]) if news else "None"
        prompt = (
            f"Indian stock morning analysis (NSE opens 9:15 AM IST).\n"
            f"Symbol: {sym} | Gap from prev close: {gap}%\n"
            f"Nifty 50 trend: {nifty}\n"
            f"Technical score: {tech.get('score',0)} | Trend: {tech.get('trend')}\n"
            f"RSI: {tech.get('rsi')} | MACD: {tech.get('macd')}\n"
            f"Candlestick patterns: {ptns}\n"
            f"Candle bias: {cd.get('bias')}\n"
            f"Recent Indian news:\n{ntxt}\n\n"
            "Is this worth trading today on NSE? Consider Indian market open conditions.\n"
            'Return ONLY JSON: {"symbol":"str","action":"BUY|SELL|SKIP",'
            '"trade_type":"INTRADAY|SWING|LONGTERM","conviction":1-10,'
            '"entry":0,"target1":0,"target2":0,"stoploss":0,'
            '"reasoning":"str","gap_note":"str"}'
        )
        try:
            return self._call(prompt, 400)
        except:
            return {"symbol":sym,"action":"SKIP"}

    def evaluate_holding(self, holding, current_price):
        entry = holding["buy_price"]
        pnl   = (current_price - entry) / entry * 100
        prompt = (
            f"Evaluate this NSE stock holding.\n"
            f"Symbol: {holding['symbol']}\n"
            f"Bought: Rs.{entry} x {holding['qty']} shares\n"
            f"Current: Rs.{current_price:.2f} | P&L: {pnl:.1f}%\n"
            f"Targets: {holding.get('targets',[])} | SL: {holding.get('stoploss','N/A')}\n"
            f"Days held: {holding.get('days_held',0)}\n"
            "Should we HOLD, SELL, or BOOK_PARTIAL profits?\n"
            'Return ONLY JSON: {"action":"HOLD|SELL|BOOK_PARTIAL",'
            '"reason":"str","urgency":"LOW|MEDIUM|HIGH"}'
        )
        try:
            return self._call(prompt, 200)
        except:
            return {"action":"HOLD","reason":"error","urgency":"LOW"}

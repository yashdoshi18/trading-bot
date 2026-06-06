import anthropic, json, logging
log = logging.getLogger(__name__)

SYS = ("You are an elite NSE/BSE analyst with 20 years experience. "
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
        for fence in ["```json", "```"]:
            text = text.replace(fence, "")
        return json.loads(text.strip())

    def full_analysis(self, symbol, intraday, swing, longterm,
                      candle, fundamentals, news, sc):
        ptns = ", ".join(p["name"] for p in candle.get("patterns",[])) or "None"
        ntxt = "\n".join(f"- {n['title']}" for n in news[:5]) if news else "No news"
        prompt = (
            f"Stock: {symbol} | Score: {sc:.1f}\n"
            f"Intraday: {json.dumps(intraday)}\n"
            f"Swing: {json.dumps(swing)}\n"
            f"Longterm: {json.dumps(longterm)}\n"
            f"Candle patterns: {ptns} | Bias: {candle.get('bias')}\n"
            f"Fundamentals: {json.dumps(fundamentals)}\n"
            f"News: {ntxt}\n"
            'Return JSON: {"symbol":"str","action":"BUY|SELL|HOLD",'
            '"conviction":1-10,"trade_type":"INTRADAY|SWING|LONGTERM",'
            '"entry_zone":{"low":0,"high":0},'
            '"targets":[{"label":"T1","level":0,"return_pct":0},'
            '{"label":"T2","level":0,"return_pct":0},'
            '{"label":"T3","level":0,"return_pct":0}],'
            '"stoploss":{"price":0,"pct":0},"risk_reward":0,'
            '"time_horizon":"str","candle_note":"str",'
            '"news_sentiment":"POSITIVE|NEGATIVE|NEUTRAL",'
            '"news_impact":"str","reasoning":"str",'
            '"risks":"str","entry_condition":"str"}'
        )
        try: return self._call(prompt)
        except Exception as e:
            log.error(f"{symbol}: {e}")
            return {"symbol":symbol,"action":"HOLD"}

    def morning_pick(self, data):
        sym  = data["symbol"]
        tech = data["tech"]
        cd   = data["candle"]
        ptns = ", ".join(p["name"] for p in cd.get("patterns",[])) or "None"
        ntxt = "\n".join(f"- {n['title']}" for n in data["news"][:4]) if data["news"] else "None"
        prompt = (
            f"Morning pick for {sym}. Gap: {data['gap_pct']}%\n"
            f"Score:{tech.get('score',0)} Trend:{tech.get('trend')} RSI:{tech.get('rsi')}\n"
            f"Candles: {ptns} Bias: {cd.get('bias')}\n"
            f"News: {ntxt}\n"
            'Return JSON: {"symbol":"str","action":"BUY|SELL|SKIP",'
            '"trade_type":"INTRADAY|SWING|LONGTERM","conviction":1-10,'
            '"entry":0,"target1":0,"target2":0,"stoploss":0,'
            '"reasoning":"str","gap_note":"str"}'
        )
        try: return self._call(prompt, 400)
        except: return {"symbol":sym,"action":"SKIP"}

    def evaluate_holding(self, holding, current_price):
        entry = holding["buy_price"]
        pnl   = (current_price-entry)/entry*100
        prompt = (
            f"Trade: {holding['symbol']} bought Rs.{entry} x {holding['qty']}\n"
            f"Current Rs.{current_price:.2f} | P&L {pnl:.1f}%\n"
            f"Targets:{holding.get('targets',[])} SL:{holding.get('stoploss','N/A')}\n"
            f"Days held:{holding.get('days_held',0)}\n"
            'Return JSON: {"action":"HOLD|SELL|BOOK_PARTIAL",'
            '"reason":"str","urgency":"LOW|MEDIUM|HIGH"}'
        )
        try: return self._call(prompt, 200)
        except: return {"action":"HOLD","reason":"error","urgency":"LOW"}

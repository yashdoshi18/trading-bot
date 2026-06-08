import anthropic, json, logging
log = logging.getLogger(__name__)

SYS = (
    "You are an elite NSE/BSE Indian stock market analyst with 20 years experience. "
    "You ALWAYS give a clear BUY, SELL, or HOLD recommendation for every stock. "
    "You never say 'insufficient data'. Even on neutral days, pick the best direction. "
    "You understand Indian market cycles, SEBI, RBI, FII/DII flows. "
    "Respond ONLY in valid JSON. No markdown. No preamble. No explanation outside JSON."
)

class AIEngine:
    def __init__(self, api_key):
        self.c = anthropic.Anthropic(api_key=api_key)

    def _call(self, prompt, max_tokens=1000):
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
        ptns = ", ".join(p["name"] for p in candle.get("patterns",[])) or "None detected"
        ntxt = "\n".join(
            f"- [{n.get('source','')}] {n.get('title','')}"
            for n in news[:5]) if news else "No recent news"

        # Build indicator summary
        ind_summary = (
            f"Trend: {swing.get('trend','?')} | "
            f"RSI: {swing.get('rsi','?')} | "
            f"MACD: {swing.get('macd','?')} | "
            f"BB%: {swing.get('bb_pct','?')} | "
            f"Volume ratio: {swing.get('volume_ratio','?')}x | "
            f"SuperTrend: {swing.get('supertrend','?')} | "
            f"ADX: {swing.get('adx','?')} | "
            f"VWAP: {'above' if swing.get('above_vwap') else 'below'} | "
            f"EMA20: {swing.get('ema20','?')} | "
            f"EMA50: {swing.get('ema50','?')}"
        )

        price = swing.get("price", intraday.get("price", 0))

        prompt = (
            f"Analyze this NSE stock and give a DEFINITIVE trading recommendation.\n\n"
            f"STOCK: {symbol}\n"
            f"CURRENT PRICE: Rs.{price}\n"
            f"NIFTY TREND: {nifty_trend}\n"
            f"COMBINED TECHNICAL SCORE: {sc:.1f} (positive=bullish, negative=bearish)\n\n"
            f"KEY INDICATORS:\n{ind_summary}\n\n"
            f"INTRADAY (15min chart): score={intraday.get('score',0):.1f} "
            f"trend={intraday.get('trend','?')}\n"
            f"SWING (daily chart): score={swing.get('score',0):.1f} "
            f"support=Rs.{swing.get('support','?')} resistance=Rs.{swing.get('resistance','?')}\n"
            f"LONGTERM (weekly chart): score={longterm.get('score',0):.1f} "
            f"trend={longterm.get('trend','?')}\n\n"
            f"CANDLESTICK PATTERNS: {ptns}\n"
            f"CANDLE BIAS: {candle.get('bias','NEUTRAL')} (score {candle.get('score',0)})\n\n"
            f"FUNDAMENTALS: PE={fundamentals.get('pe','?')} "
            f"ROE={fundamentals.get('roe','?')} "
            f"Sector={fundamentals.get('sector','?')} "
            f"From 52w high={fundamentals.get('from_52h','?')}\n\n"
            f"RECENT NEWS:\n{ntxt}\n\n"
            f"INSTRUCTIONS:\n"
            f"- Give BUY if score > 0 or news is positive or candle is bullish\n"
            f"- Give SELL if score < 0 or news is negative or candle is bearish\n"
            f"- Only HOLD if genuinely no clear direction\n"
            f"- Calculate realistic entry zone near current price Rs.{price}\n"
            f"- T1 = 3-5% above entry, T2 = 7-10%, T3 = 12-18%\n"
            f"- Stop loss = 2-3% below entry or at nearest support\n"
            f"- Be specific with prices, not vague\n\n"
            'Return ONLY this exact JSON:\n'
            '{"symbol":"' + symbol + '",'
            '"action":"BUY or SELL or HOLD",'
            '"conviction": a number 1 to 10,'
            '"trade_type":"INTRADAY or SWING or LONGTERM or MULTI",'
            '"entry_zone":{"low": price as number,"high": price as number},'
            '"targets":['
            '{"label":"T1","level": price as number,"return_pct": number},'
            '{"label":"T2","level": price as number,"return_pct": number},'
            '{"label":"T3","level": price as number,"return_pct": number}],'
            '"stoploss":{"price": number,"pct": number},'
            '"risk_reward": number,'
            '"time_horizon":"string like 1-3 days or 1-3 weeks",'
            '"candle_note":"what the candlestick pattern means",'
            '"news_sentiment":"POSITIVE or NEGATIVE or NEUTRAL",'
            '"news_impact":"one line on how news affects this",'
            '"reasoning":"3 sentences: technical + news + overall conclusion",'
            '"risks":"main risk to watch",'
            '"entry_condition":"exact condition before entering eg price above X",'
            '"position_size":"1-2% or 2-3% or 3-5% of portfolio"}'
        )
        try:
            return self._call(prompt)
        except Exception as e:
            log.error(f"full_analysis {symbol}: {e}")
            return {
                "symbol": symbol,
                "action": "HOLD",
                "conviction": 3,
                "trade_type": "SWING",
                "entry_zone": {"low": price, "high": price},
                "targets": [
                    {"label":"T1","level":round(price*1.04,1),"return_pct":4},
                    {"label":"T2","level":round(price*1.08,1),"return_pct":8},
                    {"label":"T3","level":round(price*1.12,1),"return_pct":12}
                ],
                "stoploss": {"price":round(price*0.97,1),"pct":3},
                "risk_reward": 2,
                "time_horizon": "1-3 weeks",
                "candle_note": "No pattern detected",
                "news_sentiment": "NEUTRAL",
                "news_impact": "No significant news",
                "reasoning": "Insufficient data for strong signal. Neutral bias.",
                "risks": "Market uncertainty",
                "entry_condition": "Wait for clear breakout",
                "position_size": "1-2% of portfolio",
                "raw_score": sc
            }

    def morning_pick(self, data):
        sym   = data["symbol"]
        tech  = data["tech"]
        cd    = data["candle"]
        news  = data["news"]
        gap   = data["gap_pct"]
        nifty = data.get("nifty_trend","NEUTRAL")
        ptns  = ", ".join(p["name"] for p in cd.get("patterns",[])) or "None"
        ntxt  = "\n".join(f"- {n['title']}" for n in news[:3]) if news else "No news"
        price = tech.get("price", 0)

        prompt = (
            f"Morning NSE pick - market opens 9:15 AM IST.\n"
            f"Stock: {sym} | Price: Rs.{price} | Gap: {gap}%\n"
            f"Nifty: {nifty}\n"
            f"Score: {tech.get('score',0):.1f} | Trend: {tech.get('trend')} | "
            f"RSI: {tech.get('rsi')} | MACD: {tech.get('macd')}\n"
            f"VWAP: {'above' if tech.get('above_vwap') else 'below'}\n"
            f"Support: Rs.{tech.get('support','?')} | Resistance: Rs.{tech.get('resistance','?')}\n"
            f"Candles: {ptns} | Bias: {cd.get('bias')}\n"
            f"News: {ntxt}\n\n"
            f"Give a BUY or SELL pick if any merit. SKIP only if completely flat.\n"
            f"Use Rs.{price} as base for calculating entry/target/SL.\n"
            'Return ONLY JSON: {"symbol":"' + sym + '",'
            '"action":"BUY or SELL or SKIP",'
            '"trade_type":"INTRADAY or SWING or LONGTERM",'
            '"conviction": number 1-10,'
            '"entry": price as number,'
            '"target1": price as number,'
            '"target2": price as number,'
            '"stoploss": price as number,'
            '"reasoning":"one line",'
            '"gap_note":"comment on gap if notable"}'
        )
        try:
            return self._call(prompt, 500)
        except:
            return {"symbol":sym,"action":"SKIP"}

    def evaluate_holding(self, holding, current_price):
        entry = holding["buy_price"]
        pnl   = (current_price-entry)/entry*100
        prompt = (
            f"Evaluate NSE holding: {holding['symbol']}\n"
            f"Bought Rs.{entry} x {holding['qty']} shares\n"
            f"Current Rs.{current_price:.2f} | P&L {pnl:.1f}%\n"
            f"Targets: {holding.get('targets',[])} | SL: {holding.get('stoploss','N/A')}\n"
            f"Days held: {holding.get('days_held',0)}\n"
            'Return ONLY JSON: {"action":"HOLD or SELL or BOOK_PARTIAL",'
            '"reason":"brief reason","urgency":"LOW or MEDIUM or HIGH"}'
        )
        try:
            return self._call(prompt, 200)
        except:
            return {"action":"HOLD","reason":"error","urgency":"LOW"}

    def news_triggered_analysis(self, symbol, news_title, trigger_type,
                                  intraday, swing, longterm, candle, combined_score):
        price = swing.get("price", intraday.get("price", 0))
        ptns  = ", ".join(p["name"] for p in candle.get("patterns",[])) or "None"
        prompt = (
            f"NEWS-TRIGGERED analysis for NSE stock {symbol}.\n"
            f"Current price: Rs.{price}\n"
            f"NEWS: {news_title}\n"
            f"TRIGGER: {trigger_type}\n"
            f"Technical score: {combined_score:.1f}\n"
            f"Trend: {swing.get('trend')} | RSI: {swing.get('rsi')}\n"
            f"Candles: {ptns} | Bias: {candle.get('bias','NEUTRAL')}\n\n"
            f"News is the PRIMARY driver. Give BUY unless technicals strongly disagree.\n"
            f"MERGER/ACQUISITION and ORDER_WIN = strong BUY catalyst.\n"
            f"RESULTS_BEAT = BUY if not already priced in.\n"
            f"BUYBACK = BUY signal (management confidence).\n\n"
            'Return ONLY JSON: {"symbol":"' + symbol + '",'
            '"action":"BUY or SELL or HOLD",'
            '"conviction": number 1-10,'
            '"trade_type":"INTRADAY or SWING or LONGTERM",'
            '"entry_zone":{"low":' + str(round(price*0.99,1)) + ',"high":' + str(round(price*1.01,1)) + '},'
            '"targets":['
            '{"label":"T1","level":' + str(round(price*1.05,1)) + ',"return_pct":5},'
            '{"label":"T2","level":' + str(round(price*1.10,1)) + ',"return_pct":10},'
            '{"label":"T3","level":' + str(round(price*1.15,1)) + ',"return_pct":15}],'
            '"stoploss":{"price":' + str(round(price*0.97,1)) + ',"pct":3},'
            '"risk_reward":3,"time_horizon":"1-2 weeks",'
            '"news_assessment":"how significant is this news 1-10",'
            '"reasoning":"news impact + technical combined",'
            '"entry_condition":"string","risks":"string"}'
        )
        try:
            return self._call(prompt, 600)
        except Exception as e:
            log.error(f"news_analysis {symbol}: {e}")
            return {"symbol":symbol,"action":"HOLD"}

import telebot, logging
log = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.bot     = telebot.TeleBot(token)
        self.chat_id = chat_id

    def send_message(self, text):
        try:
            self.bot.send_message(self.chat_id, text, parse_mode="Markdown")
        except Exception as e:
            log.error(f"Telegram send error: {e}")
            try:
                # Retry without markdown if formatting error
                self.bot.send_message(self.chat_id, text)
            except Exception as e2:
                log.error(f"Telegram retry error: {e2}")

    def send_full_report(self, results, ts, tier_name, nifty, scanned_count):
        """Send complete report with all stock suggestions every scan"""
        if not results:
            self.send_message(
                f"Scan ({tier_name}) - {ts}\n"
                f"No results returned from AI.")
            return

        # Header
        buys  = [r for r in results if r.get("action") == "BUY"]
        sells = [r for r in results if r.get("action") == "SELL"]
        holds = [r for r in results if r.get("action") == "HOLD"]

        header = (
            f"SCAN REPORT - {ts}\n"
            f"Scanned {scanned_count} stocks | Nifty: {nifty}\n"
            f"BUY: {len(buys)} | SELL: {len(sells)} | HOLD: {len(holds)}\n"
            f"{'=' * 26}"
        )
        self.send_message(header)

        # Send each BUY signal with full details
        for r in buys:
            self._send_signal(r, "BUY")

        # Send each SELL signal
        for r in sells:
            self._send_signal(r, "SELL")

        # Send HOLD summary (compact, one message)
        if holds:
            hold_txt = "HOLD / WATCH THESE:\n"
            for r in holds:
                sc = r.get("raw_score", 0)
                hold_txt += (
                    f"  {r.get('symbol','')} "
                    f"(score {sc:+.1f}) "
                    f"- {r.get('reasoning','')[:60]}\n"
                )
            self.send_message(hold_txt)

    def _send_signal(self, r, action):
        """Send one full signal with all details"""
        sym   = r.get("symbol","")
        conv  = r.get("conviction", 5)
        tt    = r.get("trade_type","")
        hz    = r.get("time_horizon","")
        ez    = r.get("entry_zone",{})
        sl    = r.get("stoploss",{})
        rr    = r.get("risk_reward","?")
        sc    = r.get("raw_score", 0)
        stars = conv // 2  # 1-5 stars

        # Targets
        tgt_txt = ""
        for t in r.get("targets",[]):
            tgt_txt += f"  {t.get('label','')}: Rs.{t.get('level','?')} (+{t.get('return_pct','?')}%)\n"

        # Action line
        if action == "BUY":
            action_line = f"BUY - {sym}"
        else:
            action_line = f"SELL - {sym}"

        msg = (
            f"*{action_line}*\n"
            f"{'star ' * stars}Conviction: {conv}/10\n"
            f"Type: {tt} | Horizon: {hz}\n"
            f"Tech Score: {sc:+.1f}\n"
            f"{'=' * 26}\n"
            f"Entry Zone: Rs.{ez.get('low','?')} to Rs.{ez.get('high','?')}\n"
            f"{tgt_txt}"
            f"Stop Loss: Rs.{sl.get('price','?')} (-{sl.get('pct','?')}%)\n"
            f"Risk:Reward = 1:{rr}\n"
            f"{'=' * 26}\n"
            f"Candle: {r.get('candle_note','')}\n"
            f"News ({r.get('news_sentiment','')}): {r.get('news_impact','')}\n"
            f"Analysis: {r.get('reasoning','')}\n"
            f"Enter when: {r.get('entry_condition','')}\n"
            f"Risk: {r.get('risks','')}\n"
            f"Position: {r.get('position_size','2-3% of portfolio')}"
        )
        self.send_message(msg)

    def send_scan_summary(self, signals, ts, tier_name):
        """Legacy - redirects to full report"""
        self.send_full_report(signals, ts, tier_name, "N/A", 0)

    def send_morning_report(self, intraday, swing, longterm, mkt_news, ds):
        """Morning briefing with full details"""
        # Market headlines
        if mkt_news.get("headlines"):
            hl_txt = f"MARKET HEADLINES - {ds}\n"
            for h in mkt_news.get("headlines",[])[:4]:
                hl_txt += f"- {h}\n"
            self.send_message(hl_txt)

        # Intraday picks
        if intraday:
            self.send_message(f"INTRADAY PICKS - {ds}\n(Trade within 9:15 AM - 3:30 PM)")
            for p in intraday[:3]:
                self._send_morning_pick(p, "INTRADAY")
        
        # Swing picks
        if swing:
            self.send_message("SWING PICKS\n(Hold 1-3 weeks)")
            for p in swing[:3]:
                self._send_morning_pick(p, "SWING")

        # Long term picks
        if longterm:
            txt = "LONG TERM WATCH\n"
            for p in longterm[:2]:
                txt += (
                    f"  {p.get('action','')} {p.get('symbol','')}\n"
                    f"  Entry: Rs.{p.get('entry','?')} "
                    f"SL: Rs.{p.get('stoploss','?')}\n"
                    f"  {p.get('reasoning','')}\n\n"
                )
            self.send_message(txt)

    def _send_morning_pick(self, p, trade_type):
        """Send one morning pick with full details"""
        msg = (
            f"*{p.get('action','')} - {p.get('symbol','')}*\n"
            f"Conviction: {p.get('conviction','?')}/10 | {trade_type}\n"
            f"{'=' * 26}\n"
            f"Entry: Rs.{p.get('entry','?')}\n"
            f"Target 1: Rs.{p.get('target1','?')}\n"
            f"Target 2: Rs.{p.get('target2','?')}\n"
            f"Stop Loss: Rs.{p.get('stoploss','?')}\n"
            f"{'=' * 26}\n"
            f"Reason: {p.get('reasoning','')}\n"
            f"Gap note: {p.get('gap_note','')}"
        )
        self.send_message(msg)

    def send_portfolio_alert(self, symbol, alert_type, current, pnl, extra=""):
        """Portfolio alerts - target hit, SL hit, AI suggestion"""
        if alert_type == "SL_HIT":
            msg = (
                f"*STOP LOSS HIT - {symbol}*\n"
                f"Current: Rs.{current:.2f}\n"
                f"Loss: {pnl:.1f}%\n"
                f"ACTION: EXIT NOW to limit losses\n"
                f"{extra}"
            )
        elif alert_type.startswith("TARGET"):
            t_num = alert_type.split("_")[1]
            msg = (
                f"*TARGET T{t_num} HIT - {symbol}*\n"
                f"Current: Rs.{current:.2f}\n"
                f"Profit: +{pnl:.1f}%\n"
                f"ACTION: Book {'partial' if int(t_num) < 3 else 'full'} profit\n"
                f"{extra}"
            )
        else:
            msg = (
                f"*AI UPDATE - {symbol}*\n"
                f"Current: Rs.{current:.2f} | P&L: {pnl:+.1f}%\n"
                f"{extra}"
            )
        self.send_message(msg)

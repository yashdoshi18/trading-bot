import telebot, logging
log = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.bot = telebot.TeleBot(token)
        self.chat_id = chat_id

    def send_message(self, text):
        try:
            self.bot.send_message(self.chat_id, text, parse_mode="Markdown")
        except Exception as e:
            log.error(f"Telegram: {e}")

    def send_scan_summary(self, signals, ts):
        self.send_message(
            f"SCAN COMPLETE - {ts}\n"
            f"Found {len(signals)} signal(s)")
        for s in signals[:8]:
            self._signal(s)

    def _signal(self, sig):
        a    = sig.get("action","HOLD")
        tgts = ""
        for t in sig.get("targets",[]):
            tgts += f"  {t['label']}: Rs.{t['level']} (+{t['return_pct']}%)\n"
        sl = sig.get("stoploss",{})
        ez = sig.get("entry_zone",{})
        self.send_message(
            f"*{'BUY' if a=='BUY' else 'SELL' if a=='SELL' else 'HOLD'}*"
            f" - {sig.get('symbol','')}\n"
            f"Conviction {sig.get('conviction','?')}/10 | {sig.get('trade_type','')}\n"
            f"Horizon: {sig.get('time_horizon','')}\n---\n"
            f"Entry: Rs.{ez.get('low','?')} to Rs.{ez.get('high','?')}\n"
            f"{tgts}"
            f"SL: Rs.{sl.get('price','?')} (-{sl.get('pct','?')}%)\n"
            f"R:R = 1:{sig.get('risk_reward','?')}\n---\n"
            f"Candle: {sig.get('candle_note','')}\n"
            f"News: {sig.get('news_impact','')}\n"
            f"Analysis: {sig.get('reasoning','')}\n"
            f"Enter when: {sig.get('entry_condition','')}")

    def send_morning_report(self, intraday, swing, longterm, mkt_news, ds):
        self.send_message(f"*MORNING BRIEFING - {ds}*")
        if mkt_news.get("headlines"):
            self.send_message("HEADLINES\n" +
                "\n".join(f"- {h}" for h in mkt_news["headlines"][:4]))
        if intraday:
            txt = "*INTRADAY PICKS*\n"
            for p in intraday:
                txt += (f"  {p.get('action')} {p.get('symbol','')} "
                        f"({p.get('conviction','?')}/10)\n"
                        f"  Entry Rs.{p.get('entry','?')} "
                        f"T1 Rs.{p.get('target1','?')} "
                        f"SL Rs.{p.get('stoploss','?')}\n"
                        f"  {p.get('reasoning','')}\n\n")
            self.send_message(txt)
        if swing:
            txt = "*SWING PICKS*\n"
            for p in swing:
                txt += (f"  {p.get('action')} {p.get('symbol','')} "
                        f"({p.get('conviction','?')}/10)\n"
                        f"  Entry Rs.{p.get('entry','?')} "
                        f"T1 Rs.{p.get('target1','?')} "
                        f"SL Rs.{p.get('stoploss','?')}\n"
                        f"  {p.get('reasoning','')}\n\n")
            self.send_message(txt)

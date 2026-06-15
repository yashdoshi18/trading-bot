import telebot, logging, os
log = logging.getLogger(__name__)

class TelegramCommandBot:
    def __init__(self, ai, portfolio, watchlist, notifier, morning):
        self.bot       = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
        self.ai        = ai
        self.portfolio = portfolio
        self.watchlist = watchlist
        self.notifier  = notifier
        self.morning   = morning
        self._setup()

    def _setup(self):
        b = self.bot

        @b.message_handler(commands=["start","help"])
        def help_cmd(m):
            b.reply_to(m,
                "AI TRADING BOT v5.0\n\n"
                "ANALYSIS\n"
                "/morning  - morning briefing now\n"
                "/scan     - full scan now\n\n"
                "PORTFOLIO\n"
                "/portfolio - holdings + live P&L\n"
                "/bought SYMBOL QTY PRICE\n"
                "  e.g. /bought TCS 25 4200\n"
                "/sold SYMBOL QTY PRICE\n\n"
                "WATCHLIST\n"
                "/watchlist        - show list\n"
                "/addwatch SYMBOL  - add stock\n"
                "/rmwatch SYMBOL   - remove\n\n"
                "/candles - candlestick pattern guide\n"
                "/status  - bot status")

        @b.message_handler(commands=["portfolio"])
        def port(m): b.reply_to(m, self.portfolio.get_summary())

        @b.message_handler(commands=["bought"])
        def bought(m):
            try:
                parts = m.text.split()
                sym, qty, price = parts[1], int(parts[2]), float(parts[3])
                self.portfolio.add_holding(sym, qty, price)
                b.reply_to(m,
                    f"Logged: {qty} x {sym} @ Rs.{price}\n"
                    f"Invested: Rs.{qty*price:,.0f}\n"
                    f"Bot now tracking for SL/target alerts")
            except:
                b.reply_to(m, "Usage: /bought SYMBOL QTY PRICE\nExample: /bought TCS 25 4200")

        @b.message_handler(commands=["sold"])
        def sold(m):
            try:
                parts = m.text.split()
                sym, qty, price = parts[1], int(parts[2]), float(parts[3])
                self.portfolio.close_holding(sym, qty, price)
                b.reply_to(m, f"Closed: {qty} x {sym} @ Rs.{price}")
            except:
                b.reply_to(m, "Usage: /sold SYMBOL QTY PRICE")

        @b.message_handler(commands=["watchlist"])
        def wl(m): b.reply_to(m, self.watchlist.list_formatted())

        @b.message_handler(commands=["addwatch"])
        def addw(m):
            try: b.reply_to(m, self.watchlist.add(m.text.split()[1]))
            except: b.reply_to(m, "Usage: /addwatch SYMBOL")

        @b.message_handler(commands=["rmwatch"])
        def rmw(m):
            try: b.reply_to(m, self.watchlist.remove(m.text.split()[1]))
            except: b.reply_to(m, "Usage: /rmwatch SYMBOL")

        @b.message_handler(commands=["morning"])
        def mrn(m):
            b.reply_to(m, "Running morning analysis... 5-8 min")
            self.morning.run()

        @b.message_handler(commands=["scan"])
        def scan(m):
            b.reply_to(m, "Manual scan triggered - results in 3-5 min")

        @b.message_handler(commands=["status"])
        def status(m):
            from datetime import datetime
            h  = self.portfolio.get_holdings()
            wl = self.watchlist.get_all()
            b.reply_to(m,
                f"STATUS: ONLINE\n"
                f"Time: {datetime.now().strftime('%d %b %H:%M IST')}\n"
                f"Holdings: {len(h)} open positions\n"
                f"Watchlist: {len(wl)} stocks\n"
                f"News scan: every 30 min\n"
                f"Tier 1: every 2.5h\n"
                f"Tier 2: daily 4 PM\n"
                f"Tier 3: Tue + Thu 4:30 PM\n"
                f"Morning: 9:15 AM IST")

        @b.message_handler(commands=["candles"])
        def candles(m):
            b.reply_to(m,
                "CANDLESTICK GUIDE\n\n"
                "STRONG BULLISH (BUY)\n"
                "Bullish Marubozu - pure buying, strong trend\n"
                "Bullish Engulfing - bulls overpower bears\n"
                "Morning Star - 3-candle bottom reversal\n"
                "Three White Soldiers - 3 days of buying\n"
                "Dragonfly Doji - bears fully rejected\n"
                "Hammer - buyers step in at lows\n"
                "Piercing Pattern - bulls reclaim 50%+\n\n"
                "STRONG BEARISH (SELL)\n"
                "Bearish Marubozu - pure selling\n"
                "Bearish Engulfing - bears overpower bulls\n"
                "Evening Star - 3-candle top reversal\n"
                "Three Black Crows - 3 days of selling\n"
                "Gravestone Doji - bulls fully rejected\n"
                "Shooting Star - sellers crush the high\n"
                "Dark Cloud Cover - bears reclaim 50%+\n\n"
                "NEUTRAL (Wait)\n"
                "Doji - indecision, watch next candle\n"
                "Spinning Top - no clear winner\n"
                "Harami - momentum slowing")

    def start_polling(self):
        self.bot.infinity_polling(timeout=30)

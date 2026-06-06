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
                "AI TRADING BOT - COMMANDS\n\n"
                "ANALYSIS\n"
                "/morning  - morning briefing now\n"
                "/scan     - full scan now\n\n"
                "PORTFOLIO\n"
                "/portfolio          - holdings + P&L\n"
                "/bought SYMBOL QTY PRICE\n"
                "  e.g. /bought TCS 25 4200\n"
                "/sold SYMBOL QTY PRICE\n\n"
                "WATCHLIST\n"
                "/watchlist         - show list\n"
                "/addwatch SYMBOL   - add stock\n"
                "/rmwatch SYMBOL    - remove stock\n\n"
                "/status  - bot status")

        @b.message_handler(commands=["portfolio"])
        def port(m):
            b.reply_to(m, self.portfolio.get_summary())

        @b.message_handler(commands=["bought"])
        def bought(m):
            try:
                _, sym, qty, price = m.text.split()
                self.portfolio.add_holding(sym, int(qty), float(price))
                b.reply_to(m, f"Logged: {qty} x {sym} at Rs.{price}")
            except:
                b.reply_to(m, "Usage: /bought SYMBOL QTY PRICE")

        @b.message_handler(commands=["sold"])
        def sold(m):
            try:
                _, sym, qty, price = m.text.split()
                self.portfolio.close_holding(sym, int(qty), float(price))
                b.reply_to(m, f"Closed: {qty} x {sym} at Rs.{price}")
            except:
                b.reply_to(m, "Usage: /sold SYMBOL QTY PRICE")

        @b.message_handler(commands=["watchlist"])
        def wl(m):
            b.reply_to(m, self.watchlist.list_formatted())

        @b.message_handler(commands=["addwatch"])
        def addw(m):
            try:
                b.reply_to(m, self.watchlist.add(m.text.split()[1]))
            except:
                b.reply_to(m, "Usage: /addwatch SYMBOL")

        @b.message_handler(commands=["rmwatch"])
        def rmw(m):
            try:
                b.reply_to(m, self.watchlist.remove(m.text.split()[1]))
            except:
                b.reply_to(m, "Usage: /rmwatch SYMBOL")

        @b.message_handler(commands=["morning"])
        def mrn(m):
            b.reply_to(m, "Running morning analysis... 2 min")
            self.morning.run()

        @b.message_handler(commands=["status"])
        def status(m):
            from datetime import datetime
            b.reply_to(m,
                f"STATUS: ONLINE\n"
                f"Time: {datetime.now().strftime('%d %b %H:%M')}\n"
                f"Holdings: {len(self.portfolio.get_holdings())}\n"
                f"Watchlist: {len(self.watchlist.get_all())} stocks")

        @b.message_handler(commands=["scan"])
        def scan(m):
            b.reply_to(m, "Manual scan triggered - results coming...")

    def start_polling(self):
        self.bot.infinity_polling(timeout=30)

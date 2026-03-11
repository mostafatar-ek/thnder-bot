"""
Telegram command handler — lets the user manage portfolio via chat commands.

Supported commands:
    /buy TICKER PRICE    — Add a stock to portfolio (e.g. /buy ETEL 84.80)
    /sell TICKER         — Remove a stock from portfolio (e.g. /sell ETEL)
    /portfolio           — Show all current holdings
    /scan                — Trigger an immediate market scan
    /help                — Show available commands
"""

import logging
import requests

from config import Config
from portfolio import add_holding, list_holdings, remove_holding

logger = logging.getLogger(__name__)

# Track the last processed update to avoid duplicate handling
_last_update_id = 0


def _get_updates(offset: int = 0, timeout: int = 0) -> list[dict]:
    """Fetch new messages from Telegram using long polling."""
    bot_token = Config.TELEGRAM_BOT_TOKEN
    if not bot_token:
        return []

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        resp = requests.get(
            url,
            params={"offset": offset, "timeout": timeout},
            timeout=timeout + 10,
        )
        if resp.status_code == 200:
            return resp.json().get("result", [])
    except Exception as e:
        logger.error(f"Failed to get Telegram updates: {e}")
    return []


def _reply(chat_id: str, text: str) -> None:
    """Send a reply message to the user."""
    bot_token = Config.TELEGRAM_BOT_TOKEN
    if not bot_token:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=15,
        )
    except Exception as e:
        logger.error(f"Failed to reply on Telegram: {e}")


def _handle_buy(chat_id: str, args: list[str]) -> None:
    """Handle /buy TICKER PRICE command."""
    if len(args) < 2:
        _reply(chat_id, "❌ Usage: `/buy TICKER PRICE`\nExample: `/buy ETEL 84.80`")
        return

    ticker = args[0].upper()
    try:
        price = float(args[1])
    except ValueError:
        _reply(chat_id, f"❌ Invalid price: `{args[1]}`\nUse a number like `84.80`")
        return

    shares = 0.0
    if len(args) >= 3:
        try:
            shares = float(args[2])
        except ValueError:
            pass

    holding = add_holding(ticker, price, shares=shares)
    _reply(
        chat_id,
        f"✅ *Added to portfolio*\n"
        f"📊 {holding.ticker}\n"
        f"💰 Buy price: {holding.buy_price:.2f} EGP\n"
        f"📅 Date: {holding.buy_date}\n\n"
        f"I'll monitor it and alert you when to sell! 🔔",
    )


def _handle_sell(chat_id: str, args: list[str]) -> None:
    """Handle /sell TICKER command."""
    if not args:
        _reply(chat_id, "❌ Usage: `/sell TICKER`\nExample: `/sell ETEL`")
        return

    ticker = args[0].upper()
    if remove_holding(ticker):
        _reply(chat_id, f"✅ *Removed {ticker}* from portfolio.\nNo more sell alerts for it.")
    else:
        _reply(chat_id, f"❌ `{ticker}` not found in your portfolio.")


def _handle_portfolio(chat_id: str) -> None:
    """Handle /portfolio command."""
    holdings = list_holdings()
    if not holdings:
        _reply(chat_id, "📂 Your portfolio is empty.\n\nAdd stocks with:\n`/buy TICKER PRICE`")
        return

    lines = ["📊 *Your Portfolio*\n"]
    for h in holdings:
        lines.append(
            f"• *{h.ticker}*\n"
            f"   💰 Bought at: {h.buy_price:.2f} EGP\n"
            f"   📅 Date: {h.buy_date}"
        )
        if h.shares > 0:
            lines[-1] += f"\n   📦 Shares: {h.shares:.1f}"

    lines.append(f"\n_Total: {len(holdings)} stock(s)_")
    _reply(chat_id, "\n".join(lines))


def _handle_help(chat_id: str) -> None:
    """Handle /help command."""
    _reply(
        chat_id,
        "🤖 *Thndr Bot Commands*\n\n"
        "📥 `/buy TICKER PRICE` — Add stock to portfolio\n"
        "   _Example:_ `/buy ETEL 84.80`\n"
        "   _With shares:_ `/buy ETEL 84.80 10`\n\n"
        "📤 `/sell TICKER` — Remove stock from portfolio\n"
        "   _Example:_ `/sell ETEL`\n\n"
        "📊 `/portfolio` — View your holdings\n\n"
        "🔍 `/scan` — Trigger immediate market scan\n\n"
        "❓ `/help` — Show this message\n\n"
        "The bot scans EGX every 30 min and alerts you for:\n"
        "📈 *BUY* — when a stock scores above 75/100\n"
        "🔴 *SELL* — when your holdings hit sell signals",
    )


# Flag set by /scan command, checked by bot.py
_scan_requested = False


def _handle_scan(chat_id: str) -> None:
    """Handle /scan command — sets a flag for bot.py to pick up."""
    global _scan_requested
    _scan_requested = True
    _reply(chat_id, "🔍 *Scan requested!*\nRunning market scan now... I'll send results shortly.")


def is_scan_requested() -> bool:
    """Check if user requested a scan via Telegram."""
    global _scan_requested
    if _scan_requested:
        _scan_requested = False
        return True
    return False


def process_updates() -> None:
    """Check for new Telegram messages and handle commands."""
    global _last_update_id

    allowed_chat_id = Config.TELEGRAM_CHAT_ID
    if not allowed_chat_id:
        return

    updates = _get_updates(offset=_last_update_id + 1, timeout=0)

    for update in updates:
        _last_update_id = update["update_id"]

        message = update.get("message")
        if not message:
            continue

        chat_id = str(message["chat"]["id"])
        text = message.get("text", "").strip()

        # Only respond to the authorized user
        if chat_id != allowed_chat_id:
            logger.warning(f"Ignoring message from unauthorized chat: {chat_id}")
            continue

        if not text.startswith("/"):
            continue

        parts = text.split()
        command = parts[0].lower().split("@")[0]  # handle /buy@botname format
        args = parts[1:]

        logger.info(f"Telegram command: {command} {args}")

        if command == "/buy":
            _handle_buy(chat_id, args)
        elif command == "/sell":
            _handle_sell(chat_id, args)
        elif command == "/portfolio":
            _handle_portfolio(chat_id)
        elif command == "/scan":
            _handle_scan(chat_id)
        elif command in ("/help", "/start"):
            _handle_help(chat_id)
        else:
            _reply(chat_id, f"❓ Unknown command: `{command}`\nType /help for available commands.")

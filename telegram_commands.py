"""
Telegram command handler — lets the user manage portfolio via chat commands.

Supported commands:
    /buy TICKER PRICE    — Add a stock to portfolio (e.g. /buy ETEL 84.80)
    /sell TICKER         — Remove a stock from portfolio (e.g. /sell ETEL)
    /portfolio           — Show all current holdings with live P&L
    /alert TICKER PRICE  — Set a price alert (e.g. /alert COMI 130)
    /alerts              — View active price alerts
    /scan                — Trigger an immediate market scan
    /status              — Show bot status and market info
    /help                — Show available commands
"""

import logging
import time
from datetime import datetime

import requests

from config import Config
from portfolio import (
    add_alert, add_holding, list_holdings, load_alerts,
    remove_alerts, remove_holding,
)
from stock_data import fetch_egx30, get_current_price

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
    """Handle /portfolio command — shows holdings with live P&L."""
    holdings = list_holdings()
    if not holdings:
        _reply(chat_id, "📂 Your portfolio is empty.\n\nAdd stocks with:\n`/buy TICKER PRICE`")
        return

    lines = ["📊 *Your Portfolio*\n"]
    total_invested = 0.0
    total_current = 0.0

    for h in holdings:
        current_price = get_current_price(h.ticker)
        if current_price is not None:
            pnl_pct = ((current_price - h.buy_price) / h.buy_price) * 100
            pnl_icon = "📈" if pnl_pct >= 0 else "📉"
            price_line = f"   💵 Now: {current_price:.2f} EGP ({pnl_pct:+.1f}%)"
            if h.shares > 0:
                total_invested += h.buy_price * h.shares
                total_current += current_price * h.shares
        else:
            pnl_icon = "❓"
            price_line = "   💵 Now: _unavailable_"

        lines.append(
            f"{pnl_icon} *{h.ticker}*\n"
            f"   🏷️ Bought: {h.buy_price:.2f} EGP\n"
            f"{price_line}\n"
            f"   📅 {h.buy_date}"
        )
        if h.shares > 0:
            lines[-1] += f" • {h.shares:.1f} shares"

    lines.append(f"\n_Total: {len(holdings)} stock(s)_")
    if total_invested > 0:
        total_pnl = ((total_current - total_invested) / total_invested) * 100
        lines.append(f"_Invested: {total_invested:.0f} EGP → Now: {total_current:.0f} EGP ({total_pnl:+.1f}%)_")

    lines.append("\n📌 _Prices are closing prices._")
    _reply(chat_id, "\n".join(lines))


def _handle_help(chat_id: str) -> None:
    """Handle /help command."""
    _reply(
        chat_id,
        "🤖 *Thndr Bot Commands*\n\n"
        "*Portfolio:*\n"
        "📥 `/buy TICKER PRICE` — Add stock\n"
        "   `/buy ETEL 84.80` or `/buy ETEL 84.80 10`\n"
        "📤 `/sell TICKER` — Remove stock\n"
        "📊 `/portfolio` — View holdings with live P&L\n\n"
        "*Alerts:*\n"
        "🔔 `/alert TICKER PRICE` — Price alert\n"
        "   `/alert COMI 130` (above) or `/alert COMI 120 below`\n"
        "📋 `/alerts` — View active alerts\n"
        "❌ `/removealert TICKER` — Remove alerts\n\n"
        "*Market:*\n"
        "🔍 `/scan` — Trigger market scan\n"
        "📈 `/status` — Bot status & EGX30 index\n"
        "❓ `/help` — This message\n\n"
        "_Scans EGX every 5 min during market hours_\n"
        "_Sun-Thu 10AM-3PM Cairo time_",
    )


def _handle_alert(chat_id: str, args: list[str]) -> None:
    """Handle /alert TICKER PRICE [above|below] command."""
    if len(args) < 2:
        _reply(chat_id, "❌ Usage: `/alert TICKER PRICE`\nExample: `/alert COMI 130`\nOr: `/alert COMI 120 below`")
        return

    ticker = args[0].upper()
    try:
        price = float(args[1])
    except ValueError:
        _reply(chat_id, f"❌ Invalid price: `{args[1]}`")
        return

    direction = "above"
    if len(args) >= 3 and args[2].lower() in ("below", "under", "down"):
        direction = "below"

    alert = add_alert(ticker, price, direction)
    arrow = "⬆️" if direction == "above" else "⬇️"
    _reply(
        chat_id,
        f"🔔 *Price alert set!*\n"
        f"{arrow} {alert.ticker} — alert when price goes *{direction}* {alert.target_price:.2f} EGP",
    )


def _handle_alerts(chat_id: str) -> None:
    """Handle /alerts — show active price alerts."""
    alerts = load_alerts()
    if not alerts:
        _reply(chat_id, "🔕 No active price alerts.\n\nSet one with:\n`/alert TICKER PRICE`")
        return

    lines = ["🔔 *Active Price Alerts*\n"]
    for a in alerts:
        arrow = "⬆️" if a.direction == "above" else "⬇️"
        lines.append(f"{arrow} *{a.ticker}* — {a.direction} {a.target_price:.2f} EGP")

    lines.append(f"\n_Total: {len(alerts)} alert(s)_")
    lines.append("Remove with: `/removealert TICKER`")
    _reply(chat_id, "\n".join(lines))


def _handle_remove_alert(chat_id: str, args: list[str]) -> None:
    """Handle /removealert TICKER."""
    if not args:
        _reply(chat_id, "❌ Usage: `/removealert TICKER`")
        return

    ticker = args[0].upper()
    count = remove_alerts(ticker)
    if count > 0:
        _reply(chat_id, f"✅ Removed {count} alert(s) for {ticker}")
    else:
        _reply(chat_id, f"❌ No alerts found for {ticker}")


def _handle_status(chat_id: str) -> None:
    """Handle /status — show bot status and EGX30."""
    from bot import EGYPT_TZ, is_market_hours

    cairo_now = datetime.now(EGYPT_TZ)
    market_open = is_market_hours()
    market_icon = "🟢" if market_open else "🔴"
    market_str = "OPEN" if market_open else "CLOSED"

    lines = [
        "🤖 *Bot Status*\n",
        f"⏰ Cairo time: {cairo_now.strftime('%H:%M %A')}",
        f"{market_icon} Market: *{market_str}*",
        f"⏱️ Scan interval: {Config.SCAN_INTERVAL_MINUTES} min",
    ]

    # EGX30 index
    egx30 = fetch_egx30()
    if egx30:
        idx_icon = "📈" if egx30["change"] >= 0 else "📉"
        lines.append(f"\n{idx_icon} *EGX30 Index*")
        lines.append(f"   Value: {egx30['value']:,.0f}")
        lines.append(f"   Change: {egx30['change']:+.0f} ({egx30['change_pct']:+.1f}%)")

    # Portfolio summary
    holdings = list_holdings()
    alerts = load_alerts()
    lines.append(f"\n📊 Portfolio: {len(holdings)} stock(s)")
    lines.append(f"🔔 Alerts: {len(alerts)} active")

    if market_open:
        lines.append("\n_Next scan coming soon..._")
    else:
        lines.append("\n_Scans resume when market opens (Sun-Thu 10AM)_")

    _reply(chat_id, "\n".join(lines))


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
        elif command == "/alert":
            _handle_alert(chat_id, args)
        elif command == "/alerts":
            _handle_alerts(chat_id)
        elif command == "/removealert":
            _handle_remove_alert(chat_id, args)
        elif command == "/status":
            _handle_status(chat_id)
        elif command == "/scan":
            _handle_scan(chat_id)
        elif command in ("/help", "/start"):
            _handle_help(chat_id)
        else:
            _reply(chat_id, f"❓ Unknown command: `{command}`\nType /help for available commands.")

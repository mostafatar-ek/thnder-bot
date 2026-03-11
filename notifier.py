"""
Notification system — sends deal alerts via Telegram Bot (HTTPS).
Works on all cloud platforms including Railway.
"""

import logging
from datetime import datetime

import requests

from analyzer import DealResult, SellResult
from config import Config

logger = logging.getLogger(__name__)


def _build_telegram_message(deals: list[DealResult]) -> str:
    """Build a formatted Telegram message from deal results."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"📈 *Thndr Deal Alert*",
        f"🕐 {now}",
        f"Found *{len(deals)}* deal(s) scoring above *{Config.MIN_DEAL_SCORE}*\n",
    ]

    for deal in deals:
        if deal.score >= 85:
            icon = "🔥"
        elif deal.score >= 70:
            icon = "⭐"
        else:
            icon = "📊"

        lines.append(f"{icon} *{deal.ticker}*")
        lines.append(f"   💰 Price: {deal.current_price:.2f} EGP")
        lines.append(f"   📊 Score: *{deal.score:.0f}/100*")
        lines.append(f"   📋 {deal.recommendation}")

        for s in deal.signals:
            mark = "✅" if s.bullish else "❌"
            lines.append(f"      {mark} {s.detail}")
        lines.append("")

    lines.append("⚠️ _Not financial advice. Always do your own research._")
    lines.append("📌 _Prices are closing prices (may differ from live)._")

    return "\n".join(lines)


def _build_sell_message(sell_results: list[SellResult]) -> str:
    """Build a formatted Telegram message for sell alerts."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"🔴 *Thndr SELL Alert*",
        f"🕐 {now}",
        f"Found *{len(sell_results)}* sell signal(s)\n",
    ]

    for sr in sell_results:
        if sr.recommendation in ("SELL NOW", "STRONG SELL"):
            icon = "🚨"
        elif sr.recommendation == "SELL":
            icon = "🔴"
        else:
            icon = "⚠️"

        pnl_icon = "📈" if sr.pnl_percent >= 0 else "📉"

        lines.append(f"{icon} *{sr.ticker}*")
        lines.append(f"   💰 Current: {sr.current_price:.2f} EGP")
        lines.append(f"   🏷️ Bought at: {sr.buy_price:.2f} EGP")
        lines.append(f"   {pnl_icon} P&L: *{sr.pnl_percent:+.1f}%*")
        lines.append(f"   📋 {sr.recommendation}")

        for s in sr.signals:
            if s.urgency == "HIGH":
                mark = "🚨"
            elif s.urgency == "MEDIUM":
                mark = "⚠️"
            else:
                mark = "ℹ️"
            lines.append(f"      {mark} {s.detail}")
        lines.append("")

    lines.append("⚠️ _Not financial advice. Always do your own research._")
    lines.append("📌 _Prices are closing prices (may differ from live)._")

    return "\n".join(lines)


def _send_telegram(message: str) -> bool:
    """Send a message via Telegram Bot API."""
    bot_token = Config.TELEGRAM_BOT_TOKEN
    chat_id = Config.TELEGRAM_CHAT_ID

    if not bot_token or not chat_id:
        logger.error(
            f"Telegram not configured! token={'SET' if bot_token else 'EMPTY'}, "
            f"chat_id={'SET' if chat_id else 'EMPTY'}"
        )
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        logger.info(f"Sending Telegram message to chat {chat_id}...")
        resp = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
            },
            timeout=15,
        )

        if resp.status_code == 200:
            logger.info("Telegram message sent successfully!")
            return True
        else:
            logger.error(f"Telegram API error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}", exc_info=True)
        return False


def send_deal_alert(deals: list[DealResult]) -> bool:
    """Send a Telegram alert with the top deals."""
    if not deals:
        logger.info("No deals to report — skipping notification.")
        return False

    message = _build_telegram_message(deals)
    return _send_telegram(message)


def send_sell_alert(sell_results: list[SellResult]) -> bool:
    """Send a Telegram alert with sell signals for held stocks."""
    if not sell_results:
        logger.info("No sell signals to report — skipping notification.")
        return False

    message = _build_sell_message(sell_results)
    return _send_telegram(message)

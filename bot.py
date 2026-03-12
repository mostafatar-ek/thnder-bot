"""
Thndr EGX Deal-Finder Bot
==========================
Continuously scans Egyptian Exchange stocks, scores them using technical
analysis, and sends you a Telegram alert when a great deal is found.

Usage:
    python bot.py              # Run one scan
    python bot.py --loop       # Run continuously on a schedule
    python bot.py --test        # Send a test notification to verify config
"""

import argparse
import logging
import sys
import time
from datetime import datetime

import pytz

from analyzer import DealResult, check_sell_signals, screen_all_stocks
from config import Config
from notifier import send_deal_alert, send_scan_summary, send_sell_alert, send_daily_summary, send_price_alert
from portfolio import add_holding, list_holdings, load_alerts, load_portfolio, remove_holding, remove_triggered_alert
from stock_data import EGX_TICKERS, fetch_all_stocks, fetch_egx30, fetch_stock_data, get_current_price
from telegram_commands import is_scan_requested, process_updates

# ── Logging setup ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# EGX trading hours (Egypt timezone = Africa/Cairo)
EGYPT_TZ = pytz.timezone("Africa/Cairo")
EGX_OPEN_HOUR = 10    # 10:00 AM
EGX_CLOSE_HOUR = 14   # 2:00 PM (market closes ~2:30, we scan until 3 PM for closing prices)
EGX_CLOSE_MINUTE = 59
EGX_TRADING_DAYS = (6, 0, 1, 2, 3)  # Sunday=6, Monday=0, Tuesday=1, Wednesday=2, Thursday=3


def is_market_hours() -> bool:
    """Check if we're within EGX trading hours (Sun-Thu, 10AM-3PM Cairo time)."""
    now = datetime.now(EGYPT_TZ)
    weekday = now.weekday()  # Monday=0, Sunday=6
    hour = now.hour
    minute = now.minute

    if weekday not in EGX_TRADING_DAYS:
        return False

    # 10:00 AM to 2:59 PM
    if hour < EGX_OPEN_HOUR or (hour > EGX_CLOSE_HOUR or (hour == EGX_CLOSE_HOUR and minute > EGX_CLOSE_MINUTE)):
        return False

    return True


def run_scan(forced: bool = False) -> list[DealResult]:
    """Execute one full scan cycle. If forced=True (from /scan), always send results."""
    logger.info("=" * 60)
    logger.info("Starting EGX scan...")
    logger.info(f"Watching {len(EGX_TICKERS)} stocks | Min score: {Config.MIN_DEAL_SCORE}")
    logger.info("=" * 60)

    # 1. Fetch data
    stock_data = fetch_all_stocks()
    if not stock_data:
        logger.error("No stock data retrieved. Check your internet connection.")
        return []

    # 2. Analyze
    results = screen_all_stocks(stock_data)

    # 3. Filter deals
    deals = [r for r in results if r.is_deal]

    # 4. Print summary
    logger.info("-" * 60)
    logger.info("SCAN RESULTS:")
    for r in results:
        marker = "⭐" if r.is_deal else "  "
        logger.info(
            f"  {marker} {r.ticker:12s} | Score: {r.score:5.1f} | "
            f"{r.recommendation:15s} | Price: {r.current_price:.2f} EGP"
        )
    logger.info("-" * 60)

    if forced:
        # /scan command: always send full summary
        logger.info("Sending scan summary (forced by /scan)...")
        send_scan_summary(results)
    elif deals:
        logger.info(f"🔔 {len(deals)} deal(s) found! Sending alert...")
        send_deal_alert(deals)
    else:
        logger.info("No deals scoring above threshold this scan.")

    # 5. Check price alerts
    check_price_alerts()

    # 6. Check sell signals for portfolio holdings
    holdings = load_portfolio()
    if holdings:
        logger.info(f"Checking sell signals for {len(holdings)} holding(s)...")
        sell_alerts = []
        for holding in holdings:
            df = fetch_stock_data(holding.ticker, period="3mo")
            if df is None or len(df) < Config.LONG_MA_PERIOD:
                logger.warning(f"Skipping sell check for {holding.ticker}: insufficient data")
                continue
            sell_result = check_sell_signals(holding.ticker, df, holding.buy_price)
            if sell_result.should_sell:
                sell_alerts.append(sell_result)
                logger.info(
                    f"⚠️ SELL signal for {holding.ticker}: {sell_result.recommendation} "
                    f"(P&L: {sell_result.pnl_percent:+.1f}%)"
                )
            else:
                logger.info(
                    f"✅ {holding.ticker}: {sell_result.recommendation} "
                    f"(P&L: {sell_result.pnl_percent:+.1f}%)"
                )

        if sell_alerts:
            logger.info(f"🔴 {len(sell_alerts)} sell alert(s)! Sending notification...")
            send_sell_alert(sell_alerts)
    else:
        logger.info("No holdings in portfolio — skipping sell check.")

    return deals


def check_price_alerts() -> None:
    """Check all price alerts and notify if triggered."""
    alerts = load_alerts()
    if not alerts:
        return

    triggered = []
    for alert in alerts:
        price = get_current_price(alert.ticker)
        if price is None:
            continue

        if alert.direction == "above" and price >= alert.target_price:
            triggered.append((alert, price))
        elif alert.direction == "below" and price <= alert.target_price:
            triggered.append((alert, price))

    for alert, price in triggered:
        send_price_alert(alert, price)
        remove_triggered_alert(alert)
        logger.info(f"🔔 Price alert triggered: {alert.ticker} {alert.direction} {alert.target_price} (now {price})")


def send_daily_recap() -> None:
    """Send end-of-day summary at market close."""
    logger.info("Sending daily summary...")

    # Fetch EGX30
    egx30 = fetch_egx30()

    # Portfolio P&L
    holdings = load_portfolio()
    portfolio_data = []
    for h in holdings:
        price = get_current_price(h.ticker)
        if price is not None:
            pnl_pct = ((price - h.buy_price) / h.buy_price) * 100
            portfolio_data.append((h, price, pnl_pct))

    send_daily_summary(egx30, portfolio_data)


def run_loop():
    """Run scans on a schedule, checking Telegram commands between scans."""
    interval = Config.SCAN_INTERVAL_MINUTES * 60
    logger.info(f"Bot running in loop mode — scanning every {Config.SCAN_INTERVAL_MINUTES} minutes")
    logger.info("Active hours: Sun-Thu 10:00 AM – 3:00 PM (Cairo time)")
    logger.info("Listening for Telegram commands (/buy, /sell, /portfolio, /scan)")
    logger.info("Press Ctrl+C to stop.\n")

    next_scan_time = 0  # Run first scan immediately
    was_sleeping = False
    daily_summary_sent = False

    while True:
        try:
            # Always check for Telegram commands (even outside market hours)
            process_updates()

            now = time.time()
            scan_requested = is_scan_requested()
            cairo_now = datetime.now(EGYPT_TZ)

            # Reset daily summary flag at midnight
            if cairo_now.hour == 0 and daily_summary_sent:
                daily_summary_sent = False

            # Check market hours
            if not is_market_hours() and not scan_requested:
                # Send daily summary at 3 PM (just after market close)
                if (cairo_now.hour == 15 and cairo_now.minute < 10
                        and not daily_summary_sent
                        and cairo_now.weekday() in EGX_TRADING_DAYS):
                    send_daily_recap()
                    daily_summary_sent = True

                if not was_sleeping:
                    cairo_str = cairo_now.strftime("%H:%M %A")
                    logger.info(f"💤 Market closed ({cairo_str} Cairo). Sleeping until next session...")
                    was_sleeping = True
                time.sleep(10)  # Check Telegram every 10s while sleeping
                continue

            if was_sleeping:
                logger.info("☀️ Market hours — resuming scans!")
                was_sleeping = False
                next_scan_time = 0  # Scan immediately on market open

            # Run scan if it's time or user requested one
            if now >= next_scan_time or scan_requested:
                run_scan(forced=scan_requested)
                next_scan_time = time.time() + interval
                next_str = datetime.now(EGYPT_TZ).strftime("%H:%M:%S")
                logger.info(f"Next scan in {Config.SCAN_INTERVAL_MINUTES} min (since {next_str} Cairo)...\n")

            # Short sleep so we check Telegram frequently
            time.sleep(2)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Error during loop: {e}", exc_info=True)
            logger.info("Retrying in 60 seconds...")
            time.sleep(60)


def send_test_notification():
    """Send a test Telegram notification to verify configuration."""
    logger.info("Sending test notification...")
    test_deal = DealResult(
        ticker="TEST.CA",
        score=90.0,
        current_price=42.50,
        recommendation="STRONG BUY (TEST)",
    )
    success = send_deal_alert([test_deal])
    if success:
        logger.info("Test notification sent! Check Telegram.")
    else:
        logger.error("Test notification failed. Check your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")


def main():
    parser = argparse.ArgumentParser(description="Thndr EGX Deal-Finder Bot")
    parser.add_argument("--loop", action="store_true", help="Run continuously on a schedule")
    parser.add_argument("--test", action="store_true", help="Send a test Telegram notification")
    parser.add_argument("--add", nargs=2, metavar=("TICKER", "PRICE"),
                        help="Add a stock to portfolio: --add COMI 125.50")
    parser.add_argument("--remove", metavar="TICKER", help="Remove a stock from portfolio")
    parser.add_argument("--portfolio", action="store_true", help="Show current portfolio")
    args = parser.parse_args()

    if args.test:
        send_test_notification()
    elif args.add:
        ticker, price = args.add
        h = add_holding(ticker, float(price))
        print(f"Added {h.ticker} @ {h.buy_price} EGP")
    elif args.remove:
        if remove_holding(args.remove):
            print(f"Removed {args.remove.upper()} from portfolio")
        else:
            print(f"{args.remove.upper()} not found in portfolio")
    elif args.portfolio:
        holdings = list_holdings()
        if not holdings:
            print("Portfolio is empty. Add stocks with: python bot.py --add TICKER PRICE")
        else:
            print(f"\n{'Ticker':<12} {'Buy Price':>10} {'Date':>12} {'Shares':>8}")
            print("-" * 44)
            for h in holdings:
                print(f"{h.ticker:<12} {h.buy_price:>10.2f} {h.buy_date:>12} {h.shares:>8.1f}")
    elif args.loop:
        run_loop()
    else:
        run_scan()


if __name__ == "__main__":
    main()

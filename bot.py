"""
Thndr EGX Deal-Finder Bot
==========================
Continuously scans Egyptian Exchange stocks, scores them using technical
analysis, and sends you an email when a great deal is found.

Usage:
    python bot.py              # Run one scan
    python bot.py --loop       # Run continuously on a schedule
    python bot.py --test-email # Send a test email to verify config
"""

import argparse
import logging
import sys
import time
from datetime import datetime

from analyzer import DealResult, screen_all_stocks
from config import Config
from notifier import send_deal_alert
from stock_data import EGX_TICKERS, fetch_all_stocks

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


def run_scan() -> list[DealResult]:
    """Execute one full scan cycle."""
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

    if deals:
        logger.info(f"🔔 {len(deals)} deal(s) found! Sending email alert...")
        send_deal_alert(deals)
    else:
        logger.info("No deals scoring above threshold this scan.")

    return deals


def run_loop():
    """Run scans on a schedule repeatedly."""
    interval = Config.SCAN_INTERVAL_MINUTES * 60
    logger.info(f"Bot running in loop mode — scanning every {Config.SCAN_INTERVAL_MINUTES} minutes")
    logger.info("Press Ctrl+C to stop.\n")

    while True:
        try:
            run_scan()
            next_scan = datetime.now().strftime("%H:%M:%S")
            logger.info(f"Next scan in {Config.SCAN_INTERVAL_MINUTES} min (sleeping since {next_scan})...\n")
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Error during scan: {e}", exc_info=True)
            logger.info("Retrying in 60 seconds...")
            time.sleep(60)


def send_test_email():
    """Send a test email to verify configuration."""
    logger.info("Sending test email...")
    test_deal = DealResult(
        ticker="TEST.CA",
        score=90.0,
        current_price=42.50,
        recommendation="STRONG BUY (TEST)",
    )
    success = send_deal_alert([test_deal])
    if success:
        logger.info("Test email sent successfully! Check your inbox.")
    else:
        logger.error("Test email failed. Check your .env config.")


def main():
    parser = argparse.ArgumentParser(description="Thndr EGX Deal-Finder Bot")
    parser.add_argument("--loop", action="store_true", help="Run continuously on a schedule")
    parser.add_argument("--test-email", action="store_true", help="Send a test email")
    args = parser.parse_args()

    if args.test_email:
        send_test_email()
    elif args.loop:
        run_loop()
    else:
        run_scan()


if __name__ == "__main__":
    main()

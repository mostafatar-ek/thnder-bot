"""
Portfolio tracker — tracks stocks you bought so the bot knows when to alert SELL.
Also handles price alerts.
Stores data in JSON files.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "portfolio.json")
ALERTS_FILE = os.path.join(os.path.dirname(__file__), "price_alerts.json")


@dataclass
class Holding:
    ticker: str
    buy_price: float
    buy_date: str
    shares: float = 0.0
    note: str = ""


def load_portfolio() -> list[Holding]:
    """Load the portfolio from disk."""
    if not os.path.exists(PORTFOLIO_FILE):
        return []
    try:
        with open(PORTFOLIO_FILE, "r") as f:
            data = json.load(f)
        return [Holding(**h) for h in data]
    except Exception as e:
        logger.error(f"Failed to load portfolio: {e}")
        return []


def save_portfolio(holdings: list[Holding]) -> None:
    """Save the portfolio to disk."""
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump([asdict(h) for h in holdings], f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save portfolio: {e}")


def add_holding(ticker: str, buy_price: float, shares: float = 0.0, note: str = "") -> Holding:
    """Add a stock to the portfolio."""
    ticker = ticker.upper()
    if not ticker.endswith(".CA"):
        ticker += ".CA"
    holdings = load_portfolio()
    holding = Holding(
        ticker=ticker,
        buy_price=buy_price,
        buy_date=datetime.now().strftime("%Y-%m-%d"),
        shares=shares,
        note=note,
    )
    holdings.append(holding)
    save_portfolio(holdings)
    logger.info(f"Added {ticker} @ {buy_price} EGP to portfolio")
    return holding


def remove_holding(ticker: str) -> bool:
    """Remove a stock from the portfolio (when sold)."""
    ticker = ticker.upper()
    if not ticker.endswith(".CA"):
        ticker += ".CA"
    holdings = load_portfolio()
    new_holdings = [h for h in holdings if h.ticker != ticker]
    if len(new_holdings) == len(holdings):
        return False
    save_portfolio(new_holdings)
    logger.info(f"Removed {ticker} from portfolio")
    return True


def list_holdings() -> list[Holding]:
    """List all current holdings."""
    return load_portfolio()


# ── Price Alerts ──

@dataclass
class PriceAlert:
    ticker: str
    target_price: float
    direction: str  # "above" or "below"
    created_date: str = ""


def load_alerts() -> list[PriceAlert]:
    """Load price alerts from disk."""
    if not os.path.exists(ALERTS_FILE):
        return []
    try:
        with open(ALERTS_FILE, "r") as f:
            data = json.load(f)
        return [PriceAlert(**a) for a in data]
    except Exception as e:
        logger.error(f"Failed to load alerts: {e}")
        return []


def save_alerts(alerts: list[PriceAlert]) -> None:
    """Save price alerts to disk."""
    try:
        with open(ALERTS_FILE, "w") as f:
            json.dump([asdict(a) for a in alerts], f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save alerts: {e}")


def add_alert(ticker: str, target_price: float, direction: str = "above") -> PriceAlert:
    """Add a price alert."""
    ticker = ticker.upper()
    if not ticker.endswith(".CA"):
        ticker += ".CA"
    alerts = load_alerts()
    alert = PriceAlert(
        ticker=ticker,
        target_price=target_price,
        direction=direction,
        created_date=datetime.now().strftime("%Y-%m-%d"),
    )
    alerts.append(alert)
    save_alerts(alerts)
    logger.info(f"Alert set: {ticker} {direction} {target_price} EGP")
    return alert


def remove_alerts(ticker: str) -> int:
    """Remove all alerts for a ticker. Returns count removed."""
    ticker = ticker.upper()
    if not ticker.endswith(".CA"):
        ticker += ".CA"
    alerts = load_alerts()
    new_alerts = [a for a in alerts if a.ticker != ticker]
    removed = len(alerts) - len(new_alerts)
    if removed > 0:
        save_alerts(new_alerts)
    return removed


def remove_triggered_alert(alert: PriceAlert) -> None:
    """Remove a specific triggered alert."""
    alerts = load_alerts()
    new_alerts = [a for a in alerts if not (
        a.ticker == alert.ticker and
        a.target_price == alert.target_price and
        a.direction == alert.direction
    )]
    save_alerts(new_alerts)

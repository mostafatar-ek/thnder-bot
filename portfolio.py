"""
Portfolio tracker — tracks stocks you bought so the bot knows when to alert SELL.
Stores holdings in a JSON file.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "portfolio.json")


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

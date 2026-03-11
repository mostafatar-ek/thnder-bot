"""
Fetches EGX stock data using yfinance.
Egyptian stocks on Yahoo Finance use the suffix '.CA' (e.g., COMI.CA for CIB).
"""

import logging
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Popular EGX stocks — add/remove tickers as needed
# Format: TICKER.CA for Egyptian Exchange on Yahoo Finance
EGX_TICKERS = [
    "COMI.CA",   # Commercial International Bank (CIB)
    "HRHO.CA",   # Hermes Holding
    "TMGH.CA",   # Talaat Moustafa Group
    "SWDY.CA",   # Elsewedy Electric
    "EAST.CA",   # Eastern Company
    "EFIH.CA",   # EFG Hermes
    "ORWE.CA",   # Oriental Weavers
    "ABUK.CA",   # Abu Qir Fertilizers
    "ESRS.CA",   # Ezz Steel
    "MNHD.CA",   # Madinet Nasr Housing
    "PHDC.CA",   # Palm Hills Development
    "EKHO.CA",   # El Khair for Industry
    "AMOC.CA",   # Alexandria Mineral Oils
    "DCRC.CA",   # Delta Construction
    "JUFO.CA",   # Juhayna Food Industries
    "SKPC.CA",   # Sidi Kerir Petrochemicals
    "ETEL.CA",   # Telecom Egypt
    "CLHO.CA",   # Cleopatra Hospital
    "FWRY.CA",   # Fawry for Banking Technology
    "HELI.CA",   # Heliopolis Housing
]


def fetch_stock_data(
    ticker: str, period: str = "3mo", interval: str = "1d"
) -> Optional[pd.DataFrame]:
    """Download historical OHLCV data for a single ticker."""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        if df.empty:
            logger.warning(f"No data returned for {ticker}")
            return None
        df.index = pd.to_datetime(df.index)
        return df
    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return None


def fetch_all_stocks(
    tickers: list[str] | None = None,
    period: str = "3mo",
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    """Fetch data for all EGX tickers. Returns {ticker: DataFrame}."""
    tickers = tickers or EGX_TICKERS
    results: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        logger.info(f"Fetching {ticker}...")
        df = fetch_stock_data(ticker, period=period, interval=interval)
        if df is not None:
            results[ticker] = df
    logger.info(f"Fetched data for {len(results)}/{len(tickers)} stocks")
    return results


def get_stock_info(ticker: str) -> dict:
    """Get basic stock info (name, sector, market cap, etc.)."""
    try:
        stock = yf.Ticker(ticker)
        return stock.info
    except Exception as e:
        logger.error(f"Error getting info for {ticker}: {e}")
        return {}

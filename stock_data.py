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
    # ── Banks & Financial ──
    "COMI.CA",   # Commercial International Bank (CIB)
    "ADIB.CA",   # Abu Dhabi Islamic Bank Egypt
    "CCAP.CA",   # Citadel Capital (Qalaa Holdings)
    "BINV.CA",   # Beltone Financial
    # ── Real Estate ──
    "TMGH.CA",   # Talaat Moustafa Group
    "PHDC.CA",   # Palm Hills Development
    "HELI.CA",   # Heliopolis Housing
    "OCDI.CA",   # Orascom Development
    # ── Industrial & Energy ──
    "SWDY.CA",   # Elsewedy Electric
    "ABUK.CA",   # Abu Qir Fertilizers
    "AMOC.CA",   # Alexandria Mineral Oils
    "SKPC.CA",   # Sidi Kerir Petrochemicals
    "IRON.CA",   # Egyptian Iron & Steel
    "ACGC.CA",   # Arabian Cement
    "SUGR.CA",   # Delta Sugar
    "MPRC.CA",   # Middle & East for Paper
    # ── Telecom & Tech ──
    "ETEL.CA",   # Telecom Egypt
    "FWRY.CA",   # Fawry for Banking Technology
    "RAYA.CA",   # Raya Holding
    "MTIE.CA",   # Mobinil Telecom (EITC)
    # ── Consumer & Food ──
    "EAST.CA",   # Eastern Company
    "JUFO.CA",   # Juhayna Food Industries
    "POUL.CA",   # Cairo Poultry
    "ISPH.CA",   # Ibnsina Pharma
    "MFPC.CA",   # Misr Fertilizers (MOPCO)
    "GBCO.CA",   # GB Auto
    # ── Other ──
    "HRHO.CA",   # Hermes Holding
    "EFIH.CA",   # EFG Hermes
    "ORWE.CA",   # Oriental Weavers
    "EKHO.CA",   # El Khair for Industry
    "CLHO.CA",   # Cleopatra Hospital
    "ORAS.CA",   # Orascom Construction
    "ALCN.CA",   # Alexandria Containers
    "EGAL.CA",   # EgyptAir
    "EXPA.CA",   # Export Development Bank
    "EGTS.CA",   # Egyptian Transport (EGYTRANS)
    "ETRS.CA",   # Egyptian for Tourism Resorts
    "ELKA.CA",   # El Kahera for Housing
    "SPMD.CA",   # Speed Medical
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

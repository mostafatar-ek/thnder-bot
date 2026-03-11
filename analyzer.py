"""
Technical & fundamental analysis engine.
Scores each stock on multiple signals and returns a deal score (0-100).
"""

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from config import Config

logger = logging.getLogger(__name__)


@dataclass
class DealSignal:
    """Individual analysis signal."""
    name: str
    value: float
    bullish: bool
    weight: float
    detail: str


@dataclass
class DealResult:
    """Full analysis result for one stock."""
    ticker: str
    score: float = 0.0
    signals: list[DealSignal] = field(default_factory=list)
    current_price: float = 0.0
    recommendation: str = ""

    @property
    def is_deal(self) -> bool:
        return self.score >= Config.MIN_DEAL_SCORE


# ──────────────────────── Technical indicators ────────────────────────

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """MACD line and signal line."""
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return macd_line, signal_line


def compute_bollinger_bands(
    series: pd.Series, period: int = 20, std_dev: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (upper, middle, lower) Bollinger Bands."""
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return upper, middle, lower


# ──────────────────────── Analysis functions ────────────────────────

def analyze_rsi(df: pd.DataFrame) -> DealSignal:
    """Check if RSI indicates oversold (buy) or overbought (sell)."""
    rsi = compute_rsi(df["Close"])
    current_rsi = rsi.iloc[-1]

    if np.isnan(current_rsi):
        return DealSignal("RSI", 0, False, 20, "Not enough data for RSI")

    if current_rsi <= Config.RSI_OVERSOLD:
        return DealSignal(
            "RSI", current_rsi, True, 20,
            f"RSI={current_rsi:.1f} — OVERSOLD (below {Config.RSI_OVERSOLD}), potential buy"
        )
    elif current_rsi >= Config.RSI_OVERBOUGHT:
        return DealSignal(
            "RSI", current_rsi, False, 20,
            f"RSI={current_rsi:.1f} — OVERBOUGHT (above {Config.RSI_OVERBOUGHT}), avoid"
        )
    else:
        return DealSignal(
            "RSI", current_rsi, False, 10,
            f"RSI={current_rsi:.1f} — neutral"
        )


def analyze_ma_crossover(df: pd.DataFrame) -> DealSignal:
    """Check for bullish moving-average crossover."""
    short_ma = df["Close"].rolling(window=Config.SHORT_MA_PERIOD).mean()
    long_ma = df["Close"].rolling(window=Config.LONG_MA_PERIOD).mean()

    if short_ma.iloc[-1] is np.nan or long_ma.iloc[-1] is np.nan:
        return DealSignal("MA Crossover", 0, False, 20, "Not enough data for MA")

    crossed_above = (short_ma.iloc[-1] > long_ma.iloc[-1]) and (
        short_ma.iloc[-2] <= long_ma.iloc[-2]
    )
    is_above = short_ma.iloc[-1] > long_ma.iloc[-1]

    if crossed_above:
        return DealSignal(
            "MA Crossover", 1, True, 25,
            f"GOLDEN CROSS — {Config.SHORT_MA_PERIOD}-day MA just crossed above {Config.LONG_MA_PERIOD}-day MA"
        )
    elif is_above:
        return DealSignal(
            "MA Crossover", 0.5, True, 15,
            f"Short MA above long MA — bullish trend"
        )
    else:
        return DealSignal(
            "MA Crossover", 0, False, 5,
            f"Short MA below long MA — bearish trend"
        )


def analyze_macd(df: pd.DataFrame) -> DealSignal:
    """Check MACD crossover."""
    macd_line, signal_line = compute_macd(df["Close"])
    current_macd = macd_line.iloc[-1]
    current_signal = signal_line.iloc[-1]

    if np.isnan(current_macd) or np.isnan(current_signal):
        return DealSignal("MACD", 0, False, 15, "Not enough data for MACD")

    crossed_above = (macd_line.iloc[-1] > signal_line.iloc[-1]) and (
        macd_line.iloc[-2] <= signal_line.iloc[-2]
    )

    if crossed_above:
        return DealSignal(
            "MACD", 1, True, 20,
            "MACD just crossed above signal line — bullish momentum"
        )
    elif current_macd > current_signal:
        return DealSignal(
            "MACD", 0.5, True, 10,
            "MACD above signal line — positive momentum"
        )
    else:
        return DealSignal(
            "MACD", 0, False, 5,
            "MACD below signal line — negative momentum"
        )


def analyze_volume_spike(df: pd.DataFrame) -> DealSignal:
    """Check if today's volume is significantly above average."""
    avg_volume = df["Volume"].rolling(window=20).mean().iloc[-1]
    current_volume = df["Volume"].iloc[-1]

    if avg_volume == 0 or np.isnan(avg_volume):
        return DealSignal("Volume", 0, False, 10, "Not enough volume data")

    ratio = current_volume / avg_volume
    is_spike = ratio >= Config.VOLUME_SPIKE_MULTIPLIER

    if is_spike:
        return DealSignal(
            "Volume Spike", ratio, True, 15,
            f"Volume is {ratio:.1f}x average — high interest"
        )
    else:
        return DealSignal(
            "Volume Spike", ratio, False, 5,
            f"Volume is {ratio:.1f}x average — normal"
        )


def analyze_price_dip(df: pd.DataFrame) -> DealSignal:
    """Check if the stock has dipped significantly from recent high."""
    recent_high = df["Close"].rolling(window=20).max().iloc[-1]
    current_price = df["Close"].iloc[-1]
    dip_pct = ((recent_high - current_price) / recent_high) * 100

    if dip_pct >= Config.PRICE_DIP_PERCENT:
        return DealSignal(
            "Price Dip", dip_pct, True, 15,
            f"Price dipped {dip_pct:.1f}% from 20-day high — potential buy the dip"
        )
    else:
        return DealSignal(
            "Price Dip", dip_pct, False, 5,
            f"Price is {dip_pct:.1f}% below 20-day high — no significant dip"
        )


def analyze_bollinger(df: pd.DataFrame) -> DealSignal:
    """Check if price is near lower Bollinger Band (potential buy)."""
    upper, middle, lower = compute_bollinger_bands(df["Close"])
    current_price = df["Close"].iloc[-1]
    lower_band = lower.iloc[-1]
    upper_band = upper.iloc[-1]

    if np.isnan(lower_band) or np.isnan(upper_band):
        return DealSignal("Bollinger", 0, False, 10, "Not enough data for Bollinger")

    if current_price <= lower_band:
        return DealSignal(
            "Bollinger", 1, True, 15,
            f"Price at/below lower Bollinger Band — oversold bounce potential"
        )
    elif current_price >= upper_band:
        return DealSignal(
            "Bollinger", 0, False, 5,
            f"Price at/above upper Bollinger Band — overbought"
        )
    else:
        return DealSignal(
            "Bollinger", 0.5, False, 5,
            f"Price within Bollinger Bands — neutral"
        )


# ──────────────────────── Main analyzer ────────────────────────

def analyze_stock(ticker: str, df: pd.DataFrame) -> DealResult:
    """Run all analyses on a stock and compute a composite deal score."""
    result = DealResult(ticker=ticker, current_price=round(df["Close"].iloc[-1], 2))

    analyzers = [
        analyze_rsi,
        analyze_ma_crossover,
        analyze_macd,
        analyze_volume_spike,
        analyze_price_dip,
        analyze_bollinger,
    ]

    total_weight = 0.0
    weighted_score = 0.0

    for analyzer in analyzers:
        try:
            signal = analyzer(df)
            result.signals.append(signal)
            total_weight += signal.weight
            if signal.bullish:
                weighted_score += signal.weight
        except Exception as e:
            logger.warning(f"Analyzer {analyzer.__name__} failed for {ticker}: {e}")

    if total_weight > 0:
        result.score = (weighted_score / total_weight) * 100
    else:
        result.score = 0

    # Generate recommendation
    if result.score >= 85:
        result.recommendation = "STRONG BUY"
    elif result.score >= 70:
        result.recommendation = "BUY"
    elif result.score >= 50:
        result.recommendation = "HOLD / WATCH"
    elif result.score >= 30:
        result.recommendation = "WEAK — CAUTION"
    else:
        result.recommendation = "AVOID"

    return result


def screen_all_stocks(stock_data: dict[str, pd.DataFrame]) -> list[DealResult]:
    """Analyze all stocks and return results sorted by score (best first)."""
    results = []
    for ticker, df in stock_data.items():
        if len(df) < Config.LONG_MA_PERIOD:
            logger.warning(f"Skipping {ticker}: not enough data ({len(df)} rows)")
            continue
        result = analyze_stock(ticker, df)
        results.append(result)
        logger.info(f"{ticker}: score={result.score:.1f}, rec={result.recommendation}")

    results.sort(key=lambda r: r.score, reverse=True)
    return results


# ──────────────────────── Sell signal analysis ────────────────────────

@dataclass
class SellSignal:
    """Individual sell signal."""
    name: str
    detail: str
    urgency: str  # "HIGH", "MEDIUM", "LOW"


@dataclass
class SellResult:
    """Sell analysis for one held stock."""
    ticker: str
    current_price: float
    buy_price: float
    pnl_percent: float
    signals: list[SellSignal] = field(default_factory=list)
    recommendation: str = ""

    @property
    def should_sell(self) -> bool:
        return any(s.urgency == "HIGH" for s in self.signals) or len(self.signals) >= 3


def check_sell_signals(
    ticker: str, df: pd.DataFrame, buy_price: float
) -> SellResult:
    """Check whether a held stock should be sold."""
    current_price = round(df["Close"].iloc[-1], 2)
    pnl_percent = round(((current_price - buy_price) / buy_price) * 100, 2)

    result = SellResult(
        ticker=ticker,
        current_price=current_price,
        buy_price=buy_price,
        pnl_percent=pnl_percent,
    )

    # 1) Take-profit check
    if pnl_percent >= Config.TAKE_PROFIT_PERCENT:
        result.signals.append(SellSignal(
            "Take Profit",
            f"Profit is +{pnl_percent:.1f}% (target: {Config.TAKE_PROFIT_PERCENT}%) — consider taking profit",
            "HIGH",
        ))

    # 2) Stop-loss check
    if pnl_percent <= -Config.STOP_LOSS_PERCENT:
        result.signals.append(SellSignal(
            "Stop Loss",
            f"Loss is {pnl_percent:.1f}% (limit: -{Config.STOP_LOSS_PERCENT}%) — cut losses",
            "HIGH",
        ))

    # 3) RSI overbought
    rsi = compute_rsi(df["Close"])
    current_rsi = rsi.iloc[-1]
    if not np.isnan(current_rsi) and current_rsi >= Config.RSI_OVERBOUGHT:
        result.signals.append(SellSignal(
            "RSI Overbought",
            f"RSI={current_rsi:.1f} (above {Config.RSI_OVERBOUGHT}) — stock is overbought",
            "MEDIUM",
        ))

    # 4) Death cross (short MA crosses below long MA)
    short_ma = df["Close"].rolling(window=Config.SHORT_MA_PERIOD).mean()
    long_ma = df["Close"].rolling(window=Config.LONG_MA_PERIOD).mean()
    if not np.isnan(short_ma.iloc[-1]) and not np.isnan(long_ma.iloc[-1]):
        crossed_below = (short_ma.iloc[-1] < long_ma.iloc[-1]) and (
            short_ma.iloc[-2] >= long_ma.iloc[-2]
        )
        if crossed_below:
            result.signals.append(SellSignal(
                "Death Cross",
                f"{Config.SHORT_MA_PERIOD}-day MA just crossed BELOW {Config.LONG_MA_PERIOD}-day MA",
                "HIGH",
            ))
        elif short_ma.iloc[-1] < long_ma.iloc[-1]:
            result.signals.append(SellSignal(
                "Bearish Trend",
                f"Short MA below long MA — downtrend",
                "LOW",
            ))

    # 5) MACD bearish crossover
    macd_line, signal_line = compute_macd(df["Close"])
    if not np.isnan(macd_line.iloc[-1]) and not np.isnan(signal_line.iloc[-1]):
        crossed_below = (macd_line.iloc[-1] < signal_line.iloc[-1]) and (
            macd_line.iloc[-2] >= signal_line.iloc[-2]
        )
        if crossed_below:
            result.signals.append(SellSignal(
                "MACD Bearish",
                "MACD just crossed below signal line — bearish momentum",
                "MEDIUM",
            ))

    # 6) Upper Bollinger Band touch
    upper, middle, lower = compute_bollinger_bands(df["Close"])
    if not np.isnan(upper.iloc[-1]) and current_price >= upper.iloc[-1]:
        result.signals.append(SellSignal(
            "Bollinger Upper",
            "Price at/above upper Bollinger Band — may be overextended",
            "MEDIUM",
        ))

    # Generate recommendation
    high_count = sum(1 for s in result.signals if s.urgency == "HIGH")
    total = len(result.signals)

    if high_count >= 2:
        result.recommendation = "SELL NOW"
    elif high_count == 1:
        result.recommendation = "STRONG SELL"
    elif total >= 3:
        result.recommendation = "SELL"
    elif total >= 2:
        result.recommendation = "CONSIDER SELLING"
    elif total == 1:
        result.recommendation = "WATCH CLOSELY"
    else:
        result.recommendation = "HOLD"

    return result

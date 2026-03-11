import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Email
    EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

    # Bot
    SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "30"))

    # Deal criteria
    MIN_DEAL_SCORE = float(os.getenv("MIN_DEAL_SCORE", "75"))
    RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", "30"))
    RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", "70"))
    VOLUME_SPIKE_MULTIPLIER = float(os.getenv("VOLUME_SPIKE_MULTIPLIER", "1.5"))
    PRICE_DIP_PERCENT = float(os.getenv("PRICE_DIP_PERCENT", "5.0"))
    SHORT_MA_PERIOD = int(os.getenv("SHORT_MA_PERIOD", "10"))
    LONG_MA_PERIOD = int(os.getenv("LONG_MA_PERIOD", "50"))

import os
from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


class Config:
    # Email
    @staticmethod
    def _get(key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    @property
    def EMAIL_SENDER(self):
        return _env("EMAIL_SENDER")

    @property
    def EMAIL_PASSWORD(self):
        return _env("EMAIL_PASSWORD")

    @property
    def EMAIL_RECEIVER(self):
        return _env("EMAIL_RECEIVER")

    @property
    def SMTP_SERVER(self):
        return _env("SMTP_SERVER", "smtp.gmail.com")

    @property
    def SMTP_PORT(self):
        return int(_env("SMTP_PORT", "465"))

    # Bot
    @property
    def SCAN_INTERVAL_MINUTES(self):
        return int(_env("SCAN_INTERVAL_MINUTES", "30"))

    # Deal criteria
    @property
    def MIN_DEAL_SCORE(self):
        return float(_env("MIN_DEAL_SCORE", "75"))

    @property
    def RSI_OVERSOLD(self):
        return float(_env("RSI_OVERSOLD", "30"))

    @property
    def RSI_OVERBOUGHT(self):
        return float(_env("RSI_OVERBOUGHT", "70"))

    @property
    def VOLUME_SPIKE_MULTIPLIER(self):
        return float(_env("VOLUME_SPIKE_MULTIPLIER", "1.5"))

    @property
    def PRICE_DIP_PERCENT(self):
        return float(_env("PRICE_DIP_PERCENT", "5.0"))

    @property
    def SHORT_MA_PERIOD(self):
        return int(_env("SHORT_MA_PERIOD", "10"))

    @property
    def LONG_MA_PERIOD(self):
        return int(_env("LONG_MA_PERIOD", "50"))


Config = Config()

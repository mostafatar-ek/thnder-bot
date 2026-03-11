import os
from dotenv import load_dotenv

load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


class Config:
    # Telegram
    @property
    def TELEGRAM_BOT_TOKEN(self):
        return _env("TELEGRAM_BOT_TOKEN")

    @property
    def TELEGRAM_CHAT_ID(self):
        return _env("TELEGRAM_CHAT_ID")

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

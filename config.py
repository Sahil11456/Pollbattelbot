import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8871940323:AAHlQU6eytIp3-KVaMWQhYes6T5dMEo6u5E")
    ADMIN_IDS: list[int] = [
        int(x.strip()) for x in os.getenv("ADMIN_IDS", "5636959648").split(",") if x.strip().isdigit()
    ]
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "poll_battle_bot.db")
    MAINTENANCE_MODE: bool = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
    FORCE_JOIN_CHANNEL: str = os.getenv("FORCE_JOIN_CHANNEL", "-1001234567890")
    FORCE_JOIN_CHANNEL_URL: str = os.getenv("FORCE_JOIN_CHANNEL_URL", "https://t.me/PollBattleCommunity")
    MAX_POLL_OPTIONS: int = int(os.getenv("MAX_POLL_OPTIONS", "10"))
    MIN_POLL_OPTIONS: int = int(os.getenv("MIN_POLL_OPTIONS", "2"))
    ITEMS_PER_PAGE: int = 5

config = Config()

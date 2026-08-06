import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "8871940323:AAHlQU6eytIp3-KVaMWQhYes6T5dMEo6u5E")
DB_PATH = os.getenv("DB_PATH", "bot_data.db")
DB_URL = str(BASE_DIR / DB_PATH)

ADMIN_IDS = [
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "5636959648").split(",") if x.strip().isdigit()
]

LOGS_DIR = BASE_DIR / "logs"
BACKUPS_DIR = BASE_DIR / "backups"
ASSETS_DIR = BASE_DIR / "assets"

LOGS_DIR.mkdir(exist_ok=True)
BACKUPS_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

# Gamification Metrics
XP_PER_VOTE = 10
XP_PER_POLL_CREATION = 20
XP_LEVEL_UP_BASE = 100

DEFAULT_REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@PollArena")
DEFAULT_FORCE_JOIN_ENABLED = os.getenv("FORCE_JOIN_ENABLED", "True").lower() == "true"

RATE_LIMIT_SECONDS = 0.6
SPAM_BLOCK_DURATION = 3

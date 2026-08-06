import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Logging Configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("PollBattleBot")

# Telegram Bot Credentials
BOT_TOKEN = os.getenv("BOT_TOKEN", "8871940323:AAHlQU6eytIp3-KVaMWQhYes6T5dMEo6u5E")
BOT_NAME = os.getenv("BOT_NAME", "PollManagerBot")
BOT_USERNAME = os.getenv("BOT_USERNAME", "PollManager1_Bot")

# Admin IDs (comma-separated integer IDs)
ADMIN_IDS_RAW = os.getenv("ADMIN_IDS", "5636959648")
ADMIN_IDS = [int(x.strip()) for x in ADMIN_IDS_RAW.split(",") if x.strip().isdigit()]

# Database File Path
DB_PATH = os.getenv("DB_PATH", "database.db")

# Default Poll Settings
MAX_POLL_OPTIONS = 10
MIN_POLL_OPTIONS = 2
DEFAULT_RATE_LIMIT = 5  # Max commands per 10 seconds
MAX_ANONYMOUS_NAME = "Anonymous Voter"

# Maintenance Mode
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"

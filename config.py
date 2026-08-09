import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot Credentials & Administration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8268393848:AAFUTGPtuSCWs9t59eiUo_b4oX8NoVnQ6mc")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "5636959648").split(",") if x.strip().isdigit()]

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "bot_database.db")

# Force Join Configuration
DEFAULT_FORCE_JOIN_CHANNEL = os.getenv("DEFAULT_FORCE_JOIN_CHANNEL", "")

# Anti-Cheat & Security
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-poll-key-2026")

# Rate Limiting Settings (Requests per period in seconds)
RATE_LIMIT_CALLS = int(os.getenv("RATE_LIMIT_CALLS", "5"))
RATE_LIMIT_PERIOD = int(os.getenv("RATE_LIMIT_PERIOD", "3"))

# Poll Constraints
MIN_POLL_OPTIONS = int(os.getenv("MIN_POLL_OPTIONS", "2"))
MAX_POLL_OPTIONS = int(os.getenv("MAX_POLL_OPTIONS", "10"))
MAX_TITLE_LENGTH = int(os.getenv("MAX_TITLE_LENGTH", "300"))
MAX_OPTION_LENGTH = int(os.getenv("MAX_OPTION_LENGTH", "100"))

# Automation & Scheduler Settings
AUTO_CLOSE_CHECK_INTERVAL = int(os.getenv("AUTO_CLOSE_CHECK_INTERVAL", "60"))

# Gamification & XP Settings
XP_LEVEL_UP_BASE = int(os.getenv("XP_LEVEL_UP_BASE", "100"))
XP_PER_VOTE = int(os.getenv("XP_PER_VOTE", "10"))
XP_PER_POLL = int(os.getenv("XP_PER_POLL", "25"))

# Bot Maintenance & System Defaults
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "UTC")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

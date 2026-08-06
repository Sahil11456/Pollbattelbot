import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8871940323:AAHlQU6eytIp3-KVaMWQhYes6T5dMEo6u5E")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "PollManager1_Bot")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot_database.db")

# Parse Admin IDs list
_admin_raw = os.getenv("ADMIN_IDS", "5636959648")
ADMIN_IDS: list[int] = [int(x.strip()) for x in _admin_raw.split(",") if x.strip().isdigit()]

# Reply Keyboard Menu Buttons
BTN_CREATE_POLL = "➕ Create Poll"
BTN_MY_POLLS = "📊 My Polls"
BTN_ACTIVE_POLLS = "🌍 Active Polls"
BTN_CLOSED_POLLS = "📁 Closed Polls"
BTN_TRENDING_POLLS = "🔥 Trending Polls"
BTN_FAVORITES = "⭐ Favorites"
BTN_LEADERBOARD = "🏆 Leaderboard"
BTN_SEARCH_POLL = "🔍 Search Poll"
BTN_PROFILE = "👤 Profile"
BTN_STATISTICS = "📈 Statistics"
BTN_SETTINGS = "⚙ Settings"
BTN_POLL_CHANNELS = "📢 Poll Channels"
BTN_FORCE_JOIN = "🔐 Force Join"
BTN_ADMIN_PANEL = "👨‍💼 Admin Panel"
BTN_HELP = "❓ Help"

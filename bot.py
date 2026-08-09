import os
import sys
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# Path setups
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import BOT_TOKEN, LOG_LEVEL
from database import init_db
from handlers.start import start_handler
from handlers.createpoll import get_create_poll_handler
from handlers.mypolls import mypolls_handler
from handlers.trending import trending_polls_handler
from handlers.favorites import favorites_handler
from handlers.admin import admin_dashboard_handler, get_broadcast_conversation_handler, set_footer_command, toggle_autopost_command, toggle_device_guard_command
from handlers.settings import settings_handler
from handlers.profile import profile_handler
from handlers.search import get_search_conversation_handler
from handlers.statistics import statistics_handler
from handlers.leaderboard import leaderboard_menu_handler
from handlers.help import help_handler
from handlers.forcejoin import add_channel_command, ban_user_command, unban_user_command
try:
    from callbacks import callback_query_handler, handle_callback_query
except ImportError:
    from callbacks import callback_query_handler
    handle_callback_query = callback_query_handler
from services.winner import WinnerService
from middlewares.error_handler import error_handler_middleware
from middlewares.ban_checker import check_banned
from middlewares.maintenance import check_maintenance

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure Logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO) if isinstance(LOG_LEVEL, str) else logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("bot.main")

async def post_init(application: Application) -> None:
    """Post-initialization hook to verify database, tables, and bot connectivity."""
    logger.info("Initializing SQLite database connection and schemas...")
    await init_db()
    logger.info("Database schemas verified successfully!")

    try:
        me = await application.bot.get_me()
        logger.info(f"🤖 BOT CONNECTED SUCCESSFULLY: @{me.username} (ID: {me.id})")
        logger.info("Clearing old webhooks and pending updates...")
        await application.bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"❌ Failed to authenticate bot token with Telegram API: {e}")
        raise e

async def check_expired_polls_job(context: ContextTypes.DEFAULT_TYPE):
    """Background cron job running every 60 seconds to automatically close expired polls."""
    try:
        count = await WinnerService.check_and_close_expired_polls(context)
        if count > 0:
            logger.info(f"🏁 Concluded and announced winners for {count} expired poll(s).")
    except Exception as e:
        logger.error(f"Error executing winner check job: {e}")

async def text_router_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes keyboard button text presses to their corresponding handler logic."""
    if not update.message or not update.message.text:
        return

    # Check ban & maintenance mode
    if await check_banned(update, context):
        return
    if await check_maintenance(update, context):
        return

    text = update.message.text.strip()

    if text == "➕ Create Poll":
        # Handled by conversation handler entry point
        pass
    elif text == "📝 My Polls":
        await mypolls_handler(update, context)
    elif text == "🔥 Trending":
        await trending_polls_handler(update, context)
    elif text == "⭐ Favorites":
        await favorites_handler(update, context)
    elif text == "🏆 Leaderboard":
        await leaderboard_menu_handler(update, context)
    elif text == "🔍 Search Polls":
        # Handled by search conversation handler
        pass
    elif text == "👤 My Profile":
        await profile_handler(update, context)
    elif text == "📊 Statistics":
        await statistics_handler(update, context)
    elif text == "⚙️ Settings":
        await settings_handler(update, context)
    elif text == "❓ Help":
        await help_handler(update, context)

def main():
    """Bootstraps and runs the Poll Battle Bot engine."""
    # Validate bot token
    if not BOT_TOKEN or BOT_TOKEN == "MOCK_TOKEN_FOR_SETUP":
        logger.critical("BOT_TOKEN is missing or set to placeholder value! Please supply a valid Telegram bot token inside Railway Environment Variables.")
        print("\n🛑 CRITICAL ERROR: BOT_TOKEN is missing! Please set BOT_TOKEN in Railway Variables tab.")
        sys.exit(1)

    logger.info("Starting Telegram Bot Application context builder...")
    # Initialize application with post_init hook
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Register JobQueue task to run every 60 seconds (checks for poll closures)
    if app.job_queue:
        app.job_queue.run_repeating(check_expired_polls_job, interval=60, first=10)
        logger.info("Concluded poll job queue registered successfully (interval: 60s).")

    # 1. Start and Help
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))

    # 2. Conversation Wizards
    app.add_handler(get_create_poll_handler())
    app.add_handler(get_search_conversation_handler())
    app.add_handler(get_broadcast_conversation_handler())

    # 3. Admin Command Hooks
    app.add_handler(CommandHandler("admin", admin_dashboard_handler))
    app.add_handler(CommandHandler("set_footer", set_footer_command))
    app.add_handler(CommandHandler("toggle_autopost", toggle_autopost_command))
    app.add_handler(CommandHandler("toggle_device_guard", toggle_device_guard_command))
    app.add_handler(CommandHandler("add_channel", add_channel_command))
    app.add_handler(CommandHandler("ban_user", ban_user_command))
    app.add_handler(CommandHandler("unban_user", unban_user_command))

    # 4. Callback Query Interceptors
    app.add_handler(CallbackQueryHandler(callback_query_handler))

    # 5. Core Menu Text Message Route Interceptor
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router_handler))

    # 6. Global System Exception interceptor
    app.add_error_handler(error_handler_middleware)

    logger.info("Poll Battle Bot is ONLINE and listening for events!")
    # Start bot polling loop using standard run_polling
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        pass

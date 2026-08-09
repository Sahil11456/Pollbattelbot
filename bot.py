import os
import sys
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

# Path setups
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import BOT_TOKEN
from database import init_db
from handlers.start import start_handler
from handlers.createpoll import get_create_poll_handler
from handlers.mypolls import my_polls_handler
from handlers.admin import admin_dashboard_handler, get_broadcast_conversation_handler
from handlers.settings import settings_menu_handler, set_footer_command, toggle_autopost_command, toggle_device_guard_command
from handlers.profile import profile_handler
from handlers.search import get_search_conversation_handler
from handlers.trending import trending_polls_menu_handler
from handlers.favorites import favorites_list_handler
from handlers.statistics import statistics_handler
from handlers.leaderboard import leaderboard_menu_handler
from handlers.help import help_handler
from handlers.forcejoin import add_channel_command, ban_user_command, unban_user_command
from callbacks import callback_query_handler
from services.winner import WinnerService
from middlewares.error_handler import error_handler_middleware
from middlewares.ban_checker import check_banned
from middlewares.maintenance import check_maintenance

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure Logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("bot.main")

async def check_expired_polls_job(context: ContextTypes.DEFAULT_TYPE):
    """Periodic job task to process expired poll winner announcements."""
    logger.info("Running periodic background check for expired poll arenas...")
    processed = await WinnerService.process_expired_polls(context.bot)
    if processed:
        logger.info(f"Concluded {len(processed)} expired poll arenas and notified creators.")

@check_banned()
@check_maintenance()
async def text_router_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router to direct custom persistent menu buttons to proper action handlers."""
    text = update.message.text.strip() if update.message else ""
    if not text:
        return

    if text == "🌍 Active Polls":
        # Handled by listing featured/all active polls or searching
        from handlers.search import start_search_handler
        await start_search_handler(update, context)
    elif text == "🔥 Trending Polls":
        await trending_polls_menu_handler(update, context)
    elif text == "📊 My Polls":
        await my_polls_handler(update, context)
    elif text == "⭐ Favorites":
        await favorites_list_handler(update, context)
    elif text == "🏆 Leaderboard":
        await leaderboard_menu_handler(update, context)
    elif text == "👤 Profile":
        await profile_handler(update, context)
    elif text == "📈 Statistics":
        await statistics_handler(update, context)
    elif text == "📢 Poll Channels":
        await settings_menu_handler(update, context)
    elif text == "👨💼 Admin Panel":
        await admin_dashboard_handler(update, context)
    elif text == "❓ Help":
        await help_handler(update, context)
    else:
        # Check if they are responding to any admin broadcast flows or searches
        bc_type = context.user_data.get('bc_type')
        if bc_type == 'text':
            from handlers.admin import bc_msg_received
            await bc_msg_received(update, context)
            return

        search_field = context.user_data.get('search_field')
        if search_field:
            from handlers.search import search_query_received
            await search_query_received(update, context)
            return

        # Default help
        await update.message.reply_text("💡 Button command not recognized. Use the persistent menu buttons or `/help` guide.")

async def main():
    """Bootstraps and runs the Poll Battle Bot engine."""
    logger.info("Initializing SQLite database tables...")
    await init_db()

    # Validate bot token
    if not BOT_TOKEN or BOT_TOKEN == "MOCK_TOKEN_FOR_SETUP":
        logger.critical("BOT_TOKEN is missing or set to placeholder value! Please supply a valid Telegram bot token inside .env file.")
        print("\n🛑 CRITICAL ERROR: BOT_TOKEN is missing inside '.env'. Please configure it to start the bot.")
        return

    logger.info("Starting Telegram Bot Application context builder...")
    # Initialize application
    app = Application.builder().token(BOT_TOKEN).build()

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
    # Start bot polling loop
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # Run loop until terminated
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Received close signal. Safely halting updater...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        logger.info("Systems shut down completely. Good bye!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

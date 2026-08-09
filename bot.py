import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from config import BOT_TOKEN, LOG_LEVEL
from database import init_db
from handlers.start import start_handler
from handlers.createpoll import poll_creation_conv
from handlers.mypolls import my_polls_handler
from handlers.trending import trending_polls_handler
from handlers.favorites import favorite_polls_handler
from handlers.search import search_polls_handler
from handlers.profile import profile_handler
from handlers.statistics import statistics_handler
from handlers.admin import admin_panel_handler, broadcast_conv_handler
from handlers.settings import settings_handler
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

# Configure Logging System
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO)
)
logger = logging.getLogger("bot.main")

async def menu_text_button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes persistent reply keyboard text buttons to corresponding handlers."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    logger.info(f"User {update.effective_user.id if update.effective_user else 'Unknown'} pressed menu button: {text}")

    if text in ["➕ Create Poll", "Create Poll"]:
        await update.message.reply_text("🚀 Send `/create` to start the poll creation wizard!", parse_mode="Markdown")
    elif text in ["📊 My Polls", "My Polls"]:
        await my_polls_handler(update, context)
    elif text in ["🔥 Trending", "Trending"]:
        await trending_polls_handler(update, context)
    elif text in ["⭐ Saved / Favorites", "Saved / Favorites"]:
        await favorite_polls_handler(update, context)
    elif text in ["👤 Profile & XP", "Profile & XP"]:
        await profile_handler(update, context)
    elif text in ["🏆 Leaderboard", "Leaderboard"]:
        await leaderboard_menu_handler(update, context)
    elif text in ["🔍 Search Polls", "Search Polls"]:
        await update.message.reply_text("🔎 Usage: `/search <keywords>` to locate polls.", parse_mode="Markdown")
    elif text in ["📈 System Stats", "System Stats"]:
        await statistics_handler(update, context)
    elif text in ["⚙️ Settings", "Settings"]:
        await settings_handler(update, context)
    elif text in ["❓ Help & FAQ", "Help & FAQ"]:
        await help_handler(update, context)
    else:
        await update.message.reply_text("💡 Button command not recognized. Use the persistent menu buttons or `/help` guide.")

async def post_init(application: Application):
    """Executes after bot initialization to initialize DB, verify token and clear webhooks."""
    logger.info("Initializing SQLite database tables...")
    await init_db()
    try:
        me = await application.bot.get_me()
        logger.info(f"✅ BOT CONNECTED SUCCESSFULLY: @{me.username} (ID: {me.id})")
        await application.bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"⚠️ Failed bot connectivity verification: {e}")

def main():
    """Bootstraps and runs the Poll Battle Bot engine."""
    # Validate bot token
    if not BOT_TOKEN or BOT_TOKEN == "MOCK_TOKEN_FOR_SETUP":
        logger.critical("BOT_TOKEN is missing or set to placeholder value! Please supply a valid Telegram bot token inside Railway Environment Variables.")
        print("\n" + "="*70)
        print("❌ CRITICAL ERROR: BOT_TOKEN Environment Variable is NOT configured!")
        print("👉 Add BOT_TOKEN = <Your_Telegram_Bot_Token> inside Railway dashboard.")
        print("="*70 + "\n")
        return

    # Build Application
    builder = Application.builder().token(BOT_TOKEN).post_init(post_init)
    application = builder.build()

    # 1. Register Conversation Handlers
    application.add_handler(poll_creation_conv)
    application.add_handler(broadcast_conv_handler)

    # 2. Register Command Handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("mypolls", my_polls_handler))
    application.add_handler(CommandHandler("trending", trending_polls_handler))
    application.add_handler(CommandHandler("favorites", favorite_polls_handler))
    application.add_handler(CommandHandler("search", search_polls_handler))
    application.add_handler(CommandHandler("profile", profile_handler))
    application.add_handler(CommandHandler("leaderboard", leaderboard_menu_handler))
    application.add_handler(CommandHandler("stats", statistics_handler))
    application.add_handler(CommandHandler("admin", admin_panel_handler))
    application.add_handler(CommandHandler("settings", settings_handler))
    application.add_handler(CommandHandler("help", help_handler))

    # Force Join & Moderation Commands
    application.add_handler(CommandHandler("addchannel", add_channel_command))
    application.add_handler(CommandHandler("ban", ban_user_command))
    application.add_handler(CommandHandler("unban", unban_user_command))

    # 3. Register Callback Query Handler
    application.add_handler(CallbackQueryHandler(callback_query_handler))

    # 4. Register Persistent Reply Keyboard Router
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), menu_text_button_router))

    # 5. Register Error Handler
    application.add_error_handler(error_handler_middleware)

    # 6. Initialize Background Services (Poll Expiration & Winner Announcer)
    winner_service = WinnerService(application.bot, interval_seconds=60)
    winner_service.start()

    logger.info("🚀 Poll Battle Bot is starting polling loop...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

import sys
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db
from callbacks import handle_callback_query
from services.winner import start_winner_announcer_task

# Handlers
from handlers.start import start_handler
from handlers.createpoll import create_poll_conv_handler
from handlers.mypolls import my_polls_handler
from handlers.trending import trending_polls_handler
from handlers.favorites import favorites_handler
from handlers.leaderboard import leaderboard_handler
from handlers.search import search_handler
from handlers.profile import profile_handler
from handlers.statistics import stats_handler
from handlers.forcejoin import force_join_handler, check_join_callback
from handlers.admin import admin_handler
from handlers.help import help_handler
from handlers.settings import settings_handler

# Middlewares
from middlewares.error_handler import global_error_handler
from middlewares.ban_checker import check_ban
from middlewares.maintenance import check_maintenance

# Configure Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bot.main")

@check_ban
@check_maintenance
async def menu_button_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Routes persistent reply menu button clicks to corresponding handlers."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    if text in ["➕ Create Poll", "➕ Naya Poll Banayein"]:
        await update.message.reply_text(
            "💡 To create a poll, click /createpoll or choose from the options below!"
        )
    elif text in ["📊 My Polls", "📁 Mere Polls"]:
        await my_polls_handler(update, context)
    elif text in ["🔥 Trending Polls", "🔥 Trending"]:
        await trending_polls_handler(update, context)
    elif text in ["⭐ Saved Favorites", "⭐ Favorites"]:
        await favorites_handler(update, context)
    elif text in ["🏆 Leaderboard", "🏆 Rank Board"]:
        await leaderboard_handler(update, context)
    elif text in ["🔍 Search Polls", "🔍 Search"]:
        await update.message.reply_text(
            "🔍 **Search Polls**\n\nType `/search <keyword>` to find polls by title or topic.\nExample: `/search tech`",
            parse_mode="Markdown"
        )
    elif text in ["👤 Voter Profile", "👤 Profile"]:
        await profile_handler(update, context)
    elif text in ["📈 System Stats", "📊 Statistics"]:
        await stats_handler(update, context)
    elif text in ["ℹ️ Help & FAQ", "❓ Help"]:
        await help_handler(update, context)
    elif text in ["⚙️ Admin Settings", "⚙️ Settings"]:
        await settings_handler(update, context)
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
        # Start winner background loop
        asyncio.create_task(start_winner_announcer_task(application.bot))
    except Exception as e:
        logger.error(f"❌ Failed connecting to Telegram API: {e}")

def main():
    """Bootstraps and runs the Poll Battle Bot engine."""
    # Validate bot token
    if not BOT_TOKEN or BOT_TOKEN == "MOCK_TOKEN_FOR_SETUP":
        logger.critical("BOT_TOKEN is missing or set to placeholder value! Please supply a valid Telegram bot token inside Railway Environment Variables.")
        print("\n" + "="*70)
        print(" CRITICAL ERROR: BOT_TOKEN Environment Variable Missing!")
        print(" Please set BOT_TOKEN inside your Railway project environment variables.")
        print("="*70 + "\n")

    # Build Application
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Register Conversation Handler (Poll Wizard)
    app.add_handler(create_poll_conv_handler)

    # Register Core Command Handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("mypolls", my_polls_handler))
    app.add_handler(CommandHandler("trending", trending_polls_handler))
    app.add_handler(CommandHandler("favorites", favorites_handler))
    app.add_handler(CommandHandler("leaderboard", leaderboard_handler))
    app.add_handler(CommandHandler("search", search_handler))
    app.add_handler(CommandHandler("profile", profile_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("forcejoin", force_join_handler))
    app.add_handler(CommandHandler("admin", admin_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("settings", settings_handler))

    # Callback Query Router
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # Menu Button Text Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_button_text_router))

    # Global Exception Handler Middleware
    app.add_error_handler(global_error_handler)

    # Start Polling
    logger.info("🚀 Starting Poll Battle Bot Polling Engine...")
    app.run_polling(poll_interval=1.0, drop_pending_updates=True)

if __name__ == "__main__":
    main()

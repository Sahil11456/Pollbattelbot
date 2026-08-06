import asyncio
import logging
import traceback
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

import config
from database import db
from handlers.start_handler import start_command, force_join_callback, profile_command, help_command
from handlers.poll_handler import (
    start_create_poll,
    receive_question,
    receive_options,
    receive_poll_type,
    receive_is_multiple,
    receive_expiry,
    cancel_creation,
    QUESTION, OPTIONS, POLL_TYPE, IS_MULTIPLE, EXPIRY
)
from handlers.vote_handler import handle_vote_callback
from handlers.search_handler import (
    trending_polls_command,
    search_polls_command,
    search_keyword_handler,
    leaderboard_command,
    favorites_command,
)
from handlers.admin_handler import (
    admin_panel_command,
    handle_admin_callback,
    receive_broadcast,
    receive_ban,
    receive_unban,
    BROADCAST_MSG, BAN_ID, UNBAN_ID
)
from handlers.channel_handler import channel_setup_command, add_channel_command, force_join_toggle_command
from utils.announcement import format_winner_announcement

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def auto_check_poll_expiries(context: ContextTypes.DEFAULT_TYPE):
    """
    Periodic job (runs every 10 seconds) to detect expired polls,
    close them, calculate winners, and send Winner Announcements inside Bot and Linked Channels!
    """
    try:
        expired_polls = await db.get_expired_open_polls()
        for poll in expired_polls:
            closed_poll = await db.close_poll_and_set_winner(poll["poll_id"])
            if not closed_poll:
                continue

            announcement_text = format_winner_announcement(closed_poll)

            # 1. Send announcement to poll creator inside bot
            try:
                await context.bot.send_message(
                    chat_id=closed_poll["creator_id"],
                    text=f"🔔 <b>YOUR POLL HAS CLOSED!</b>\n\n{announcement_text}",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify creator {closed_poll['creator_id']}: {e}")

            # 2. Send announcement to target channel if linked
            if closed_poll.get("target_channel_id"):
                try:
                    await context.bot.send_message(
                        chat_id=closed_poll["target_channel_id"],
                        text=announcement_text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Failed to notify target channel {closed_poll['target_channel_id']}: {e}")

    except Exception as e:
        logger.error(f"Error in auto_check_poll_expiries job: {e}")

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global Error Handler for PTB v22"""
    err_str = str(context.error)
    tb_str = "".join(traceback.format_exception(None, context.error, context.error.__traceback__)) if context.error else ""
    user_id = update.effective_user.id if isinstance(update, Update) and update.effective_user else None

    logger.error(f"Global Error Handled: {err_str}\n{tb_str}")
    await db.log_error(user_id, err_str, tb_str)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text("⚠️ An internal error occurred. Our team has been notified.")
        except Exception:
            pass

async def post_init(application: Application):
    """Run DB setup on bot startup"""
    await db.init_db()
    logger.info("Database initialized successfully.")

def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        logger.warning("BOT_TOKEN is not configured! Please set BOT_TOKEN in .env or config.py.")

    # PTB v22 Application Builder
    builder = Application.builder().token(config.BOT_TOKEN)
    builder.post_init(post_init)
    application = builder.build()

    # --- CONVERSATION HANDLERS ---
    poll_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^➕ Create Poll$"), start_create_poll),
            CommandHandler("create", start_create_poll)
        ],
        states={
            QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question)],
            OPTIONS: [MessageHandler(filters.TEXT, receive_options)],
            POLL_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_poll_type)],
            IS_MULTIPLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_is_multiple)],
            EXPIRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_expiry)],
        },
        fallbacks=[CommandHandler("cancel", cancel_creation)]
    )

    admin_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_admin_callback, pattern="^admin:")],
        states={
            BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_broadcast)],
            BAN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ban)],
            UNBAN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_unban)],
        },
        fallbacks=[CommandHandler("cancel", cancel_creation)]
    )

    # --- HANDLER REGISTRATION ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("trending", trending_polls_command))
    application.add_handler(CommandHandler("search", search_keyword_handler))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    application.add_handler(CommandHandler("favorites", favorites_command))
    application.add_handler(CommandHandler("admin", admin_panel_command))
    application.add_handler(CommandHandler("channel", channel_setup_command))
    application.add_handler(CommandHandler("addchannel", add_channel_command))
    application.add_handler(CommandHandler("forcejoin", force_join_toggle_command))

    # Reply Keyboard Regex Handlers
    application.add_handler(MessageHandler(filters.Regex("^🔥 Trending Polls$"), trending_polls_command))
    application.add_handler(MessageHandler(filters.Regex("^🔍 Search Polls$"), search_polls_command))
    application.add_handler(MessageHandler(filters.Regex("^🏆 Leaderboard$"), leaderboard_command))
    application.add_handler(MessageHandler(filters.Regex("^❤️ Favorites$"), favorites_command))
    application.add_handler(MessageHandler(filters.Regex("^👤 My Profile$"), profile_command))
    application.add_handler(MessageHandler(filters.Regex("^📢 Channel Setup$"), channel_setup_command))
    application.add_handler(MessageHandler(filters.Regex("^ℹ️ Help$"), help_command))
    application.add_handler(MessageHandler(filters.Regex("^⚡ Admin Panel$"), admin_panel_command))

    # Conversations & Callbacks
    application.add_handler(poll_conv_handler)
    application.add_handler(admin_conv_handler)
    application.add_handler(CallbackQueryHandler(force_join_callback, pattern="^join_check:"))
    application.add_handler(CallbackQueryHandler(handle_vote_callback))

    # Global Error Handler
    application.add_error_handler(global_error_handler)

    # Job Queue for Auto Expiry Check (every 10 seconds)
    if application.job_queue:
        application.job_queue.run_repeating(auto_check_poll_expiries, interval=10, first=5)

    logger.info("Starting Telegram Poll Battle Bot...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

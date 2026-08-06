import logging
import asyncio
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
)
from config import config
from database import init_db
from handlers.start import start_handler
from handlers.createpoll import start_create_poll, handle_title, handle_type, handle_options, TITLE, TYPE, OPTIONS
from handlers.admin import admin_panel_handler
from callbacks import poll_callback_handler

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

async def post_init(application):
    await init_db()

def build_bot():
    app = ApplicationBuilder().token(config.BOT_TOKEN).post_init(post_init).build()

    create_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^➕ Create Poll$"), start_create_poll),
            CommandHandler("create", start_create_poll)
        ],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_title)],
            TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_type)],
            OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_options)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(create_conv)
    app.add_handler(MessageHandler(filters.Regex("^👨‍💼 Admin Panel$"), admin_panel_handler))
    app.add_handler(CallbackQueryHandler(poll_callback_handler))

    return app

if __name__ == "__main__":
    app = build_bot()
    logger = logging.getLogger(__name__)
    logger.info("Starting Telegram Poll Battle Bot v22.4.0-PRO...")
    app.run_polling()

import os
import sys
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import BOT_TOKEN
from database import init_db
from handlers.start import start_handler
from handlers.profile import profile_handler
from callbacks import callback_query_handler
from middlewares.ban_checker import check_banned
from middlewares.maintenance import check_maintenance

# Configure Logger
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("bot.main")

@check_banned()
@check_maintenance()
async def text_router_handler(update: Update, context: context):
    # Route button strings to respective handler subroutines...
    pass

async def main():
    logger.info("Initializing SQLite database tables...")
    await init_db()

    if not BOT_TOKEN or BOT_TOKEN == "MOCK_TOKEN_FOR_SETUP":
        logger.critical("BOT_TOKEN is missing!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Core commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router_handler))

    logger.info("Poll Battle Bot is ONLINE and listening for events!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import get_db_connection

logger = logging.getLogger("bot.middlewares.error_handler")

async def error_handler_middleware(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Global system exceptions interceptor middleware."""
    logger.error(f"System Exception caught during event loop: {context.error}", exc_info=context.error)
    
    # Save exception details to SQLite logs table for system auditing
    try:
        user_id = None
        if isinstance(update, Update) and update.effective_user:
            user_id = update.effective_user.id
            
        async with await get_db_connection() as conn:
            await conn.execute("""
            INSERT INTO logs (level, module, message, user_id)
            VALUES ('ERROR', 'MIDDLEWARE_EXCEPTION', ?, ?);
            """, (str(context.error), user_id))
            await conn.commit()
    except Exception as e:
        logger.critical(f"Failed to log system exception inside SQLite logs: {e}")

    # Inform the user gracefully
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ **An internal database exception occurred.**\n"
                "System administrators have been notified. Please try again shortly.",
                parse_mode="Markdown"
            )
        except Exception:
            # Message could fail if chat was deleted or already responded
            pass

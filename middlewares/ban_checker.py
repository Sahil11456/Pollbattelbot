import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from database import get_db_connection

logger = logging.getLogger("bot.middlewares.ban_checker")

def check_banned():
    """
    Decorator to intercept banned users and deny access.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            if not user:
                return await func(update, context, *args, **kwargs)

            async with await get_db_connection() as conn:
                async with conn.execute("SELECT is_banned FROM users WHERE user_id = ?;", (user.id,)) as cursor:
                    row = await cursor.fetchone()
            
            if row and row[0] == 1:
                text = "❌ **Access Denied:** Your account has been suspended for violating voting rules."
                if update.message:
                    await update.message.reply_text(text, parse_mode="Markdown")
                elif update.callback_query:
                    await update.callback_query.answer("❌ Account Suspended.", show_alert=True)
                return

            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

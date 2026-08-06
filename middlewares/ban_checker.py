from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from database import get_db_connection

def check_banned():
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
                        if update.message:
                            await update.message.reply_text("❌ Account restricted. You are banned from interacting with the bot.")
                        return
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

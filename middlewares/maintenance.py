from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from database import get_db_connection

def check_maintenance():
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            if not user:
                return await func(update, context, *args, **kwargs)
                
            async with await get_db_connection() as conn:
                async with conn.execute("SELECT setting_value FROM settings WHERE setting_key = 'maintenance_mode';") as cursor:
                    m_row = await cursor.fetchone()
                
                if m_row and m_row[0].lower() == 'true':
                    async with conn.execute("SELECT role FROM users WHERE user_id = ?;", (user.id,)) as r_cursor:
                        r_row = await r_cursor.fetchone()
                    if not r_row or r_row[0] != 'admin':
                        if update.message:
                            await update.message.reply_text("🛠️ **System Maintenance Active**\n\nThe server is temporarily locked for performance optimization. Try again soon!")
                        return
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

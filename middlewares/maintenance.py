import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from database import get_db_connection

logger = logging.getLogger("bot.middlewares.maintenance")

def check_maintenance():
    """
    Decorator that checks if system is in maintenance mode.
    Admins bypass lock.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            if not user:
                return await func(update, context, *args, **kwargs)

            # Query settings
            async with await get_db_connection() as conn:
                async with conn.execute("SELECT setting_value FROM settings WHERE setting_key = 'maintenance_mode';") as cursor:
                    row = await cursor.fetchone()
                
                m_mode = row[0].lower() == "true" if row else False
                
                if m_mode:
                    # Check if user is admin to bypass
                    async with conn.execute("SELECT role FROM users WHERE user_id = ?;", (user.id,)) as role_cursor:
                        role_row = await role_cursor.fetchone()
                    
                    is_admin = role_row and role_row[0] == 'admin'
                    
                    if not is_admin:
                        text = "🛠️ **System Maintenance in Progress**\n\nThe bot engine is temporarily locked for backend optimization. Please try again shortly."
                        if update.message:
                            await update.message.reply_text(text, parse_mode="Markdown")
                        elif update.callback_query:
                            await update.callback_query.answer("🛠️ System Locked for backend optimization.", show_alert=True)
                        return

            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

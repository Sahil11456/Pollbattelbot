from telegram import Update
from telegram.ext import ContextTypes
from database import get_db_connection
from utils.keyboards import get_main_menu_keyboard
from config import ADMIN_IDS

async def register_user_if_not_exists(user_id: int, username: str, full_name: str) -> dict:
    async with await get_db_connection() as conn:
        async with conn.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,)) as cursor:
            row = await cursor.fetchone()
        if not row:
            role = "admin" if user_id in ADMIN_IDS else "user"
            await conn.execute("""
            INSERT INTO users (user_id, username, full_name, role, xp, level, rank)
            VALUES (?, ?, ?, ?, 0, 1, '🌱 Novice Creator');
            """, (user_id, username, full_name, role))
            await conn.commit()
            return {"user_id": user_id, "username": username, "full_name": full_name, "role": role, "is_banned": 0}
        return {"user_id": row[0], "username": row[1], "full_name": row[2], "role": row[3], "is_banned": row[8]}

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user: return
    user_data = await register_user_if_not_exists(user.id, user.username or "Anonymous", user.full_name or "Anonymous User")
    
    if user_data.get("is_banned") == 1:
        await update.message.reply_text("❌ Access restricted by administrators.")
        return
        
    is_admin = user_data.get("role") == "admin"
    await update.message.reply_text(
        text=f"🚀 **Welcome to the Arena, {user.first_name}!** 🎉\n\nCreate customized polls, track performance metrics, and climb the leaderboard!",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="Markdown"
    )

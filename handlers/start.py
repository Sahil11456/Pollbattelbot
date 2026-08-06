from telegram import Update
from telegram.ext import ContextTypes
from database import get_db
from utils.keyboards import get_main_menu_keyboard
from config import config

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return
    
    async with await get_db() as db:
        await db.execute(
            """INSERT INTO users (user_id, username, first_name, is_admin)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name""",
            (user.id, user.username or "", user.first_name or "", 1 if user.id in config.ADMIN_IDS else 0)
        )
        await db.commit()

    welcome_text = (
        "⚔️ **Welcome to Poll Battle Bot, " + (user.first_name or "Warrior") + "!** ⚔️\n\n"
        "Create viral community poll battles, predict outcomes, participate in real-time voting contests, "
        "and climb the global leaderboard!\n\n"
        "👇 Choose an action from the menu below:"
    )
    is_admin = user.id in config.ADMIN_IDS
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=get_main_menu_keyboard(is_admin))

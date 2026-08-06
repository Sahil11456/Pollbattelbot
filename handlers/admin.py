from telegram import Update
from telegram.ext import ContextTypes
from database import get_db
from config import config

async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔ **Access Denied**: Admin permissions required.")
        return

    async with await get_db() as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            u_count = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM polls") as c:
            p_count = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM votes") as c:
            v_count = (await c.fetchone())[0]

    msg = (
        "👨‍💼 **Poll Battle System Admin Dashboard**\n\n"
        "👤 Total Users: " + str(u_count) + "\n"
        "📊 Total Polls: " + str(p_count) + "\n"
        "🗳️ Total Votes Cast: " + str(v_count) + "\n\n"
        "**Admin Commands:**\n"
        "• `/broadcast <msg>` - Global user broadcast\n"
        "• `/ban <user_id>` - Ban user from bot\n"
        "• `/unban <user_id>` - Lift ban on user\n"
        "• `/maintenance` - Toggle maintenance mode"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

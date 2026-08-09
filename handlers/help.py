import logging
from telegram import Update
from telegram.ext import ContextTypes
import database

logger = logging.getLogger("bot.handlers.help")

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides a detailed guide of the bot's features and commands."""
    user = update.effective_user
    if not user or not update.message:
        return
        
    db_user = await database.get_user(user.id)
    is_admin = bool(db_user and db_user.get('role') == 'admin')

    help_text = (
        f"❓ **Poll Battle Bot Guide**\n"
        f"—————————————————————\n"
        f"Welcome to the ultimate guide on using the **Telegram Poll Battle Bot**.\n\n"
        f"💡 **Voter Core Actions:**\n"
        f"• **➕ Create Poll** - Initiate a new poll creation sequence.\n"
        f"• **🌍 Active Polls** - Show list of ongoing active poll battles.\n"
        f"• **🔥 Trending Polls** - Sort active polls by votes, shares, newest, or views.\n"
        f"• **📊 My Polls** - Manage your created polls (close, delete, or share).\n"
        f"• **⭐ Favorites** - Quick view folder for saved topics.\n"
        f"• **🏆 Leaderboard** - Hall of Fame highlighting top creators & active voters.\n"
        f"• **🔍 Search Polls** - Locate specific active or closed topics.\n"
        f"• **👤 Profile** - Review level metrics, XP bars, titles, and achievements.\n"
        f"• **📈 Statistics** - Analyze real-time visual distributions of system votes.\n\n"
        f"🎮 **Gamification Mechanics:**\n"
        f"• Casting a vote awards **+10 XP**.\n"
        f"• Launching a poll awards **+25 XP**.\n"
        f"• Scale levels to unlock exclusive ranks and badges!\n\n"
    )

    if is_admin:
        help_text += (
            f"👨‍💼 **System Admin Control Guide:**\n"
            f"• Persistent Admin button - Open central administration deck.\n"
            f"• `/set_footer <text>` - Update poll custom footer branding.\n"
            f"• `/add_channel <username>` - Register a force-join channel.\n"
            f"• `/ban_user <id>` - Restrict a bad user from system operations.\n"
            f"• `/unban_user <id>` - Lift ban on a user."
        )
    else:
        help_text += "📬 _Need human support? Contact @SupportArena._"

    await update.message.reply_text(
        text=help_text,
        parse_mode="Markdown"
    )

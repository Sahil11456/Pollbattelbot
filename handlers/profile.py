import logging
from telegram import Update
from telegram.ext import ContextTypes
import database
from utils.helpers import calculate_level_and_xp, get_rank_by_level
from config import XP_LEVEL_UP_BASE

logger = logging.getLogger("bot.handlers.profile")

async def profile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches user profile, experience milestones, titles, and achievements from SQLite."""
    user = update.effective_user
    if not user or not update.message:
        return
        
    db_user = await database.get_user(user.id)
    if not db_user:
        db_user = await database.get_or_create_user(user.id, user.username or "", user.full_name or "")

    xp = db_user.get("xp", 0)
    level = db_user.get("level", 1)
    rank = db_user.get("rank", "🌱 Novice")
    role = db_user.get("role", "user")
    reg_date = db_user.get("created_at", db_user.get("registration_date", ""))

    polls_count = await database.get_user_polls_count(user.id)
    votes_count = await database.get_user_votes_count(user.id)
    achievements = await database.get_user_achievements(user.id)

    _, current_progress_xp = calculate_level_and_xp(xp)
    width = 10
    filled = max(0, min(width, int(round(width * current_progress_xp / XP_LEVEL_UP_BASE))))
    bar = '█' * filled + '░' * (width - filled)
    xp_bar_str = f"`{bar}` {current_progress_xp}/{XP_LEVEL_UP_BASE} XP"

    if not achievements:
        ach_str = "🌱 _No accomplishments unlocked yet. Create polls and vote to unlock!_"
    else:
        ach_str = "\n".join([f"🏆 **{ach.get('achievement_name', ach)}**" for ach in achievements])

    date_str = str(reg_date).split(' ')[0] if reg_date else "Today"

    profile_text = (
        f"👤 **Voter Profile: {user.first_name}**\n"
        f"—————————————————————\n"
        f"👑 **Rank/Title:** `{rank}`\n"
        f"⚡ **Level:** `{level}`\n"
        f"📈 **Experience:** {xp_bar_str}\n\n"
        f"📝 **Polls Created:** `{polls_count}`\n"
        f"🗳️ **Votes Cast:** `{votes_count}`\n"
        f"🛡️ **System Role:** `{role.upper()}`\n"
        f"📅 **Registered:** `{date_str}`\n\n"
        f"🏆 **Unlocked Achievements:**\n"
        f"{ach_str}"
    )

    await update.message.reply_text(
        text=profile_text,
        parse_mode="Markdown"
    )

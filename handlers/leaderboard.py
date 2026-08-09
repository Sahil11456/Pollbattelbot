import logging
from telegram import Update
from telegram.ext import ContextTypes
import database
from utils.keyboards import get_leaderboard_options_keyboard

logger = logging.getLogger("bot.handlers.leaderboard")

async def leaderboard_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the leaderboard selector menu."""
    if not update.message:
        return

    await update.message.reply_text(
        "🏆 **Hall of Fame & Leaderboards**\n\n"
        "Check out top users on the network based on participation criteria:",
        reply_markup=get_leaderboard_options_keyboard(),
        parse_mode="Markdown"
    )

async def display_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, criteria: str = "xp"):
    """Retrieves and lists leading users based on selected metrics from SQLite."""
    rows = await database.get_leaderboard(limit=10, criteria=criteria)
    trigger_msg = update.callback_query.message if update.callback_query else update.message

    if not trigger_msg:
        return

    if not rows:
        await trigger_msg.reply_text("📭 Leaderboard is empty. Be the first to start the climb!")
        return

    if criteria == "creators":
        title_caption = "📝 **Top Poll Creators**"
        metric_label = "created"
    elif criteria == "voters":
        title_caption = "🗳️ **Top Voters**"
        metric_label = "votes"
    else:
        title_caption = "⚡ **System Level Leaders (XP)**"
        metric_label = "XP"

    board_text = f"{title_caption}\n" + "—" * 25 + "\n"
    
    medals = ["🥇", "🥈", "🥉", "🏅", "🏅", "🏅", "🏅", "🏅", "🏅", "🏅"]
    for i, row in enumerate(rows):
        medal = medals[i] if i < len(medals) else "🏅"
        name = row.get("full_name") or row.get("username") or "User"
        username_handle = f" (@{row['username']})" if row.get("username") and row["username"] != "Anonymous" else ""
        metric_val = row.get("metric_val", row.get("xp", 0))
        level = row.get("level", 1)
        
        board_text += f"{medal} **{i+1}. {name}**{username_handle}\n    └ `{metric_val}` {metric_label} | Level: `{level}`\n"

    await trigger_msg.reply_text(
        text=board_text,
        parse_mode="Markdown"
    )

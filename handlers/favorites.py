import logging
from telegram import Update
from telegram.ext import ContextTypes
import database
from utils.keyboards import get_voting_inline_keyboard

logger = logging.getLogger("bot.handlers.favorites")

async def favorites_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and displays the user's saved/favorited active polls."""
    user = update.effective_user
    if not user or not update.message:
        return
        
    favs = await database.get_user_favorites(user.id)

    if not favs:
        await update.message.reply_text(
            "⭐ **Your Favorites is empty!**\n\nSave polls to your bookmarks by tapping the `☆ Favorite` button on any poll.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        f"⭐ **Your Favorited Polls ({len(favs)})**:",
        parse_mode="Markdown"
    )

    for p in favs:
        p_id = p.get("poll_id", "")
        title = p.get("title", "")
        desc = p.get("description", "")
        options = p.get("options", [])
        status = p.get("status", "active")
        status_emoji = "🟢 Active" if status == "active" else "🔴 Closed"

        user_vote = await database.get_user_vote(p_id, user.id)
        voted_opt = user_vote.get("option_index") if user_vote else None
        is_owner = (p.get("creator_id") == user.id)

        caption = f"🗳️ **{title}**\n🔑 ID: `{p_id}` | Status: {status_emoji}"
        if desc:
            caption += f"\n_{desc}_"

        await update.message.reply_text(
            text=caption,
            reply_markup=get_voting_inline_keyboard(
                poll_id=p_id,
                options=options,
                user_voted_option=voted_opt,
                is_closed=(status == "closed"),
                is_fav=True,
                is_owner=is_owner
            ),
            parse_mode="Markdown"
        )

async def toggle_favorite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, poll_id: str):
    """Toggles favorite record in SQLite database for the calling user."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user = query.from_user
    is_now_fav = await database.toggle_favorite(user.id, poll_id)
    
    alert_text = "⭐ Added to Favorites!" if is_now_fav else "❌ Removed from Favorites!"
    await query.answer(text=alert_text, show_alert=True)

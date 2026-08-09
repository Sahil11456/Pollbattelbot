import logging
from telegram import Update
from telegram.ext import ContextTypes
import database
from utils.keyboards import get_trending_options_keyboard, get_voting_inline_keyboard

logger = logging.getLogger("bot.handlers.trending")

async def trending_polls_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the trending selector menu."""
    if not update.message:
        return

    await update.message.reply_text(
        "🔥 **Trending & Featured Polls**\n\n"
        "Explore popular polls across the platform:",
        reply_markup=get_trending_options_keyboard(),
        parse_mode="Markdown"
    )

async def list_trending_polls(update: Update, context: ContextTypes.DEFAULT_TYPE, filter_by: str = "votes"):
    """Fetches and sends polls sorted by selected trend metrics."""
    polls = await database.get_trending_polls(limit=5, order_by=filter_by)

    msg_target = update.callback_query.message if update.callback_query else update.message
    if not msg_target:
        return

    if not polls:
        await msg_target.reply_text("📭 No active polls found for this filter right now.")
        return

    user_id = update.effective_user.id if update.effective_user else 0

    await msg_target.reply_text(
        f"🔥 **Top Trending Polls ({filter_by.upper()})**",
        parse_mode="Markdown"
    )

    for p in polls:
        p_id = p.get("poll_id", "")
        title = p.get("title", "")
        desc = p.get("description", "")
        options = p.get("options", [])
        is_closed = p.get("status") == "closed"

        user_vote = await database.get_user_vote(p_id, user_id)
        voted_opt = user_vote.get("option_index") if user_vote else None
        is_fav = await database.is_favorite(p_id, user_id)
        is_owner = (p.get("creator_id") == user_id)

        caption = f"🗳️ **{title}**"
        if desc:
            caption += f"\n_{desc}_"
        caption += f"\n🔑 ID: `{p_id}` | 👁️ Views: {p.get('views', 0)} | 🗳️ Votes: {p.get('vote_count', 0)}"

        await msg_target.reply_text(
            text=caption,
            reply_markup=get_voting_inline_keyboard(
                poll_id=p_id,
                options=options,
                user_voted_option=voted_opt,
                is_closed=is_closed,
                is_fav=is_fav,
                is_owner=is_owner
            ),
            parse_mode="Markdown"
        )

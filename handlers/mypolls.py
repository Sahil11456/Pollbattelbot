import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import database

logger = logging.getLogger("bot.handlers.mypolls")

async def my_polls_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and lists all polls created by the requesting user."""
    user = update.effective_user
    if not user or not update.message:
        return
        
    polls = await database.get_user_polls(user.id)

    if not polls:
        await update.message.reply_text(
            "📭 **You have not created any polls yet!**\n\nClick the '➕ Create Poll' button in the main menu to launch your first topic.",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text(
        f"📊 **My Created Polls ({len(polls)})**\nHere are the polls you have launched:",
        parse_mode="Markdown"
    )

    for p in polls:
        p_id = p.get("poll_id", "")
        title = p.get("title", "")
        status = p.get("status", "active")
        vote_count = p.get("vote_count", 0)
        views = p.get("views", 0)
        shares = p.get("shares", 0)

        status_emoji = "🟢 Active" if status == "active" else "🔴 Closed"
        poll_details_text = (
            f"🗳️ **{title}**\n"
            f"🔑 ID: `{p_id}`\n"
            f"📈 Status: {status_emoji}\n"
            f"🗳️ Votes: `{vote_count}` | 👁️ Views: `{views}` | 🔗 Shares: `{shares}`"
        )
        
        inline_buttons = []
        if status == "active":
            inline_buttons.append(InlineKeyboardButton("🔒 Close Poll", callback_data=f"close_{p_id}"))
        inline_buttons.append(InlineKeyboardButton("🗑️ Delete Poll", callback_data=f"delete_{p_id}"))
        
        keyboard = InlineKeyboardMarkup([
            inline_buttons,
            [InlineKeyboardButton("🔗 Share Poll", switch_inline_query_current_chat=f"share_{p_id}")]
        ])
        
        await update.message.reply_text(
            text=poll_details_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

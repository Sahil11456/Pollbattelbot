import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)
import database
from utils.keyboards import get_search_options_keyboard, get_cancel_reply_keyboard, get_main_menu_keyboard, get_voting_inline_keyboard

logger = logging.getLogger("bot.handlers.search")

SEARCH_QUERY = 0

async def start_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Begins search workflow."""
    if not update.message:
        return

    await update.message.reply_text(
        "🔍 **Search Polls**\n\nChoose search filter from the options below:",
        reply_markup=get_search_options_keyboard(),
        parse_mode="Markdown"
    )

async def search_query_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Processes search query against database."""
    if not update.message or not update.message.text:
        return SEARCH_QUERY

    query_text = update.message.text.strip()
    user = update.effective_user
    db_user = await database.get_user(user.id)
    is_admin = bool(db_user and db_user.get("role") == "admin")

    if not query_text:
        await update.message.reply_text("⚠️ Please enter a search query:")
        return SEARCH_QUERY

    field = context.user_data.get('search_field', 'title')
    results = await database.search_polls(query_text, field=field, limit=5)

    if not results:
        await update.message.reply_text(
            f"❌ No matching polls found for query: `{query_text}`.",
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return ConversationHandler.END

    await update.message.reply_text(
        f"✅ Found {len(results)} matching poll(s):",
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="Markdown"
    )

    for p in results:
        p_id = p.get("poll_id", "")
        title = p.get("title", "")
        desc = p.get("description", "")
        options = p.get("options", [])
        status = p.get("status", "active")
        status_emoji = "🟢 Active" if status == "active" else "🔴 Closed"
        
        user_vote = await database.get_user_vote(p_id, user.id)
        voted_opt = user_vote.get("option_index") if user_vote else None
        is_fav = await database.is_favorite(p_id, user.id)
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
                is_fav=is_fav,
                is_owner=is_owner
            ),
            parse_mode="Markdown"
        )

    context.user_data.clear()
    return ConversationHandler.END

async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    db_user = await database.get_user(user.id)
    is_admin = bool(db_user and db_user.get("role") == "admin")

    if update.message:
        await update.message.reply_text("❌ Search cancelled.", reply_markup=get_main_menu_keyboard(is_admin=is_admin))
    context.user_data.clear()
    return ConversationHandler.END

def get_search_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🔍 Search Polls$"), start_search_handler),
            CommandHandler("search", start_search_handler),
        ],
        states={
            SEARCH_QUERY: [
                MessageHandler(filters.Regex("^❌ Cancel$"), cancel_search),
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_query_received)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_search),
            MessageHandler(filters.Regex("^❌ Cancel$"), cancel_search)
        ]
    )

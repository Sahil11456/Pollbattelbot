import logging
from telegram import Update
from telegram.ext import ContextTypes

from config import ADMIN_IDS
import database
from utils.keyboards import get_poll_inline_keyboard
from utils.progressbar import generate_poll_results_text
from utils.helpers import calculate_rank

logger = logging.getLogger("bot.callbacks")

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Central router for all inline keyboard callback queries.
    Format parsing pattern: 'action:param1:param2'
    """
    query = update.callback_query
    if not query:
        return

    data = query.data
    user = query.from_user
    if not user:
        return

    # Ensure user is registered
    await database.register_user(user.id, user.username, user.first_name)

    # Route by callback prefix
    if data.startswith("vote:"):
        _, poll_id, opt_idx_str = data.split(":")
        await handle_vote(update, context, poll_id, int(opt_idx_str))
    elif data.startswith("refresh:"):
        _, poll_id = data.split(":")
        await handle_refresh_poll(update, context, poll_id)
    elif data.startswith("fav:"):
        _, poll_id = data.split(":")
        await handle_toggle_favorite(update, context, poll_id)
    elif data.startswith("close:"):
        _, poll_id = data.split(":")
        await handle_close_poll(update, context, poll_id)
    elif data.startswith("delete:"):
        _, poll_id = data.split(":")
        await handle_delete_poll(update, context, poll_id)
    elif data.startswith("admin_"):
        await handle_admin_callbacks(update, context, data)
    else:
        await query.answer("⚠️ Unknown action command.", show_alert=True)

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, poll_id: str, option_index: int):
    """Processes user vote on specific poll option."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user = query.from_user
    success, message = await database.cast_vote(poll_id, user.id, option_index)

    if success:
        # Reward user +10 XP per vote
        xp, level, leveled_up = await database.add_xp(user.id, 10)
        pop_msg = f"✅ {message}\n+10 XP awarded!"
        if leveled_up:
            rank = calculate_rank(level)
            pop_msg += f"\n🎉 LEVEL UP! You reached Level {level} ({rank})!"
        await query.answer(pop_msg, show_alert=True)

        # Refresh view
        await handle_refresh_poll(update, context, poll_id)
    else:
        await query.answer(f"⚠️ {message}", show_alert=True)

async def handle_refresh_poll(update: Update, context: ContextTypes.DEFAULT_TYPE, poll_id: str):
    """Refreshes poll card text and percentage bars without throwing unchanged text exceptions."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user = query.from_user
    poll_obj = await database.get_poll(poll_id)
    if not poll_obj:
        await query.answer("❌ Poll no longer exists.", show_alert=True)
        return

    results = await database.get_poll_results(poll_id)
    user_voted_opt = await database.get_user_voted_option(poll_id, user.id)
    is_fav = await database.is_favorite(user.id, poll_id)
    is_closed = bool(poll_obj.get("is_closed", 0))
    is_owner = (poll_obj.get("creator_id") == user.id) or (user.id in ADMIN_IDS)

    updated_text = (
        f"📊 **{poll_obj['title']}**\n"
        f"_{poll_obj.get('description', '')}_\n\n"
        f"{generate_poll_results_text(results, user_voted_opt)}\n"
        f"🆔 `Poll ID: {poll_id}`"
    )

    try:
        await query.edit_message_text(
            text=updated_text,
            reply_markup=get_poll_inline_keyboard(
                poll_id=poll_id,
                options=poll_obj["options"],
                user_voted_option=user_voted_opt,
                is_closed=is_closed,
                is_fav=is_fav,
                is_owner=is_owner
            ),
            parse_mode="Markdown"
        )
        await query.answer("🔄 Refresh completed!")
    except Exception as e:
        # Ignore message not modified exception
        if "Message is not modified" in str(e):
            await query.answer("✨ Results are already up-to-date!")
        else:
            await query.answer("🔄 Updated.")

async def handle_toggle_favorite(update: Update, context: ContextTypes.DEFAULT_TYPE, poll_id: str):
    """Toggles saved favorite state for poll."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user = query.from_user
    is_fav = await database.toggle_favorite(user.id, poll_id)
    poll_obj = await database.get_poll(poll_id)

    if is_fav:
        await query.answer("⭐ Saved to your Favorites!", show_alert=True)
    else:
        await query.answer("🗑️ Removed from Favorites.", show_alert=True)

    if not poll_obj:
        return

    results = await database.get_poll_results(poll_id)
    user_voted_opt = await database.get_user_voted_option(poll_id, user.id)
    is_closed = bool(poll_obj.get("is_closed", 0))
    is_owner = (poll_obj.get("creator_id") == user.id) or (user.id in ADMIN_IDS)

    try:
        await query.edit_message_reply_markup(
            reply_markup=get_poll_inline_keyboard(
                poll_id=poll_id,
                options=poll_obj["options"],
                user_voted_option=user_voted_opt,
                is_closed=is_closed,
                is_fav=is_fav,
                is_owner=is_owner
            )
        )
    except Exception:
        pass

async def handle_close_poll(update: Update, context: ContextTypes.DEFAULT_TYPE, poll_id: str):
    """Closes voting status on target poll."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user = query.from_user
    poll_obj = await database.get_poll(poll_id)
    if not poll_obj:
        await query.answer("❌ Poll not found.", show_alert=True)
        return

    if poll_obj.get("creator_id") != user.id:
        db_user = await database.get_user(user.id)
        if not db_user or db_user.get("role") != "admin":
            await query.answer("❌ You are not authorized to close this poll.", show_alert=True)
            return

    await database.close_poll(poll_id)
    await query.answer("🔒 Poll closed successfully!", show_alert=True)
    await handle_refresh_poll(update, context, poll_id)

async def handle_delete_poll(update: Update, context: ContextTypes.DEFAULT_TYPE, poll_id: str):
    """Deletes target poll."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user = query.from_user
    poll_obj = await database.get_poll(poll_id)
    if not poll_obj:
        await query.answer("❌ Poll not found.", show_alert=True)
        return

    if poll_obj.get("creator_id") != user.id:
        db_user = await database.get_user(user.id)
        if not db_user or db_user.get("role") != "admin":
            await query.answer("❌ You are not authorized to delete this poll.", show_alert=True)
            return

    await database.delete_poll(poll_id)
    await query.answer("🗑️ Poll deleted.", show_alert=True)
    if query.message:
        try:
            await query.message.delete()
        except Exception:
            pass

async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
    """Handles admin-only control panel buttons."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user = query.from_user
    db_user = await database.get_user(user.id)
    if not db_user or db_user.get('role') != 'admin':
        await query.answer("❌ Admin access restricted.", show_alert=True)
        return

    if callback_data == "admin_stats":
        stats = await database.get_system_stats()
        await query.answer("📊 System stats updated!", show_alert=True)
        if query.message:
            await query.message.reply_text(
                f"📊 **System Status**\n"
                f"• Users: {stats.get('total_users')}\n"
                f"• Polls: {stats.get('total_polls')}\n"
                f"• Votes: {stats.get('total_votes')}\n"
                f"• Active Polls: {stats.get('active_polls')}",
                parse_mode="Markdown"
            )
    else:
        await query.answer(f"Admin action: {callback_data}")

# Alias for compatibility across imports
handle_callback_query = callback_query_handler

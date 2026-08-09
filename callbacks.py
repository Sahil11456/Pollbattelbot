import logging
from telegram import Update
from telegram.ext import ContextTypes
import database
from utils.keyboards import get_poll_inline_keyboard
from utils.progressbar import generate_progress_bar

logger = logging.getLogger("bot.callbacks")

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main router for all inline button callbacks in the bot.
    Handles voting, revoting, refreshing, closing, deleting, dynamic results, and admin actions.
    """
    query = update.callback_query
    if not query:
        return

    data = query.data
    if not data:
        return

    user = query.from_user

    # 1. Handle Vote Casting: vote:<poll_id>:<option_idx>
    if data.startswith("vote:"):
        parts = data.split(":")
        if len(parts) >= 3:
            poll_id = parts[1]
            try:
                option_idx = int(parts[2])
            except ValueError:
                await query.answer("❌ Invalid option selection.", show_alert=True)
                return
            await handle_vote_action(update, context, poll_id, option_idx)
            return

    # 2. Handle Revote Action: revote:<poll_id>
    elif data.startswith("revote:"):
        parts = data.split(":")
        if len(parts) >= 2:
            poll_id = parts[1]
            await handle_revote_action(update, context, poll_id)
            return

    # 3. Handle Refresh Poll View: refresh:<poll_id>
    elif data.startswith("refresh:"):
        parts = data.split(":")
        if len(parts) >= 2:
            poll_id = parts[1]
            await handle_refresh_poll(update, context, poll_id)
            return

    # 4. Handle Close Poll: close:<poll_id>
    elif data.startswith("close:"):
        parts = data.split(":")
        if len(parts) >= 2:
            poll_id = parts[1]
            await handle_close_poll(update, context, poll_id)
            return

    # 5. Handle Delete Poll: delete:<poll_id>
    elif data.startswith("delete:"):
        parts = data.split(":")
        if len(parts) >= 2:
            poll_id = parts[1]
            await handle_delete_poll(update, context, poll_id)
            return

    # 6. Handle Favorite Toggle: fav:<poll_id>
    elif data.startswith("fav:"):
        parts = data.split(":")
        if len(parts) >= 2:
            poll_id = parts[1]
            is_fav = await database.toggle_favorite(user.id, poll_id)
            status_msg = "⭐ Saved to Favorites!" if is_fav else "❌ Removed from Favorites."
            await query.answer(status_msg, show_alert=True)
            await handle_refresh_poll(update, context, poll_id)
            return

    # 7. Admin Panel Buttons
    elif data.startswith("admin_"):
        await handle_admin_callbacks(update, context, data)
        return

    else:
        await query.answer("ℹ️ Unrecognized button command.", show_alert=True)

async def handle_vote_action(update: Update, context: ContextTypes.DEFAULT_TYPE, poll_id: str, option_idx: int):
    """Processes user vote submission asynchronously."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user = query.from_user
    # Ensure user exists in database
    await database.get_or_create_user(user.id, user.username or "", user.full_name or "")

    poll_obj = await database.get_poll(poll_id)
    if not poll_obj:
        await query.answer("❌ This poll no longer exists.", show_alert=True)
        return

    if poll_obj.get("status") != "active":
        await query.answer("🔒 Voting is closed on this poll.", show_alert=True)
        return

    # Check existing vote
    existing_vote = await database.get_user_vote(user.id, poll_id)
    if existing_vote:
        if not poll_obj.get("allow_revote", 1):
            await query.answer("⚠️ You have already voted on this poll! Revoting is disabled.", show_alert=True)
            return
        else:
            # Change existing vote
            await database.cast_vote(user.id, poll_id, option_idx)
            await query.answer("🔄 Your vote has been updated!", show_alert=False)
    else:
        # Cast new vote and award XP
        await database.cast_vote(user.id, poll_id, option_idx)
        await database.add_user_xp(user.id, 10)
        await query.answer("✅ Vote recorded! (+10 XP)", show_alert=False)

    # Refresh message UI with new counts
    await handle_refresh_poll(update, context, poll_id)

async def handle_revote_action(update: Update, context: ContextTypes.DEFAULT_TYPE, poll_id: str):
    """Prompts or clears user's current choice to let them choose again."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user = query.from_user
    poll_obj = await database.get_poll(poll_id)
    if not poll_obj:
        await query.answer("❌ Poll not found.", show_alert=True)
        return

    if not poll_obj.get("allow_revote", 1):
        await query.answer("❌ Revoting is not permitted for this poll.", show_alert=True)
        return

    existing_vote = await database.get_user_vote(user.id, poll_id)
    if not existing_vote:
        await query.answer("ℹ️ You haven't voted yet!", show_alert=True)
        return

    await query.answer("🔄 Select any option above to change your vote.", show_alert=True)

async def handle_refresh_poll(update: Update, context: ContextTypes.DEFAULT_TYPE, poll_id: str):
    """Refreshes the rendered progress bar breakdown and keyboard buttons for the target poll."""
    query = update.callback_query
    if not query or not query.message:
        return

    user = query.from_user
    poll_obj = await database.get_poll(poll_id)
    if not poll_obj:
        return

    options = poll_obj.get("options", [])
    total_votes = poll_obj.get("total_votes", 0)
    is_closed = poll_obj.get("status") != "active"
    hide_results = poll_obj.get("hide_results_until_closed", 0) and not is_closed

    user_vote = await database.get_user_vote(user.id, poll_id) if user else None
    user_voted_opt = user_vote.get("option_index") if user_vote else None
    is_fav = await database.is_favorite(user.id, poll_id) if user else False
    is_owner = (poll_obj.get("creator_id") == user.id) if user else False

    # Format poll results body text
    body = f"📊 **{poll_obj.get('title')}**\n"
    if poll_obj.get('description'):
        body += f"_{poll_obj.get('description')}_\n"
    body += "----------------------------------------\n\n"

    if hide_results:
        body += "🔒 *Results are hidden until voting closes.*\n\n"
        for opt in options:
            mark = " 👈 (Your Choice)" if opt.get("option_index") == user_voted_opt else ""
            body += f"• **{opt.get('option_text')}**{mark}\n"
    else:
        for opt in options:
            opt_cnt = opt.get("vote_count", 0)
            percentage = (opt_cnt / total_votes * 100) if total_votes > 0 else 0.0
            bar = generate_progress_bar(percentage)
            mark = " 👈" if opt.get("option_index") == user_voted_opt else ""
            body += f"**{opt.get('option_text')}**{mark}\n`{bar}` {percentage:.1f}% ({opt_cnt} votes)\n\n"

    footer_text = await database.get_setting("footer_text", "⚡ Powered by Telegram Poll Battle Bot")
    body += f"🗳️ Total Votes: `{total_votes}` | Status: `{'CLOSED 🔒' if is_closed else 'ACTIVE 🟢'}`\n\n_{footer_text}_"

    try:
        await query.message.edit_text(
            text=body,
            reply_markup=get_poll_inline_keyboard(
                poll_id=poll_id,
                options=options,
                user_voted_opt=user_voted_opt,
                is_closed=is_closed,
                is_fav=is_fav,
                is_owner=is_owner
            ),
            parse_mode="Markdown"
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

# Alias for compatibility
handle_callback_query = callback_query_handler

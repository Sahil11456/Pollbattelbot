import logging
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ContextTypes
import database
from utils.progressbar import draw_progress_bar
from utils.keyboards import get_voting_inline_keyboard
from handlers.favorites import toggle_favorite_callback
from handlers.trending import list_trending_polls
from handlers.leaderboard import display_leaderboard
from handlers.forcejoin import check_force_join_subscriptions, get_force_join_prompt_keyboard

logger = logging.getLogger("bot.callbacks")

user_last_click_time = {}

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router for all inline key callback query requests."""
    query = update.callback_query
    if not query or not query.from_user or not query.data:
        return

    user = query.from_user
    data = query.data

    # Rate Limiter Guard
    now = datetime.now(timezone.utc).timestamp()
    last_time = user_last_click_time.get(user.id, 0)
    if now - last_time < 0.5:
        await query.answer("⚠️ Please wait a moment between actions.", show_alert=True)
        return
    user_last_click_time[user.id] = now

    # Maintenance Mode Guard
    m_mode = await database.get_setting("maintenance_mode", "false")
    if m_mode.lower() == "true":
        db_user = await database.get_user(user.id)
        if not db_user or db_user.get("role") != "admin":
            await query.answer("🛠️ Maintenance in progress. Please try again later.", show_alert=True)
            return

    # Routing
    if data.startswith("vote_"):
        parts = data.split("_")
        if len(parts) >= 3:
            poll_id = parts[1]
            option_idx = int(parts[2])
            await handle_cast_vote(update, context, poll_id, option_idx)
        return

    elif data.startswith("fav_"):
        poll_id = data.replace("fav_", "")
        await toggle_favorite_callback(update, context, poll_id)
        return

    elif data.startswith("close_"):
        poll_id = data.replace("close_", "")
        await handle_close_poll(update, context, poll_id)
        return

    elif data.startswith("delete_") or data.startswith("del_"):
        poll_id = data.replace("delete_", "").replace("del_yes_", "").replace("del_confirm_", "")
        await handle_delete_poll(update, context, poll_id)
        return

    elif data.startswith("refresh_"):
        poll_id = data.replace("refresh_", "")
        await handle_refresh_poll(update, context, poll_id)
        return

    elif data.startswith("trend_"):
        criteria = data.replace("trend_", "")
        await query.answer()
        await list_trending_polls(update, context, criteria)
        return

    elif data.startswith("lb_"):
        criteria = data.replace("lb_tab_", "").replace("lb_per_", "").replace("lb_", "")
        await query.answer()
        await display_leaderboard(update, context, criteria)
        return

    elif data.startswith("search_"):
        criteria = data.replace("search_by_", "").replace("search_", "")
        context.user_data['search_field'] = criteria
        await query.answer()
        if query.message:
            await query.message.reply_text(
                f"🔍 **Search Filter Selected: {criteria.upper()}**\n\nPlease type your search query in the chat:",
                parse_mode="Markdown"
            )
        return

    elif data == "verify_member_sub":
        is_sub, unsub = await check_force_join_subscriptions(user.id, context.bot)
        if is_sub:
            await query.answer("🎉 Verification successful! Access granted.", show_alert=True)
            if query.message:
                try:
                    await query.message.delete()
                except Exception:
                    pass
        else:
            await query.answer("❌ Verification failed. Please join required channels first.", show_alert=True)
        return

    elif data.startswith("admin_"):
        await handle_admin_callbacks(update, context, data)
        return

async def handle_cast_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, poll_id: str, option_idx: int):
    """Casts vote and refreshes message view."""
    query = update.callback_query
    if not query or not query.from_user:
        return

    user = query.from_user

    # Force Join Check
    is_sub, unsub = await check_force_join_subscriptions(user.id, context.bot)
    if not is_sub:
        await query.answer("🔐 Action Restricted: Channel subscription required.", show_alert=True)
        if query.message:
            await query.message.reply_text(
                "🔐 **Force-Join Policy Active**\n\nPlease join our required channel(s) to vote:",
                reply_markup=get_force_join_prompt_keyboard(unsub),
                parse_mode="Markdown"
            )
        return

    poll_obj = await database.get_poll(poll_id)
    if not poll_obj:
        await query.answer("❌ Poll not found.", show_alert=True)
        return

    if poll_obj.get("status") != "active":
        await query.answer("🔒 This poll is closed.", show_alert=True)
        return

    # Check expiration
    expires_at = poll_obj.get("expires_at")
    if expires_at:
        try:
            exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp_dt:
                await database.close_poll(poll_id)
                await query.answer("🔒 Voting period expired.", show_alert=True)
                return
        except Exception:
            pass

    # Cast vote in db
    success, message = await database.cast_vote(poll_id, user.id, option_idx)
    await query.answer(message, show_alert=True)

    if success:
        # Refresh poll UI
        await handle_refresh_poll(update, context, poll_id)

async def handle_refresh_poll(update: Update, context: ContextTypes.DEFAULT_TYPE, poll_id: str):
    """Refreshes poll results display on the message."""
    query = update.callback_query
    if not query or not query.from_user or not query.message:
        return

    user = query.from_user
    poll_obj = await database.get_poll(poll_id)
    if not poll_obj:
        await query.answer("❌ Poll not found.", show_alert=True)
        return

    title = poll_obj.get("title", "")
    desc = poll_obj.get("description", "")
    options = poll_obj.get("options", [])
    total_votes = poll_obj.get("vote_count", 0)
    is_closed = poll_obj.get("status") == "closed"

    user_vote = await database.get_user_vote(poll_id, user.id)
    voted_opt = user_vote.get("option_index") if user_vote else None
    is_fav = await database.is_favorite(poll_id, user.id)
    is_owner = (poll_obj.get("creator_id") == user.id)

    results_text = f"🗳️ **{title}**\n"
    if desc:
        results_text += f"_{desc}_\n"
    results_text += "\n"

    for opt in options:
        opt_text = opt.get("option_text", "")
        cnt = opt.get("vote_count", 0)
        pct = (cnt / total_votes * 100) if total_votes > 0 else 0
        bar = draw_progress_bar(pct, cnt)
        results_text += f"• **{opt_text}** ({cnt} votes)\n{bar}\n\n"

    results_text += f"📊 Total Votes: `{total_votes}` | 👁️ Views: `{poll_obj.get('views', 0)}`"

    try:
        await query.edit_message_text(
            text=results_text,
            reply_markup=get_voting_inline_keyboard(
                poll_id=poll_id,
                options=options,
                user_voted_option=voted_opt,
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

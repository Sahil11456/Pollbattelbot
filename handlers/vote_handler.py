from telegram import Update
from telegram.ext import ContextTypes
from database import db
from keyboards import get_poll_inline_keyboard
from utils.helpers import format_poll_card, escape_html
from utils.anti_spam import anti_spam

async def handle_vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data:
        return

    callback_data = query.data
    user = update.effective_user

    if not anti_spam.validate_callback(callback_data):
        await query.answer("Invalid request.", show_alert=True)
        return

    parts = callback_data.split(":")
    action = parts[0]

    # --- VOTE ACTION ---
    if action == "vote":
        if len(parts) < 3:
            return
        poll_id = parts[1]
        option_id = int(parts[2])

        # Cast vote in DB
        res = await db.cast_vote(poll_id, user.id, option_id)
        await query.answer(res["message"], show_alert=not res["success"])

        if res["success"]:
            # Update inline message with live vote count & progress bars
            poll = await db.get_poll(poll_id)
            user_votes = await db.get_user_voted_options(poll_id, user.id)
            text = format_poll_card(poll, user_votes)
            kb = get_poll_inline_keyboard(poll, user_votes)

            try:
                await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass  # Message unchanged

    # --- REFRESH ACTION ---
    elif action == "refresh":
        poll_id = parts[1]
        poll = await db.get_poll(poll_id)
        if not poll:
            await query.answer("Poll no longer exists.", show_alert=True)
            return

        user_votes = await db.get_user_voted_options(poll_id, user.id)
        text = format_poll_card(poll, user_votes)
        kb = get_poll_inline_keyboard(poll, user_votes)

        try:
            await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
            await query.answer("🔄 Poll updated!")
        except Exception:
            await query.answer("Already up to date!")

    # --- STATS ACTION ---
    elif action == "stats":
        poll_id = parts[1]
        poll = await db.get_poll(poll_id)
        if not poll:
            await query.answer("Poll not found.", show_alert=True)
            return

        total_v = poll.get("total_votes", 0)
        options = poll.get("options", [])
        breakdown = "\n".join([f"• {opt['option_text']}: {opt['vote_count']} votes" for opt in options])

        msg = (
            f"📊 <b>POLL STATS</b>\n\n"
            f"❓ <b>Question:</b> {escape_html(poll['question'])}\n"
            f"👥 <b>Total Voters:</b> {total_v}\n\n"
            f"<b>Options Breakdown:</b>\n{breakdown}"
        )
        await query.answer()
        await context.bot.send_message(chat_id=user.id, text=msg, parse_mode="HTML")

    # --- FAVORITE ACTION ---
    elif action == "fav":
        poll_id = parts[1]
        is_added = await db.toggle_favorite(user.id, poll_id)
        msg = "❤️ Added to Favorites!" if is_added else "💔 Removed from Favorites."
        await query.answer(msg, show_alert=True)

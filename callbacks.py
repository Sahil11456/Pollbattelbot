from telegram import Update
from telegram.ext import ContextTypes
from services.vote_service import cast_vote
from services.poll_service import get_poll_details
from utils.keyboards import build_poll_inline_keyboard

async def poll_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split(":")
    action = data[0]
    
    if action == "vote":
        poll_id, option_id = data[1], data[2]
        success, msg = await cast_vote(poll_id, option_id, query.from_user.id)
        await query.answer(msg, show_alert=not success)
        
        poll, options = await get_poll_details(poll_id)
        if poll and options:
            total_votes = sum(o["votes"] for o in options)
            for o in options:
                o["pct"] = round((o["votes"] / total_votes * 100), 1) if total_votes > 0 else 0
            
            kb = build_poll_inline_keyboard(poll_id, options)
            await query.edit_message_reply_markup(reply_markup=kb)

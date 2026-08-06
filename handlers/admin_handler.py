from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from database import db
from keyboards import get_admin_inline_keyboard
from utils.helpers import escape_html
import config

BROADCAST_MSG, BAN_ID, UNBAN_ID = range(10, 13)

async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔ <b>Unauthorized access.</b>", parse_mode="HTML")
        return

    stats = await db.get_system_stats()
    m_mode = await db.get_maintenance_mode()

    text = (
        f"⚡ <b>ADMIN PANEL DASHBOARD</b> ⚡\n\n"
        f"👥 <b>Total Users:</b> {stats['total_users']}\n"
        f"📝 <b>Total Polls:</b> {stats['total_polls']}\n"
        f"🗳️ <b>Total Votes:</b> {stats['total_votes']}\n"
        f"🔥 <b>Active Polls:</b> {stats['active_polls']}\n"
        f"🛠️ <b>Maintenance Mode:</b> {'ENABLED' if m_mode else 'DISABLED'}\n\n"
        f"Select an admin action below:"
    )
    kb = get_admin_inline_keyboard()
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.data:
        return

    user = update.effective_user
    if user.id not in config.ADMIN_IDS:
        await query.answer("Unauthorized", show_alert=True)
        return

    cb = query.data

    if cb == "admin:maintenance":
        curr = await db.get_maintenance_mode()
        new_val = not curr
        await db.set_maintenance_mode(new_val)
        status_str = "ENABLED 🛠️" if new_val else "DISABLED ✅"
        await query.answer(f"Maintenance mode set to {status_str}", show_alert=True)
        # Refresh panel
        await admin_panel_command(query, context)

    elif cb == "admin:logs":
        logs = await db.get_recent_error_logs(limit=5)
        if not logs:
            await query.answer("No error logs recorded!", show_alert=True)
            return

        text = "📋 <b>RECENT ERROR LOGS:</b>\n\n"
        for l in logs:
            text += f"▪️ <b>User {l.get('user_id')}:</b> {escape_html(l['error_message'])}\n<code>{l['created_at']}</code>\n\n"

        await query.answer()
        await context.bot.send_message(chat_id=user.id, text=text, parse_mode="HTML")

    elif cb == "admin:broadcast":
        await query.answer()
        await context.bot.send_message(chat_id=user.id, text="📢 Send the message text to broadcast to all users (or /cancel):")
        return BROADCAST_MSG

    elif cb == "admin:ban":
        await query.answer()
        await context.bot.send_message(chat_id=user.id, text="🚫 Send the Telegram User ID to BAN (or /cancel):")
        return BAN_ID

    elif cb == "admin:unban":
        await query.answer()
        await context.bot.send_message(chat_id=user.id, text="✅ Send the Telegram User ID to UNBAN (or /cancel):")
        return UNBAN_ID

async def receive_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_ids = await db.get_all_user_ids()

    success, failed = 0, 0
    await update.message.reply_text(f"⏳ Broadcasting to {len(user_ids)} users...")

    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=text, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"✅ Broadcast complete!\nSuccess: {success} | Failed: {failed}")
    return ConversationHandler.END

async def receive_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(update.message.text.strip())
        res = await db.ban_user(uid)
        if res:
            await update.message.reply_text(f"🚫 User {uid} has been BANNED.")
        else:
            await update.message.reply_text(f"❌ User {uid} not found.")
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID.")
    return ConversationHandler.END

async def receive_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(update.message.text.strip())
        res = await db.unban_user(uid)
        if res:
            await update.message.reply_text(f"✅ User {uid} has been UNBANNED.")
        else:
            await update.message.reply_text(f"❌ User {uid} not found.")
    except ValueError:
        await update.message.reply_text("❌ Invalid User ID.")
    return ConversationHandler.END

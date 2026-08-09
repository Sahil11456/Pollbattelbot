import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
import database
from utils.keyboards import get_admin_dashboard_keyboard, get_admin_broadcast_types_keyboard, get_cancel_reply_keyboard, get_main_menu_keyboard

logger = logging.getLogger("bot.handlers.admin")

BC_TEXT, BC_MEDIA, BC_FORWARD = range(3)

async def admin_dashboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Serves the central administrative control deck to verified admins."""
    user = update.effective_user
    if not user or not update.message:
        return
        
    db_user = await database.get_user(user.id)
    if not db_user or db_user.get('role') != 'admin':
        await update.message.reply_text("❌ **Permission Denied:** This module is restricted to system administrators.")
        return

    stats = await database.get_system_stats()
    m_mode = await database.get_setting("maintenance_mode", "false")
    status_str = "⚠️ MAINTENANCE ACTIVE" if m_mode.lower() == "true" else "🟢 NOMINAL OPERATION"

    text = (
        f"👨‍💼 **System Admin Control Center**\n"
        f"—————————————————————\n"
        f"📈 **Status:** `{status_str}`\n"
        f"👥 **Users Registered:** `{stats.get('total_users', 0)}`\n"
        f"📝 **Polls Created:** `{stats.get('total_polls', 0)}`\n"
        f"🗳️ **Votes Cast:** `{stats.get('total_votes', 0)}`\n\n"
        f"Select an admin action below:"
    )

    await update.message.reply_text(
        text=text,
        reply_markup=get_admin_dashboard_keyboard(),
        parse_mode="Markdown"
    )

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Invokes selection of announcement broadcast format."""
    if update.message:
        await update.message.reply_text(
            "📢 **Select Announcement Format:**",
            reply_markup=get_admin_broadcast_types_keyboard(),
            parse_mode="Markdown"
        )
    return ConversationHandler.END

async def bc_msg_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends text broadcast to all registered users."""
    if not update.message or not update.message.text:
        return BC_TEXT

    text = update.message.text.strip()
    users = await database.get_all_users()

    await update.message.reply_text(f"⏳ Sending message to {len(users)} users...")
    
    success, fail = 0, 0
    for u in users:
        u_id = u.get("user_id")
        if not u_id:
            continue
        try:
            await context.bot.send_message(
                chat_id=u_id,
                text=f"📢 **ANNOUNCEMENT:**\n\n{text}",
                parse_mode="Markdown"
            )
            success += 1
        except Exception:
            fail += 1

    await update.message.reply_text(
        f"📢 **Broadcast Complete!**\n\n✅ Delivered: `{success}`\n❌ Failed: `{fail}`",
        reply_markup=get_main_menu_keyboard(is_admin=True),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def bc_media_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Broadcasts media with caption to users."""
    if not update.message:
        return BC_MEDIA

    photo = update.message.photo[-1] if update.message.photo else None
    caption = update.message.caption or update.message.text or ""
    
    if not photo:
        await update.message.reply_text("⚠️ Please send a Photo with a caption to broadcast:")
        return BC_MEDIA
        
    users = await database.get_all_users()

    success, fail = 0, 0
    for u in users:
        u_id = u.get("user_id")
        if not u_id:
            continue
        try:
            await context.bot.send_photo(
                chat_id=u_id,
                photo=photo.file_id,
                caption=f"📢 **MEDIA UPDATE**\n\n{caption}",
                parse_mode="Markdown"
            )
            success += 1
        except Exception:
            fail += 1

    await update.message.reply_text(
        f"🖼️ **Media Broadcast Complete!**\n\n✅ Delivered: `{success}`\n❌ Failed: `{fail}`",
        reply_markup=get_main_menu_keyboard(is_admin=True),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def bc_forward_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Forwards a target message to all users."""
    msg = update.message
    if not msg:
        return BC_FORWARD

    users = await database.get_all_users()

    success, fail = 0, 0
    for u in users:
        u_id = u.get("user_id")
        if not u_id:
            continue
        try:
            await context.bot.forward_message(
                chat_id=u_id,
                from_chat_id=msg.chat_id,
                message_id=msg.message_id
            )
            success += 1
        except Exception:
            fail += 1

    await update.message.reply_text(
        f"➡️ **Forwarding Complete!**\n\n✅ Delivered: `{success}`\n❌ Failed: `{fail}`",
        reply_markup=get_main_menu_keyboard(is_admin=True),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def cancel_bc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("❌ Broadcast sequence cancelled.", reply_markup=get_main_menu_keyboard(is_admin=True))
    return ConversationHandler.END

def get_broadcast_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("admin_broadcast", start_broadcast),
        ],
        states={
            BC_TEXT: [
                MessageHandler(filters.Regex("^❌ Cancel$"), cancel_bc),
                MessageHandler(filters.TEXT & ~filters.COMMAND, bc_msg_received)
            ],
            BC_MEDIA: [
                MessageHandler(filters.Regex("^❌ Cancel$"), cancel_bc),
                MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, bc_media_received)
            ],
            BC_FORWARD: [
                MessageHandler(filters.Regex("^❌ Cancel$"), cancel_bc),
                MessageHandler(filters.ALL, bc_forward_received)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_bc),
            MessageHandler(filters.Regex("^❌ Cancel$"), cancel_bc)
        ]
    )

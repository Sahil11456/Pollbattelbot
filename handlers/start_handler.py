from telegram import Update
from telegram.ext import ContextTypes
from database import db
from keyboards import get_main_reply_keyboard, get_poll_inline_keyboard, get_force_join_inline_keyboard
from utils.helpers import format_poll_card, escape_html
from utils.anti_spam import anti_spam
import config

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    # Maintenance Mode Check
    if await db.get_maintenance_mode() and user.id not in config.ADMIN_IDS:
        await update.message.reply_text("🛠️ <b>Bot is currently under maintenance. Please try again later!</b>", parse_mode="HTML")
        return

    # Anti-Spam Check
    if anti_spam.is_rate_limited(user.id):
        await update.message.reply_text("⚠️ <b>Slow down! Too many requests.</b>", parse_mode="HTML")
        return

    # Device Signature & Add User
    device_sig = anti_spam.generate_device_signature(update)
    user_db = await db.add_or_update_user(user.id, user.username, user.first_name, user.last_name, device_sig)

    if user_db and user_db.get("is_banned"):
        await update.message.reply_text("🚫 <b>Your account has been banned from using this bot.</b>", parse_mode="HTML")
        return

    # Force Join Check
    fj_channels = await db.get_force_join_channels()
    if fj_channels and user.id not in config.ADMIN_IDS:
        # Check membership for each channel
        unjoined = []
        for ch in fj_channels:
            try:
                member = await context.bot.get_chat_member(ch["channel_id"], user.id)
                if member.status in ("left", "kicked"):
                    unjoined.append(ch)
            except Exception:
                unjoined.append(ch)

        if unjoined:
            kb = get_force_join_inline_keyboard(unjoined)
            await update.message.reply_text(
                "📢 <b>To use this bot, you must join our official channels first:</b>",
                reply_markup=kb,
                parse_mode="HTML"
            )
            return

    # Handle Deep Links (e.g. /start poll_123456)
    if context.args and len(context.args) > 0:
        arg = context.args[0]
        if arg.startswith("poll_"):
            poll_id = arg.replace("poll_", "")
            poll = await db.get_poll(poll_id)
            if poll:
                user_votes = await db.get_user_voted_options(poll_id, user.id)
                text = format_poll_card(poll, user_votes)
                kb = get_poll_inline_keyboard(poll, user_votes)
                await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
                return

    is_admin = user.id in config.ADMIN_IDS
    reply_kb = get_main_reply_keyboard(is_admin)

    welcome_text = (
        f"👋 <b>Welcome to {escape_html(config.BOT_NAME)}!</b>\n\n"
        f"Create interactive polls, launch battles, track live votes, "
        f"post to channels, and detect automatic winners!\n\n"
        f"Choose an option from the menu below to get started:"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_kb, parse_mode="HTML")

async def force_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Checking membership...")

    user = update.effective_user
    fj_channels = await db.get_force_join_channels()

    unjoined = []
    for ch in fj_channels:
        try:
            member = await context.bot.get_chat_member(ch["channel_id"], user.id)
            if member.status in ("left", "kicked"):
                unjoined.append(ch)
        except Exception:
            unjoined.append(ch)

    if unjoined:
        kb = get_force_join_inline_keyboard(unjoined)
        await query.edit_message_text(
            "❌ <b>You have not joined all channels yet! Please join and click below:</b>",
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        is_admin = user.id in config.ADMIN_IDS
        reply_kb = get_main_reply_keyboard(is_admin)
        await query.message.delete()
        await context.bot.send_message(
            chat_id=user.id,
            text="✅ <b>Verification successful! Welcome to Poll Battle Bot.</b>",
            reply_markup=reply_kb,
            parse_mode="HTML"
        )

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_db = await db.get_user(user.id)
    if not user_db:
        return

    polls = await db.get_user_polls(user.id)
    total_created = len(polls)
    
    text = (
        f"👤 <b>USER PROFILE</b>\n\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"👤 <b>Name:</b> {escape_html(user.first_name)}\n"
        f"🏷️ <b>Username:</b> @{escape_html(user.username or 'N/A')}\n"
        f"📊 <b>Polls Created:</b> {total_created}\n"
        f"🔒 <b>Status:</b> {'Admin' if user_db.get('is_admin') else 'Active User'}\n\n"
        f"🤖 <b>{escape_html(config.BOT_NAME)}</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        f"ℹ️ <b>{escape_html(config.BOT_NAME)} Guide</b>\n\n"
        f"• <b>Create Poll:</b> Step-by-step wizard to create Public, Private, Anonymous, or Quiz polls.\n"
        f"• <b>Trending Polls:</b> View top voted live polls.\n"
        f"• <b>Search Polls:</b> Find polls by question keywords.\n"
        f"• <b>Leaderboard:</b> Top voters and poll creators.\n"
        f"• <b>Auto Winner Announcement:</b> When expiry time is reached, winner is posted automatically!\n\n"
        f"🤖 <b>{escape_html(config.BOT_NAME)}</b>"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")

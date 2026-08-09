import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import database

logger = logging.getLogger("bot.handlers.forcejoin")

async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to register a new required force-join channel."""
    user = update.effective_user
    if not user or not update.message:
        return

    db_user = await database.get_user(user.id)
    if not db_user or db_user.get('role') != 'admin':
        await update.message.reply_text("❌ Permission Denied.")
        return

    channel_username = context.args[0].strip() if context.args else ""
    if not channel_username or not channel_username.startswith("@"):
        await update.message.reply_text("⚠️ Syntax: `/add_channel @ChannelUsername`", parse_mode="Markdown")
        return

    await database.add_force_join_channel(channel_username, channel_title=channel_username)

    await update.message.reply_text(
        f"✅ **Success:** Force-Join required channel `{channel_username}` registered successfully.",
        parse_mode="Markdown"
    )

async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to restrict a specific user."""
    user = update.effective_user
    if not user or not update.message:
        return

    db_user = await database.get_user(user.id)
    if not db_user or db_user.get('role') != 'admin':
        await update.message.reply_text("❌ Permission Denied.")
        return

    target_id_str = context.args[0].strip() if context.args else ""
    if not target_id_str or not target_id_str.isdigit():
        await update.message.reply_text("⚠️ Syntax: `/ban_user <user_id_integer>`", parse_mode="Markdown")
        return

    target_id = int(target_id_str)
    await database.ban_user(target_id)

    await update.message.reply_text(f"✅ **Success:** User ID `{target_id}` is now banned.", parse_mode="Markdown")

async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to lift a ban on a specific user."""
    user = update.effective_user
    if not user or not update.message:
        return

    db_user = await database.get_user(user.id)
    if not db_user or db_user.get('role') != 'admin':
        await update.message.reply_text("❌ Permission Denied.")
        return

    target_id_str = context.args[0].strip() if context.args else ""
    if not target_id_str or not target_id_str.isdigit():
        await update.message.reply_text("⚠️ Syntax: `/unban_user <user_id_integer>`", parse_mode="Markdown")
        return

    target_id = int(target_id_str)
    await database.unban_user(target_id)

    await update.message.reply_text(f"✅ **Success:** Ban lifted on User ID `{target_id}`.", parse_mode="Markdown")

async def check_force_join_subscriptions(user_id: int, bot) -> tuple[bool, list]:
    """
    Verifies if a user is subscribed to all configured active force-join channels.
    """
    channels = await database.get_force_join_channels()
    if not channels:
        return True, []

    unsubscribed = []
    for ch in channels:
        ch_uname = ch.get("channel_username") or ch.get("channel_id")
        if not ch_uname:
            continue
        try:
            member = await bot.get_chat_member(chat_id=ch_uname, user_id=user_id)
            if member.status not in ['creator', 'administrator', 'member', 'restricted']:
                unsubscribed.append(ch_uname)
        except Exception as e:
            logger.warning(f"Failed subscription check for user {user_id} on {ch_uname}: {e}")
            unsubscribed.append(ch_uname)

    if unsubscribed:
        return False, unsubscribed
    return True, []

def get_force_join_prompt_keyboard(channels: list) -> InlineKeyboardMarkup:
    """Creates buttons pointing to required subscription links alongside verification action."""
    buttons = []
    for ch in channels:
        ch_str = str(ch)
        clean_ch = ch_str.replace("@", "")
        buttons.append([InlineKeyboardButton(f"📢 Join {ch_str}", url=f"https://t.me/{clean_ch}")])
    buttons.append([InlineKeyboardButton("🔄 Verify Membership", callback_data="verify_member_sub")])
    return InlineKeyboardMarkup(buttons)

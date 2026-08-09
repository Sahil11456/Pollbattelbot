import logging
from telegram import Update
from telegram.ext import ContextTypes
import database

logger = logging.getLogger("bot.handlers.settings")

async def settings_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows admins or users to see current system configs or customize their settings."""
    user = update.effective_user
    if not user or not update.message:
        return
        
    db_user = await database.get_user(user.id)
    is_admin = bool(db_user and db_user.get('role') == 'admin')

    m_mode = await database.get_setting('maintenance_mode', 'false')
    footer = await database.get_setting('custom_footer', 'Powered by Poll Battle Bot')
    auto_post = await database.get_setting('auto_post_polls', 'true')
    device_check = await database.get_setting('device_verification', 'true')

    text = (
        f"⚙️ **System Settings Configuration**\n"
        f"—————————————————————\n"
        f"• **Maintenance Mode:** `{m_mode}`\n"
        f"• **Auto Channel Posting:** `{auto_post}`\n"
        f"• **Unique Device Guard:** `{device_check}`\n"
        f"• **Channel Custom Footer:** `{footer}`\n\n"
    )
    
    if is_admin:
        text += (
            f"🔧 **Admin Customization Commands:**\n"
            f"• `/set_footer <text>` - Update poll custom footer branding\n"
            f"• `/toggle_autopost` - Enable/Disable automatic channel posts\n"
            f"• `/toggle_device_guard` - Require single-device vote verification"
        )
    else:
        text += "💡 _System configuration is managed by server administrators._"

    await update.message.reply_text(
        text=text,
        parse_mode="Markdown"
    )

async def set_footer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to update custom footer text."""
    user = update.effective_user
    if not user or not update.message:
        return

    db_user = await database.get_user(user.id)
    if not db_user or db_user.get('role') != 'admin':
        await update.message.reply_text("❌ Permission Denied.")
        return

    new_footer = " ".join(context.args).strip() if context.args else ""
    if not new_footer:
        await update.message.reply_text("⚠️ Syntax: `/set_footer <My Brand Custom Name>`", parse_mode="Markdown")
        return

    await database.set_setting('custom_footer', new_footer)
    await update.message.reply_text(f"✅ **Success:** Custom footer updated to: `{new_footer}`", parse_mode="Markdown")

async def toggle_autopost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to toggle automatic channel posting."""
    user = update.effective_user
    if not user or not update.message:
        return

    db_user = await database.get_user(user.id)
    if not db_user or db_user.get('role') != 'admin':
        await update.message.reply_text("❌ Permission Denied.")
        return

    current = await database.get_setting('auto_post_polls', 'true')
    new_val = "false" if current.lower() == "true" else "true"
    await database.set_setting('auto_post_polls', new_val)

    await update.message.reply_text(f"✅ **Success:** Auto-Posting set to `{new_val}`", parse_mode="Markdown")

async def toggle_device_guard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to toggle single-device voter security check."""
    user = update.effective_user
    if not user or not update.message:
        return

    db_user = await database.get_user(user.id)
    if not db_user or db_user.get('role') != 'admin':
        await update.message.reply_text("❌ Permission Denied.")
        return

    current = await database.get_setting('device_verification', 'true')
    new_val = "false" if current.lower() == "true" else "true"
    await database.set_setting('device_verification', new_val)

    await update.message.reply_text(f"✅ **Success:** Unique device guard set to `{new_val}`", parse_mode="Markdown")

from telegram import Update
from telegram.ext import ContextTypes
from database import db
from utils.helpers import escape_html
import config

async def channel_setup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        "📢 <b>CHANNEL SETUP & FORCE JOIN</b>\n\n"
        "To connect a Telegram Channel to auto-post polls or require users to join before voting:\n\n"
        "1. Add @PollBattleBot as <b>Administrator</b> in your Telegram Channel.\n"
        "2. Forward any post from your Channel to this chat, OR send:\n"
        "<code>/addchannel @yourchannelusername</code>\n\n"
        "3. Enable Force-Join requirement with:\n"
        "<code>/forcejoin @yourchannelusername</code>\n\n"
        f"🤖 <b>{escape_html(config.BOT_NAME)}</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML")

async def add_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: <code>/addchannel @channelusername</code>", parse_mode="HTML")
        return

    channel_username = context.args[0].replace("@", "")
    try:
        chat = await context.bot.get_chat(f"@{channel_username}")
        await db.add_channel(
            channel_id=chat.id,
            title=chat.title or channel_username,
            username=channel_username,
            force_join=False
        )
        await update.message.reply_text(
            f"✅ Channel <b>{escape_html(chat.title)}</b> (@{channel_username}) connected successfully!",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to connect channel: {escape_html(str(e))}")

async def force_join_toggle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: <code>/forcejoin @channelusername</code>", parse_mode="HTML")
        return

    channel_username = context.args[0].replace("@", "")
    try:
        chat = await context.bot.get_chat(f"@{channel_username}")
        await db.add_channel(
            channel_id=chat.id,
            title=chat.title or channel_username,
            username=channel_username,
            force_join=True
        )
        await update.message.reply_text(
            f"📢 Force-Join ENABLED for channel: <b>{escape_html(chat.title)}</b> (@{channel_username})!",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to configure channel: {escape_html(str(e))}")

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from services.poll_service import create_poll

TITLE, TYPE, OPTIONS = range(3)

async def start_create_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✏️ **Step 1/3**: Enter the title or question for your Poll Battle:")
    return TITLE

async def handle_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("📊 **Step 2/3**: Select poll type: Send 'public', 'quiz', or 'anonymous':")
    return TYPE

async def handle_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["poll_type"] = update.message.text.lower()
    await update.message.reply_text("📝 **Step 3/3**: Enter poll options separated by commas (e.g., Option A, Option B, Option C):")
    return OPTIONS

async def handle_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text
    options = [o.strip() for o in raw.split(",") if o.strip()]
    if len(options) < 2:
        await update.message.reply_text("⚠️ You must provide at least 2 options! Please try again:")
        return OPTIONS

    user = update.effective_user
    title = context.user_data["title"]
    poll_type = context.user_data.get("poll_type", "public")
    
    poll_id = await create_poll(user.id, user.first_name, title, poll_type, "single", options)
    await update.message.reply_text("🎉 **Poll Battle Created Successfully!**\n\nPoll ID: " + poll_id + "\nUse /poll_" + poll_id + " to view!")
    return ConversationHandler.END

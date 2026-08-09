import uuid
import logging
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)
import database
from utils.keyboards import get_main_menu_keyboard, get_cancel_reply_keyboard, get_voting_inline_keyboard

logger = logging.getLogger("bot.handlers.createpoll")

# States for the conversation wizard
TITLE, DESCRIPTION, OPTIONS, DURATION = range(4)

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the poll creation wizard."""
    user = update.effective_user
    context.user_data.clear()
    
    # Check if user is admin
    db_user = await database.get_user(user.id)
    is_admin = bool(db_user and db_user.get('role') == 'admin')

    if update.message:
        await update.message.reply_text(
            "❌ **Poll Creation Cancelled.**\nReturned to Main Menu.",
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
            parse_mode="Markdown"
        )
    return ConversationHandler.END

async def start_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the poll creation process."""
    user = update.effective_user
    
    # Check if banned
    if await database.is_user_banned(user.id):
        if update.message:
            await update.message.reply_text("❌ You are restricted from creating new content.")
        return ConversationHandler.END

    if update.message:
        await update.message.reply_text(
            "📝 **Poll Creation Wizard**\n\nStep 1: Enter the poll title / question (e.g. _Which framework is best in 2026?_):",
            reply_markup=get_cancel_reply_keyboard(),
            parse_mode="Markdown"
        )
    return TITLE

async def title_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the title and asks for description."""
    if not update.message or not update.message.text:
        return TITLE

    title = update.message.text.strip()
    if not title or len(title) < 5:
        await update.message.reply_text("⚠️ Title must be at least 5 characters long. Please try again:")
        return TITLE
        
    context.user_data['title'] = title
    await update.message.reply_text(
        "📝 **Step 2: Enter Description**\n\nProvide more context or description for this poll (or type `/skip` to bypass):",
        reply_markup=get_cancel_reply_keyboard(),
        parse_mode="Markdown"
    )
    return DESCRIPTION

async def description_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the description and asks for options."""
    if not update.message or not update.message.text:
        return DESCRIPTION

    desc = update.message.text.strip()
    if desc.lower() == "/skip":
        context.user_data['description'] = ""
    else:
        context.user_data['description'] = desc

    await update.message.reply_text(
        "📝 **Step 3: Enter Voting Options**\n\nSubmit options as a **comma-separated list** (minimum 2 options, maximum 10, e.g. _React, Vue, Svelte, Angular_):",
        reply_markup=get_cancel_reply_keyboard(),
        parse_mode="Markdown"
    )
    return OPTIONS

async def options_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves options and asks for duration."""
    if not update.message or not update.message.text:
        return OPTIONS

    raw_text = update.message.text.strip()
    options = [opt.strip() for opt in raw_text.split(",") if opt.strip()]
    
    if len(options) < 2:
        await update.message.reply_text("⚠️ You must provide at least 2 valid options. Please enter again:")
        return OPTIONS
    if len(options) > 10:
        await update.message.reply_text("⚠️ A maximum of 10 options is allowed. Please enter again:")
        return OPTIONS
        
    context.user_data['options'] = options
    await update.message.reply_text(
        "📝 **Step 4: Set Poll Duration**\n\nHow many hours should this poll accept votes? Enter a number between `1` and `168` (e.g. `24` for 1 day):",
        reply_markup=get_cancel_reply_keyboard(),
        parse_mode="Markdown"
    )
    return DURATION

async def duration_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves duration, creates poll in SQLite database, awards XP, and displays preview."""
    if not update.message or not update.message.text:
        return DURATION

    raw_duration = update.message.text.strip()
    if not raw_duration.isdigit():
        await update.message.reply_text("⚠️ Please enter a valid positive integer number of hours:")
        return DURATION
        
    hours = int(raw_duration)
    if hours < 1 or hours > 168:
        await update.message.reply_text("⚠️ Duration must be between 1 and 168 hours (7 days). Try again:")
        return DURATION

    user = update.effective_user
    title = context.user_data['title']
    description = context.user_data['description']
    options = context.user_data['options']
    
    poll_id = str(uuid.uuid4())[:8]
    duration_seconds = hours * 3600
    created_at = datetime.now(timezone.utc)
    expires_at = (created_at + timedelta(seconds=duration_seconds)).isoformat()
    
    # Save to database using helper
    await database.create_poll(
        poll_id=poll_id,
        creator_id=user.id,
        title=title,
        options=options,
        description=description,
        duration_seconds=duration_seconds,
        expires_at=expires_at
    )

    # Award XP & level up user
    new_lvl, new_xp = await database.update_user_xp(user.id, 25)
    db_user = await database.get_user(user.id)
    is_admin = bool(db_user and db_user.get('role') == 'admin')

    footer_text = await database.get_setting('custom_footer', 'Powered by Poll Battle Bot')

    preview_msg = (
        f"📊 **Poll Published Successfully!**\n\n"
        f"📋 **Question:** {title}\n"
        f"📝 **Description:** {description if description else '_No description provided_'}\n"
        f"⏱️ **Duration:** {hours} hour(s)\n"
        f"🔑 **Poll ID:** `{poll_id}`\n\n"
        f"_{footer_text}_"
    )

    await update.message.reply_text(
        text=preview_msg,
        reply_markup=get_main_menu_keyboard(is_admin=is_admin),
        parse_mode="Markdown"
    )
    
    # Fetch poll details with options from db to construct voting keyboard
    poll_obj = await database.get_poll(poll_id)
    poll_options = poll_obj.get("options", []) if poll_obj else []

    await update.message.reply_text(
        text=f"🔥 **VOTE NOW:**\n\n🗳️ *{title}*\n{description}",
        reply_markup=get_voting_inline_keyboard(poll_id, poll_options, is_owner=True),
        parse_mode="Markdown"
    )
    
    context.user_data.clear()
    return ConversationHandler.END

def get_create_poll_handler() -> ConversationHandler:
    """Returns the ConversationHandler containing the setup sequence."""
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^➕ Create Poll$"), start_creation),
            CommandHandler("create_poll", start_creation)
        ],
        states={
            TITLE: [
                MessageHandler(filters.Regex("^❌ Cancel$"), cancel_creation),
                MessageHandler(filters.TEXT & ~filters.COMMAND, title_received)
            ],
            DESCRIPTION: [
                MessageHandler(filters.Regex("^❌ Cancel$"), cancel_creation),
                MessageHandler(filters.TEXT & ~filters.COMMAND, description_received)
            ],
            OPTIONS: [
                MessageHandler(filters.Regex("^❌ Cancel$"), cancel_creation),
                MessageHandler(filters.TEXT & ~filters.COMMAND, options_received)
            ],
            DURATION: [
                MessageHandler(filters.Regex("^❌ Cancel$"), cancel_creation),
                MessageHandler(filters.TEXT & ~filters.COMMAND, duration_received)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_creation),
            MessageHandler(filters.Regex("^❌ Cancel$"), cancel_creation)
        ]
    )

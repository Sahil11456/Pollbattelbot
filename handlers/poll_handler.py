import uuid
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from database import db
from keyboards import get_poll_inline_keyboard
from utils.helpers import format_poll_card, escape_html
import config

# Conversation States
QUESTION, OPTIONS, POLL_TYPE, IS_MULTIPLE, EXPIRY, CHANNEL_SELECT = range(6)

async def start_create_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_poll"] = {
        "options": []
    }
    await update.message.reply_text(
        "📝 <b>Step 1/6: Enter your Poll Question:</b>\n\n(Send /cancel to abort at any time)",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    return QUESTION

async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question_text = update.message.text.strip()
    if len(question_text) < 3:
        await update.message.reply_text("❌ Question is too short. Please enter a valid question:")
        return QUESTION

    context.user_data["new_poll"]["question"] = question_text
    await update.message.reply_text(
        "🔢 <b>Step 2/6: Enter Poll Options:</b>\n\n"
        "Send option texts <b>one by one</b>.\n"
        "When finished, send <code>/done</code> (Minimum 2, Maximum 10 options).",
        parse_mode="HTML"
    )
    return OPTIONS

async def receive_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    opts = context.user_data["new_poll"]["options"]

    if text.lower() == "/done":
        if len(opts) < config.MIN_POLL_OPTIONS:
            await update.message.reply_text(
                f"❌ You must provide at least {config.MIN_POLL_OPTIONS} options before finishing! Current: {len(opts)}"
            )
            return OPTIONS

        # Ask Poll Type
        kb = ReplyKeyboardMarkup([
            ["Public", "Private"],
            ["Anonymous", "Quiz"]
        ], resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            "🌐 <b>Step 3/6: Choose Poll Privacy & Type:</b>\n\n"
            "• <b>Public:</b> Visible in global trending & search.\n"
            "• <b>Private:</b> Accessible only via direct link.\n"
            "• <b>Anonymous:</b> Voter identities hidden.\n"
            "• <b>Quiz:</b> Has correct answer.",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return POLL_TYPE

    if len(opts) >= config.MAX_POLL_OPTIONS:
        await update.message.reply_text(f"⚠️ Maximum limit of {config.MAX_POLL_OPTIONS} options reached! Type /done to proceed.")
        return OPTIONS

    opts.append({"text": text, "is_correct": False})
    await update.message.reply_text(f"✅ Added option {len(opts)}: <b>{escape_html(text)}</b>\nSend next option or /done", parse_mode="HTML")
    return OPTIONS

async def receive_poll_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    p_type = update.message.text.strip().lower()
    if p_type not in ("public", "private", "anonymous", "quiz"):
        await update.message.reply_text("❌ Invalid type! Please select Public, Private, Anonymous, or Quiz.")
        return POLL_TYPE

    context.user_data["new_poll"]["poll_type"] = p_type

    kb = ReplyKeyboardMarkup([["Yes", "No"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "🔀 <b>Step 4/6: Allow Multiple Choice Voting?</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    return IS_MULTIPLE

async def receive_is_multiple(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.message.text.strip().lower()
    context.user_data["new_poll"]["is_multiple"] = (ans == "yes")

    kb = ReplyKeyboardMarkup([
        ["15 Minutes", "1 Hour"],
        ["1 Day", "No Expiry"]
    ], resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        "⏳ <b>Step 5/6: Select Poll Duration / Expiry Time:</b>\n\n"
        "When duration ends, the poll automatically closes and announces the winner!",
        reply_markup=kb,
        parse_mode="HTML"
    )
    return EXPIRY

async def receive_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    now = datetime.utcnow()
    expiry_str = None

    if text == "15 Minutes":
        expiry_str = (now + timedelta(minutes=15)).isoformat()
    elif text == "1 Hour":
        expiry_str = (now + timedelta(hours=1)).isoformat()
    elif text == "1 Day":
        expiry_str = (now + timedelta(days=1)).isoformat()

    context.user_data["new_poll"]["expiry_time"] = expiry_str

    user = update.effective_user
    poll_id = uuid.uuid4().hex[:8]
    p_data = context.user_data["new_poll"]

    # Save to Database
    poll = await db.create_poll(
        poll_id=poll_id,
        creator_id=user.id,
        creator_name=user.first_name,
        question=p_data["question"],
        options=p_data["options"],
        poll_type=p_data["poll_type"],
        is_multiple=p_data["is_multiple"],
        allow_vote_change=True,
        expiry_time=p_data["expiry_time"]
    )

    card_text = format_poll_card(poll, [])
    kb = get_poll_inline_keyboard(poll, [])

    await update.message.reply_text("🎉 <b>Poll Created Successfully!</b>", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await update.message.reply_text(card_text, reply_markup=kb, parse_mode="HTML")

    return ConversationHandler.END

async def cancel_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Poll creation cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

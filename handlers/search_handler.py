from telegram import Update
from telegram.ext import ContextTypes
from database import db
from keyboards import get_poll_inline_keyboard
from utils.helpers import format_poll_card, escape_html
import config

async def trending_polls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    polls = await db.get_trending_polls(limit=5)

    if not polls:
        await update.message.reply_text("🔥 <b>No trending polls found right now. Create one!</b>", parse_mode="HTML")
        return

    await update.message.reply_text("🔥 <b>TOP TRENDING POLLS:</b>", parse_mode="HTML")
    for poll in polls:
        user_votes = await db.get_user_voted_options(poll["poll_id"], user.id)
        text = format_poll_card(poll, user_votes)
        kb = get_poll_inline_keyboard(poll, user_votes)
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def search_polls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 <b>Search Polls:</b>\n\n"
        "Send your search keyword using command:\n"
        "<code>/search <your keyword></code>\n\n"
        "Example: <code>/search sports</code>",
        parse_mode="HTML"
    )

async def search_keyword_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please provide a search term. Usage: <code>/search football</code>", parse_mode="HTML")
        return

    query_str = " ".join(context.args)
    polls = await db.search_polls(query_str)

    if not polls:
        await update.message.reply_text(f"🔍 No polls found matching '<b>{escape_html(query_str)}</b>'.", parse_mode="HTML")
        return

    user = update.effective_user
    await update.message.reply_text(f"🔍 <b>Found {len(polls)} polls matching '{escape_html(query_str)}':</b>", parse_mode="HTML")
    for poll in polls[:3]:
        user_votes = await db.get_user_voted_options(poll["poll_id"], user.id)
        text = format_poll_card(poll, user_votes)
        kb = get_poll_inline_keyboard(poll, user_votes)
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = await db.get_leaderboard(limit=10)
    if not users:
        await update.message.reply_text("🏆 No leaderboard stats available yet.", parse_mode="HTML")
        return

    text = "🏆 <b>POLL BATTLE LEADERBOARD</b> 🏆\n\n"
    for idx, u in enumerate(users, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        name = escape_html(u.get("first_name", "User"))
        votes = u.get("total_votes_cast", 0)
        polls = u.get("total_polls_created", 0)
        text += f"{medal} <b>{name}</b> — 🗳️ {votes} votes | 📝 {polls} polls\n"

    text += f"\n🤖 <b>{escape_html(config.BOT_NAME)}</b>"
    await update.message.reply_text(text, parse_mode="HTML")

async def favorites_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    polls = await db.get_user_favorites(user.id)

    if not polls:
        await update.message.reply_text("❤️ <b>You have no saved favorite polls yet.</b>", parse_mode="HTML")
        return

    await update.message.reply_text("❤️ <b>YOUR FAVORITE POLLS:</b>", parse_mode="HTML")
    for poll in polls[:5]:
        user_votes = await db.get_user_voted_options(poll["poll_id"], user.id)
        text = format_poll_card(poll, user_votes)
        kb = get_poll_inline_keyboard(poll, user_votes)
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

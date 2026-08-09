import logging
from telegram import Update
from telegram.ext import ContextTypes
import database
from utils.keyboards import get_main_menu_keyboard

logger = logging.getLogger("bot.handlers.start")

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command and deep links."""
    user = update.effective_user
    if not user:
        return
        
    username = user.username or "Anonymous"
    full_name = user.full_name or "Anonymous User"
    user_id = user.id
    
    # Get or create user
    user_data = await database.get_or_create_user(user_id, username, full_name)
    
    # Check if banned
    if await database.is_user_banned(user_id):
        if update.message:
            await update.message.reply_text(
                "❌ **Access Denied**\n\nYour account has been restricted by system administrators."
            )
        return
        
    is_admin = bool(user_data and user_data.get("role") == "admin")
    
    # Check for deep-link poll sharing parameter: /start poll_id
    if context.args and len(context.args) > 0:
        poll_id = context.args[0]
        poll_obj = await database.get_poll(poll_id)
        if poll_obj:
            from utils.keyboards import get_voting_inline_keyboard
            await database.increment_poll_views(poll_id)
            title = poll_obj.get("title", "")
            desc = poll_obj.get("description", "")
            options = poll_obj.get("options", [])
            is_closed = poll_obj.get("status") == "closed"
            
            user_vote = await database.get_user_vote(poll_id, user_id)
            voted_opt = user_vote.get("option_index") if user_vote else None
            is_fav = await database.is_favorite(poll_id, user_id)
            is_owner = (poll_obj.get("creator_id") == user_id)

            msg = f"📊 **Poll Question:**\n\n🗳️ *{title}*"
            if desc:
                msg += f"\n_{desc}_"
            if is_closed:
                msg += "\n\n🔒 *This poll is closed.*"

            if update.message:
                await update.message.reply_text(
                    text=msg,
                    reply_markup=get_voting_inline_keyboard(
                        poll_id=poll_id,
                        options=options,
                        user_voted_option=voted_opt,
                        is_closed=is_closed,
                        is_fav=is_fav,
                        is_owner=is_owner
                    ),
                    parse_mode="Markdown"
                )
            return

    welcome_text = (
        f"🚀 **Welcome to Poll Battle Bot, {user.first_name}!** 🎉\n\n"
        f"This is the ultimate, professional **Telegram Polling Engine**.\n\n"
        f"• ➕ Create interactive polls with real-time dynamic voting.\n"
        f"• 🗳️ Cast votes and watch instant live updates.\n"
        f"• 🏆 Earn XP, level up, and conquer the leaderboards!\n"
        f"• 📊 Track detailed views, votes, and analytics.\n\n"
        f"Use the menu buttons below to get started."
    )
    
    if update.message:
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=get_main_menu_keyboard(is_admin=is_admin),
            parse_mode="Markdown"
        )

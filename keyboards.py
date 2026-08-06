from typing import List, Dict, Any
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import config

def get_main_reply_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Main Menu Reply Keyboard with clean grid layout.
    """
    keyboard = [
        ["➕ Create Poll", "🔥 Trending Polls"],
        ["🔍 Search Polls", "🏆 Leaderboard"],
        ["❤️ Favorites", "👤 My Profile"],
        ["📢 Channel Setup", "ℹ️ Help"]
    ]
    if is_admin:
        keyboard.append(["⚡ Admin Panel"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=true, is_persistent=True)

def get_poll_inline_keyboard(poll: Dict[str, Any], user_voted_options: List[int] = None) -> InlineKeyboardMarkup:
    """
    Inline voting buttons + Refresh + Statistics + Share + Favorites.
    """
    if user_voted_options is None:
        user_voted_options = []

    poll_id = poll["poll_id"]
    is_closed = poll.get("is_closed", False)
    options = poll.get("options", [])
    
    keyboard = []

    if not is_closed:
        # Option buttons
        for idx, opt in enumerate(options, 1):
            opt_id = opt["option_id"]
            is_selected = opt_id in user_voted_options
            check_icon = " ✅" if is_selected else ""
            btn_text = f"{idx}. {opt['option_text']}{check_icon}"
            keyboard.append([
                InlineKeyboardButton(btn_text, callback_data=f"vote:{poll_id}:{opt_id}")
            ])

    # Action Row
    action_row = [
        InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh:{poll_id}"),
        InlineKeyboardButton("📊 Stats", callback_data=f"stats:{poll_id}"),
        InlineKeyboardButton("❤️ Favorite", callback_data=f"fav:{poll_id}")
    ]
    keyboard.append(action_row)

    # Share Button (Deep link inline query / forward)
    bot_username = config.BOT_USERNAME
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}?start=poll_{poll_id}&text=Vote%20in%20this%20Poll%20Battle!"
    keyboard.append([
        InlineKeyboardButton("📤 Share Poll", url=share_url)
    ])

    return InlineKeyboardMarkup(keyboard)

def get_force_join_inline_keyboard(channels: List[Dict[str, Any]], poll_id: str = None) -> InlineKeyboardMarkup:
    keyboard = []
    for ch in channels:
        ch_username = ch.get("username")
        url = f"https://t.me/{ch_username}" if ch_username else "https://t.me"
        keyboard.append([
            InlineKeyboardButton(f"📢 Join {ch.get('title', 'Channel')}", url=url)
        ])
    
    callback_data = f"join_check:{poll_id}" if poll_id else "join_check:menu"
    keyboard.append([
        InlineKeyboardButton("✅ I Have Joined", callback_data=callback_data)
    ])
    return InlineKeyboardMarkup(keyboard)

def get_admin_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin:broadcast")],
        [InlineKeyboardButton("🚫 Ban User", callback_data="admin:ban"), InlineKeyboardButton("✅ Unban User", callback_data="admin:unban")],
        [InlineKeyboardButton("🛠️ Maintenance Mode", callback_data="admin:maintenance")],
        [InlineKeyboardButton("📋 System Error Logs", callback_data="admin:logs")]
    ])

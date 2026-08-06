from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("➕ Create Poll"), KeyboardButton("📊 My Polls")],
        [KeyboardButton("🌍 Active Polls"), KeyboardButton("📁 Closed Polls")],
        [KeyboardButton("🔥 Trending Polls"), KeyboardButton("⭐ Favorites")],
        [KeyboardButton("🏆 Leaderboard"), KeyboardButton("🔍 Search Poll")],
        [KeyboardButton("👤 Profile"), KeyboardButton("📈 Statistics")],
        [KeyboardButton("⚙ Settings"), KeyboardButton("📢 Poll Channels")],
        [KeyboardButton("🔐 Force Join"), KeyboardButton("❓ Help")]
    ]
    if is_admin:
        keyboard.insert(0, [KeyboardButton("👨‍💼 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def build_poll_inline_keyboard(poll_id: str, options: list, is_favorite: bool = False) -> InlineKeyboardMarkup:
    buttons = []
    for opt in options:
        pct = f"({opt['pct']}%)" if 'pct' in opt else ""
        btn_text = f"{opt['option_text']} {pct} — {opt['votes']} votes"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"vote:{poll_id}:{opt['option_id']}")])
    
    fav_text = "❤️ Favorited" if is_favorite else "🤍 Favorite"
    control_row = [
        InlineKeyboardButton(fav_text, callback_data=f"fav:{poll_id}"),
        InlineKeyboardButton("🚀 Share", switch_inline_query=f"poll_{poll_id}"),
        InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh:{poll_id}")
    ]
    buttons.append(control_row)
    return InlineKeyboardMarkup(buttons)

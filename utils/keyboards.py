from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        ["🌍 Active Polls", "🔥 Trending Polls"],
        ["➕ Create Poll", "📊 My Polls"],
        ["⭐ Favorites", "🏆 Leaderboard"],
        ["👤 Profile", "📈 Statistics"],
        ["📢 Poll Channels", "❓ Help"]
    ]
    if is_admin:
        keyboard.append(["👨💼 Admin Panel"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict, Any, Optional

def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Returns the main menu reply keyboard layout."""
    keyboard = [
        [KeyboardButton("➕ Create Poll"), KeyboardButton("🌍 Active Polls")],
        [KeyboardButton("🔥 Trending Polls"), KeyboardButton("📊 My Polls")],
        [KeyboardButton("⭐ Favorites"), KeyboardButton("🏆 Leaderboard")],
        [KeyboardButton("🔍 Search Polls"), KeyboardButton("👤 Profile")],
        [KeyboardButton("📈 Statistics"), KeyboardButton("📢 Poll Channels")],
        [KeyboardButton("❓ Help")]
    ]
    if is_admin:
        keyboard.insert(5, [KeyboardButton("👨‍💼 Admin Panel")])
        
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, persistent=True)

def get_cancel_reply_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard containing a Cancel button for wizards."""
    return ReplyKeyboardMarkup([[KeyboardButton("❌ Cancel")]], resize_keyboard=True, one_time_keyboard=True)

def get_voting_inline_keyboard(
    poll_id: str,
    options: List[Dict[str, Any]],
    user_voted_option: Optional[int] = None,
    is_closed: bool = False,
    is_fav: bool = False,
    is_owner: bool = False,
    hide_results: bool = False
) -> InlineKeyboardMarkup:
    """Builds an interactive inline voting keyboard for a poll."""
    buttons = []
    
    # Option buttons
    for opt in options:
        idx = opt.get("option_index", opt.get("index", 0))
        text = opt.get("option_text", opt.get("text", ""))
        votes = opt.get("vote_count", opt.get("votes", 0))
        
        # Display indicator if user voted for this option
        prefix = "✅ " if user_voted_option == idx else "🗳️ "
        label = f"{prefix}{text}"
        
        if not is_closed and not hide_results and votes > 0:
            label += f" ({votes})"
            
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"vote_{poll_id}_{idx}"
        )])

    # Action row 1: Share & Favorite
    fav_label = "⭐ Saved" if is_fav else "☆ Favorite"
    action_row = [
        InlineKeyboardButton("🔗 Share Poll", switch_inline_query=f"share_{poll_id}"),
        InlineKeyboardButton(fav_label, callback_data=f"fav_{poll_id}")
    ]
    buttons.append(action_row)

    # Action row 2: Refresh Results & Close (if owner)
    action_row_2 = [
        InlineKeyboardButton("🔄 Refresh Results", callback_data=f"refresh_{poll_id}")
    ]
    if is_owner and not is_closed:
        action_row_2.append(InlineKeyboardButton("🔒 Close Poll", callback_data=f"close_{poll_id}"))
    buttons.append(action_row_2)

    return InlineKeyboardMarkup(buttons)

def get_poll_type_keyboard() -> InlineKeyboardMarkup:
    """Poll type selection keyboard for poll creation wizard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎯 Single Choice", callback_data="polltype_single"),
            InlineKeyboardButton("☑️ Multiple Choice", callback_data="polltype_multiple")
        ],
        [
            InlineKeyboardButton("🧠 Quiz Mode", callback_data="polltype_quiz")
        ]
    ])

def get_poll_privacy_keyboard() -> InlineKeyboardMarkup:
    """Poll privacy selection keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌍 Public (In Search & Trending)", callback_data="privacy_public"),
            InlineKeyboardButton("🔒 Private (Direct Link Only)", callback_data="privacy_private")
        ]
    ])

def get_poll_duration_keyboard() -> InlineKeyboardMarkup:
    """Poll duration selection keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏱️ 1 Hour", callback_data="duration_3600"),
            InlineKeyboardButton("⏱️ 6 Hours", callback_data="duration_21600")
        ],
        [
            InlineKeyboardButton("⏱️ 24 Hours", callback_data="duration_86400"),
            InlineKeyboardButton("⏱️ 3 Days", callback_data="duration_259200")
        ],
        [
            InlineKeyboardButton("⏱️ 7 Days", callback_data="duration_604800"),
            InlineKeyboardButton("♾️ Unlimited", callback_data="duration_0")
        ]
    ])

def get_trending_options_keyboard() -> InlineKeyboardMarkup:
    """Trending filters options keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗳️ Most Votes", callback_data="trend_votes"),
            InlineKeyboardButton("🔗 Most Shared", callback_data="trend_shares")
        ],
        [
            InlineKeyboardButton("🕒 Newest First", callback_data="trend_newest"),
            InlineKeyboardButton("🔥 High Views", callback_data="trend_views")
        ]
    ])

def get_leaderboard_options_keyboard() -> InlineKeyboardMarkup:
    """Leaderboard criteria inline keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏆 XP Leaders", callback_data="lb_xp"),
            InlineKeyboardButton("📝 Top Creators", callback_data="lb_creators")
        ]
    ])

def get_search_options_keyboard() -> InlineKeyboardMarkup:
    """Criteria selector for searching polls."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("❓ Question Title", callback_data="search_title"),
            InlineKeyboardButton("🔑 Poll ID", callback_data="search_id")
        ]
    ])

def get_admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Interactive admin capabilities menu."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [
            InlineKeyboardButton("👥 User Management", callback_data="admin_users"),
            InlineKeyboardButton("⚙️ System Config", callback_data="admin_config")
        ],
        [
            InlineKeyboardButton("📈 Refresh Stats", callback_data="admin_stats")
        ]
    ])

def get_admin_broadcast_types_keyboard() -> InlineKeyboardMarkup:
    """Selection options for admin announcement broadcast formats."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💬 Text Announcement", callback_data="bc_type_text"),
            InlineKeyboardButton("🖼️ Photo / Media", callback_data="bc_type_media")
        ],
        [
            InlineKeyboardButton("➡️ Forward Message", callback_data="bc_type_forward")
        ]
    ])

def get_confirmation_keyboard(action_code: str) -> InlineKeyboardMarkup:
    """Generic confirmation keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{action_code}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{action_code}")
        ]
    ])

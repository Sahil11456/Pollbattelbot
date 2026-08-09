import re
from datetime import datetime, timezone
from config import XP_LEVEL_UP_BASE

def get_rank_by_level(level: int) -> str:
    """Calculates the user's title rank based on their level."""
    if level >= 15:
        return "🌌 Supreme Overlord of Battles"
    elif level >= 10:
        return "🏆 Grandmaster Battle Creator"
    elif level >= 7:
        return "🎖️ Elite Poll Champion"
    elif level >= 4:
        return "⭐ Expert Poll Curator"
    elif level >= 2:
        return "📝 Rising Contributor"
    return "🌱 Novice Creator"

def calculate_level_and_xp(current_xp: int) -> tuple[int, int, bool]:
    """
    Given total XP, calculates:
    (level, progress_xp_towards_next_level, did_level_up)
    """
    # Level increases by 1 for every XP_LEVEL_UP_BASE XP
    level = (current_xp // XP_LEVEL_UP_BASE) + 1
    progress_xp = current_xp % XP_LEVEL_UP_BASE
    return level, progress_xp

def format_datetime(dt_str: str) -> str:
    """Formats an ISO or SQLite UTC datetime string into user-friendly format."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y at %I:%M %p UTC")
    except ValueError:
        return dt_str

def escape_markdown_v2(text: str) -> str:
    """Escapes special characters for Telegram's MarkdownV2 format."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(r'([' + re.escape(escape_chars) + r'])', r'\\\1', text)

def escape_html(text: str) -> str:
    """Escapes HTML entities safely."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def get_remaining_time_str(expires_at_str: str) -> str:
    """Calculates remaining time till expire string."""
    try:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = expires_at - now
        if diff.total_seconds() <= 0:
            return "Expired"
        
        hours, remainder = divmod(int(diff.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 24:
            days = hours // 24
            remaining_hours = hours % 24
            return f"{days}d {remaining_hours}h remaining"
        elif hours > 0:
            return f"{hours}h {minutes}m remaining"
        else:
            return f"{minutes}m {seconds}s remaining"
    except Exception:
        return "Unknown Time"

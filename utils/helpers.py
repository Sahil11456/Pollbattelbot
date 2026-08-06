import re
from datetime import datetime, timezone
from config import XP_LEVEL_UP_BASE

def get_rank_by_level(level: int) -> str:
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

def calculate_level_and_xp(current_xp: int) -> tuple[int, int]:
    level = (current_xp // XP_LEVEL_UP_BASE) + 1
    progress_xp = current_xp % XP_LEVEL_UP_BASE
    return level, progress_xp

def escape_markdown_v2(text: str) -> str:
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(r'([' + re.escape(escape_chars) + r'])', r'\\\1', text)

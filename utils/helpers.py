import html
import math
from typing import List, Dict, Any

def create_progress_bar(vote_count: int, total_votes: int, length: int = 10) -> str:
    """Generates a visual progress bar e.g. [██████░░░░] 60%"""
    if total_votes == 0:
        percent = 0.0
    else:
        percent = (vote_count / total_votes) * 100

    filled_len = int(round(length * percent / 100))
    bar = "█" * filled_len + "░" * (length - filled_len)
    return f"[{bar}] {percent:.1f}%"

def calculate_percentage(vote_count: int, total_votes: int) -> float:
    if total_votes == 0:
        return 0.0
    return round((vote_count / total_votes) * 100, 1)

def escape_html(text: str) -> str:
    if not text:
        return ""
    return html.escape(str(text))

def format_poll_card(poll: Dict[str, Any], user_voted_options: List[int] = None) -> str:
    """
    Formats a full poll view with Question, Options, Progress Bar, Percentage, Total Votes, Footer Bot Name.
    """
    if user_voted_options is None:
        user_voted_options = []

    poll_id = poll["poll_id"]
    question = escape_html(poll["question"])
    poll_type = poll.get("poll_type", "public").capitalize()
    is_multiple = "Yes" if poll.get("is_multiple") else "No"
    is_closed = poll.get("is_closed", False)
    total_votes = poll.get("total_votes", 0)

    status_icon = "🔴 CLOSED" if is_closed else "🟢 ACTIVE"
    type_badge = f"<b>[{poll_type} Poll]</b>"
    
    text = f"🔥 <b>POLL BATTLE</b> | {status_icon}\n\n"
    text += f"❓ <b>{question}</b>\n\n"
    text += f"⚙️ <i>Type: {poll_type} | Multi-Choice: {is_multiple}</i>\n\n"

    options = poll.get("options", [])
    for idx, opt in enumerate(options, 1):
        opt_id = opt["option_id"]
        opt_text = escape_html(opt["option_text"])
        vote_count = opt.get("vote_count", 0)
        p_bar = create_progress_bar(vote_count, total_votes)
        
        is_user_choice = opt_id in user_voted_options
        check_mark = " ✅ (Your Vote)" if is_user_choice else ""
        
        text += f"{idx}. <b>{opt_text}</b>{check_mark}\n"
        text += f"   {p_bar} ({vote_count} votes)\n\n"

    text += f"📊 <b>Total Votes:</b> {total_votes}\n"
    if poll.get("expiry_time"):
        text += f"⏳ <b>Ends At:</b> <code>{poll['expiry_time']}</code>\n"

    # Strict footer mandate: Footer should show ONLY Bot Name
    text += f"\n🤖 <b>{escape_html(poll.get('bot_name', 'Poll Battle Bot'))}</b>"
    return text

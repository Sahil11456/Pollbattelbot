from typing import Dict, Any, List
from utils.helpers import escape_html, calculate_percentage
import config

def format_winner_announcement(poll: Dict[str, Any]) -> str:
    """
    Formats complete Winner Announcement as required:
    - Question
    - All Options
    - Winner
    - Winner Votes
    - Percentage
    - Total Votes
    - End Time
    - Footer should show only Bot Name
    """
    question = escape_html(poll["question"])
    total_votes = poll.get("total_votes", 0)
    options = poll.get("options", [])
    expiry_time = poll.get("expiry_time", "Ended")

    # Determine Winner
    if options and total_votes > 0:
        winner_opt = max(options, key=lambda x: x["vote_count"])
        winner_text = escape_html(winner_opt["option_text"])
        winner_votes = winner_opt["vote_count"]
        winner_pct = calculate_percentage(winner_votes, total_votes)
    else:
        winner_text = "No votes cast (Tie)"
        winner_votes = 0
        winner_pct = 0.0

    text = "🏆 <b>POLL BATTLE WINNER ANNOUNCEMENT</b> 🏆\n\n"
    text += f"❓ <b>Question:</b> {question}\n\n"
    text += "📊 <b>All Options Results:</b>\n"

    for idx, opt in enumerate(options, 1):
        opt_text = escape_html(opt["option_text"])
        v_count = opt["vote_count"]
        pct = calculate_percentage(v_count, total_votes)
        is_winner = (opt_text == winner_text and v_count > 0)
        trophy = " 🥇" if is_winner else ""
        text += f"{idx}. {opt_text}: {v_count} votes ({pct}%){trophy}\n"

    text += "\n----------------------------------------\n"
    text += f"👑 <b>Winner:</b> {winner_text}\n"
    text += f"🗳️ <b>Winner Votes:</b> {winner_votes}\n"
    text += f"📈 <b>Percentage:</b> {winner_pct}%\n"
    text += f"👥 <b>Total Votes:</b> {total_votes}\n"
    text += f"⏰ <b>End Time:</b> <code>{expiry_time}</code>\n\n"

    # Footer should show ONLY Bot Name
    text += f"🤖 <b>{escape_html(config.BOT_NAME)}</b>"
    return text

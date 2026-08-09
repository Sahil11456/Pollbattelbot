import json
import logging
from datetime import datetime, timezone
from database import get_db_connection

logger = logging.getLogger("bot.services.winner")

class WinnerService:
    @staticmethod
    async def process_expired_polls(bot) -> list[dict]:
        """
        Scans SQLite database for expired active polls, calculates winners,
        commits records to winner_history, and returns winner details list.
        """
        now = datetime.now(timezone.utc).isoformat()
        processed_winners = []
        
        async with await get_db_connection() as conn:
            # Query polls that have expired but are still marked active
            async with conn.execute("""
            SELECT poll_id, title, creator_id, options_json 
            FROM polls 
            WHERE status = 'active' AND expires_at <= ?;
            """, (now,)) as cursor:
                expired_polls = await cursor.fetchall()
                
            for poll_id, title, creator_id, options_json in expired_polls:
                try:
                    # Calculate highest voted option
                    async with conn.execute("""
                    SELECT option_index, COUNT(*) as vote_count 
                    FROM votes 
                    WHERE poll_id = ? 
                    GROUP BY option_index 
                    ORDER BY vote_count DESC 
                    LIMIT 1;
                    """, (poll_id,)) as cursor_vote:
                        winning_row = await cursor_vote.fetchone()
                        
                    options = json.loads(options_json)
                    
                    if winning_row:
                        win_idx, win_votes = winning_row
                        winner_option_text = options[win_idx]
                    else:
                        winner_option_text = "No votes cast"
                        win_votes = 0
                        
                    # Insert record into winner_history
                    await conn.execute("""
                    INSERT INTO winner_history (poll_id, winner_option, total_votes_won)
                    VALUES (?, ?, ?);
                    """, (poll_id, winner_option_text, win_votes))
                    
                    # Update poll status to 'closed'
                    await conn.execute("UPDATE polls SET status = 'closed' WHERE poll_id = ?;", (poll_id,))
                    await conn.commit()
                    
                    processed_winners.append({
                        "poll_id": poll_id,
                        "title": title,
                        "creator_id": creator_id,
                        "winner_option": winner_option_text,
                        "votes": win_votes
                    })
                    
                    # Notify creator
                    try:
                        await bot.send_message(
                            chat_id=creator_id,
                            text=f"🔒 **Poll Arena Concluded!** 🔒\n\n"
                                 f"Your poll *\"{title}\"* has reached its voting duration limits.\n\n"
                                 f"🏆 **Winner Option:** `{winner_option_text}`\n"
                                 f"🗳️ **Votes Captured:** `{win_votes}`\n\n"
                                 f"Detailed analysis is available in My Polls dashboard.",
                            parse_mode="Markdown"
                        )
                    except Exception as err:
                        logger.warning(f"Failed to deliver victory notification to creator {creator_id}: {err}")
                        
                except Exception as ex:
                    logger.error(f"Failed processing winner calculation for poll {poll_id}: {ex}")
                    
        return processed_winners
                          

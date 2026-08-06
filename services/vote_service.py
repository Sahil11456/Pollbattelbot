import logging
from database import get_db
from utils.helpers import generate_short_id

logger = logging.getLogger(__name__)

async def cast_vote(poll_id: str, option_id: str, user_id: int) -> tuple[bool, str]:
    async with await get_db() as db:
        async with db.execute("SELECT is_closed, choice_mode FROM polls WHERE poll_id = ?", (poll_id,)) as cursor:
            poll = await cursor.fetchone()
        if not poll:
            return False, "Poll not found!"
        if poll["is_closed"]:
            return False, "This poll battle has ended!"

        async with db.execute("SELECT vote_id FROM votes WHERE poll_id = ? AND user_id = ?", (poll_id, user_id)) as cursor:
            existing = await cursor.fetchone()
            
        if existing and poll["choice_mode"] == "single":
            return False, "You have already voted in this battle!"

        vote_id = generate_short_id()
        await db.execute(
            "INSERT INTO votes (vote_id, poll_id, option_id, user_id) VALUES (?, ?, ?, ?)",
            (vote_id, poll_id, option_id, user_id)
        )
        await db.execute("UPDATE options SET votes = votes + 1 WHERE option_id = ?", (option_id,))
        await db.execute("UPDATE polls SET hot_score = hot_score + 5 WHERE poll_id = ?", (poll_id,))
        await db.execute("UPDATE users SET votes_cast = votes_cast + 1, points = points + 2 WHERE user_id = ?", (user_id,))
        await db.commit()
        return True, "Your vote has been counted!"

import logging
from database import get_db
from utils.helpers import generate_short_id

logger = logging.getLogger(__name__)

async def create_poll(creator_id: int, creator_name: str, title: str, poll_type: str, choice_mode: str, option_texts: list[str]) -> str:
    poll_id = generate_short_id()
    async with await get_db() as db:
        await db.execute(
            """INSERT INTO polls (poll_id, creator_id, creator_name, title, poll_type, choice_mode)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (poll_id, creator_id, creator_name, title, poll_type, choice_mode)
        )
        for idx, text in enumerate(option_texts):
            option_id = generate_short_id()
            await db.execute(
                """INSERT INTO options (option_id, poll_id, option_text, option_order)
                   VALUES (?, ?, ?, ?)""",
                (option_id, poll_id, text, idx)
            )
        await db.execute(
            "UPDATE users SET polls_created = polls_created + 1, points = points + 10 WHERE user_id = ?",
            (creator_id,)
        )
        await db.commit()
    return poll_id

async def get_poll_details(poll_id: str):
    async with await get_db() as db:
        async with db.execute("SELECT * FROM polls WHERE poll_id = ?", (poll_id,)) as cursor:
            poll = await cursor.fetchone()
        if not poll:
            return None, None
        
        async with db.execute("SELECT * FROM options WHERE poll_id = ? ORDER BY option_order", (poll_id,)) as cursor:
            options = await cursor.fetchall()
            
        return dict(poll), [dict(o) for o in options]

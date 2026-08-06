import aiosqlite
import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
import config

class Database:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path

    async def get_connection(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    async def init_db(self):
        async with await self.get_connection() as conn:
            # Users Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT NOT NULL,
                    last_name TEXT,
                    device_signature TEXT,
                    is_banned INTEGER DEFAULT 0,
                    is_admin INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                );
            """)

            # Polls Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS polls (
                    poll_id TEXT PRIMARY KEY,
                    creator_id INTEGER NOT NULL,
                    creator_name TEXT NOT NULL,
                    question TEXT NOT NULL,
                    poll_type TEXT NOT NULL DEFAULT 'public',
                    is_multiple INTEGER DEFAULT 0,
                    is_closed INTEGER DEFAULT 0,
                    allow_vote_change INTEGER DEFAULT 1,
                    expiry_time TEXT,
                    created_at TEXT NOT NULL,
                    total_votes INTEGER DEFAULT 0,
                    winner_option_id INTEGER,
                    target_channel_id INTEGER,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id)
                );
            """)

            # Poll Options Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS poll_options (
                    option_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    poll_id TEXT NOT NULL,
                    option_text TEXT NOT NULL,
                    vote_count INTEGER DEFAULT 0,
                    is_correct INTEGER DEFAULT 0,
                    FOREIGN KEY (poll_id) REFERENCES polls(poll_id) ON DELETE CASCADE
                );
            """)

            # Votes Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS votes (
                    vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    poll_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    option_id INTEGER NOT NULL,
                    voted_at TEXT NOT NULL,
                    FOREIGN KEY (poll_id) REFERENCES polls(poll_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (option_id) REFERENCES poll_options(option_id) ON DELETE CASCADE,
                    UNIQUE(poll_id, user_id, option_id)
                );
            """)

            # Channels Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    username TEXT,
                    force_join INTEGER DEFAULT 0,
                    added_at TEXT NOT NULL
                );
            """)

            # Favorites Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    user_id INTEGER NOT NULL,
                    poll_id TEXT NOT NULL,
                    added_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, poll_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (poll_id) REFERENCES polls(poll_id) ON DELETE CASCADE
                );
            """)

            # System Settings / Maintenance
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            # Error Logs Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    error_message TEXT NOT NULL,
                    traceback_str TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

            # Create Indexes for maximum performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_polls_creator ON polls(creator_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_polls_closed ON polls(is_closed);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_polls_expiry ON polls(expiry_time);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_options_poll ON poll_options(poll_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_poll_user ON votes(poll_id, user_id);")

            await conn.commit()

    # --- USER METHODS ---
    async def add_or_update_user(self, user_id: int, username: Optional[str], first_name: str, last_name: Optional[str], device_sig: str = "telegram_client") -> Dict[str, Any]:
        async with await self.get_connection() as conn:
            now = datetime.utcnow().isoformat()
            is_admin = 1 if user_id in config.ADMIN_IDS else 0
            await conn.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, device_signature, is_admin, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    device_signature = excluded.device_signature,
                    is_admin = CASE WHEN excluded.is_admin = 1 THEN 1 ELSE is_admin END;
            """, (user_id, username, first_name, last_name, device_sig, is_admin, now))
            await conn.commit()
            return await self.get_user(user_id)

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_user_ids((self)) -> List[int]:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("SELECT user_id FROM users WHERE is_banned = 0;")
            rows = await cursor.fetchall()
            return [row["user_id"] for row in rows]

    async def ban_user(self, user_id: int) -> bool:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?;", (user_id,))
            await conn.commit()
            return cursor.rowcount > 0

    async def unban_user(self, user_id: int) -> bool:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?;", (user_id,))
            await conn.commit()
            return cursor.rowcount > 0

    # --- POLL METHODS ---
    async def create_poll(
        self,
        poll_id: str,
        creator_id: int,
        creator_name: str,
        question: str,
        options: List[Dict[str, Any]], # [{"text": "Option A", "is_correct": False}]
        poll_type: str = "public",
        is_multiple: bool = False,
        allow_vote_change: bool = True,
        expiry_time: Optional[str] = None,
        target_channel_id: Optional[int] = None
    ) -> Dict[str, Any]:
        async with await self.get_connection() as conn:
            now = datetime.utcnow().isoformat()
            await conn.execute("""
                INSERT INTO polls (poll_id, creator_id, creator_name, question, poll_type, is_multiple, is_closed, allow_vote_change, expiry_time, created_at, target_channel_id)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?);
            """, (poll_id, creator_id, creator_name, question, poll_type, 1 if is_multiple else 0, 1 if allow_vote_change else 0, expiry_time, now, target_channel_id))

            for opt in options:
                is_corr = 1 if opt.get("is_correct", False) else 0
                await conn.execute("""
                    INSERT INTO poll_options (poll_id, option_text, vote_count, is_correct)
                    VALUES (?, ?, 0, ?);
                """, (poll_id, opt["text"], is_corr))

            await conn.commit()
            return await self.get_poll(poll_id)

    async def get_poll(self, poll_id: str) -> Optional[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM polls WHERE poll_id = ?;", (poll_id,))
            poll_row = await cursor.fetchone()
            if not poll_row:
                return None
            poll = dict(poll_row)

            opt_cursor = await conn.execute("SELECT * FROM poll_options WHERE poll_id = ? ORDER BY option_id ASC;", (poll_id,))
            opt_rows = await opt_cursor.fetchall()
            poll["options"] = [dict(r) for r in opt_rows]
            return poll

    async def get_user_polls(self, user_id: int) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM polls WHERE creator_id = ? ORDER BY created_at DESC;", (user_id,))
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p = dict(r)
                opt_cursor = await conn.execute("SELECT * FROM poll_options WHERE poll_id = ? ORDER BY option_id ASC;", (p["poll_id"],))
                p["options"] = [dict(opt) for opt in await opt_cursor.fetchall()]
                polls.append(p)
            return polls

    async def search_polls(self, query: str) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            like_query = f"%{query}%"
            cursor = await conn.execute("SELECT * FROM polls WHERE question LIKE ? ORDER BY total_votes DESC LIMIT 20;", (like_query,))
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p = dict(r)
                opt_cursor = await conn.execute("SELECT * FROM poll_options WHERE poll_id = ? ORDER BY option_id ASC;", (p["poll_id"],))
                p["options"] = [dict(opt) for opt in await opt_cursor.fetchall()]
                polls.append(p)
            return polls

    async def get_trending_polls(self, limit: int = 10) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM polls WHERE is_closed = 0 ORDER BY total_votes DESC, created_at DESC LIMIT ?;", (limit,))
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p = dict(r)
                opt_cursor = await conn.execute("SELECT * FROM poll_options WHERE poll_id = ? ORDER BY option_id ASC;", (p["poll_id"],))
                p["options"] = [dict(opt) for opt in await opt_cursor.fetchall()]
                polls.append(p)
            return polls

    # --- VOTING METHODS ---
    async def cast_vote(self, poll_id: str, user_id: int, option_id: int) -> Dict[str, Any]:
        """
        Casts a vote for option_id. Returns status dict.
        Handles single vs multiple choice, vote change, remove vote.
        """
        async with await self.get_connection() as conn:
            poll = await self.get_poll(poll_id)
            if not poll:
                return {"success": False, "message": "Poll not found."}

            if poll["is_closed"]:
                return {"success": False, "message": "This poll is closed."}

            # Check existing votes by user on this poll
            cursor = await conn.execute("SELECT * FROM votes WHERE poll_id = ? AND user_id = ?;", (poll_id, user_id))
            user_votes = [dict(r) for r in await cursor.fetchall()]

            # Has user already voted for this specific option? -> Toggle/Remove vote
            existing_option_vote = next((v for v in user_votes if v["option_id"] == option_id), None)
            if existing_option_vote:
                if not poll["allow_vote_change"]:
                    return {"success": False, "message": "Vote removal or change is not allowed for this poll."}
                # Remove vote for this option
                await conn.execute("DELETE FROM votes WHERE vote_id = ?;", (existing_option_vote["vote_id"],))
                await conn.execute("UPDATE poll_options SET vote_count = MAX(0, vote_count - 1) WHERE option_id = ?;", (option_id,))
                await conn.execute("UPDATE polls SET total_votes = MAX(0, total_votes - 1) WHERE poll_id = ?;", (poll_id,))
                await conn.commit()
                return {"success": True, "action": "removed", "message": "Your vote was removed."}

            # If not multiple choice and user already voted for another option
            if not poll["is_multiple"] and user_votes:
                if not poll["allow_vote_change"]:
                    return {"success": False, "message": "Vote change is not allowed for this poll."}
                # Remove previous vote
                prev_vote = user_votes[0]
                await conn.execute("DELETE FROM votes WHERE vote_id = ?;", (prev_vote["vote_id"],))
                await conn.execute("UPDATE poll_options SET vote_count = MAX(0, vote_count - 1) WHERE option_id = ?;", (prev_vote["option_id"],))
                # Now insert new vote
                now = datetime.utcnow().isoformat()
                await conn.execute("INSERT INTO votes (poll_id, user_id, option_id, voted_at) VALUES (?, ?, ?, ?);", (poll_id, user_id, option_id, now))
                await conn.execute("UPDATE poll_options SET vote_count = vote_count + 1 WHERE option_id = ?;", (option_id,))
                await conn.commit()
                return {"success": True, "action": "changed", "message": "Your vote was changed!"}

            # Standard new vote
            now = datetime.utcnow().isoformat()
            await conn.execute("INSERT INTO votes (poll_id, user_id, option_id, voted_at) VALUES (?, ?, ?, ?);", (poll_id, user_id, option_id, now))
            await conn.execute("UPDATE poll_options SET vote_count = vote_count + 1 WHERE option_id = ?;", (option_id,))
            await conn.execute("UPDATE polls SET total_votes = total_votes + 1 WHERE poll_id = ?;", (poll_id,))
            await conn.commit()
            return {"success": True, "action": "added", "message": "Your vote has been recorded!"}

    async def get_user_voted_options(self, poll_id: str, user_id: int) -> List[int]:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("SELECT option_id FROM votes WHERE poll_id = ? AND user_id = ?;", (poll_id, user_id))
            rows = await cursor.fetchall()
            return [r["option_id"] for r in rows]

    # --- POLL EXPIRY & WINNER ANNOUNCEMENT ---
    async def get_expired_open_polls(self) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            now = datetime.utcnow().isoformat()
            cursor = await conn.execute("""
                SELECT * FROM polls 
                WHERE is_closed = 0 AND expiry_time IS NOT NULL AND expiry_time <= ?;
            """, (now,))
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p = dict(r)
                opt_cursor = await conn.execute("SELECT * FROM poll_options WHERE poll_id = ? ORDER BY option_id ASC;", (p["poll_id"],))
                p["options"] = [dict(opt) for opt in await opt_cursor.fetchall()]
                polls.append(p)
            return polls

    async def close_poll_and_set_winner(self, poll_id: str) -> Dict[str, Any]:
        async with await self.get_connection() as conn:
            poll = await self.get_poll(poll_id)
            if not poll:
                return None

            options = poll["options"]
            winner_opt = max(options, key=lambda x: x["vote_count"]) if options else None
            winner_id = winner_opt["option_id"] if winner_opt else None

            await conn.execute("""
                UPDATE polls SET is_closed = 1, winner_option_id = ? WHERE poll_id = ?;
            """, (winner_id, poll_id))
            await conn.commit()

            poll["is_closed"] = 1
            poll["winner_option_id"] = winner_id
            return poll

    # --- FAVORITES ---
    async def toggle_favorite(self, user_id: int, poll_id: str) -> bool:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM favorites WHERE user_id = ? AND poll_id = ?;", (user_id, poll_id))
            if await cursor.fetchone():
                await conn.execute("DELETE FROM favorites WHERE user_id = ? AND poll_id = ?;", (user_id, poll_id))
                await conn.commit()
                return False  # Removed
            else:
                now = datetime.utcnow().isoformat()
                await conn.execute("INSERT INTO favorites (user_id, poll_id, added_at) VALUES (?, ?, ?);", (user_id, poll_id, now))
                await conn.commit()
                return True  # Added

    async def get_user_favorites(self, user_id: int) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("""
                SELECT p.* FROM polls p 
                JOIN favorites f ON p.poll_id = f.poll_id 
                WHERE f.user_id = ? 
                ORDER BY f.added_at DESC;
            """, (user_id,))
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p = dict(r)
                opt_cursor = await conn.execute("SELECT * FROM poll_options WHERE poll_id = ? ORDER BY option_id ASC;", (p["poll_id"],))
                p["options"] = [dict(opt) for opt in await opt_cursor.fetchall()]
                polls.append(p)
            return polls

    # --- LEADERBOARD & STATS ---
    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("""
                SELECT u.user_id, u.username, u.first_name, 
                       COUNT(DISTINCT v.vote_id) as total_votes_cast,
                       COUNT(DISTINCT p.poll_id) as total_polls_created
                FROM users u
                LEFT JOIN votes v ON u.user_id = v.user_id
                LEFT JOIN polls p ON u.user_id = p.creator_id
                WHERE u.is_banned = 0
                GROUP BY u.user_id
                ORDER BY total_votes_cast DESC, total_polls_created DESC
                LIMIT ?;
            """, (limit,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_system_stats(self) -> Dict[str, Any]:
        async with await self.get_connection() as conn:
            users_c = await conn.execute("SELECT COUNT(*) as cnt FROM users;")
            polls_c = await conn.execute("SELECT COUNT(*) as cnt FROM polls;")
            votes_c = await conn.execute("SELECT COUNT(*) as cnt FROM votes;")
            active_c = await conn.execute("SELECT COUNT(*) as cnt FROM polls WHERE is_closed = 0;")
            
            return {
                "total_users": (await users_c.fetchone())["cnt"],
                "total_polls": (await polls_c.fetchone())["cnt"],
                "total_votes": (await votes_c.fetchone())["cnt"],
                "active_polls": (await active_c.fetchone())["cnt"],
            }

    # --- CHANNELS & FORCE JOIN ---
    async def add_channel(self, channel_id: int, title: str, username: Optional[str], force_join: bool = True):
        async with await self.get_connection() as conn:
            now = datetime.utcnow().isoformat()
            await conn.execute("""
                INSERT INTO channels (channel_id, title, username, force_join, added_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    title = excluded.title,
                    username = excluded.username,
                    force_join = excluded.force_join;
            """, (channel_id, title, username, 1 if force_join else 0, now))
            await conn.commit()

    async def get_force_join_channels(self) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM channels WHERE force_join = 1;")
            return [dict(r) for r in await cursor.fetchall()]

    # --- MAINTENANCE MODE ---
    async def set_maintenance_mode(self, enabled: bool):
        async with await self.get_connection() as conn:
            val = "true" if enabled else "false"
            await conn.execute("INSERT INTO settings (key, value) VALUES ('maintenance', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value;", (val,))
            await conn.commit()

    async def get_maintenance_mode(self) -> bool:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("SELECT value FROM settings WHERE key = 'maintenance';")
            row = await cursor.fetchone()
            if row:
                return row["value"] == "true"
            return config.MAINTENANCE_MODE

    # --- LOGGING ---
    async def log_error(self, user_id: Optional[int], message: str, traceback_str: str):
        async with await self.get_connection() as conn:
            now = datetime.utcnow().isoformat()
            await conn.execute("""
                INSERT INTO error_logs (user_id, error_message, traceback_str, created_at)
                VALUES (?, ?, ?, ?);
            """, (user_id, message, traceback_str, now))
            await conn.commit()

    async def get_recent_error_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        async with await self.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM error_logs ORDER BY id DESC LIMIT ?;", (limit,))
            return [dict(r) for r in await cursor.fetchall()]

db = Database()

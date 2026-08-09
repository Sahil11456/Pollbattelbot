import os
import json
import logging
import aiosqlite
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

from config import DATABASE_PATH

logger = logging.getLogger("bot.database")

@asynccontextmanager
async def get_db_connection():
    """Yields an active aiosqlite connection with foreign keys enabled."""
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        await conn.execute("PRAGMA journal_mode = WAL;")
        await conn.execute("PRAGMA synchronous = NORMAL;")
        yield conn

async def init_db():
    """Initializes the database schema with all required tables, indices, and constraints."""
    async with get_db_connection() as conn:
        # 1. Users Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            role TEXT DEFAULT 'user',
            is_banned INTEGER DEFAULT 0,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Polls Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            poll_id TEXT PRIMARY KEY,
            creator_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            options TEXT NOT NULL, -- JSON String
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_closed INTEGER DEFAULT 0,
            channel_id INTEGER,
            is_anonymous INTEGER DEFAULT 0,
            FOREIGN KEY (creator_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """)

        # 3. Votes Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            option_index INTEGER NOT NULL,
            voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(poll_id, user_id),
            FOREIGN KEY (poll_id) REFERENCES polls(poll_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """)

        # 4. Favorites Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER NOT NULL,
            poll_id TEXT NOT NULL,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, poll_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (poll_id) REFERENCES polls(poll_id) ON DELETE CASCADE
        );
        """)

        # 5. Required Channels Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS required_channels (
            channel_id INTEGER PRIMARY KEY,
            title TEXT,
            invite_link TEXT NOT NULL
        );
        """)

        # 6. Banned Users Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY,
            reason TEXT,
            banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 7. System Settings Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """)

        # Default maintenance mode setting
        await conn.execute("""
        INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance_mode', 'off');
        """)

        # Speed Optimization Indices
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_poll ON votes(poll_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_user ON votes(user_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_polls_creator ON polls(creator_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_polls_expires ON polls(expires_at);")

        await conn.commit()
        logger.info("SQLite Database initialized successfully with indices and foreign keys!")

async def register_user(user_id: INTEGER, username: Optional[str], first_name: Optional[str]) -> bool:
    """Registers user if not existing, or updates existing metadata."""
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = await cursor.fetchone()
        if not exists:
            await conn.execute(
                "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name)
            )
            await conn.commit()
            return True
        else:
            await conn.execute(
                "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                (username, first_name, user_id)
            )
            await conn.commit()
            return False

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves user profile row."""
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_xp(user_id: int, xp_amount: int) -> Tuple[int, int, bool]:
    """
    Adds XP to user and calculates level up.
    Returns: (new_xp, new_level, leveled_up)
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if not row:
            return 0, 1, False

        curr_xp = row["xp"] + xp_amount
        curr_lvl = row["level"]

        # Level formula: Every 100 XP grants 1 Level
        new_lvl = (curr_xp // 100) + 1
        leveled_up = new_lvl > curr_lvl

        await conn.execute(
            "UPDATE users SET xp = ?, level = ? WHERE user_id = ?",
            (curr_xp, new_lvl, user_id)
        )
        await conn.commit()
        return curr_xp, new_lvl, leveled_up

async def create_poll(
    poll_id: str,
    creator_id: int,
    title: str,
    description: str,
    options: List[str],
    expires_at: Optional[datetime] = None,
    channel_id: Optional[int] = None,
    is_anonymous: bool = False
) -> bool:
    """Inserts a new poll record into SQLite database."""
    options_json = json.dumps(options)
    async with get_db_connection() as conn:
        await conn.execute(
            """
            INSERT INTO polls (poll_id, creator_id, title, description, options, expires_at, channel_id, is_anonymous)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                poll_id,
                creator_id,
                title,
                description,
                options_json,
                expires_at.strftime("%Y-%m-%d %H:%M:%S") if expires_at else None,
                channel_id,
                1 if is_anonymous else 0
            )
        )
        await conn.commit()
        return True

async def get_poll(poll_id: str) -> Optional[Dict[str, Any]]:
    """Fetches single poll details by ID."""
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM polls WHERE poll_id = ?", (poll_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        poll = dict(row)
        poll["options"] = json.loads(poll["options"])
        return poll

async def cast_vote(poll_id: str, user_id: int, option_index: int) -> Tuple[bool, str]:
    """
    Casts or updates vote for user in poll.
    Enforces expiration, closed state, and UNIQUE constraints.
    """
    async with get_db_connection() as conn:
        # Verify Poll status
        cursor = await conn.execute("SELECT is_closed, expires_at FROM polls WHERE poll_id = ?", (poll_id,))
        poll = await cursor.fetchone()
        if not poll:
            return False, "Poll not found!"
        if poll["is_closed"] == 1:
            return False, "This poll is closed!"
        if poll["expires_at"]:
            exp_time = datetime.strptime(poll["expires_at"], "%Y-%m-%d %H:%M:%S")
            if datetime.now() > exp_time:
                await conn.execute("UPDATE polls SET is_closed = 1 WHERE poll_id = ?", (poll_id,))
                await conn.commit()
                return False, "This poll has expired!"

        # Check existing vote
        cursor = await conn.execute("SELECT option_index FROM votes WHERE poll_id = ? AND user_id = ?", (poll_id, user_id))
        existing_vote = await cursor.fetchone()

        if existing_vote:
            if existing_vote["option_index"] == option_index:
                return False, "You have already voted for this option!"
            # Update vote
            await conn.execute(
                "UPDATE votes SET option_index = ?, voted_at = CURRENT_TIMESTAMP WHERE poll_id = ? AND user_id = ?",
                (option_index, poll_id, user_id)
            )
            await conn.commit()
            return True, "Your vote has been updated!"
        else:
            # Insert new vote
            await conn.execute(
                "INSERT INTO votes (poll_id, user_id, option_index) VALUES (?, ?, ?)",
                (poll_id, user_id, option_index)
            )
            await conn.commit()
            return True, "Vote recorded successfully!"

async def get_poll_results(poll_id: str) -> Dict[str, Any]:
    """
    Calculates total votes and option-wise distribution breakdown.
    """
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT options FROM polls WHERE poll_id = ?", (poll_id,))
        row = await cursor.fetchone()
        if not row:
            return {"total_votes": 0, "breakdown": {}}

        options = json.loads(row["options"])
        cursor = await conn.execute(
            "SELECT option_index, COUNT(*) as count FROM votes WHERE poll_id = ? GROUP BY option_index",
            (poll_id,)
        )
        votes_data = await cursor.fetchall()

        counts = {i: 0 for i in range(len(options))}
        total_votes = 0
        for v in votes_data:
            idx = v["option_index"]
            cnt = v["count"]
            counts[idx] = cnt
            total_votes += cnt

        breakdown = []
        for idx, opt in enumerate(options):
            cnt = counts.get(idx, 0)
            percentage = (cnt / total_votes * 100) if total_votes > 0 else 0.0
            breakdown.append({
                "index": idx,
                "option": opt,
                "votes": cnt,
                "percentage": percentage
            })

        return {
            "total_votes": total_votes,
            "breakdown": breakdown
        }

async def get_user_voted_option(poll_id: str, user_id: int) -> Optional[int]:
    """Returns option index user voted for, or None."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT option_index FROM votes WHERE poll_id = ? AND user_id = ?",
            (poll_id, user_id)
        )
        row = await cursor.fetchone()
        return row["option_index"] if row else None

async def toggle_favorite(user_id: int, poll_id: str) -> bool:
    """Toggles favorite status for user poll. Returns True if saved, False if removed."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND poll_id = ?",
            (user_id, poll_id)
        )
        exists = await cursor.fetchone()
        if exists:
            await conn.execute("DELETE FROM favorites WHERE user_id = ? AND poll_id = ?", (user_id, poll_id))
            await conn.commit()
            return False
        else:
            await conn.execute("INSERT INTO favorites (user_id, poll_id) VALUES (?, ?)", (user_id, poll_id))
            await conn.commit()
            return True

async def is_favorite(user_id: int, poll_id: str) -> bool:
    """Checks if poll is favorited by user."""
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT 1 FROM favorites WHERE user_id = ? AND poll_id = ?", (user_id, poll_id))
        row = await cursor.fetchone()
        return True if row else False

async def get_user_polls(creator_id: int, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    """Retrieves polls created by specific user."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT * FROM polls WHERE creator_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (creator_id, limit, offset)
        )
        rows = await cursor.fetchall()
        polls = []
        for r in rows:
            p = dict(r)
            p["options"] = json.loads(p["options"])
            polls.append(p)
        return polls

async def get_favorite_polls(user_id: int, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    """Retrieves saved favorite polls of user."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT p.* FROM polls p
            JOIN favorites f ON p.poll_id = f.poll_id
            WHERE f.user_id = ?
            ORDER BY f.saved_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset)
        )
        rows = await cursor.fetchall()
        polls = []
        for r in rows:
            p = dict(r)
            p["options"] = json.loads(p["options"])
            polls.append(p)
        return polls

async def get_trending_polls(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves top active polls sorted by vote counts."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            """
            SELECT p.*, COUNT(v.id) as vote_count
            FROM polls p
            LEFT JOIN votes v ON p.poll_id = v.poll_id
            WHERE p.is_closed = 0
            GROUP BY p.poll_id
            ORDER BY vote_count DESC, p.created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = await cursor.fetchall()
        polls = []
        for r in rows:
            p = dict(r)
            p["options"] = json.loads(p["options"])
            polls.append(p)
        return polls

async def search_polls(query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Searches polls matching title or description query."""
    async with get_db_connection() as conn:
        pattern = f"%{query_text}%"
        cursor = await conn.execute(
            """
            SELECT * FROM polls
            WHERE (title LIKE ? OR description LIKE ?) AND is_closed = 0
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (pattern, pattern, limit)
        )
        rows = await cursor.fetchall()
        polls = []
        for r in rows:
            p = dict(r)
            p["options"] = json.loads(p["options"])
            polls.append(p)
        return polls

async def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches top XP users for leaderboard."""
    async with get_db_connection() as conn:
        cursor = await conn.execute(
            "SELECT user_id, username, first_name, xp, level FROM users ORDER BY xp DESC LIMIT ?",
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def close_poll(poll_id: str) -> bool:
    """Closes voting on specified poll."""
    async with get_db_connection() as conn:
        await conn.execute("UPDATE polls SET is_closed = 1 WHERE poll_id = ?", (poll_id,))
        await conn.commit()
        return True

async def delete_poll(poll_id: str) -> bool:
    """Deletes poll and associated votes/favorites."""
    async with get_db_connection() as conn:
        await conn.execute("DELETE FROM polls WHERE poll_id = ?", (poll_id,))
        await conn.commit()
        return True

async def add_required_channel(channel_id: int, title: str, invite_link: str) -> bool:
    """Adds force-join requirement channel."""
    async with get_db_connection() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO required_channels (channel_id, title, invite_link) VALUES (?, ?, ?)",
            (channel_id, title, invite_link)
        )
        await conn.commit()
        return True

async def remove_required_channel(channel_id: int) -> bool:
    """Removes force-join channel constraint."""
    async with get_db_connection() as conn:
        await conn.execute("DELETE FROM required_channels WHERE channel_id = ?", (channel_id,))
        await conn.commit()
        return True

async def get_required_channels() -> List[Dict[str, Any]]:
    """Gets list of all force-join channels."""
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT * FROM required_channels")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def ban_user(user_id: int, reason: str = "Violation of terms") -> bool:
    """Bans user from bot interaction."""
    async with get_db_connection() as conn:
        await conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        await conn.execute(
            "INSERT OR REPLACE INTO banned_users (user_id, reason) VALUES (?, ?)",
            (user_id, reason)
        )
        await conn.commit()
        return True

async def unban_user(user_id: int) -> bool:
    """Unbans user from bot."""
    async with get_db_connection() as conn:
        await conn.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        await conn.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
        await conn.commit()
        return True

async def is_user_banned(user_id: int) -> bool:
    """Checks if user is banned."""
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return bool(row["is_banned"]) if row else False

async def get_system_stats() -> Dict[str, Any]:
    """Compiles dashboard telemetry metrics."""
    async with get_db_connection() as conn:
        u_cur = await conn.execute("SELECT COUNT(*) as count FROM users")
        total_users = (await u_cur.fetchone())["count"]

        p_cur = await conn.execute("SELECT COUNT(*) as count FROM polls")
        total_polls = (await p_cur.fetchone())["count"]

        v_cur = await conn.execute("SELECT COUNT(*) as count FROM votes")
        total_votes = (await v_cur.fetchone())["count"]

        act_cur = await conn.execute("SELECT COUNT(*) as count FROM polls WHERE is_closed = 0")
        active_polls = (await act_cur.fetchone())["count"]

        return {
            "total_users": total_users,
            "total_polls": total_polls,
            "total_votes": total_votes,
            "active_polls": active_polls
        }

async def set_setting(key: str, value: str):
    """Sets system configuration key/value."""
    async with get_db_connection() as conn:
        await conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await conn.commit()

async def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Gets system setting by key."""
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else default

async def get_all_users() -> List[int]:
    """Retrieves user IDs list for broadcasts."""
    async with get_db_connection() as conn:
        cursor = await conn.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [r["user_id"] for r in rows]

async def check_and_close_expired_polls() -> List[Dict[str, Any]]:
    """Checks and closes all expired polls, returning list of newly closed polls."""
    async with get_db_connection() as conn:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = await conn.execute(
            "SELECT * FROM polls WHERE is_closed = 0 AND expires_at IS NOT NULL AND expires_at <= ?",
            (now_str,)
        )
        expired_rows = await cursor.fetchall()
        expired_polls = []
        for r in expired_rows:
            p = dict(r)
            p["options"] = json.loads(p["options"])
            expired_polls.append(p)

        if expired_polls:
            await conn.execute(
                "UPDATE polls SET is_closed = 1 WHERE is_closed = 0 AND expires_at IS NOT NULL AND expires_at <= ?",
                (now_str,)
            )
            await conn.commit()

        return expired_polls

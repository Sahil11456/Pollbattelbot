import os
import json
import logging
import aiosqlite
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

from config import DATABASE_PATH, ADMIN_IDS

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
            username TEXT DEFAULT 'Anonymous',
            full_name TEXT DEFAULT 'Anonymous User',
            role TEXT DEFAULT 'user',
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            rank TEXT DEFAULT '🌱 Novice',
            is_banned INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Polls Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            poll_id TEXT PRIMARY KEY,
            creator_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            is_multiple INTEGER DEFAULT 0,
            is_anonymous INTEGER DEFAULT 0,
            is_public INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            views INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            FOREIGN KEY(creator_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """)

        # 3. Poll Options Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS poll_options (
            option_id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id TEXT NOT NULL,
            option_index INTEGER NOT NULL,
            option_text TEXT NOT NULL,
            vote_count INTEGER DEFAULT 0,
            FOREIGN KEY(poll_id) REFERENCES polls(poll_id) ON DELETE CASCADE
        );
        """)

        # 4. Votes Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            option_index INTEGER NOT NULL,
            voted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(poll_id) REFERENCES polls(poll_id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            UNIQUE(poll_id, user_id, option_index)
        );
        """)

        # 5. Favorites Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            favorite_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            poll_id TEXT NOT NULL,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY(poll_id) REFERENCES polls(poll_id) ON DELETE CASCADE,
            UNIQUE(user_id, poll_id)
        );
        """)

        # 6. Force Join Channels Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS force_join_channels (
            channel_id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_username TEXT NOT NULL UNIQUE,
            channel_title TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 7. System Settings Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 8. Rate Limit Tracking Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            last_action_timestamp REAL NOT NULL,
            PRIMARY KEY(user_id, action_type)
        );
        """)

        # 9. Device Verification Logs Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS device_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ip_address TEXT DEFAULT '',
            user_agent TEXT DEFAULT '',
            verified_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 10. System Audit Logs Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT DEFAULT 'INFO',
            module TEXT DEFAULT '',
            message TEXT NOT NULL,
            user_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_polls_creator ON polls(creator_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_polls_status ON polls(status);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_poll ON votes(poll_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_user ON votes(user_id);")

        await conn.commit()
        logger.info("Database initialized successfully!")

# ================= USER OPERATIONS =================

async def register_user(user_id: int, username: str = "Anonymous", full_name: str = "Anonymous User", role: str = "user") -> Dict[str, Any]:
    """Registers or updates a user in the database."""
    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, username, full_name, role)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name;
        """, (user_id, username or "Anonymous", full_name or "Anonymous User", role))
        await conn.commit()
    return await get_user(user_id)

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves user profile data by user_id."""
    async with get_db_connection() as conn:
        async with conn.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_or_create_user(user_id: int, username: str = "Anonymous", full_name: str = "Anonymous User") -> Dict[str, Any]:
    """Retrieves an existing user or creates a new user record with appropriate admin role."""
    user = await get_user(user_id)
    if user:
        if (user.get("username") != username or user.get("full_name") != full_name) and username and full_name:
            async with get_db_connection() as conn:
                await conn.execute(
                    "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?;",
                    (username, full_name, user_id)
                )
                await conn.commit()
                user["username"] = username
                user["full_name"] = full_name
        return user

    role = "user"
    if user_id in ADMIN_IDS:
        role = "admin"
    else:
        all_users = await get_all_users()
        if not all_users:
            role = "admin"

    return await register_user(user_id, username or "Anonymous", full_name or "Anonymous User", role)

async def get_user_polls_count(user_id: int) -> int:
    """Returns count of polls created by user."""
    async with get_db_connection() as conn:
        async with conn.execute("SELECT COUNT(*) as cnt FROM polls WHERE creator_id = ?;", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

async def get_user_votes_count(user_id: int) -> int:
    """Returns count of votes cast by user."""
    async with get_db_connection() as conn:
        async with conn.execute("SELECT COUNT(*) as cnt FROM votes WHERE user_id = ?;", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

async def get_user_achievements(user_id: int) -> List[Dict[str, Any]]:
    """Returns unlocked achievement milestones for a user."""
    polls_cnt = await get_user_polls_count(user_id)
    votes_cnt = await get_user_votes_count(user_id)
    achievements = []

    if votes_cnt >= 1:
        achievements.append({"achievement_name": "🌱 First Vote Cast"})
    if votes_cnt >= 10:
        achievements.append({"achievement_name": "🗳️ Voting Centurion (10+ Votes)"})
    if votes_cnt >= 50:
        achievements.append({"achievement_name": "⚡ Democracy Master (50+ Votes)"})

    if polls_cnt >= 1:
        achievements.append({"achievement_name": "📝 Poll Creator Pioneer"})
    if polls_cnt >= 5:
        achievements.append({"achievement_name": "🔥 Poll Mastermind (5+ Polls)"})
    if polls_cnt >= 20:
        achievements.append({"achievement_name": "🌌 Battle Overlord (20+ Polls)"})

    return achievements

async def get_all_users() -> List[Dict[str, Any]]:
    """Retrieves all registered users."""
    async with get_db_connection() as conn:
        async with conn.execute("SELECT * FROM users ORDER BY created_at DESC;") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def update_user_xp(user_id: int, xp_gained: int) -> Tuple[int, int]:
    """Increments user XP, updates level/rank if milestone crossed. Returns (new_level, new_xp)."""
    user = await get_user(user_id)
    if not user:
        return 1, 0

    current_xp = user.get("xp", 0) + xp_gained
    new_level = max(1, (current_xp // 100) + 1)
    
    ranks = ["🌱 Novice", "🥉 Bronze Voter", "🥈 Silver Strategist", "🥇 Gold Commander", "💎 Diamond Overlord", "👑 Voting Legend"]
    rank_idx = min(len(ranks) - 1, (new_level - 1) // 2)
    new_rank = ranks[rank_idx]

    async with get_db_connection() as conn:
        await conn.execute("""
            UPDATE users SET xp = ?, level = ?, rank = ? WHERE user_id = ?;
        """, (current_xp, new_level, new_rank, user_id))
        await conn.commit()

    return new_level, current_xp

async def ban_user(user_id: int) -> bool:
    """Sets user is_banned flag to 1."""
    async with get_db_connection() as conn:
        await conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?;", (user_id,))
        await conn.commit()
        return True

async def unban_user(user_id: int) -> bool:
    """Sets user is_banned flag to 0."""
    async with get_db_connection() as conn:
        await conn.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?;", (user_id,))
        await conn.commit()
        return True

async def is_user_banned(user_id: int) -> bool:
    """Checks if a user is currently banned."""
    user = await get_user(user_id)
    return bool(user and user.get("is_banned") == 1)

# ================= POLL OPERATIONS =================

async def _attach_poll_details(conn: aiosqlite.Connection, poll: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to attach options array and total votes to poll dict."""
    p_id = poll["poll_id"]
    async with conn.execute(
        "SELECT * FROM poll_options WHERE poll_id = ? ORDER BY option_index ASC;",
        (p_id,)
    ) as opt_cursor:
        opt_rows = await opt_cursor.fetchall()
        poll["options"] = [dict(o) for o in opt_rows]

    async with conn.execute(
        "SELECT COUNT(*) as total FROM votes WHERE poll_id = ?;",
        (p_id,)
    ) as count_cursor:
        cnt_row = await count_cursor.fetchone()
        tot = cnt_row["total"] if cnt_row else 0
        poll["total_votes"] = tot
        poll["vote_count"] = tot

    return poll

async def create_poll(
    poll_id: str,
    creator_id: int,
    title: str,
    options: List[str],
    description: str = "",
    is_multiple: bool = False,
    is_anonymous: bool = False,
    is_public: bool = True,
    expires_at: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Saves a new poll structure into the database."""
    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO polls (poll_id, creator_id, title, description, is_multiple, is_anonymous, is_public, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (poll_id, creator_id, title, description, int(is_multiple), int(is_anonymous), int(is_public), expires_at))

        for idx, opt in enumerate(options):
            await conn.execute("""
                INSERT INTO poll_options (poll_id, option_index, option_text, vote_count)
                VALUES (?, ?, ?, 0);
            """, (poll_id, idx, opt))

        await conn.commit()

    await update_user_xp(creator_id, 25) # Award creator 25 XP
    return await get_poll(poll_id)

async def get_poll(poll_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves poll, options, and calculated total votes."""
    async with get_db_connection() as conn:
        async with conn.execute("SELECT * FROM polls WHERE poll_id = ?;", (poll_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            poll = dict(row)
            return await _attach_poll_details(conn, poll)

async def get_user_polls(user_id: int) -> List[Dict[str, Any]]:
    """Retrieves all polls created by a user."""
    async with get_db_connection() as conn:
        async with conn.execute(
            "SELECT * FROM polls WHERE creator_id = ? ORDER BY created_at DESC;",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p_dict = dict(r)
                p_dict = await _attach_poll_details(conn, p_dict)
                polls.append(p_dict)
            return polls

async def get_active_polls() -> List[Dict[str, Any]]:
    """Retrieves all active public polls."""
    async with get_db_connection() as conn:
        async with conn.execute(
            "SELECT * FROM polls WHERE status = 'active' AND is_public = 1 ORDER BY created_at DESC;"
        ) as cursor:
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p_dict = dict(r)
                p_dict = await _attach_poll_details(conn, p_dict)
                polls.append(p_dict)
            return polls

async def get_trending_polls(limit: int = 5, order_by: str = "votes") -> List[Dict[str, Any]]:
    """Retrieves top public active polls ordered by votes, views, or date."""
    async with get_db_connection() as conn:
        order_clause = "ORDER BY (SELECT COUNT(*) FROM votes WHERE poll_id = polls.poll_id) DESC"
        if order_by == "views":
            order_clause = "ORDER BY views DESC"
        elif order_by in ("recent", "date", "newest"):
            order_clause = "ORDER BY created_at DESC"

        async with conn.execute(f"SELECT * FROM polls WHERE is_public = 1 AND status = 'active' {order_clause} LIMIT ?;", (limit,)) as cursor:
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p_dict = dict(r)
                p_dict = await _attach_poll_details(conn, p_dict)
                polls.append(p_dict)
            return polls

async def get_expired_active_polls() -> List[Dict[str, Any]]:
    """Retrieves active polls that have passed their expiration timestamp."""
    async with get_db_connection() as conn:
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        async with conn.execute("""
            SELECT * FROM polls 
            WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at <= ?;
        """, (now_str,)) as cursor:
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p_dict = dict(r)
                p_dict = await _attach_poll_details(conn, p_dict)
                polls.append(p_dict)
            return polls

async def close_poll(poll_id: str) -> bool:
    """Sets poll status to closed."""
    async with get_db_connection() as conn:
        await conn.execute("UPDATE polls SET status = 'closed' WHERE poll_id = ?;", (poll_id,))
        await conn.commit()
        return True

async def delete_poll(poll_id: str) -> bool:
    """Deletes poll and cascades to options/votes."""
    async with get_db_connection() as conn:
        await conn.execute("DELETE FROM polls WHERE poll_id = ?;", (poll_id,))
        await conn.commit()
        return True

async def increment_poll_views(poll_id: str):
    """Increments the view count of a poll."""
    async with get_db_connection() as conn:
        await conn.execute("UPDATE polls SET views = views + 1 WHERE poll_id = ?;", (poll_id,))
        await conn.commit()

async def increment_poll_shares(poll_id: str):
    """Increments the share count of a poll."""
    async with get_db_connection() as conn:
        await conn.execute("UPDATE polls SET shares = shares + 1 WHERE poll_id = ?;", (poll_id,))
        await conn.commit()

async def search_polls(query: str, field: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
    """Searches public polls by title or description."""
    async with get_db_connection() as conn:
        pattern = f"%{query}%"
        async with conn.execute("""
            SELECT * FROM polls
            WHERE is_public = 1 AND (title LIKE ? OR description LIKE ?)
            ORDER BY created_at DESC LIMIT ?;
        """, (pattern, pattern, limit)) as cursor:
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p_dict = dict(r)
                p_dict = await _attach_poll_details(conn, p_dict)
                polls.append(p_dict)
            return polls

# ================= VOTE OPERATIONS =================

async def cast_vote(poll_id: str, user_id: int, option_index: int) -> Tuple[bool, str]:
    """Safely saves a user's vote into the SQLite database."""
    poll = await get_poll(poll_id)
    if not poll:
        return False, "Poll not found."

    if poll.get("status") == "closed":
        return False, "This poll is closed."

    async with get_db_connection() as conn:
        is_multiple = bool(poll.get("is_multiple", 0))

        if not is_multiple:
            async with conn.execute(
                "SELECT option_index FROM votes WHERE poll_id = ? AND user_id = ?;",
                (poll_id, user_id)
            ) as v_cursor:
                existing_vote = await v_cursor.fetchone()
                if existing_vote:
                    prev_idx = existing_vote["option_index"]
                    if prev_idx == option_index:
                        return False, "You already voted for this option!"
                    
                    # Switch vote: Remove previous vote, decrement option count
                    await conn.execute(
                        "DELETE FROM votes WHERE poll_id = ? AND user_id = ?;",
                        (poll_id, user_id)
                    )
                    await conn.execute(
                        "UPDATE poll_options SET vote_count = MAX(0, vote_count - 1) WHERE poll_id = ? AND option_index = ?;",
                        (poll_id, prev_idx)
                    )

        # Record new vote
        try:
            await conn.execute("""
                INSERT INTO votes (poll_id, user_id, option_index)
                VALUES (?, ?, ?);
            """, (poll_id, user_id, option_index))

            await conn.execute("""
                UPDATE poll_options SET vote_count = vote_count + 1
                WHERE poll_id = ? AND option_index = ?;
            """, (poll_id, option_index))

            await conn.commit()
        except aiosqlite.IntegrityError:
            return False, "You have already voted on this option."

        await update_user_xp(user_id, 10)
        return True, "Vote recorded successfully!"

async def get_user_vote(arg1: Any, arg2: Any) -> Optional[Dict[str, int]]:
    """Returns dict {'option_index': idx} if user voted on poll, or None. Handles flexible parameter order."""
    if isinstance(arg1, str):
        poll_id, user_id = arg1, int(arg2)
    else:
        user_id, poll_id = int(arg1), str(arg2)

    async with get_db_connection() as conn:
        async with conn.execute(
            "SELECT option_index FROM votes WHERE poll_id = ? AND user_id = ?;",
            (poll_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return {"option_index": row["option_index"]} if row else None

# ================= FAVORITES OPERATIONS =================

async def add_favorite(user_id: int, poll_id: str) -> bool:
    """Adds poll to user favorites."""
    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT OR IGNORE INTO favorites (user_id, poll_id)
            VALUES (?, ?);
        """, (user_id, poll_id))
        await conn.commit()
        return True

async def remove_favorite(user_id: int, poll_id: str) -> bool:
    """Removes poll from user favorites."""
    async with get_db_connection() as conn:
        await conn.execute("DELETE FROM favorites WHERE user_id = ? AND poll_id = ?;", (user_id, poll_id))
        await conn.commit()
        return True

async def is_favorite(arg1: Any, arg2: Any) -> bool:
    """Checks if a poll is in user's favorites, supporting both (user_id, poll_id) and (poll_id, user_id)."""
    if isinstance(arg1, str):
        poll_id, user_id = arg1, int(arg2)
    else:
        user_id, poll_id = int(arg1), str(arg2)

    async with get_db_connection() as conn:
        async with conn.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND poll_id = ?;",
            (user_id, poll_id)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row)

async def toggle_favorite(user_id: int, poll_id: str) -> bool:
    """Toggles favorite state for user on a poll. Returns True if now favorited, False if removed."""
    if await is_favorite(user_id, poll_id):
        await remove_favorite(user_id, poll_id)
        return False
    else:
        await add_favorite(user_id, poll_id)
        return True

async def get_user_favorites(user_id: int) -> List[Dict[str, Any]]:
    """Gets all favorite polls for a user."""
    async with get_db_connection() as conn:
        async with conn.execute("""
            SELECT p.* FROM polls p
            JOIN favorites f ON p.poll_id = f.poll_id
            WHERE f.user_id = ?
            ORDER BY f.added_at DESC;
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p_dict = dict(r)
                p_dict = await _attach_poll_details(conn, p_dict)
                polls.append(p_dict)
            return polls

# ================= FORCE JOIN & CHANNEL OPERATIONS =================

async def add_force_join_channel(channel_username: str, channel_title: str = "") -> bool:
    """Adds or updates a required force join channel by username."""
    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO force_join_channels (channel_username, channel_title, is_active)
            VALUES (?, ?, 1)
            ON CONFLICT(channel_username) DO UPDATE SET
                channel_title = excluded.channel_title,
                is_active = 1;
        """, (channel_username, channel_title or channel_username))
        await conn.commit()
        return True

async def remove_force_join_channel(channel_id: int) -> bool:
    """Deletes or deactivates a force join channel."""
    async with get_db_connection() as conn:
        await conn.execute("DELETE FROM force_join_channels WHERE channel_id = ?;", (channel_id,))
        await conn.commit()
        return True

async def get_force_join_channels() -> List[Dict[str, Any]]:
    """Retrieves all active required force join channels."""
    async with get_db_connection() as conn:
        async with conn.execute("SELECT * FROM force_join_channels WHERE is_active = 1;") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

# ================= LEADERBOARD & STATS =================

async def get_leaderboard(limit: int = 10, criteria: str = "xp") -> List[Dict[str, Any]]:
    """Retrieves top users by XP, created polls, or votes cast."""
    async with get_db_connection() as conn:
        if criteria in ("creators", "creator"):
            query = """
                SELECT u.user_id, u.username, u.full_name, u.level, u.rank,
                       COUNT(p.poll_id) as metric_val, u.xp
                FROM users u
                LEFT JOIN polls p ON u.user_id = p.creator_id
                GROUP BY u.user_id
                ORDER BY metric_val DESC, u.xp DESC LIMIT ?;
            """
        elif criteria in ("voters", "voter", "votes"):
            query = """
                SELECT u.user_id, u.username, u.full_name, u.level, u.rank,
                       COUNT(v.vote_id) as metric_val, u.xp
                FROM users u
                LEFT JOIN votes v ON u.user_id = v.user_id
                GROUP BY u.user_id
                ORDER BY metric_val DESC, u.xp DESC LIMIT ?;
            """
        else:
            query = """
                SELECT u.user_id, u.username, u.full_name, u.xp as metric_val, u.level, u.rank, u.xp
                FROM users u
                ORDER BY u.xp DESC LIMIT ?;
            """

        async with conn.execute(query, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_system_stats() -> Dict[str, Any]:
    """Retrieves high-level analytics for admin dashboard."""
    async with get_db_connection() as conn:
        stats = {}
        
        async with conn.execute("SELECT COUNT(*) as cnt FROM users;") as c:
            stats["total_users"] = (await c.fetchone())["cnt"]
            
        async with conn.execute("SELECT COUNT(*) as cnt FROM polls;") as c:
            stats["total_polls"] = (await c.fetchone())["cnt"]

        async with conn.execute("SELECT COUNT(*) as cnt FROM polls WHERE status = 'active';") as c:
            stats["active_polls"] = (await c.fetchone())["cnt"]

        async with conn.execute("SELECT COUNT(*) as cnt FROM votes;") as c:
            stats["total_votes"] = (await c.fetchone())["cnt"]

        return stats

# ================= SYSTEM SETTINGS =================

async def get_setting(key: str, default: str = "") -> str:
    """Gets a global system configuration value."""
    async with get_db_connection() as conn:
        async with conn.execute("SELECT setting_value FROM system_settings WHERE setting_key = ?;", (key,)) as cursor:
            row = await cursor.fetchone()
            return row["setting_value"] if row else default

async def set_setting(key: str, value: str) -> bool:
    """Sets or updates a global system configuration value."""
    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO system_settings (setting_key, setting_value)
            VALUES (?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = CURRENT_TIMESTAMP;
        """, (key, value))
        await conn.commit()
        return True

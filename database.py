import os
import json
import logging
import aiosqlite
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

from config import DATABASE_PATH, ADMIN_IDS

logger = logging.getLogger("bot.database")

async def get_db_connection() -> aiosqlite.Connection:
    """Returns an active aiosqlite connection with foreign keys enabled."""
    conn = await aiosqlite.connect(DATABASE_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON;")
    await conn.execute("PRAGMA journal_mode = WAL;")
    await conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

async def init_db():
    """Initializes the database schema with all required tables, indices, and constraints."""
    async with await get_db_connection() as conn:
        # 1. Users Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'user', -- 'user' or 'admin'
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            rank TEXT DEFAULT 'Beginner',
            is_banned INTEGER DEFAULT 0,
            ban_reason TEXT DEFAULT '',
            notifications_enabled INTEGER DEFAULT 1,
            registration_date TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Polls Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            poll_id TEXT PRIMARY KEY,
            creator_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            poll_type TEXT DEFAULT 'single', -- 'single', 'multiple', 'quiz'
            is_anonymous INTEGER DEFAULT 0,
            is_public INTEGER DEFAULT 1,
            is_featured INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active', -- 'active' or 'closed'
            quiz_correct_option INTEGER DEFAULT -1,
            allow_revote INTEGER DEFAULT 1,
            hide_results_until_closed INTEGER DEFAULT 0,
            force_join_channel TEXT DEFAULT '',
            password_hash TEXT DEFAULT '',
            category TEXT DEFAULT 'General',
            views INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            duration_seconds INTEGER DEFAULT 86400,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            win_announcement_sent INTEGER DEFAULT 0,
            FOREIGN KEY (creator_id) REFERENCES users (user_id) ON DELETE CASCADE
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
            FOREIGN KEY (poll_id) REFERENCES polls (poll_id) ON DELETE CASCADE
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
            UNIQUE(poll_id, user_id),
            FOREIGN KEY (poll_id) REFERENCES polls (poll_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        );
        """)

        # 5. Poll Channels Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS poll_channels (
            channel_id INTEGER PRIMARY KEY,
            channel_name TEXT NOT NULL,
            channel_username TEXT NOT NULL UNIQUE,
            members_count INTEGER DEFAULT 0,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
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

        # 7. Favorites Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER NOT NULL,
            poll_id TEXT NOT NULL,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, poll_id),
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
            FOREIGN KEY (poll_id) REFERENCES polls (poll_id) ON DELETE CASCADE
        );
        """)

        # 8. Settings Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 9. Winner History Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS winner_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id TEXT NOT NULL,
            winner_option TEXT NOT NULL,
            total_votes_won INTEGER DEFAULT 0,
            announced_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (poll_id) REFERENCES polls (poll_id) ON DELETE CASCADE
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
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_poll_user ON votes(poll_id, user_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);")

        # Initial Default Settings
        default_settings = [
            ('maintenance_mode', 'False'),
            ('custom_footer', 'Powered by Poll Battle Bot'),
            ('auto_post_polls', 'True'),
            ('winner_announcements', 'True')
        ]
        for key, val in default_settings:
            await conn.execute("""
                INSERT OR IGNORE INTO settings (setting_key, setting_value)
                VALUES (?, ?);
            """, (key, val))

        await conn.commit()
        logger.info("Database initialized successfully.")


# ================= USER OPERATIONS =================

async def register_user(user_id: int, username: str, full_name: str, role: str = 'user') -> Dict[str, Any]:
    """Registers or updates a user in the database."""
    async with await get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, username, full_name, role)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name;
        """, (user_id, username, full_name, role))
        await conn.commit()
        return await get_user(user_id)

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single user by user_id."""
    async with await get_db_connection() as conn:
        async with conn.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_or_create_user(user_id: int, username: str = "Anonymous", full_name: str = "Anonymous User") -> Dict[str, Any]:
    """Retrieves an existing user or creates a new user record with appropriate admin role."""
    user = await get_user(user_id)
    if user:
        if (user.get("username") != username or user.get("full_name") != full_name) and username and full_name:
            async with await get_db_connection() as conn:
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
    async with await get_db_connection() as conn:
        async with conn.execute("SELECT COUNT(*) as cnt FROM polls WHERE creator_id = ?;", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

async def get_user_votes_count(user_id: int) -> int:
    """Returns count of votes cast by user."""
    async with await get_db_connection() as conn:
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
    async with await get_db_connection() as conn:
        async with conn.execute("SELECT * FROM users ORDER BY registration_date DESC;") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def ban_user(user_id: int, reason: str = "") -> bool:
    """Bans a user."""
    async with await get_db_connection() as conn:
        await conn.execute("""
            UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?;
        """, (reason, user_id))
        await conn.commit()
        return True

async def unban_user(user_id: int) -> bool:
    """Unbans a user."""
    async with await get_db_connection() as conn:
        await conn.execute("UPDATE users SET is_banned = 0, ban_reason = '' WHERE user_id = ?;", (user_id,))
        await conn.commit()
        return True

async def is_user_banned(user_id: int) -> bool:
    """Checks if a user is banned."""
    user = await get_user(user_id)
    return bool(user and user.get("is_banned"))

async def update_user_xp(user_id: int, amount: int = 10) -> Tuple[int, int]:
    """Adds XP to user and handles level ups."""
    async with await get_db_connection() as conn:
        user = await get_user(user_id)
        if not user:
            return 1, 0
        new_xp = user.get("xp", 0) + amount
        new_level = 1 + (new_xp // 100)
        rank = "Beginner"
        if new_level >= 10:
            rank = "Master"
        elif new_level >= 5:
            rank = "Pro"
        elif new_level >= 2:
            rank = "Intermediate"

        await conn.execute("""
            UPDATE users SET xp = ?, level = ?, rank = ? WHERE user_id = ?;
        """, (new_xp, new_level, rank, user_id))
        await conn.commit()
        return new_level, new_xp


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
    poll_type: str = "single",
    is_anonymous: bool = False,
    is_public: bool = True,
    quiz_correct_option: int = -1,
    duration_seconds: int = 86400,
    allow_revote: bool = True,
    hide_results_until_closed: bool = False,
    force_join_channel: str = "",
    password_hash: str = "",
    category: str = "General",
    expires_at: Optional[str] = None
) -> str:
    """Creates a new poll with its options."""
    async with await get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO polls (
                poll_id, creator_id, title, description, poll_type,
                is_anonymous, is_public, quiz_correct_option, duration_seconds,
                allow_revote, hide_results_until_closed, force_join_channel,
                password_hash, category, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            poll_id, creator_id, title, description, poll_type,
            1 if is_anonymous else 0, 1 if is_public else 0,
            quiz_correct_option, duration_seconds,
            1 if allow_revote else 0, 1 if hide_results_until_closed else 0,
            force_join_channel, password_hash, category, expires_at
        ))

        for index, option_text in enumerate(options):
            await conn.execute("""
                INSERT INTO poll_options (poll_id, option_index, option_text)
                VALUES (?, ?, ?);
            """, (poll_id, index, option_text))

        await conn.commit()
        return poll_id

async def get_poll(poll_id: str) -> Optional[Dict[str, Any]]:
    """Fetches poll details by poll_id."""
    async with await get_db_connection() as conn:
        async with conn.execute("SELECT * FROM polls WHERE poll_id = ?;", (poll_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            poll = dict(row)
            return await _attach_poll_details(conn, poll)

async def get_user_polls(user_id: int) -> List[Dict[str, Any]]:
    """Retrieves all polls created by a user."""
    async with await get_db_connection() as conn:
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
    async with await get_db_connection() as conn:
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
    async with await get_db_connection() as conn:
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
    async with await get_db_connection() as conn:
        now_str = datetime.utcnow().isoformat()
        async with conn.execute(
            "SELECT * FROM polls WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at <= ?;",
            (now_str,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def close_poll(poll_id: str) -> bool:
    """Closes an active poll."""
    async with await get_db_connection() as conn:
        await conn.execute("UPDATE polls SET status = 'closed' WHERE poll_id = ?;", (poll_id,))
        await conn.commit()
        return True

async def delete_poll(poll_id: str) -> bool:
    """Deletes a poll and associated records."""
    async with await get_db_connection() as conn:
        await conn.execute("DELETE FROM polls WHERE poll_id = ?;", (poll_id,))
        await conn.commit()
        return True

async def increment_poll_views(poll_id: str):
    """Increments the view count of a poll."""
    async with await get_db_connection() as conn:
        await conn.execute("UPDATE polls SET views = views + 1 WHERE poll_id = ?;", (poll_id,))
        await conn.commit()

async def increment_poll_shares(poll_id: str):
    """Increments the share count of a poll."""
    async with await get_db_connection() as conn:
        await conn.execute("UPDATE polls SET shares = shares + 1 WHERE poll_id = ?;", (poll_id,))
        await conn.commit()

async def search_polls(query: str, field: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
    """Searches public polls by title or description."""
    async with await get_db_connection() as conn:
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
    """Casts or updates a user's vote on a poll."""
    async with await get_db_connection() as conn:
        poll = await get_poll(poll_id)
        if not poll:
            return False, "Poll not found."
        if poll["status"] != "active":
            return False, "This poll is closed."

        # Check existing vote
        async with conn.execute(
            "SELECT * FROM votes WHERE poll_id = ? AND user_id = ?;",
            (poll_id, user_id)
        ) as cursor:
            existing = await cursor.fetchone()

        if existing:
            if not poll["allow_revote"]:
                return False, "Revoting is disabled for this poll."
            old_index = existing["option_index"]
            if old_index == option_index:
                return False, "You already voted for this option."
            # Decrement old option vote count
            await conn.execute("""
                UPDATE poll_options SET vote_count = MAX(0, vote_count - 1)
                WHERE poll_id = ? AND option_index = ?;
            """, (poll_id, old_index))
            # Update vote entry
            await conn.execute("""
                UPDATE votes SET option_index = ?, voted_at = CURRENT_TIMESTAMP
                WHERE poll_id = ? AND user_id = ?;
            """, (option_index, poll_id, user_id))
        else:
            # Insert vote entry
            await conn.execute("""
                INSERT INTO votes (poll_id, user_id, option_index)
                VALUES (?, ?, ?);
            """, (poll_id, user_id, option_index))

        # Increment new option vote count
        await conn.execute("""
            UPDATE poll_options SET vote_count = vote_count + 1
            WHERE poll_id = ? AND option_index = ?;
        """, (poll_id, option_index))

        await conn.commit()

        # Update User XP
        await update_user_xp(user_id, 10)
        return True, "Vote recorded successfully!"

async def get_user_vote(arg1: Any, arg2: Any) -> Optional[Dict[str, int]]:
    """Returns dict {'option_index': idx} if user voted on poll, or None. Handles flexible parameter order."""
    if isinstance(arg1, str):
        poll_id, user_id = arg1, int(arg2)
    else:
        user_id, poll_id = int(arg1), str(arg2)

    async with await get_db_connection() as conn:
        async with conn.execute(
            "SELECT option_index FROM votes WHERE poll_id = ? AND user_id = ?;",
            (poll_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            return {"option_index": row["option_index"]} if row else None


# ================= FAVORITES OPERATIONS =================

async def add_favorite(user_id: int, poll_id: str) -> bool:
    """Adds a poll to user's favorites."""
    async with await get_db_connection() as conn:
        await conn.execute("""
            INSERT OR IGNORE INTO favorites (user_id, poll_id) VALUES (?, ?);
        """, (user_id, poll_id))
        await conn.commit()
        return True

async def remove_favorite(user_id: int, poll_id: str) -> bool:
    """Removes a poll from user's favorites."""
    async with await get_db_connection() as conn:
        await conn.execute("DELETE FROM favorites WHERE user_id = ? AND poll_id = ?;", (user_id, poll_id))
        await conn.commit()
        return True

async def is_favorite(arg1: Any, arg2: Any) -> bool:
    """Checks if a poll is in user's favorites, supporting both (user_id, poll_id) and (poll_id, user_id)."""
    if isinstance(arg1, str):
        poll_id, user_id = arg1, int(arg2)
    else:
        user_id, poll_id = int(arg1), str(arg2)

    async with await get_db_connection() as conn:
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
    async with await get_db_connection() as conn:
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
    async with await get_db_connection() as conn:
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
    """Deactivates/removes a force join channel."""
    async with await get_db_connection() as conn:
        await conn.execute("DELETE FROM force_join_channels WHERE channel_id = ?;", (channel_id,))
        await conn.commit()
        return True

async def get_force_join_channels() -> List[Dict[str, Any]]:
    """Retrieves all active force join channels."""
    async with await get_db_connection() as conn:
        async with conn.execute(
            "SELECT * FROM force_join_channels WHERE is_active = 1;"
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ================= LEADERBOARD & STATS =================

async def get_leaderboard(limit: int = 10, criteria: str = "xp") -> List[Dict[str, Any]]:
    """Retrieves top users by XP, created polls, or votes cast."""
    async with await get_db_connection() as conn:
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
    """Gathers overall system statistics for admin dashboard."""
    async with await get_db_connection() as conn:
        async with conn.execute("SELECT COUNT(*) as cnt FROM users;") as c:
            users_cnt = (await c.fetchone())["cnt"]
        async with conn.execute("SELECT COUNT(*) as cnt FROM polls;") as c:
            polls_cnt = (await c.fetchone())["cnt"]
        async with conn.execute("SELECT COUNT(*) as cnt FROM votes;") as c:
            votes_cnt = (await c.fetchone())["cnt"]
        async with conn.execute("SELECT COUNT(*) as cnt FROM polls WHERE status = 'active';") as c:
            active_cnt = (await c.fetchone())["cnt"]

        return {
            "total_users": users_cnt,
            "total_polls": polls_cnt,
            "total_votes": votes_cnt,
            "active_polls": active_cnt
        }


# ================= SETTINGS OPERATIONS =================

async def get_setting(key: str, default: str = "") -> str:
    """Gets a global setting value."""
    async with await get_db_connection() as conn:
        async with conn.execute("SELECT setting_value FROM settings WHERE setting_key = ?;", (key,)) as cursor:
            row = await cursor.fetchone()
            return row["setting_value"] if row else default

async def set_setting(key: str, value: str) -> bool:
    """Sets a global setting value."""
    async with await get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = CURRENT_TIMESTAMP;
        """, (key, value))
        await conn.commit()
        return True

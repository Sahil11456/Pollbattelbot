import aiosqlite
import logging
from typing import Optional, List, Dict, Any
from config import DATABASE_PATH, ADMIN_IDS

logger = logging.getLogger("bot.database")

def get_db_connection():
    """Returns an async context manager connection to SQLite database."""
    conn = aiosqlite.connect(DATABASE_PATH)
    conn.row_factory = aiosqlite.Row
    return conn

async def init_db():
    """Initializes SQLite database schemas, tables, and default settings."""
    async with get_db_connection() as conn:
        await conn.execute("PRAGMA foreign_keys = ON;")
        await conn.execute("PRAGMA journal_mode = WAL;")

        # 1. Users Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            rank TEXT DEFAULT '🌱 Novice',
            is_banned INTEGER DEFAULT 0,
            registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
            notifications_enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2. Polls Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            poll_id TEXT PRIMARY KEY,
            creator_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            is_anonymous INTEGER DEFAULT 0,
            is_public INTEGER DEFAULT 1,
            is_featured INTEGER DEFAULT 0,
            poll_type TEXT DEFAULT 'regular',
            quiz_correct_option INTEGER DEFAULT -1,
            allow_revote INTEGER DEFAULT 1,
            hide_results_until_closed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT,
            closed_at TEXT,
            views INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            duration_seconds INTEGER DEFAULT 86400,
            category TEXT DEFAULT 'General',
            pin_code TEXT,
            win_announcement_sent INTEGER DEFAULT 0,
            FOREIGN KEY (creator_id) REFERENCES users (user_id) ON DELETE CASCADE
        );
        """)

        # 3. Options Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS options (
            option_id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id TEXT NOT NULL,
            option_index INTEGER NOT NULL,
            option_text TEXT NOT NULL,
            vote_count INTEGER DEFAULT 0,
            FOREIGN KEY (poll_id) REFERENCES polls (poll_id) ON DELETE CASCADE,
            UNIQUE(poll_id, option_index)
        );
        """)

        # 4. Votes Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            option_index INTEGER NOT NULL,
            device_token TEXT,
            voted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (poll_id) REFERENCES polls (poll_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
            UNIQUE(poll_id, user_id)
        );
        """)

        # 5. Channel Subscriptions Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS channel_subscriptions (
            channel_id INTEGER PRIMARY KEY,
            channel_username TEXT NOT NULL UNIQUE,
            channel_title TEXT,
            members_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
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

        # 10. System Logs Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL,
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
    async with get_db_connection() as conn:
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

    unlocked = []
    if votes_cnt >= 1:
        unlocked.append({"achievement_name": "🗳️ First Vote Cast", "description": "Cast your first vote in the Arena"})
    if votes_cnt >= 10:
        unlocked.append({"achievement_name": "⭐ Active Voter", "description": "Cast 10 votes"})
    if votes_cnt >= 50:
        unlocked.append({"achievement_name": "🔥 Master Voter", "description": "Cast 50 votes"})
    if polls_cnt >= 1:
        unlocked.append({"achievement_name": "📝 Creator Spark", "description": "Created your first poll"})
    if polls_cnt >= 5:
        unlocked.append({"achievement_name": "🏆 Master Creator", "description": "Created 5 polls"})

    return unlocked

async def update_user_xp(user_id: int, xp_to_add: int) -> Dict[str, Any]:
    """Adds XP to user and calculates level/rank up."""
    from utils.helpers import calculate_level_and_xp, get_rank_by_level
    user = await get_user(user_id)
    if not user:
        return {}

    new_xp = user.get("xp", 0) + xp_to_add
    new_level, _, _ = calculate_level_and_xp(new_xp)
    new_rank = get_rank_by_level(new_level)

    async with get_db_connection() as conn:
        await conn.execute("""
            UPDATE users
            SET xp = ?, level = ?, rank = ?
            WHERE user_id = ?;
        """, (new_xp, new_level, new_rank, user_id))
        await conn.commit()

    user["xp"] = new_xp
    user["level"] = new_level
    user["rank"] = new_rank
    return user

async def is_user_banned(user_id: int) -> bool:
    """Checks if a user is currently banned."""
    user = await get_user(user_id)
    return bool(user and user.get("is_banned", 0) == 1)

async def ban_user(user_id: int) -> bool:
    """Bans a target user."""
    async with get_db_connection() as conn:
        await conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?;", (user_id,))
        await conn.commit()
        return True

async def unban_user(user_id: int) -> bool:
    """Unbans a target user."""
    async with get_db_connection() as conn:
        await conn.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?;", (user_id,))
        await conn.commit()
        return True

async def get_all_users() -> List[Dict[str, Any]]:
    """Retrieves all registered users."""
    async with get_db_connection() as conn:
        async with conn.execute("SELECT * FROM users ORDER BY created_at DESC;") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


# ================= POLL OPERATIONS =================

async def create_poll(
    poll_id: str,
    creator_id: int,
    title: str,
    description: str,
    options: List[str],
    category: str = "General",
    duration_seconds: int = 86400,
    is_anonymous: bool = False,
    is_public: bool = True,
    poll_type: str = "regular",
    quiz_correct_option: int = -1,
    allow_revote: bool = True,
    pin_code: Optional[str] = None
) -> Dict[str, Any]:
    """Creates a new poll record with option entries."""
    from datetime import datetime, timedelta, timezone
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)).isoformat()

    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO polls (
                poll_id, creator_id, title, description, category,
                duration_seconds, expires_at, is_anonymous, is_public,
                poll_type, quiz_correct_option, allow_revote, pin_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            poll_id, creator_id, title, description, category,
            duration_seconds, expires_at, int(is_anonymous), int(is_public),
            poll_type, quiz_correct_option, int(allow_revote), pin_code
        ))

        for idx, opt_text in enumerate(options):
            await conn.execute("""
                INSERT INTO options (poll_id, option_index, option_text, vote_count)
                VALUES (?, ?, ?, 0);
            """, (poll_id, idx, opt_text))

        await conn.commit()

    await update_user_xp(creator_id, 20)
    return await get_poll(poll_id)

async def get_poll(poll_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves poll details including options and vote counts."""
    async with get_db_connection() as conn:
        async with conn.execute("SELECT * FROM polls WHERE poll_id = ?;", (poll_id,)) as cursor:
            poll_row = await cursor.fetchone()
            if not poll_row:
                return None

            poll_dict = dict(poll_row)
            return await _attach_poll_details(conn, poll_dict)

async def _attach_poll_details(conn, poll_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Helper method to attach options and total vote count to a poll dict."""
    poll_id = poll_dict["poll_id"]
    async with conn.execute("SELECT * FROM options WHERE poll_id = ? ORDER BY option_index ASC;", (poll_id,)) as opt_cursor:
        opt_rows = await opt_cursor.fetchall()
        options = [dict(r) for r in opt_rows]

    async with conn.execute("SELECT SUM(vote_count) as total FROM options WHERE poll_id = ?;", (poll_id,)) as sum_cursor:
        sum_row = await sum_cursor.fetchone()
        total_votes = sum_row["total"] if sum_row and sum_row["total"] is not None else 0

    poll_dict["options"] = options
    poll_dict["total_votes"] = total_votes
    return poll_dict

async def increment_poll_view(poll_id: str):
    """Increments view counter for a poll."""
    async with get_db_connection() as conn:
        await conn.execute("UPDATE polls SET views = views + 1 WHERE poll_id = ?;", (poll_id,))
        await conn.commit()

async def get_user_polls(creator_id: int) -> List[Dict[str, Any]]:
    """Gets all polls created by a specific user."""
    async with get_db_connection() as conn:
        async with conn.execute("SELECT * FROM polls WHERE creator_id = ? ORDER BY created_at DESC;", (creator_id,)) as cursor:
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p_dict = dict(r)
                p_dict = await _attach_poll_details(conn, p_dict)
                polls.append(p_dict)
            return polls

async def get_trending_polls(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetches trending active public polls ordered by view and vote popularity."""
    async with get_db_connection() as conn:
        async with conn.execute("""
            SELECT p.*, (p.views + COALESCE((SELECT SUM(vote_count) FROM options WHERE poll_id = p.poll_id), 0) * 3) as score
            FROM polls p
            WHERE p.status = 'active' AND p.is_public = 1
            ORDER BY score DESC, p.created_at DESC
            LIMIT ?;
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p_dict = dict(r)
                p_dict = await _attach_poll_details(conn, p_dict)
                polls.append(p_dict)
            return polls

async def search_polls(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Searches public polls by title, description, or poll_id keyword."""
    async with get_db_connection() as conn:
        q = f"%{query}%"
        async with conn.execute("""
            SELECT * FROM polls
            WHERE (title LIKE ? OR description LIKE ? OR poll_id = ?) AND is_public = 1
            ORDER BY created_at DESC LIMIT ?;
        """, (q, q, query, limit)) as cursor:
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p_dict = dict(r)
                p_dict = await _attach_poll_details(conn, p_dict)
                polls.append(p_dict)
            return polls

async def close_poll(poll_id: str) -> bool:
    """Closes a poll from further voting."""
    from datetime import datetime, timezone
    closed_at = datetime.now(timezone.utc).isoformat()
    async with get_db_connection() as conn:
        await conn.execute("""
            UPDATE polls SET status = 'closed', closed_at = ? WHERE poll_id = ?;
        """, (closed_at, poll_id))
        await conn.commit()
        return True

async def delete_poll(poll_id: str) -> bool:
    """Deletes a poll permanently."""
    async with get_db_connection() as conn:
        await conn.execute("DELETE FROM polls WHERE poll_id = ?;", (poll_id,))
        await conn.commit()
        return True

async def get_expired_active_polls() -> List[Dict[str, Any]]:
    """Retrieves active polls whose expires_at timestamp has passed."""
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    async with get_db_connection() as conn:
        async with conn.execute("""
            SELECT * FROM polls
            WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at <= ?;
        """, (now_iso,)) as cursor:
            rows = await cursor.fetchall()
            polls = []
            for r in rows:
                p_dict = dict(r)
                p_dict = await _attach_poll_details(conn, p_dict)
                polls.append(p_dict)
            return polls


# ================= VOTE OPERATIONS =================

async def record_vote(poll_id: str, user_id: int, option_index: int, device_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Records a vote for a user on a given poll option with transaction safety.
    Handles revoting if allowed.
    """
    poll_obj = await get_poll(poll_id)
    if not poll_obj:
        return {"success": False, "error": "Poll not found."}

    if poll_obj.get("status") != "active":
        return {"success": False, "error": "This poll is closed."}

    async with get_db_connection() as conn:
        # Check if user already voted
        async with conn.execute("SELECT option_index FROM votes WHERE poll_id = ? AND user_id = ?;", (poll_id, user_id)) as cursor:
            existing_vote = await cursor.fetchone()

        if existing_vote:
            if not poll_obj.get("allow_revote", 1):
                return {"success": False, "error": "Revoting is disabled for this poll."}

            old_option_index = existing_vote["option_index"]
            if old_option_index == option_index:
                return {"success": False, "error": "You already voted for this option!"}

            # Decrement old option vote count
            await conn.execute("""
                UPDATE options SET vote_count = MAX(0, vote_count - 1)
                WHERE poll_id = ? AND option_index = ?;
            """, (poll_id, old_option_index))

            # Update vote record
            await conn.execute("""
                UPDATE votes SET option_index = ?, device_token = ?, voted_at = CURRENT_TIMESTAMP
                WHERE poll_id = ? AND user_id = ?;
            """, (option_index, device_token, poll_id, user_id))
        else:
            # New Vote record
            await conn.execute("""
                INSERT INTO votes (poll_id, user_id, option_index, device_token)
                VALUES (?, ?, ?, ?);
            """, (poll_id, user_id, option_index, device_token))

        # Increment new option vote count
        await conn.execute("""
            UPDATE options SET vote_count = vote_count + 1
            WHERE poll_id = ? AND option_index = ?;
        """, (poll_id, option_index))

        await conn.commit()

    # Reward voter with XP
    await update_user_xp(user_id, 10)
    updated_poll = await get_poll(poll_id)
    return {"success": True, "poll": updated_poll}

async def get_user_vote(poll_id: str, user_id: int) -> Optional[int]:
    """Gets option index user voted for in a poll."""
    async with get_db_connection() as conn:
        async with conn.execute("SELECT option_index FROM votes WHERE poll_id = ? AND user_id = ?;", (poll_id, user_id)) as cursor:
            row = await cursor.fetchone()
            return row["option_index"] if row else None


# ================= FAVORITES OPERATIONS =================

async def add_favorite(user_id: int, poll_id: str) -> bool:
    """Adds a poll to user's favorites list."""
    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT OR IGNORE INTO favorites (user_id, poll_id)
            VALUES (?, ?);
        """, (user_id, poll_id))
        await conn.commit()
        return True

async def remove_favorite(user_id: int, poll_id: str) -> bool:
    """Removes a poll from user's favorites list."""
    async with get_db_connection() as conn:
        await conn.execute("DELETE FROM favorites WHERE user_id = ? AND poll_id = ?;", (user_id, poll_id))
        await conn.commit()
        return True

async def is_favorite(user_id: int, poll_id: str) -> bool:
    """Checks if a poll is favorited by user."""
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
    """Deactivates/removes a force join channel."""
    async with get_db_connection() as conn:
        await conn.execute("DELETE FROM force_join_channels WHERE channel_id = ?;", (channel_id,))
        await conn.commit()
        return True

async def get_force_join_channels() -> List[Dict[str, Any]]:
    """Retrieves all active force join channels."""
    async with get_db_connection() as conn:
        async with conn.execute(
            "SELECT * FROM force_join_channels WHERE is_active = 1;"
        ) as cursor:
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
    """Gathers overall system statistics for admin dashboard."""
    async with get_db_connection() as conn:
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
    async with get_db_connection() as conn:
        async with conn.execute("SELECT setting_value FROM settings WHERE setting_key = ?;", (key,)) as cursor:
            row = await cursor.fetchone()
            return row["setting_value"] if row else default

async def set_setting(key: str, value: str) -> bool:
    """Sets a global setting value."""
    async with get_db_connection() as conn:
        await conn.execute("""
            INSERT INTO settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = CURRENT_TIMESTAMP;
        """, (key, value))
        await conn.commit()
        return True

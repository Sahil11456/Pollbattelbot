import aiosqlite
import logging
from config import DB_URL

logger = logging.getLogger("bot.database")

async def get_db_connection() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_URL)
    await conn.execute("PRAGMA foreign_keys = ON;")
    await conn.execute("PRAGMA journal_mode = WAL;")
    await conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

async def init_db():
    async with await get_db_connection() as conn:
        # 1. Users
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'user',
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            rank TEXT DEFAULT 'Beginner',
            is_joined_channel INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            registration_date TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # 2. Polls Table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            poll_id TEXT PRIMARY KEY,
            creator_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            options_json TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            views INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            is_featured INTEGER DEFAULT 0,
            duration_seconds INTEGER DEFAULT 86400,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES users (user_id) ON DELETE CASCADE
        );
        """)

        # 3. Votes (Composite Unique Lock)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            poll_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            option_index INTEGER NOT NULL,
            voted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (poll_id, user_id),
            FOREIGN KEY (poll_id) REFERENCES polls (poll_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        );
        """)

        # 4. Settings
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Indexing for hyper-fast search query and analytics rendering
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_polls_creator ON polls(creator_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_polls_status ON polls(status);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_user ON votes(user_id);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_votes_poll_user ON votes(poll_id, user_id);")

        # Seeding Default settings
        default_settings = [
            ('maintenance_mode', 'False'),
            ('custom_footer', 'Powered by My Poll Battle Bot'),
            ('auto_post_polls', 'True'),
            ('device_verification', 'True'),
            ('winner_announcements', 'True')
        ]
        for key, val in default_settings:
            await conn.execute("INSERT OR IGNORE INTO settings (setting_key, setting_value) VALUES (?, ?);", (key, val))
            
        await conn.commit()

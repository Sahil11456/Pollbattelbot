import aiosqlite
import logging
from config import config

logger = logging.getLogger(__name__)

async def get_db():
    conn = await aiosqlite.connect(config.DATABASE_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON;")
    return conn

async def init_db():
    async with await get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                points INTEGER DEFAULT 0,
                votes_cast INTEGER DEFAULT 0,
                polls_created INTEGER DEFAULT 0,
                wins_count INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS polls (
                poll_id TEXT PRIMARY KEY,
                creator_id INTEGER NOT NULL,
                creator_name TEXT NOT NULL,
                title TEXT NOT NULL,
                poll_type TEXT NOT NULL DEFAULT 'public',
                choice_mode TEXT NOT NULL DEFAULT 'single',
                is_closed INTEGER DEFAULT 0,
                is_featured INTEGER DEFAULT 0,
                correct_option_id TEXT,
                hot_score INTEGER DEFAULT 0,
                shares_count INTEGER DEFAULT 0,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS options (
                option_id TEXT PRIMARY KEY,
                poll_id TEXT NOT NULL,
                option_text TEXT NOT NULL,
                option_order INTEGER NOT NULL,
                votes INTEGER DEFAULT 0,
                FOREIGN KEY (poll_id) REFERENCES polls(poll_id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                vote_id TEXT PRIMARY KEY,
                poll_id TEXT NOT NULL,
                option_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (poll_id) REFERENCES polls(poll_id) ON DELETE CASCADE,
                FOREIGN KEY (option_id) REFERENCES options(option_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(poll_id, option_id, user_id)
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                poll_id TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, poll_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (poll_id) REFERENCES polls(poll_id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS poll_channels (
                channel_id INTEGER PRIMARY KEY,
                channel_title TEXT NOT NULL,
                added_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS force_join_channels (
                channel_id TEXT PRIMARY KEY,
                channel_url TEXT NOT NULL,
                channel_title TEXT NOT NULL
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                badge TEXT NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS winner_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id TEXT NOT NULL,
                winner_option_id TEXT NOT NULL,
                winning_votes INTEGER NOT NULL,
                announced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Indexes for Performance Optimization
        await db.execute("CREATE INDEX IF NOT EXISTS idx_polls_creator ON polls(creator_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_polls_hot ON polls(hot_score DESC);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_options_poll ON options(poll_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_votes_user ON votes(user_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_votes_poll ON votes(poll_id);")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_points ON users(points DESC);")

        await db.commit()
        logger.info("SQLite Database initialized with full indexes and constraints successfully.")

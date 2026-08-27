"""
PocketPlot Universe (v17) - schema migrations.

Adds:
  v17:
    - subscribers.username (public profile handle)
    - subscribers.is_public (opt-in to public showcase)
    - subscribers.featured_story_ids (JSON list, max 3)
    - worlds.is_public, worlds.view_count, worlds.read_count
    - world_episodes.view_count, world_episodes.read_count
    - story_views (per-day view log for analytics)
    - story_reads (per-day completed-episode log)
    - remix_history (track remixed-from worlds)
    - feature_flags (admin toggleable feature flags)

All migrations idempotent.
"""


NEW_COLUMNS = [
    "ALTER TABLE subscribers ADD COLUMN username TEXT",
    "ALTER TABLE subscribers ADD COLUMN is_public INTEGER DEFAULT 0",
    "ALTER TABLE subscribers ADD COLUMN featured_story_ids TEXT DEFAULT '[]'",
    "ALTER TABLE worlds ADD COLUMN is_public INTEGER DEFAULT 0",
    "ALTER TABLE worlds ADD COLUMN view_count INTEGER DEFAULT 0",
    "ALTER TABLE worlds ADD COLUMN read_count INTEGER DEFAULT 0",
    "ALTER TABLE world_episodes ADD COLUMN view_count INTEGER DEFAULT 0",
    "ALTER TABLE world_episodes ADD COLUMN read_count INTEGER DEFAULT 0",
]


MIGRATION_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS story_views (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id        INTEGER NOT NULL REFERENCES worlds(id),
        episode_id      INTEGER REFERENCES world_episodes(id),
        viewer_hash     TEXT,  -- hashed viewer identifier (privacy)
        viewed_at       TEXT NOT NULL,
        source          TEXT DEFAULT 'me'  -- 'me' | 'public' | 'shared'
    )
    """,
    "CREATE INDEX IF NOT EXISTS story_views_world ON story_views(world_id, viewed_at DESC)",
    "CREATE INDEX IF NOT EXISTS story_views_episode ON story_views(episode_id)",

    """
    CREATE TABLE IF NOT EXISTS story_reads (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id        INTEGER NOT NULL REFERENCES worlds(id),
        episode_id      INTEGER NOT NULL REFERENCES world_episodes(id),
        reader_hash     TEXT,
        completed       INTEGER DEFAULT 1,
        duration_seconds INTEGER DEFAULT 0,
        read_at         TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS story_reads_world ON story_reads(world_id, read_at DESC)",
    "CREATE INDEX IF NOT EXISTS story_reads_episode ON story_reads(episode_id)",

    """
    CREATE TABLE IF NOT EXISTS remix_history (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        original_world_id INTEGER NOT NULL REFERENCES worlds(id),
        new_world_id      INTEGER NOT NULL REFERENCES worlds(id),
        from_genre        TEXT NOT NULL,
        to_genre          TEXT NOT NULL,
        created_at        TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS remix_history_orig ON remix_history(original_world_id)",

    """
    CREATE TABLE IF NOT EXISTS feature_flags (
        key             TEXT PRIMARY KEY,
        enabled         INTEGER DEFAULT 1,
        description     TEXT,
        updated_at      TEXT,
        updated_by      TEXT
    )
    """,

    # Default feature flags. Admin can toggle via /admin/features.
    """
    INSERT OR IGNORE INTO feature_flags(key, enabled, description, updated_at)
    VALUES
        ('library',           1, 'Story Library page',                datetime('now')),
        ('seed_generator',    1, 'Story Seed random prompt generator', datetime('now')),
        ('story_remix',       1, 'Story Remix (Pro & Creator)',       datetime('now')),
        ('public_profile',    1, 'Public Profile pages',              datetime('now')),
        ('story_analytics',   1, 'Story Analytics (Pro & Creator)',   datetime('now')),
        ('weekly_summary',    1, 'Weekly summary emails (Pro/Creator)', datetime('now')),
        ('milestone_emails',  1, 'Milestone celebration emails',      datetime('now')),
        ('genre_animations',  1, 'Homepage CSS animations',           datetime('now'))
    """,

    """
    CREATE TABLE IF NOT EXISTS user_milestones (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
        milestone       TEXT NOT NULL,  -- 'first_story' | '10_words' | '100_words' | '1000_words' | '10000_words' | 'streak_7' | 'streak_30'
        achieved_at     TEXT NOT NULL,
        celebrated      INTEGER DEFAULT 0
    )
    """,
    "CREATE INDEX IF NOT EXISTS user_milestones_sub ON user_milestones(subscriber_id, milestone)",

    """
    CREATE TABLE IF NOT EXISTS weekly_summary_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
        week_start      TEXT NOT NULL,
        sent_at         TEXT NOT NULL,
        stats_json      TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS weekly_summary_log_sub ON weekly_summary_log(subscriber_id, week_start)",

    # Social graph: follows + notifications. v17 ships the data model and a
    # couple of stub routes so the follow feature is a clean follow-up.
    """
    CREATE TABLE IF NOT EXISTS follows (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        follower_id     INTEGER NOT NULL REFERENCES subscribers(id),
        followee_id     INTEGER NOT NULL REFERENCES subscribers(id),
        created_at      TEXT NOT NULL,
        UNIQUE(follower_id, followee_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS follows_follower ON follows(follower_id)",
    "CREATE INDEX IF NOT EXISTS follows_followee ON follows(followee_id, created_at DESC)",

    """
    CREATE TABLE IF NOT EXISTS notifications (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_id    INTEGER NOT NULL REFERENCES subscribers(id),
        kind            TEXT NOT NULL,  -- 'new_story' | 'milestone' | 'weekly_summary' | 'system'
        title           TEXT NOT NULL,
        body            TEXT,
        link            TEXT,
        is_read         INTEGER DEFAULT 0,
        created_at      TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS notifications_recipient ON notifications(recipient_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS notifications_unread ON notifications(recipient_id, is_read)",
]


def migrate(db):
    """Apply v17 migrations. Safe to call repeatedly on every boot."""
    conn = db()
    for stmt in NEW_COLUMNS:
        try:
            conn.execute(stmt)
        except Exception as e:
            msg = str(e).lower()
            if "duplicate column" not in msg and "already exists" not in msg:
                raise
    for stmt in MIGRATION_STATEMENTS:
        try:
            conn.execute(stmt)
        except Exception as e:
            msg = str(e).lower()
            if "already exists" not in msg and "duplicate" not in msg:
                raise
    conn.commit()
    conn.close()

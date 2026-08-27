"""
PocketPlot Universe (v11 + v13) — schema migrations.

Adds:
  v11:
    - subscribers.profile_type
    - subscribers.tier
    - subscribers.grandfathereProPrice
    - external_api_keys
    - worlds
    - world_episodes
    - api_call_log
    - validation_log

  v13:
    - audit_log
    - feature_requests
    - contact_messages

All migrations idempotent.
"""
import datetime as dt


# Column migrations for existing tables (subscribers gets new columns,
# deliveries gets world_id). ALTER TABLE ADD raises "duplicate column" if
# the column already exists; the migrate() helper swallows that.
ALTER_STATEMENTS = [
    "ALTER TABLE subscribers ADD COLUMN profile_type TEXT DEFAULT 'adult'",
    "ALTER TABLE subscribers ADD COLUMN tier TEXT DEFAULT 'free'",
    "ALTER TABLE subscribers ADD COLUMN grandfathereProPrice INTEGER DEFAULT 0",
    "ALTER TABLE deliveries ADD COLUMN world_id INTEGER",
]


# Each statement is its own string. This avoids the multi-statement
# parsing issues that broke v13's tables when they were embedded inside
# a giant Python triple-quoted blob.
MIGRATION_STATEMENTS = [
    # ---- v11 ----
    """
    CREATE TABLE IF NOT EXISTS external_api_keys (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
        key_type        TEXT NOT NULL,
        api_key_enc     TEXT NOT NULL,
        base_url        TEXT,
        model_name      TEXT,
        is_active       INTEGER DEFAULT 1,
        created_at      TEXT NOT NULL,
        last_used_at    TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS external_api_keys_sub ON external_api_keys(subscriber_id, key_type)",
    """
    CREATE TABLE IF NOT EXISTS worlds (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
        title           TEXT NOT NULL,
        genre           TEXT NOT NULL DEFAULT 'fantasy',
        tone            TEXT NOT NULL DEFAULT 'hopeful',
        setting         TEXT NOT NULL,
        state_json      TEXT NOT NULL DEFAULT '{}',
        seed            INTEGER NOT NULL,
        is_active       INTEGER DEFAULT 1,
        created_at      TEXT NOT NULL,
        last_played_at  TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS worlds_sub ON worlds(subscriber_id, last_played_at DESC)",
    """
    CREATE TABLE IF NOT EXISTS world_episodes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        world_id        INTEGER NOT NULL REFERENCES worlds(id),
        subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
        episode_number  INTEGER NOT NULL,
        title           TEXT NOT NULL,
        body            TEXT NOT NULL,
        choices_json    TEXT,
        chosen_choice   INTEGER,
        created_at      TEXT NOT NULL,
        chosen_at       TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS world_episodes_world ON world_episodes(world_id, episode_number)",
    """
    CREATE TABLE IF NOT EXISTS api_call_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
        call_date       TEXT NOT NULL,
        call_type       TEXT NOT NULL,
        success         INTEGER DEFAULT 1
    )
    """,
    "CREATE INDEX IF NOT EXISTS api_call_log_sub ON api_call_log(subscriber_id, call_date)",
    """
    CREATE TABLE IF NOT EXISTS validation_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        subscriber_id   INTEGER,
        pass            TEXT NOT NULL,
        verdict         TEXT NOT NULL,
        reason          TEXT,
        snippet         TEXT,
        created_at      TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS validation_log_sub ON validation_log(subscriber_id, created_at DESC)",

    # ---- v13 ----
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_id        INTEGER,
        actor_type      TEXT NOT NULL DEFAULT 'subscriber',
        action          TEXT NOT NULL,
        target_type     TEXT,
        target_id       INTEGER,
        metadata_json   TEXT,
        ip              TEXT,
        user_agent      TEXT,
        created_at      TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS audit_log_actor ON audit_log(actor_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS audit_log_action ON audit_log(action, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS audit_log_target ON audit_log(target_type, target_id)",
    """
    CREATE TABLE IF NOT EXISTS feature_requests (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        title           TEXT NOT NULL,
        description     TEXT,
        votes           INTEGER NOT NULL DEFAULT 0,
        status          TEXT NOT NULL DEFAULT 'open',
        submitter_email TEXT,
        created_at      TEXT NOT NULL,
        updated_at      TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS feature_requests_status ON feature_requests(status, votes DESC)",
    """
    CREATE TABLE IF NOT EXISTS contact_messages (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        email           TEXT NOT NULL,
        subject         TEXT NOT NULL,
        body            TEXT NOT NULL,
        ip              TEXT,
        created_at      TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS contact_messages_created ON contact_messages(created_at DESC)",
]


def migrate(db):
    """Apply migrations. Safe to call repeatedly on every boot."""
    conn = db()
    # Column additions
    for stmt in ALTER_STATEMENTS:
        try:
            conn.execute(stmt)
        except Exception as e:
            msg = str(e).lower()
            if "duplicate column" not in msg and "already exists" not in msg:
                raise
    # New tables + indexes (one statement at a time so SQLite parses each cleanly)
    for stmt in MIGRATION_STATEMENTS:
        try:
            conn.execute(stmt)
        except Exception as e:
            log_msg = str(e).lower()
            if "already exists" not in log_msg and "duplicate" not in log_msg:
                # Re-raise so unexpected errors get attention in the boot log
                raise
    conn.commit()
    conn.close()

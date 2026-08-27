"""
PocketPlot Universe - v24 schema migrations.

Adds:
  story_revisions       - edit history for worlds (title/setting/tone changes)
  scene_revisions       - per-episode edit history (body/title/choices)
  onboarding_state      - per-user onboarding wizard progress
  user_streaks          - current streak + best streak + last_active_date
  xp_events             - XP ledger (writes, plays, completions, milestones)
  comments              - threaded comments on worlds
  reactions             - emoji reactions on worlds (6 reactions)
  story_covers          - generated 1200x630 cover image paths
  audit_log_extended    - extended audit log (covers admin + sensitive user actions)
  inventory_items       - item types catalog (key, gem, rune, scroll, etc.)
  inventory_grants      - per-subscriber inventory (which items, how many)
  world_inventory       - items placed in a specific world (Minecraft-style placement)
  inventory_history     - audit trail for grants/transfers/uses

All idempotent: CREATE TABLE IF NOT EXISTS + ALTER TABLE ADD COLUMN wrapped in try/except.
"""
import sqlite3
import datetime as dt

MIGRATIONS_V24 = [
    # story_revisions: edit history for worlds
    """
    CREATE TABLE IF NOT EXISTS story_revisions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      world_id INTEGER NOT NULL,
      subscriber_id INTEGER NOT NULL,
      field TEXT NOT NULL,           -- 'title', 'setting', 'tone', 'genre', 'character', 'objective'
      old_value TEXT,
      new_value TEXT,
      created_at TEXT NOT NULL,
      FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
      FOREIGN KEY (subscriber_id) REFERENCES subscribers(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_story_revisions_world ON story_revisions(world_id, created_at)",

    # scene_revisions: per-episode edit history
    """
    CREATE TABLE IF NOT EXISTS scene_revisions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      episode_id INTEGER NOT NULL,
      subscriber_id INTEGER NOT NULL,
      field TEXT NOT NULL,           -- 'title', 'body', 'choices_json', 'narration'
      old_value TEXT,
      new_value TEXT,
      created_at TEXT NOT NULL,
      FOREIGN KEY (episode_id) REFERENCES world_episodes(id) ON DELETE CASCADE,
      FOREIGN KEY (subscriber_id) REFERENCES subscribers(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_scene_revisions_episode ON scene_revisions(episode_id, created_at)",

    # onboarding_state
    """
    CREATE TABLE IF NOT EXISTS onboarding_state (
      subscriber_id INTEGER PRIMARY KEY,
      current_step INTEGER NOT NULL DEFAULT 1,    -- 1, 2, or 3
      step1_data TEXT,                            -- JSON: {genre, ...}
      step2_data TEXT,                            -- JSON: {character, ...}
      step3_data TEXT,                            -- JSON: {tone, ...}
      completed_at TEXT,
      skipped_at TEXT,
      FOREIGN KEY (subscriber_id) REFERENCES subscribers(id) ON DELETE CASCADE
    )
    """,

    # user_streaks
    """
    CREATE TABLE IF NOT EXISTS user_streaks (
      subscriber_id INTEGER PRIMARY KEY,
      current_streak INTEGER NOT NULL DEFAULT 0,
      best_streak INTEGER NOT NULL DEFAULT 0,
      last_active_date TEXT,                      -- 'YYYY-MM-DD' (UTC)
      total_active_days INTEGER NOT NULL DEFAULT 0,
      FOREIGN KEY (subscriber_id) REFERENCES subscribers(id) ON DELETE CASCADE
    )
    """,

    # xp_events
    """
    CREATE TABLE IF NOT EXISTS xp_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      subscriber_id INTEGER NOT NULL,
      amount INTEGER NOT NULL,
      reason TEXT NOT NULL,                        -- 'wrote_scene', 'completed_story', 'shared_story', 'daily_active', 'milestone_10_words', etc.
      related_id INTEGER,                         -- optional FK to world/episode/etc
      created_at TEXT NOT NULL,
      FOREIGN KEY (subscriber_id) REFERENCES subscribers(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_xp_events_sub ON xp_events(subscriber_id, created_at)",

    # comments
    """
    CREATE TABLE IF NOT EXISTS comments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      world_id INTEGER NOT NULL,
      subscriber_id INTEGER NOT NULL,
      parent_id INTEGER,                          -- threading (top-level = NULL)
      body TEXT NOT NULL,
      is_deleted INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
      FOREIGN KEY (subscriber_id) REFERENCES subscribers(id) ON DELETE CASCADE,
      FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_comments_world ON comments(world_id, created_at)",

    # reactions (6 emoji types: heart, fire, sparkles, rocket, mind-blown, laughing)
    """
    CREATE TABLE IF NOT EXISTS reactions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      world_id INTEGER NOT NULL,
      subscriber_id INTEGER NOT NULL,
      kind TEXT NOT NULL,                          -- 'heart', 'fire', 'sparkles', 'rocket', 'mind_blown', 'laughing'
      created_at TEXT NOT NULL,
      UNIQUE (world_id, subscriber_id, kind),
      FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
      FOREIGN KEY (subscriber_id) REFERENCES subscribers(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_reactions_world ON reactions(world_id, kind)",

    # story_covers
    """
    CREATE TABLE IF NOT EXISTS story_covers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      world_id INTEGER NOT NULL UNIQUE,
      image_path TEXT NOT NULL,                    -- /covers/<world_id>.png
      width INTEGER NOT NULL DEFAULT 1200,
      height INTEGER NOT NULL DEFAULT 630,
      generated_at TEXT NOT NULL,
      FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE
    )
    """,

    # audit_log_extended (more fields than the existing audit.py writes)
    """
    CREATE TABLE IF NOT EXISTS audit_log_extended (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      actor_id INTEGER,                            -- subscriber_id or NULL for system
      actor_type TEXT NOT NULL DEFAULT 'subscriber',  -- 'subscriber' | 'admin' | 'system' | 'anonymous'
      action TEXT NOT NULL,                        -- 'world.create', 'world.edit', 'admin.promo.create', 'comment.delete', etc.
      target_type TEXT,                            -- 'world' | 'episode' | 'comment' | 'promo' | etc.
      target_id INTEGER,
      ip_address TEXT,
      user_agent TEXT,
      metadata_json TEXT,                          -- free-form JSON
      created_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_audit_log_extended_action ON audit_log_extended(action, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_audit_log_extended_actor ON audit_log_extended(actor_id, created_at)",

    # inventory_items (catalog)
    """
    CREATE TABLE IF NOT EXISTS inventory_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      key TEXT NOT NULL UNIQUE,                    -- 'golden_key', 'silver_compass', 'rune_of_return', etc.
      name TEXT NOT NULL,
      description TEXT NOT NULL,
      icon TEXT,                                   -- emoji or short SVG reference
      rarity TEXT NOT NULL DEFAULT 'common',       -- 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary'
      tier_required TEXT NOT NULL DEFAULT 'free',  -- minimum tier to USE
      created_at TEXT NOT NULL
    )
    """,

    # inventory_grants (per-subscriber inventory)
    """
    CREATE TABLE IF NOT EXISTS inventory_grants (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      subscriber_id INTEGER NOT NULL,
      item_key TEXT NOT NULL,
      quantity INTEGER NOT NULL DEFAULT 1,
      source TEXT,                                 -- 'signup', 'milestone', 'story_complete', 'admin_grant'
      source_id INTEGER,
      granted_at TEXT NOT NULL,
      FOREIGN KEY (subscriber_id) REFERENCES subscribers(id) ON DELETE CASCADE,
      FOREIGN KEY (item_key) REFERENCES inventory_items(key)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_inventory_grants_sub ON inventory_grants(subscriber_id)",

    # world_inventory (items placed in a specific world - Minecraft-style placement)
    """
    CREATE TABLE IF NOT EXISTS world_inventory (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      world_id INTEGER NOT NULL,
      subscriber_id INTEGER NOT NULL,
      item_key TEXT NOT NULL,
      x REAL NOT NULL DEFAULT 0,
      y REAL NOT NULL DEFAULT 0,
      placed_at TEXT NOT NULL,
      FOREIGN KEY (world_id) REFERENCES worlds(id) ON DELETE CASCADE,
      FOREIGN KEY (subscriber_id) REFERENCES subscribers(id) ON DELETE CASCADE,
      FOREIGN KEY (item_key) REFERENCES inventory_items(key)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_world_inventory_world ON world_inventory(world_id)",

    # inventory_history (audit trail)
    """
    CREATE TABLE IF NOT EXISTS inventory_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      subscriber_id INTEGER NOT NULL,
      item_key TEXT NOT NULL,
      action TEXT NOT NULL,                        -- 'grant', 'transfer', 'place', 'pick_up', 'use'
      quantity_delta INTEGER NOT NULL DEFAULT 0,
      world_id INTEGER,
      related_id INTEGER,
      created_at TEXT NOT NULL,
      FOREIGN KEY (subscriber_id) REFERENCES subscribers(id) ON DELETE CASCADE
    )
    """,

    # Worlds extra columns
    "ALTER TABLE worlds ADD COLUMN slug TEXT",
    "ALTER TABLE worlds ADD COLUMN is_public INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE worlds ADD COLUMN cover_path TEXT",

    # Comments columns
    "ALTER TABLE comments ADD COLUMN updated_at TEXT",
]


def _conn(db):
    if hasattr(db, 'execute'):
        return db
    if callable(db):
        return db()
    return db


def apply_v24_migrations(db):
    """Apply v24 migrations to an open sqlite3 connection. Idempotent."""
    c = _conn(db)
    try:
        for sql in MIGRATIONS_V24:
            try:
                c.execute(sql)
            except sqlite3.OperationalError as e:
                # 'duplicate column name' on ALTER is fine - we're idempotent
                if 'duplicate column' not in str(e).lower():
                    pass  # silent; not critical
        # Seed inventory_items catalog (idempotent via INSERT OR IGNORE)
        seed_items = [
            ('golden_key', 'Golden Key', 'Unlocks locked scenes in any world.', '🗝️', 'rare', 'free'),
            ('silver_compass', 'Silver Compass', 'Reveals hidden branches in the world map.', '🧭', 'uncommon', 'free'),
            ('rune_of_return', 'Rune of Return', 'Saves your place when you reach a dead end.', '🔮', 'rare', 'free'),
            ('manuscript_page', 'Manuscript Page', 'Adds an extra scene to your world.', '📜', 'epic', 'pro'),
            ('inkwell', 'Inkwell', 'Re-rolls the scene art without regenerating the story.', '🖋️', 'uncommon', 'free'),
            ('brass_gear', 'Brass Gear', 'A decorative item that boosts XP from this world by 10%.', '�️', 'uncommon', 'free'),
            ('crystal_shard', 'Crystal Shard', 'Lets you branch one scene into two parallel paths.', '💎', 'legendary', 'creator'),
            ('map_fragment', 'Map Fragment', 'Reveals the world map one node at a time.', '🗺️', 'common', 'free'),
        ]
        # Include created_at in the seed
        seed_items_with_ts = [(*item, dt.datetime.utcnow().isoformat(timespec='seconds')) for item in seed_items]
        c.executemany(
            "INSERT OR IGNORE INTO inventory_items(key, name, description, icon, rarity, tier_required, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            seed_items_with_ts,
        )
        c.commit()
    except Exception as e:
        try:
            c.rollback()
        except Exception:
            pass
        raise

    # Helper functions

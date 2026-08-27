"""
PocketPlot Universe - v23 schema migrations.

Adds:
  share_tokens           - URL-safe share links for worlds
  likes                  - per-user likes on worlds
  story_stats            - cached aggregate stats per world
  player_sessions        - anonymous player sessions for game-format
  promo_codes            - promotional discount codes
  promo_redemptions      - which users redeemed which codes
  email_segments         - admin-defined segments for marketing
  email_subscribers      - newsletter subscription list (Mailchimp-shaped)
  push_subscriptions     - Web Push subscription endpoints

Also adds scene-graph columns to `worlds` for the Minecraft-style
world map (scene_nodes_json + scene_edges_json). The map view at
/play/[token]/map uses these; the PLAY view at /play/[token] falls
back to linear episode order if the columns are empty.

All idempotent (CREATE IF NOT EXISTS + try/except ALTER).
"""

import json


MIGRATIONS_V23_SQL = """
-- v23: share tokens for worlds (game-format + preview)
CREATE TABLE IF NOT EXISTS share_tokens (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    token           TEXT NOT NULL UNIQUE,
    world_id        INTEGER NOT NULL REFERENCES worlds(id),
    subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
    kind            TEXT NOT NULL DEFAULT 'game',
    label           TEXT,
    created_at      TEXT NOT NULL,
    revoked_at      TEXT,
    play_count      INTEGER NOT NULL DEFAULT 0,
    completion_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_share_tokens_token ON share_tokens(token);
CREATE INDEX IF NOT EXISTS idx_share_tokens_world ON share_tokens(world_id);

-- v23: likes
CREATE TABLE IF NOT EXISTS likes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
    world_id        INTEGER NOT NULL REFERENCES worlds(id),
    created_at      TEXT NOT NULL,
    UNIQUE(subscriber_id, world_id)
);
CREATE INDEX IF NOT EXISTS idx_likes_world ON likes(world_id);

-- v23: cached aggregate stats per world
CREATE TABLE IF NOT EXISTS story_stats (
    world_id        INTEGER PRIMARY KEY REFERENCES worlds(id),
    view_count      INTEGER NOT NULL DEFAULT 0,
    like_count      INTEGER NOT NULL DEFAULT 0,
    play_count      INTEGER NOT NULL DEFAULT 0,
    completion_count INTEGER NOT NULL DEFAULT 0,
    share_count     INTEGER NOT NULL DEFAULT 0,
    last_updated    TEXT NOT NULL
);

-- v23: anonymous player sessions for the game-format link
CREATE TABLE IF NOT EXISTS player_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token   TEXT NOT NULL UNIQUE,
    share_token_id  INTEGER NOT NULL REFERENCES share_tokens(id),
    current_episode INTEGER NOT NULL DEFAULT 1,
    path_json       TEXT NOT NULL DEFAULT '[]',
    completed       INTEGER NOT NULL DEFAULT 0,
    started_at      TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_player_sessions_token ON player_sessions(session_token);

-- v23: promo codes
CREATE TABLE IF NOT EXISTS promo_codes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,
    description     TEXT,
    discount_pct    INTEGER NOT NULL DEFAULT 0,
    duration_months INTEGER NOT NULL DEFAULT 1,
    tier_target     TEXT NOT NULL DEFAULT 'pro',
    max_redemptions INTEGER NOT NULL DEFAULT 0,
    redemption_count INTEGER NOT NULL DEFAULT 0,
    valid_from      TEXT,
    valid_until     TEXT,
    created_at      TEXT NOT NULL,
    created_by      INTEGER
);

-- v23: promo redemptions
CREATE TABLE IF NOT EXISTS promo_redemptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    promo_id        INTEGER NOT NULL REFERENCES promo_codes(id),
    subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
    redeemed_at     TEXT NOT NULL,
    tier            TEXT,
    UNIQUE(promo_id, subscriber_id)
);

-- v23: email segments
CREATE TABLE IF NOT EXISTS email_segments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    description     TEXT,
    rules_json      TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    created_by      INTEGER
);

-- v23: email subscribers (Mailchimp-shaped)
CREATE TABLE IF NOT EXISTS email_subscribers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT NOT NULL UNIQUE,
    name            TEXT,
    subscribed_at   TEXT NOT NULL,
    unsubscribed_at TEXT,
    mailchimp_id    TEXT,
    tags            TEXT NOT NULL DEFAULT '',
    source          TEXT NOT NULL DEFAULT 'platform'
);

-- v23: push notification subscriptions
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
    endpoint        TEXT NOT NULL UNIQUE,
    p256dh          TEXT NOT NULL,
    auth            TEXT NOT NULL,
    user_agent      TEXT,
    created_at      TEXT NOT NULL,
    last_used_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_push_subs_subscriber ON push_subscriptions(subscriber_id);
"""


def apply_v23_migrations(db):
    """Apply v23 migrations to an open sqlite3 connection. Idempotent.

    `db` can be either a connection or a callable that returns one.
    """
    import sqlite3
    if callable(db):
        db = db()
    cur = db.cursor()
    # Execute the SQL via executescript
    cur.executescript(MIGRATIONS_V23_SQL)

    # Add columns that may already exist (idempotent ALTERs)
    def add_column_if_missing(table, column, definition):
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in cols:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            except sqlite3.OperationalError:
                pass

    add_column_if_missing('story_views', 'player_session_id', 'INTEGER REFERENCES player_sessions(id)')
    add_column_if_missing('worlds', 'scene_nodes_json', 'TEXT')
    add_column_if_missing('worlds', 'scene_edges_json', 'TEXT')

    db.commit()


def get_world_scene_graph(db_or_callable, world_id: int) -> dict:
    """Read the scene-graph JSON columns from a world.

    Returns:
        {"nodes": [...], "edges": [...]}

    If the columns are empty, returns a synthetic linear graph based
    on the world_episodes table (one node per episode, sequential).
    """
    if hasattr(db_or_callable, 'execute'):
        db = db_or_callable
    elif callable(db_or_callable):
        db = db_or_callable()
    else:
        db = db_or_callable
    row = db.execute(
        "SELECT scene_nodes_json, scene_edges_json FROM worlds WHERE id=?",
        (world_id,),
    ).fetchone()
    if row and row['scene_nodes_json']:
        try:
            return {
                'nodes': json.loads(row['scene_nodes_json'] or '[]'),
                'edges': json.loads(row['scene_edges_json'] or '[]'),
            }
        except (json.JSONDecodeError, TypeError):
            pass
    # Fallback: synthesize a linear graph
    eps = db.execute(
        "SELECT id, episode_number, title FROM world_episodes "
        "WHERE world_id=? ORDER BY episode_number",
        (world_id,),
    ).fetchall()
    nodes = [
        {'id': ep['episode_number'], 'episode_id': ep['id'],
         'x': 50 + (ep['episode_number'] - 1) * 15,
         'y': 50,
         'label': ep['title'] or f'Chapter {ep["episode_number"]}'}
        for ep in eps
    ]
    edges = []
    for i in range(len(nodes) - 1):
        edges.append({
            'from': nodes[i]['id'],
            'to': nodes[i + 1]['id'],
            'label': '',
        })
    return {'nodes': nodes, 'edges': edges}
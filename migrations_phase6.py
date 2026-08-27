"""Phase 6-10 schema migrations. Run inside init_db() to add all new
tables and columns needed for: avatars, gamification (streaks/badges/word
score), story packs, weekly insights.

Idempotent — uses CREATE TABLE IF NOT EXISTS + try/except on ALTER.
"""
MIGRATIONS = r"""
-- v10 (Phase 6): Avatar (Pro)
ALTER TABLE subscribers ADD COLUMN avatar_json TEXT;
ALTER TABLE subscribers ADD COLUMN avatar_updated_at TEXT;

-- v10 (Phase 7): Gamification — streak tracking
-- Single row per (subscriber, calendar_date) where they had at least one
-- engagement (story-read OR game-play). UNIQUE prevents double-counting
-- if both signals fire on the same day.
CREATE TABLE IF NOT EXISTS daily_engagements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
    engagement_date TEXT NOT NULL,        -- ISO date "YYYY-MM-DD"
    source          TEXT NOT NULL,         -- "story_read" | "game_play"
    created_at      TEXT NOT NULL,
    UNIQUE(subscriber_id, engagement_date)
);
CREATE INDEX IF NOT EXISTS daily_eng_sub ON daily_engagements(subscriber_id, engagement_date DESC);

-- Word Vault: one row per (subscriber, word). UNIQUE so we count each word once.
CREATE TABLE IF NOT EXISTS word_vault (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
    word            TEXT NOT NULL,
    word_tier       TEXT,
    word_definition TEXT,
    learned_at      TEXT NOT NULL,
    UNIQUE(subscriber_id, word)
);
CREATE INDEX IF NOT EXISTS word_vault_sub ON word_vault(subscriber_id, learned_at DESC);

-- Badges awarded to subscribers.
CREATE TABLE IF NOT EXISTS badges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
    badge_code      TEXT NOT NULL,         -- "first_story", "week_1", etc.
    awarded_at      TEXT NOT NULL,
    UNIQUE(subscriber_id, badge_code)
);

-- v10 (Phase 8): Story Packs — one-time-purchase / theme-of-month content.
CREATE TABLE IF NOT EXISTS story_packs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    price_usd   INTEGER NOT NULL,    -- cents (e.g. 499 = $4.99). 0 = free/Pro-included.
    theme       TEXT NOT NULL,       -- 'dinosaurs','space','magic','underwater'
    character_pool_json TEXT,        -- optional override of CHARACTERS names
    setting_pool_json   TEXT,        -- optional override of SETTINGS
    problem_pool_json   TEXT,        -- optional override of PROBLEMS (index-aligned with resolutions)
    is_pro_bonus INTEGER NOT NULL DEFAULT 0,   -- 1 = free for Pro (theme of the month)
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL
);

-- Track which subs "own" which packs.
CREATE TABLE IF NOT EXISTS subscriber_packs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
    pack_id         INTEGER NOT NULL REFERENCES story_packs(id),
    acquired_at     TEXT NOT NULL,
    UNIQUE(subscriber_id, pack_id)
);

-- Pro theme-of-the-month rotation: which pack is "free" for Pro subs
-- in a given month. Read by the night generator.
CREATE TABLE IF NOT EXISTS monthly_theme (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    year_month  TEXT NOT NULL,       -- "YYYY-MM"
    pack_id     INTEGER NOT NULL REFERENCES story_packs(id),
    UNIQUE(year_month)
);
"""

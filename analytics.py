"""
PocketPlot Universe — Story Analytics (v17).

Per-tier analytics for stories and users. Pro + Creator tiers see
their own stats; admins see the top-N view/read leaderboards.

Privacy: viewer_hash is a SHA256 of the (subscriber_id + world_id +
daily_salt) so we can de-dupe per-day views without storing the
viewer identity itself.
"""
import datetime as dt
import hashlib
import logging

log = logging.getLogger("pocketplot.analytics")

_DAILY_SALT = "pocketplot-v17-daily"


def _today() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%d")


def _now() -> str:
    return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def viewer_hash_for(subscriber_id: int, world_id: int, day: str = None) -> str:
    """Return a privacy-preserving daily view token."""
    day = day or _today()
    raw = f"{subscriber_id}|{world_id}|{day}|{_DAILY_SALT}".encode()
    return hashlib.sha256(raw).hexdigest()[:32]


# ---- write paths ----

def record_view(db, world_id: int, *, episode_id: int = None,
                  viewer_subscriber_id: int = None, source: str = "me") -> None:
    """Record a story view. Idempotent per (viewer, world, day)."""
    try:
        conn = db()
        # Bump the world view count
        conn.execute(
            "UPDATE worlds SET view_count = view_count + 1 WHERE id=?",
            (world_id,),
        )
        if episode_id:
            conn.execute(
                "UPDATE world_episodes SET view_count = view_count + 1 "
                "WHERE id=?",
                (episode_id,),
            )
        # Log the per-day view (de-duped per viewer)
        if viewer_subscriber_id is not None:
            vh = viewer_hash_for(viewer_subscriber_id, world_id)
            existing = conn.execute(
                "SELECT 1 FROM story_views WHERE world_id=? AND viewer_hash=? "
                "AND substr(viewed_at, 1, 10)=?",
                (world_id, vh, _today()),
            ).fetchone()
            if existing:
                conn.close()
                return
            conn.execute(
                "INSERT INTO story_views(world_id, episode_id, viewer_hash, "
                "viewed_at, source) VALUES (?, ?, ?, ?, ?)",
                (world_id, episode_id, vh, _now(), source),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning("record_view failed: %s", e)


def record_read(db, world_id: int, episode_id: int, *,
                  reader_subscriber_id: int = None,
                  duration_seconds: int = 0) -> None:
    """Record a completed episode read."""
    try:
        conn = db()
        conn.execute(
            "UPDATE world_episodes SET read_count = read_count + 1 "
            "WHERE id=?",
            (episode_id,),
        )
        conn.execute(
            "UPDATE worlds SET read_count = read_count + 1 WHERE id=?",
            (world_id,),
        )
        if reader_subscriber_id is not None:
            rh = viewer_hash_for(reader_subscriber_id, world_id)
            conn.execute(
                "INSERT INTO story_reads(world_id, episode_id, reader_hash, "
                "completed, duration_seconds, read_at) "
                "VALUES (?, ?, ?, 1, ?, ?)",
                (world_id, episode_id, rh, duration_seconds, _now()),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning("record_read failed: %s", e)


# ---- read paths ----

def world_stats(db, world_id: int) -> dict:
    """Aggregate stats for a single world."""
    conn = db()
    world = conn.execute(
        "SELECT view_count, read_count FROM worlds WHERE id=?",
        (world_id,),
    ).fetchone()
    if not world:
        conn.close()
        return {}
    episodes = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(view_count), 0) AS views, "
        "COALESCE(SUM(read_count), 0) AS reads FROM world_episodes "
        "WHERE world_id=?",
        (world_id,),
    ).fetchone()
    # Reading time estimate: ~200 words/minute, average episode ~400 words
    avg_words_per_episode = 400
    reading_minutes = max(1, int((episodes["n"] * avg_words_per_episode) / 200))
    conn.close()
    return {
        "view_count":   int(world["view_count"] or 0),
        "read_count":   int(world["read_count"] or 0),
        "episode_count": int(episodes["n"] or 0),
        "episode_views": int(episodes["views"] or 0),
        "episode_reads": int(episodes["reads"] or 0),
        "reading_minutes": reading_minutes,
    }


def subscriber_stats(db, subscriber_id: int) -> dict:
    """Aggregate stats across all the subscriber's worlds."""
    conn = db()
    worlds = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(view_count), 0) AS v, "
        "COALESCE(SUM(read_count), 0) AS r FROM worlds WHERE subscriber_id=?",
        (subscriber_id,),
    ).fetchone()
    words_row = conn.execute(
        "SELECT COALESCE(SUM(LENGTH(body) - LENGTH(REPLACE(body, ' ', ''))), 0) AS approx "
        "FROM world_episodes e JOIN worlds w ON e.world_id=w.id "
        "WHERE w.subscriber_id=?",
        (subscriber_id,),
    ).fetchone()
    # Approx words from length-difference isn't reliable; use a 5-chars-per-word
    # heuristic across episode body lengths.
    raw_row = conn.execute(
        "SELECT COALESCE(SUM(LENGTH(body)), 0) AS chars "
        "FROM world_episodes e JOIN worlds w ON e.world_id=w.id "
        "WHERE w.subscriber_id=?",
        (subscriber_id,),
    ).fetchone()
    approx_words = max(0, int((raw_row["chars"] or 0) / 6))
    conn.close()
    return {
        "world_count":    int(worlds["n"] or 0),
        "total_views":    int(worlds["v"] or 0),
        "total_reads":    int(worlds["r"] or 0),
        "approx_words":   approx_words,
    }


def top_stories(db, limit: int = 10) -> list:
    """Top-N stories by view count. Used by /admin/top."""
    conn = db()
    rows = conn.execute(
        "SELECT w.id, w.title, w.genre, w.tone, w.view_count, w.read_count, "
        "w.subscriber_id, s.email, s.child_name "
        "FROM worlds w LEFT JOIN subscribers s ON w.subscriber_id=s.id "
        "ORDER BY w.view_count DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Milestones ----

MILESTONES = [
    {"id": "first_story", "words": 1, "label": "First Story"},
    {"id": "10_words",    "words": 10,    "label": "10 Words"},
    {"id": "100_words",   "words": 100,   "label": "100 Words"},
    {"id": "1000_words",  "words": 1000,  "label": "1,000 Words"},
    {"id": "10000_words", "words": 10000, "label": "10,000 Words"},
]


def check_milestones(db, subscriber_id: int) -> list:
    """Return list of newly-achieved milestones (not previously recorded)."""
    conn = db()
    stats = subscriber_stats(db, subscriber_id)
    achieved_now = []
    for ms in MILESTONES:
        if stats["approx_words"] >= ms["words"]:
            existing = conn.execute(
                "SELECT 1 FROM user_milestones WHERE subscriber_id=? AND milestone=?",
                (subscriber_id, ms["id"]),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO user_milestones(subscriber_id, milestone, achieved_at) "
                    "VALUES (?, ?, ?)",
                    (subscriber_id, ms["id"], _now()),
                )
                achieved_now.append(ms)
    conn.commit()
    conn.close()
    return achieved_now


def has_feature(db, key: str) -> bool:
    """Check if a feature flag is enabled. Returns True if the flag doesn't
    exist (open by default for new features)."""
    try:
        conn = db()
        row = conn.execute(
            "SELECT enabled FROM feature_flags WHERE key=?",
            (key,),
        ).fetchone()
        conn.close()
        return bool(row["enabled"]) if row else True
    except Exception:
        return True


def set_feature(db, key: str, enabled: bool, *, actor: str = "admin") -> None:
    """Toggle a feature flag."""
    conn = db()
    conn.execute(
        "INSERT OR REPLACE INTO feature_flags(key, enabled, updated_at, updated_by) "
        "VALUES (?, ?, ?, ?)",
        (key, 1 if enabled else 0, _now(), actor),
    )
    conn.commit()
    conn.close()


def list_features(db) -> list:
    """All feature flags, sorted by key."""
    conn = db()
    rows = conn.execute(
        "SELECT key, enabled, description, updated_at, updated_by "
        "FROM feature_flags ORDER BY key"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

"""
PocketPlot — Gamification (Phase 7)

Tracks three engagement signals:
  - Streak: consecutive calendar days a child had at least one engagement
    (story-read OR game-play). One engagement per day counts; we don't
    double-count if both happen on the same day.
  - Word Vault: every unique word a subscriber learns gets one row. We
    count rows for the "Word Score" badge.
  - Badges: awarded on milestones. Idempotent — a subscriber gets each
    badge at most once.

We DO NOT retroactively award badges for actions taken before this code
shipped. The first nightly run after this code deploys starts the streak
from whatever the subscriber did THAT day (or empty if nothing).
"""
import datetime as dt
import json
import logging

log = logging.getLogger("pocketplot.gamification")


# ---- Badge definitions. Order matters: checked in this order when
# evaluating "what badges does this subscriber now qualify for?" ----
BADGES = [
    {
        "code":  "first_story",
        "label": "First Story Read",
        "icon":  "📖",
        "rule":  lambda stats: stats["stories_sent"] >= 1,
    },
    {
        "code":  "week_1",
        "label": "Week 1 Wonder",
        "icon":  "🌟",
        "rule":  lambda stats: stats["streak_days"] >= 7,
    },
    {
        "code":  "ten_words",
        "label": "10 Words Learned",
        "icon":  "📚",
        "rule":  lambda stats: stats["word_count"] >= 10,
    },
    {
        "code":  "twentyfive_words",
        "label": "25 Words Learned",
        "icon":  "🌱",
        "rule":  lambda stats: stats["word_count"] >= 25,
    },
    {
        "code":  "fifty_words",
        "label": "50 Words Learned",
        "icon":  "🌳",
        "rule":  lambda stats: stats["word_count"] >= 50,
    },
    {
        "code":  "streak_3",
        "label": "Streak Keeper (3 days)",
        "icon":  "🔥",
        "rule":  lambda stats: stats["streak_days"] >= 3,
    },
    {
        "code":  "streak_14",
        "label": "Fortnight Friend (14 days)",
        "icon":  "🏅",
        "rule":  lambda stats: stats["streak_days"] >= 14,
    },
    {
        "code":  "first_game",
        "label": "First Adventure Played",
        "icon":  "🎮",
        "rule":  lambda stats: stats["game_plays"] >= 1,
    },
]


# ---- Engagement recording (called from story-send + game-finish) ----

def record_engagement(db, subscriber_id: int, source: str) -> bool:
    """Record an engagement event for the subscriber's streak.

    `source` is one of "story_read", "game_play". One row per (sub, day)
    thanks to the UNIQUE constraint — we silently ignore the second
    engagement of the same day (whether same source or different).

    Returns True if a NEW day row was created (caller can use this to
    decide whether to award streak-related badges).
    """
    today = dt.date.today().isoformat()
    conn = db()
    try:
        conn.execute(
            "INSERT INTO daily_engagements(subscriber_id, engagement_date, source, created_at) "
            "VALUES(?, ?, ?, ?)",
            (subscriber_id, today, source, dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"),
        )
        conn.commit()
        return True
    except Exception as e:
        # Likely the UNIQUE constraint — already recorded today.
        if "UNIQUE" in str(e).upper() or "unique" in str(e).lower():
            return False
        log.warning("record_engagement failed for sub %s: %s", subscriber_id, e)
        return False
    finally:
        conn.close()


def record_word(db, subscriber_id: int, word: str, tier: str = "",
                definition: str = "") -> bool:
    """Add a word to the vault. Returns True if NEW (not already there).
    Caller can use this to award the next-tier word badge."""
    if not word:
        return False
    conn = db()
    try:
        conn.execute(
            "INSERT INTO word_vault(subscriber_id, word, word_tier, word_definition, learned_at) "
            "VALUES(?, ?, ?, ?, ?)",
            (subscriber_id, word.strip().lower(), tier, definition,
             dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"),
        )
        conn.commit()
        return True
    except Exception as e:
        if "UNIQUE" in str(e).upper() or "unique" in str(e).lower():
            return False
        log.warning("record_word failed for sub %s: %s", subscriber_id, e)
        return False
    finally:
        conn.close()


# ---- Streak math ----

def compute_streak(db, subscriber_id: int) -> int:
    """Return the consecutive-day streak ending today (or yesterday — if
    the subscriber hasn't engaged today yet, we still credit the streak
    through yesterday so a 'haven't read yet today' doesn't reset the
    counter visibly. If the gap from yesterday is > 1 day, streak is 0.
    """
    conn = db()
    rows = conn.execute(
        "SELECT DISTINCT engagement_date FROM daily_engagements "
        "WHERE subscriber_id=? ORDER BY engagement_date DESC LIMIT 365",
        (subscriber_id,),
    ).fetchall()
    conn.close()
    if not rows:
        return 0
    days = [dt.date.fromisoformat(r[0]) for r in rows]
    today = dt.date.today()
    # The most recent engagement day. If today, streak is alive; if
    # yesterday, still alive (haven't engaged today yet, but streak
    # hasn't visibly broken).
    if days[0] == today:
        anchor = today
    elif days[0] == today - dt.timedelta(days=1):
        anchor = today - dt.timedelta(days=1)
    else:
        return 0
    streak = 1
    cursor = anchor
    for d in days[1:]:
        cursor = cursor - dt.timedelta(days=1)
        if d == cursor:
            streak += 1
        else:
            break
    return streak


# ---- Aggregations for the dashboard ----

def stats_for_subscriber(db, subscriber_id: int) -> dict:
    conn = db()
    stories_sent = conn.execute(
        "SELECT COUNT(*) FROM deliveries WHERE subscriber_id=?",
        (subscriber_id,),
    ).fetchone()[0]
    game_plays = conn.execute(
        "SELECT COUNT(*) FROM daily_engagements "
        "WHERE subscriber_id=? AND source='game_play'",
        (subscriber_id,),
    ).fetchone()[0]
    word_count = conn.execute(
        "SELECT COUNT(*) FROM word_vault WHERE subscriber_id=?",
        (subscriber_id,),
    ).fetchone()[0]
    badge_count = conn.execute(
        "SELECT COUNT(*) FROM badges WHERE subscriber_id=?",
        (subscriber_id,),
    ).fetchone()[0]
    conn.close()
    return {
        "stories_sent":  stories_sent,
        "game_plays":     game_plays,
        "word_count":     word_count,
        "badge_count":    badge_count,
        "streak_days":    compute_streak(db, subscriber_id),
    }


def recent_words(db, subscriber_id: int, limit: int = 7) -> list:
    conn = db()
    rows = conn.execute(
        "SELECT word, word_tier, word_definition, learned_at FROM word_vault "
        "WHERE subscriber_id=? ORDER BY learned_at DESC LIMIT ?",
        (subscriber_id, limit),
    ).fetchall()
    conn.close()
    return rows


def earned_badges(db, subscriber_id: int) -> list:
    """Returns a list of badge dicts in display order, joined with the
    `awarded_at` timestamp for each. Badges that haven't been earned yet
    are NOT in the list."""
    earned_codes = set()
    awarded_at = {}
    conn = db()
    for r in conn.execute(
        "SELECT badge_code, awarded_at FROM badges WHERE subscriber_id=?",
        (subscriber_id,),
    ).fetchall():
        earned_codes.add(r[0])
        awarded_at[r[0]] = r[1]
    conn.close()
    out = []
    for b in BADGES:
        if b["code"] in earned_codes:
            out.append({**b, "awarded_at": awarded_at.get(b["code"], "")})
    return out


# ---- Badge award (called after each engagement / word record) ----

def evaluate_and_award(db, subscriber_id: int) -> list:
    """Check which badges the subscriber NOW qualifies for, and award any
    not-yet-earned. Returns the list of newly-awarded badge dicts."""
    stats = stats_for_subscriber(db, subscriber_id)
    earned_codes = set()
    conn = db()
    for r in conn.execute(
        "SELECT badge_code FROM badges WHERE subscriber_id=?",
        (subscriber_id,),
    ).fetchall():
        earned_codes.add(r[0])
    newly = []
    now = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    for b in BADGES:
        if b["code"] in earned_codes:
            continue
        try:
            if b["rule"](stats):
                conn.execute(
                    "INSERT INTO badges(subscriber_id, badge_code, awarded_at) "
                    "VALUES(?, ?, ?)",
                    (subscriber_id, b["code"], now),
                )
                newly.append(b)
        except Exception as e:
            # UNIQUE collision (race): another concurrent process awarded
            # the same badge. Safe to ignore.
            if "UNIQUE" not in str(e).upper() and "unique" not in str(e).lower():
                log.warning("award_badge %s failed: %s", b["code"], e)
    if newly:
        conn.commit()
    conn.close()
    return newly

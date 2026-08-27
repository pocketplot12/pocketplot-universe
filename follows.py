"""
PocketPlot Universe - Social Graph (v17).

Follow/following + notifications. v17 ships the data model + a thin
helper layer. Rich interactions (timeline, suggested follows, activity
feed) are deferred follow-ups.

Public API:
  - is_following(db, follower_id, followee_id) -> bool
  - follow(db, follower_id, followee_id) -> int (follow id)
  - unfollow(db, follower_id, followee_id) -> None
  - follower_count(db, subscriber_id) -> int
  - following_count(db, subscriber_id) -> int
  - notifications(db, recipient_id, kind, title, body=None, link=None)
  - recent_notifications(db, recipient_id, limit=20) -> list
  - mark_notifications_read(db, recipient_id) -> int
  - set_public(db, subscriber_id, is_public) -> None
  - set_username(db, subscriber_id, username) -> bool  # returns False if taken
"""
import datetime as dt
import logging
import re

log = logging.getLogger("pocketplot.follows")


def _now() -> str:
    return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"


# ---- Follows ----

def is_following(db, follower_id: int, followee_id: int) -> bool:
    if follower_id == followee_id:
        return False
    conn = db()
    row = conn.execute(
        "SELECT 1 FROM follows WHERE follower_id=? AND followee_id=?",
        (follower_id, followee_id),
    ).fetchone()
    conn.close()
    return bool(row)


def follow(db, follower_id: int, followee_id: int) -> int:
    if follower_id == followee_id:
        return 0
    conn = db()
    cur = conn.execute(
        "INSERT OR IGNORE INTO follows(follower_id, followee_id, created_at) "
        "VALUES (?, ?, ?)",
        (follower_id, followee_id, _now()),
    )
    fid = cur.lastrowid
    conn.commit()
    conn.close()
    return fid


def unfollow(db, follower_id: int, followee_id: int) -> None:
    conn = db()
    conn.execute(
        "DELETE FROM follows WHERE follower_id=? AND followee_id=?",
        (follower_id, followee_id),
    )
    conn.commit()
    conn.close()


def follower_count(db, subscriber_id: int) -> int:
    conn = db()
    n = conn.execute(
        "SELECT COUNT(*) AS n FROM follows WHERE followee_id=?",
        (subscriber_id,),
    ).fetchone()["n"]
    conn.close()
    return int(n)


def following_count(db, subscriber_id: int) -> int:
    conn = db()
    n = conn.execute(
        "SELECT COUNT(*) AS n FROM follows WHERE follower_id=?",
        (subscriber_id,),
    ).fetchone()["n"]
    conn.close()
    return int(n)


def followers(db, subscriber_id: int, limit: int = 100) -> list:
    conn = db()
    rows = conn.execute(
        "SELECT s.id, s.email, s.child_name, s.username, f.created_at "
        "FROM follows f JOIN subscribers s ON f.follower_id=s.id "
        "WHERE f.followee_id=? ORDER BY f.created_at DESC LIMIT ?",
        (subscriber_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def following(db, subscriber_id: int, limit: int = 100) -> list:
    conn = db()
    rows = conn.execute(
        "SELECT s.id, s.email, s.child_name, s.username, f.created_at "
        "FROM follows f JOIN subscribers s ON f.followee_id=s.id "
        "WHERE f.follower_id=? ORDER BY f.created_at DESC LIMIT ?",
        (subscriber_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- Notifications ----

def notify(db, recipient_id: int, kind: str, title: str,
             body: str = None, link: str = None) -> int:
    conn = db()
    cur = conn.execute(
        "INSERT INTO notifications(recipient_id, kind, title, body, link, "
        "created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (recipient_id, kind, title, body, link, _now()),
    )
    nid = cur.lastrowid
    conn.commit()
    conn.close()
    return nid


def recent_notifications(db, recipient_id: int, limit: int = 20) -> list:
    conn = db()
    rows = conn.execute(
        "SELECT id, kind, title, body, link, is_read, created_at "
        "FROM notifications WHERE recipient_id=? "
        "ORDER BY created_at DESC LIMIT ?",
        (recipient_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_notifications_read(db, recipient_id: int) -> int:
    conn = db()
    cur = conn.execute(
        "UPDATE notifications SET is_read=1 WHERE recipient_id=? AND is_read=0",
        (recipient_id,),
    )
    conn.commit()
    conn.close()
    return cur.rowcount or 0


def unread_count(db, recipient_id: int) -> int:
    conn = db()
    n = conn.execute(
        "SELECT COUNT(*) AS n FROM notifications WHERE recipient_id=? AND is_read=0",
        (recipient_id,),
    ).fetchone()["n"]
    conn.close()
    return int(n)


# ---- Public profile + username ----

USERNAME_RE = re.compile(r"^[a-z0-9_-]{3,24}$")


def set_username(db, subscriber_id: int, username: str) -> bool:
    """Set the public handle. Returns False if invalid or taken."""
    u = (username or "").strip().lower()
    if not USERNAME_RE.match(u):
        return False
    conn = db()
    try:
        conn.execute(
            "UPDATE subscribers SET username=? WHERE id=?",
            (u, subscriber_id),
        )
        if conn.execute(
            "SELECT changes() AS n",
        ).fetchone()["n"] == 0:
            conn.close()
            return False
        conn.commit()
    except Exception as e:
        # unique constraint violation = taken
        log.info("username '%s' taken: %s", u, e)
        conn.close()
        return False
    conn.close()
    return True


def set_public(db, subscriber_id: int, is_public: bool) -> None:
    conn = db()
    conn.execute(
        "UPDATE subscribers SET is_public=? WHERE id=?",
        (1 if is_public else 0, subscriber_id),
    )
    conn.commit()
    conn.close()


def set_featured_stories(db, subscriber_id: int, world_ids: list) -> bool:
    """Set the user's featured-stories list (max 3)."""
    if not isinstance(world_ids, list):
        return False
    if len(world_ids) > 3:
        world_ids = world_ids[:3]
    import json as _json
    conn = db()
    conn.execute(
        "UPDATE subscribers SET featured_story_ids=? WHERE id=?",
        (_json.dumps(world_ids), subscriber_id),
    )
    conn.commit()
    conn.close()
    return True


def get_featured_stories(db, subscriber_id: int) -> list:
    import json as _json
    conn = db()
    row = conn.execute(
        "SELECT featured_story_ids FROM subscribers WHERE id=?",
        (subscriber_id,),
    ).fetchone()
    conn.close()
    if not row:
        return []
    try:
        return _json.loads(row["featured_story_ids"] or "[]")
    except Exception:
        return []


def lookup_subscriber_by_username(db, username: str) -> dict | None:
    """Public-profile lookup. Returns None if the user doesn't exist
    OR has set is_public=0."""
    conn = db()
    row = conn.execute(
        "SELECT id, username, child_name, is_public, created_at "
        "FROM subscribers WHERE username=? AND is_public=1",
        (username,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_public_worlds_for(db, subscriber_id: int, limit: int = 12) -> list:
    """Public worlds owned by this subscriber, newest first."""
    conn = db()
    rows = conn.execute(
        "SELECT * FROM worlds WHERE subscriber_id=? AND is_public=1 "
        "ORDER BY last_played_at DESC LIMIT ?",
        (subscriber_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

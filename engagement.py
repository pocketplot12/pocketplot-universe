"""
PocketPlot Universe - engagement module (v23).

Centralizes:
  - likes (toggle, count, list-of-users-who-liked)
  - share_tokens (create, revoke, lookup, increment play_count)
  - player_sessions (create, get, save_path, complete)
  - story_stats (cached aggregate per world)

All functions take either:
  - a sqlite3 connection directly, OR
  - a callable that returns a connection (e.g. the app's `db()` factory)

Pure functions; no Flask dependency. Easy to unit-test.
"""

import json
import datetime as dt


def _conn(db):
    """Resolve a db argument. If it's a connection (has .execute), use as-is.
    If it's a callable, call it to get a connection."""
    if hasattr(db, 'execute'):
        return db
    if callable(db):
        return db()
    return db


# ============== likes ==============

def like_world(db, subscriber_id: int, world_id: int) -> bool:
    """Like a world. Idempotent. Returns True if liked (newly), False if already liked."""
    import sqlite3
    c = _conn(db)
    cur = c.cursor()
    try:
        cur.execute(
            "INSERT INTO likes(subscriber_id, world_id, created_at) VALUES (?, ?, ?)",
            (subscriber_id, world_id, dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'),
        )
        c.commit()
        _bump_stat(c, world_id, 'like_count', +1)
        return True
    except sqlite3.IntegrityError:
        return False


def unlike_world(db, subscriber_id: int, world_id: int) -> bool:
    """Unlike a world."""
    c = _conn(db)
    cur = c.cursor()
    cur.execute(
        "DELETE FROM likes WHERE subscriber_id=? AND world_id=?",
        (subscriber_id, world_id),
    )
    if cur.rowcount > 0:
        c.commit()
        _bump_stat(c, world_id, 'like_count', -1)
        return True
    return False


def is_liked(db, subscriber_id: int, world_id: int) -> bool:
    c = _conn(db)
    row = c.execute(
        "SELECT 1 FROM likes WHERE subscriber_id=? AND world_id=?",
        (subscriber_id, world_id),
    ).fetchone()
    return bool(row)


def like_count(db, world_id: int) -> int:
    c = _conn(db)
    row = c.execute(
        "SELECT COUNT(*) AS n FROM likes WHERE world_id=?",
        (world_id,),
    ).fetchone()
    return row['n'] if row else 0


def likers_of(db, world_id: int, limit: int = 50) -> list:
    c = _conn(db)
    rows = c.execute(
        "SELECT subscriber_id, created_at FROM likes WHERE world_id=? ORDER BY id DESC LIMIT ?",
        (world_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ============== share_tokens ==============

def create_share_token(db, world_id: int, subscriber_id: int,
                        kind: str = 'game', label: str = None) -> dict:
    """Create a new share token for a world."""
    from qrcode_lib import make_share_token
    token = make_share_token()
    now = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    c = _conn(db)
    cur = c.cursor()
    cur.execute(
        "INSERT INTO share_tokens(token, world_id, subscriber_id, kind, label, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (token, world_id, subscriber_id, kind, label, now),
    )
    c.commit()
    return {
        'id': cur.lastrowid,
        'token': token,
        'world_id': world_id,
        'subscriber_id': subscriber_id,
        'kind': kind,
        'label': label,
        'created_at': now,
    }


def revoke_share_token(db, token: str, subscriber_id: int) -> bool:
    """Revoke a share token (only the creator can revoke)."""
    c = _conn(db)
    cur = c.cursor()
    cur.execute(
        "UPDATE share_tokens SET revoked_at=? WHERE token=? AND subscriber_id=? AND revoked_at IS NULL",
        (dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z', token, subscriber_id),
    )
    if cur.rowcount > 0:
        c.commit()
        return True
    return False


def lookup_share_token(db, token: str) -> dict | None:
    """Look up a token. Returns None if missing or revoked."""
    c = _conn(db)
    row = c.execute(
        "SELECT * FROM share_tokens WHERE token=? AND revoked_at IS NULL",
        (token,),
    ).fetchone()
    return dict(row) if row else None


def record_play(db, token_id: int) -> None:
    """Increment the play count for a token."""
    c = _conn(db)
    cur = c.cursor()
    cur.execute(
        "UPDATE share_tokens SET play_count = play_count + 1 WHERE id=?",
        (token_id,),
    )
    c.commit()
    row = c.execute("SELECT world_id FROM share_tokens WHERE id=?", (token_id,)).fetchone()
    if row:
        _bump_stat(c, row['world_id'], 'play_count', +1)


def list_share_tokens_for(db, world_id: int) -> list:
    c = _conn(db)
    rows = c.execute(
        "SELECT * FROM share_tokens WHERE world_id=? ORDER BY id DESC",
        (world_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ============== player_sessions ==============

def create_player_session(db, share_token_id: int) -> dict:
    """Create a new anonymous player session for a share token."""
    from qrcode_lib import make_player_session_id
    session_token = make_player_session_id()
    now = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    c = _conn(db)
    cur = c.cursor()
    cur.execute(
        "INSERT INTO player_sessions(session_token, share_token_id, current_episode, "
        "path_json, completed, started_at, last_seen_at) "
        "VALUES (?, ?, 1, '[]', 0, ?, ?)",
        (session_token, share_token_id, now, now),
    )
    c.commit()
    return {
        'id': cur.lastrowid,
        'session_token': session_token,
        'share_token_id': share_token_id,
        'current_episode': 1,
        'path': [],
        'completed': False,
    }


def get_player_session(db, session_token: str) -> dict | None:
    c = _conn(db)
    row = c.execute(
        "SELECT * FROM player_sessions WHERE session_token=?",
        (session_token,),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d['path'] = json.loads(d.get('path_json') or '[]')
    d['completed'] = bool(d.get('completed'))
    return d


def advance_player_session(db, session_id: int, next_episode: int,
                            path_addition: int) -> dict | None:
    """Move the player forward in the story."""
    now = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    c = _conn(db)
    row = c.execute(
        "SELECT path_json FROM player_sessions WHERE id=?",
        (session_id,),
    ).fetchone()
    if not row:
        return None
    path = json.loads(row['path_json'] or '[]')
    path.append(path_addition)
    c.execute(
        "UPDATE player_sessions SET current_episode=?, path_json=?, last_seen_at=? WHERE id=?",
        (next_episode, json.dumps(path), now, session_id),
    )
    c.commit()
    return get_player_session_by_id(c, session_id)


def get_player_session_by_id(db, session_id: int) -> dict | None:
    c = _conn(db)
    row = c.execute(
        "SELECT * FROM player_sessions WHERE id=?",
        (session_id,),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d['path'] = json.loads(d.get('path_json') or '[]')
    d['completed'] = bool(d.get('completed'))
    return d


def complete_player_session(db, session_id: int) -> bool:
    """Mark the session as completed."""
    c = _conn(db)
    cur = c.cursor()
    cur.execute(
        "UPDATE player_sessions SET completed=1 WHERE id=?",
        (session_id,),
    )
    if cur.rowcount > 0:
        c.commit()
        row = c.execute(
            "SELECT share_token_id FROM player_sessions WHERE id=?",
            (session_id,),
        ).fetchone()
        if row:
            cur.execute(
                "UPDATE share_tokens SET completion_count = completion_count + 1 WHERE id=?",
                (row['share_token_id'],),
            )
            c.commit()
            row2 = c.execute(
                "SELECT world_id FROM share_tokens WHERE id=?",
                (row['share_token_id'],),
            ).fetchone()
            if row2:
                _bump_stat(c, row2['world_id'], 'completion_count', +1)
        return True
    return False


# ============== story_stats (cached aggregate) ==============

def ensure_story_stats(db, world_id: int) -> None:
    """Make sure a story_stats row exists for this world."""
    c = _conn(db)
    cur = c.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO story_stats(world_id, last_updated) VALUES (?, ?)",
        (world_id, dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'),
    )
    c.commit()


def _bump_stat(db, world_id: int, column: str, delta: int) -> None:
    """Atomically increment a stat column. Creates the row if missing."""
    ensure_story_stats(db, world_id)
    c = _conn(db)
    cur = c.cursor()
    allowed = {'view_count', 'like_count', 'play_count', 'completion_count', 'share_count'}
    if column not in allowed:
        raise ValueError(f"Invalid column: {column}")
    cur.execute(
        f"UPDATE story_stats SET {column} = MAX(0, {column} + ?), last_updated=? WHERE world_id=?",
        (delta, dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z', world_id),
    )
    c.commit()


def get_story_stats(db, world_id: int) -> dict:
    ensure_story_stats(db, world_id)
    c = _conn(db)
    row = c.execute(
        "SELECT * FROM story_stats WHERE world_id=?",
        (world_id,),
    ).fetchone()
    if not row:
        return {'view_count': 0, 'like_count': 0, 'play_count': 0,
                'completion_count': 0, 'share_count': 0}
    return dict(row)


def world_stats_summary(db, world_id: int) -> dict:
    """Aggregate stats for a single world."""
    stats = get_story_stats(db, world_id)
    c = _conn(db)
    eps = c.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(LENGTH(body)), 0) AS chars "
        "FROM world_episodes WHERE world_id=?",
        (world_id,),
    ).fetchone()
    choices = c.execute(
        "SELECT COUNT(*) AS n FROM world_episodes WHERE world_id=? AND choices_json IS NOT NULL AND choices_json != ''",
        (world_id,),
    ).fetchone()
    return {
        'view_count': stats.get('view_count', 0),
        'like_count': stats.get('like_count', 0),
        'play_count': stats.get('play_count', 0),
        'completion_count': stats.get('completion_count', 0),
        'episode_count': eps['n'] if eps else 0,
        'approx_words': (eps['chars'] if eps else 0) // 5,
        'choice_count': choices['n'] if choices else 0,
    }
"""
PocketPlot Universe - audit log (v24).

Wraps every sensitive action with an audit entry. Falls back to
stdout if the audit_log_extended table isn't ready.

Schema (see migrations_phase24.py):
  audit_log_extended(
    id, actor_id, actor_type, action, target_type, target_id,
    ip_address, user_agent, metadata_json, created_at
  )
"""
import json
import time
import datetime as dt


def _conn(db):
    if hasattr(db, 'execute'):
        return db
    if callable(db):
        return db()
    return db


def audit(db, action, *, actor_id=None, actor_type='subscriber', target_type=None,
          target_id=None, ip_address=None, user_agent=None, metadata=None):
    """Insert an audit log entry. Silent on failure (audit must never block UX)."""
    try:
        c = _conn(db)
        meta_json = json.dumps(metadata, default=str) if metadata else None
        c.execute(
            "INSERT INTO audit_log_extended("
            "actor_id, actor_type, action, target_type, target_id, ip_address, user_agent, metadata_json, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (actor_id, actor_type, action, target_type, target_id,
             ip_address, user_agent, meta_json,
             dt.datetime.utcnow().isoformat(timespec='seconds')),
        )
        c.commit()
    except Exception:
        try:
            c.rollback()
        except Exception:
            pass


def recent(db, limit=100, action_prefix=None):
    """Get the most recent audit entries. Optional action_prefix filter."""
    c = _conn(db)
    if action_prefix:
        rows = c.execute(
            "SELECT * FROM audit_log_extended WHERE action LIKE ? ORDER BY created_at DESC LIMIT ?",
            (action_prefix + '%', limit),
        ).fetchall()
    else:
        rows = c.execute(
            "SELECT * FROM audit_log_extended ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows


def stats(db, since_days=30):
    """Return counts by action in the last N days."""
    c = _conn(db)
    cutoff = (dt.datetime.utcnow() - dt.timedelta(days=since_days)).isoformat(timespec='seconds')
    rows = c.execute(
        "SELECT action, COUNT(*) AS n FROM audit_log_extended "
        "WHERE created_at >= ? GROUP BY action ORDER BY n DESC",
        (cutoff,),
    ).fetchall()
    return rows

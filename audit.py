"""
PocketPlot Universe — Audit log helper (v13).

Tiny module that wraps every important admin/subscriber/system action
with an audit row. Failures here are silent — the audit log must never
break the action it's logging.

Schema (migrations_phase11.py):
  audit_log(
    id, actor_id, actor_type, action, target_type, target_id,
    metadata_json, ip, user_agent, created_at
  )
"""
import datetime as dt
import json
import logging

log = logging.getLogger("pocketplot.audit")


def _now() -> str:
    return dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def record(db, actor_id: int = None, actor_type: str = "system",
           action: str = "unknown", target_type: str = None,
           target_id: int = None, metadata: dict = None,
           ip: str = None, user_agent: str = None) -> None:
    """Persist one audit row. Silent on DB failure."""
    try:
        conn = db()
        conn.execute(
            "INSERT INTO audit_log(actor_id, actor_type, action, "
            "target_type, target_id, metadata_json, ip, user_agent, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (actor_id, actor_type, action, target_type, target_id,
             json.dumps(metadata or {}), ip, user_agent, _now()),
        )
        conn.commit(); conn.close()
    except Exception as e:
        log.warning("audit_log insert failed: %s", e)


def recent(db, limit: int = 200, action_prefix: str = None):
    """Return the most recent audit rows (admin dashboard)."""
    conn = db()
    if action_prefix:
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE action LIKE ? ORDER BY id DESC LIMIT ?",
            (action_prefix + "%", limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return rows


def by_target(db, target_type: str, target_id: int, limit: int = 50):
    conn = db()
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE target_type=? AND target_id=? "
        "ORDER BY id DESC LIMIT ?",
        (target_type, target_id, limit),
    ).fetchall()
    conn.close()
    return rows


# ---- Feature requests (used by /roadmap) ----

def list_feature_requests(db, status: str = None, limit: int = 100):
    conn = db()
    if status:
        rows = conn.execute(
            "SELECT id, title, description, votes, status, "
            "submitter_email, created_at, updated_at FROM feature_requests "
            "WHERE status=? ORDER BY votes DESC, id DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, description, votes, status, "
            "submitter_email, created_at, updated_at FROM feature_requests "
            "ORDER BY votes DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return rows


def add_feature_request(db, title: str, description: str = "",
                          submitter_email: str = None) -> int:
    conn = db()
    cur = conn.execute(
        "INSERT INTO feature_requests(title, description, submitter_email, created_at) "
        "VALUES (?, ?, ?, ?)",
        (title[:200], description or "", submitter_email, _now()),
    )
    rid = cur.lastrowid
    conn.commit(); conn.close()
    return rid


def vote_feature_request(db, feature_id: int) -> int:
    conn = db()
    conn.execute(
        "UPDATE feature_requests SET votes = votes + 1, updated_at=? WHERE id=?",
        (_now(), feature_id),
    )
    row = conn.execute("SELECT votes FROM feature_requests WHERE id=?", (feature_id,)).fetchone()
    conn.commit(); conn.close()
    return int(row["votes"]) if row else 0


# ---- Contact messages (used by /contact) ----

def save_contact_message(db, email: str, subject: str, body: str,
                            ip: str = None) -> int:
    conn = db()
    cur = conn.execute(
        "INSERT INTO contact_messages(email, subject, body, ip, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (email[:200], subject[:200], body[:5000], ip, _now()),
    )
    mid = cur.lastrowid
    conn.commit(); conn.close()
    return mid


def list_contact_messages(db, limit: int = 100):
    conn = db()
    rows = conn.execute(
        "SELECT * FROM contact_messages ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return rows

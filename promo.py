"""
PocketPlot Universe - promo codes + admin segmentation (v23).

Promo codes:
  - Admins create codes with discount_pct + duration_months + tier_target
  - Users redeem codes at checkout or via /redeem
  - Each code has max_redemptions (0 = unlimited)
  - Each user can only redeem a given code once
  - Optional valid_from / valid_until windows

Admin segmentation:
  - Email segments are named queries (rules_json) that match users
  - Used for newsletter blasts, admin-targeted emails, etc.
"""

import json
import datetime as dt
import secrets
import string


def _conn(db):
    """Resolve a db argument. Connection -> use as-is; callable -> call it."""
    if hasattr(db, 'execute'):
        return db
    if callable(db):
        return db()
    return db


# ============== promo_codes ==============

def _normalize_code(code: str) -> str:
    """Normalize a promo code to uppercase ASCII alphanumeric."""
    return ''.join(c for c in code.upper() if c.isalnum())


def create_promo_code(db, code: str, discount_pct: int, duration_months: int = 1,
                      max_redemptions: int = 0, tier_target: str = 'pro',
                      description: str = '', valid_from: str = None,
                      valid_until: str = None, created_by: int = None) -> dict:
    """Create a promo code. Raises ValueError if the code already exists."""
    import sqlite3
    code = _normalize_code(code)
    if not (1 <= discount_pct <= 100):
        raise ValueError(f"discount_pct must be 1-100, got {discount_pct}")
    now = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    c = _conn(db)
    try:
        cur = c.cursor()
        cur.execute(
            "INSERT INTO promo_codes(code, description, discount_pct, duration_months, "
            "tier_target, max_redemptions, valid_from, valid_until, created_at, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (code, description, discount_pct, duration_months, tier_target,
             max_redemptions, valid_from, valid_until, now, created_by),
        )
        c.commit()
    except sqlite3.IntegrityError:
        raise ValueError(f"promo code '{code}' already exists")
    return {
        'id': cur.lastrowid,
        'code': code,
        'description': description,
        'discount_pct': discount_pct,
        'duration_months': duration_months,
        'tier_target': tier_target,
        'max_redemptions': max_redemptions,
        'valid_from': valid_from,
        'valid_until': valid_until,
    }


def list_promo_codes(db, limit: int = 50) -> list:
    c = _conn(db)
    rows = c.execute(
        "SELECT * FROM promo_codes ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def lookup_promo(db, code: str) -> dict | None:
    code = _normalize_code(code)
    c = _conn(db)
    row = c.execute(
        "SELECT * FROM promo_codes WHERE code=?",
        (code,),
    ).fetchone()
    return dict(row) if row else None


def is_promo_valid(promo: dict) -> tuple[bool, str]:
    """Returns (valid, reason)."""
    if not promo:
        return False, "Code not found"
    if promo['max_redemptions'] and promo['redemption_count'] >= promo['max_redemptions']:
        return False, "Code has reached its maximum redemptions"
    now = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    if promo['valid_from'] and now < promo['valid_from']:
        return False, "Code is not yet active"
    if promo['valid_until'] and now > promo['valid_until']:
        return False, "Code has expired"
    return True, ""


def redeem_promo(db, code: str, subscriber_id: int, tier: str = None) -> dict:
    """Redeem a promo code for a subscriber."""
    promo = lookup_promo(db, code)
    valid, reason = is_promo_valid(promo)
    if not valid:
        raise ValueError(reason)
    c = _conn(db)
    cur = c.cursor()
    cur.execute(
        "SELECT id FROM promo_redemptions WHERE promo_id=? AND subscriber_id=?",
        (promo['id'], subscriber_id),
    )
    if cur.fetchone():
        raise ValueError("You've already redeemed this code")
    now = dt.datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    cur.execute(
        "INSERT INTO promo_redemptions(promo_id, subscriber_id, redeemed_at, tier) VALUES (?, ?, ?, ?)",
        (promo['id'], subscriber_id, now, tier or promo['tier_target']),
    )
    cur.execute(
        "UPDATE promo_codes SET redemption_count = redemption_count + 1 WHERE id=?",
        (promo['id'],),
    )
    c.commit()
    return {
        'promo_id': promo['id'],
        'code': promo['code'],
        'discount_pct': promo['discount_pct'],
        'duration_months': promo['duration_months'],
        'tier_target': promo['tier_target'],
        'redeemed_at': now,
    }


# ============== Email segmentation ==============

def create_segment(db, name: str, rules: dict, description: str = '',
                   created_by: int = None) -> dict:
    """Create a named user segment."""
    c = _conn(db)
    cur = c.cursor()
    cur.execute(
        "INSERT INTO email_segments(name, description, rules_json, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?)",
        (name, description, json.dumps(rules), dt.datetime.utcnow().isoformat() + 'Z', created_by),
    )
    c.commit()
    return {'id': cur.lastrowid, 'name': name, 'rules': rules}


def list_segments(db, limit: int = 50) -> list:
    c = _conn(db)
    rows = c.execute(
        "SELECT * FROM email_segments ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def resolve_segment(db, segment_id: int) -> list:
    """Resolve a segment to the list of subscriber dicts that match its rules."""
    c = _conn(db)
    seg = c.execute(
        "SELECT * FROM email_segments WHERE id=?",
        (segment_id,),
    ).fetchone()
    if not seg:
        return []
    rules = json.loads(seg['rules_json'])
    where = []
    params = []
    if 'plan' in rules or 'tier' in rules:
        plan = rules.get('plan') or rules.get('tier')
        where.append("s.plan=?")
        params.append(plan)
    if 'tier_in' in rules:
        placeholders = ",".join("?" * len(rules['tier_in']))
        where.append(f"s.plan IN ({placeholders})")
        params.extend(rules['tier_in'])
    if 'active' in rules:
        where.append("s.active=?")
        params.append(1 if rules['active'] else 0)
    if 'created_within_days' in rules:
        cutoff = (dt.datetime.utcnow() - dt.timedelta(days=rules['created_within_days'])).isoformat() + 'Z'
        where.append("s.created_at >= ?")
        params.append(cutoff)
    joins = ""
    if 'has_worlds_min' in rules:
        joins = " JOIN (SELECT subscriber_id, COUNT(*) AS n FROM worlds GROUP BY subscriber_id) w ON w.subscriber_id = s.id"
        where.append("w.n >= ?")
        params.append(rules['has_worlds_min'])
    if 'view_count_min' in rules:
        joins += " LEFT JOIN (SELECT subscriber_id, COUNT(*) AS n FROM story_views GROUP BY subscriber_id) v ON v.subscriber_id = s.id"
        where.append("COALESCE(v.n, 0) >= ?")
        params.append(rules['view_count_min'])
    sql = f"SELECT s.id, s.email, s.child_name, s.plan FROM subscribers s{joins}"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " LIMIT 500"
    rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def subscribe_email(db, email: str, name: str = "", source: str = 'platform',
                     tags: str = '') -> bool:
    """Subscribe an address to email_subscribers (newsletter). Idempotent."""
    import sqlite3
    c = _conn(db)
    cur = c.cursor()
    now = dt.datetime.utcnow().isoformat() + 'Z'
    try:
        cur.execute(
            "INSERT INTO email_subscribers(email, name, subscribed_at, source, tags) VALUES (?, ?, ?, ?)",
            (email, name, now, source, tags),
        )
        c.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def unsubscribe_email(db, email: str) -> bool:
    c = _conn(db)
    cur = c.cursor()
    cur.execute(
        "UPDATE email_subscribers SET unsubscribed_at=? WHERE email=? AND unsubscribed_at IS NULL",
        (dt.datetime.utcnow().isoformat() + 'Z', email),
    )
    if cur.rowcount > 0:
        c.commit()
        return True
    return False
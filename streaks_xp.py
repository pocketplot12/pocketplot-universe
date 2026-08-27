"""
PocketPlot Universe - streaks + XP module (v24).

Tracks:
  - user_streaks (current/best streak, last_active_date, total_active_days)
  - xp_events (immutable ledger of every XP gain)

XP rules (per event):
  - 'wrote_scene'             : 10 XP
  - 'completed_story'         : 50 XP
  - 'shared_story'            : 20 XP
  - 'first_like'              : 5 XP
  - 'daily_active'            : 5 XP (once per day)
  - 'milestone_10_words'      : 50 XP
  - 'milestone_100_words'     : 200 XP
  - 'milestone_1000_words'    : 500 XP
  - 'milestone_10000_words'   : 2000 XP
  - 'streak_7_days'           : 100 XP
  - 'streak_30_days'          : 500 XP
  - 'streak_100_days'         : 2000 XP

Streak rules:
  - A day counts as active if the user performed ANY XP-eligible action that day.
  - Current streak: consecutive days ending today (or yesterday if today not yet active).
  - Best streak: max(current, historical max).
"""
import datetime as dt


def _conn(db):
    if hasattr(db, 'execute'):
        return db
    if callable(db):
        return db()
    return db


# XP per event reason
XP_REWARDS = {
    'wrote_scene': 10,
    'completed_story': 50,
    'shared_story': 20,
    'first_like': 5,
    'daily_active': 5,
    'milestone_10_words': 50,
    'milestone_100_words': 200,
    'milestone_1000_words': 500,
    'milestone_10000_words': 2000,
    'streak_7_days': 100,
    'streak_30_days': 500,
    'streak_100_days': 2000,
}


def _today_str():
    return dt.datetime.utcnow().strftime('%Y-%m-%d')


def ensure_streak_row(db, subscriber_id):
    """Create a user_streaks row if missing."""
    c = _conn(db)
    cur = c.execute("SELECT subscriber_id FROM user_streaks WHERE subscriber_id=?",
                    (subscriber_id,)).fetchone()
    if not cur:
        c.execute("INSERT INTO user_streaks(subscriber_id) VALUES (?)", (subscriber_id,))
        c.commit()


def award_xp(db, subscriber_id, reason, related_id=None):
    """Award XP for a reason. Returns (xp_amount, new_total_xp).

    Also bumps the streak if today is a new active day.
    """
    if reason not in XP_REWARDS:
        return 0, _total_xp(db, subscriber_id)
    xp = XP_REWARDS[reason]
    c = _conn(db)
    ensure_streak_row(db, subscriber_id)
    c.execute(
        "INSERT INTO xp_events(subscriber_id, amount, reason, related_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (subscriber_id, xp, reason, related_id,
         dt.datetime.utcnow().isoformat(timespec='seconds')),
    )
    # Bump streak
    bump_streak(db, subscriber_id)
    # Auto-trigger streak milestones
    streak = get_streak(db, subscriber_id)
    if streak['current_streak'] >= 7 and streak['current_streak'] < 14:
        # Idempotent: only award 7-day once per crossing
        already = c.execute(
            "SELECT id FROM xp_events WHERE subscriber_id=? AND reason='streak_7_days' LIMIT 1",
            (subscriber_id,),
        ).fetchone()
        if not already:
            c.execute(
                "INSERT INTO xp_events(subscriber_id, amount, reason, created_at) VALUES (?, ?, ?, ?)",
                (subscriber_id, 100, 'streak_7_days',
                 dt.datetime.utcnow().isoformat(timespec='seconds')),
            )
    if streak['current_streak'] >= 30 and streak['current_streak'] < 37:
        already = c.execute(
            "SELECT id FROM xp_events WHERE subscriber_id=? AND reason='streak_30_days' LIMIT 1",
            (subscriber_id,),
        ).fetchone()
        if not already:
            c.execute(
                "INSERT INTO xp_events(subscriber_id, amount, reason, created_at) VALUES (?, ?, ?, ?)",
                (subscriber_id, 500, 'streak_30_days',
                 dt.datetime.utcnow().isoformat(timespec='seconds')),
            )
    c.commit()
    return xp, _total_xp(db, subscriber_id)


def bump_streak(db, subscriber_id):
    """Update streak based on today. If last_active_date == today: no-op. If yesterday: +1. Else: reset to 1."""
    c = _conn(db)
    ensure_streak_row(db, subscriber_id)
    today = _today_str()
    row = c.execute("SELECT current_streak, best_streak, last_active_date, total_active_days "
                    "FROM user_streaks WHERE subscriber_id=?",
                    (subscriber_id,)).fetchone()
    cur_streak, best, last_date, total_days = row[0], row[1], row[2], row[3]
    if last_date == today:
        # Already counted today
        return
    if last_date is None:
        new_streak = 1
    else:
        try:
            last_dt = dt.datetime.strptime(last_date, '%Y-%m-%d').date()
            today_dt = dt.datetime.strptime(today, '%Y-%m-%d').date()
            delta = (today_dt - last_dt).days
        except Exception:
            delta = 99
        if delta == 1:
            new_streak = cur_streak + 1
        else:
            new_streak = 1  # broken streak
    best = max(best, new_streak)
    c.execute(
        "UPDATE user_streaks SET current_streak=?, best_streak=?, last_active_date=?, "
        "total_active_days = total_active_days + 1 WHERE subscriber_id=?",
        (new_streak, best, today, subscriber_id),
    )


def get_streak(db, subscriber_id):
    """Return dict with streak info."""
    c = _conn(db)
    ensure_streak_row(db, subscriber_id)
    row = c.execute("SELECT current_streak, best_streak, last_active_date, total_active_days "
                    "FROM user_streaks WHERE subscriber_id=?",
                    (subscriber_id,)).fetchone()
    return {
        'current_streak': row[0],
        'best_streak': row[1],
        'last_active_date': row[2],
        'total_active_days': row[3],
    }


def _total_xp(db, subscriber_id):
    c = _conn(db)
    row = c.execute("SELECT COALESCE(SUM(amount), 0) FROM xp_events WHERE subscriber_id=?",
                    (subscriber_id,)).fetchone()
    return row[0] or 0


def get_stats(db, subscriber_id):
    """Return user-friendly stats: total_xp, level (XP/100), streak, today_xp."""
    c = _conn(db)
    streak = get_streak(db, subscriber_id)
    total = _total_xp(db, subscriber_id)
    today = dt.datetime.utcnow().strftime('%Y-%m-%d')
    today_row = c.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM xp_events WHERE subscriber_id=? AND created_at LIKE ?",
        (subscriber_id, today + '%'),
    ).fetchone()
    return {
        'total_xp': total,
        'level': total // 100,
        'today_xp': today_row[0] or 0,
        **streak,
    }

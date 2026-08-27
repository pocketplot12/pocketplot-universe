"""Phase 4 — Review Queue helpers (independent module).

Functions for queueing, listing, approving, rejecting, and sending reviewed
stories. Imported by app.py via `import review_queue`.
"""
import datetime as dt
import json
import logging

log = logging.getLogger("pocketplot.queue")


def queue_story(db, sub_id, story, hero_svg, word, questions,
                moment_text, parent_guide, audio_filename, poll_question,
                seed):
    """Persist a freshly-generated story to the review queue. Returns the queue id."""
    conn = db()
    cur = conn.execute(
        """INSERT INTO review_queue
           (subscriber_id, kind, status, story_json, hero_svg, word_json,
            questions_json, moment_text, parent_guide, audio_filename,
            poll_question, seed, created_at)
           VALUES (?, 'story', 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sub_id,
         json.dumps(story, ensure_ascii=False),
         hero_svg or "",
         json.dumps(word, ensure_ascii=False) if word else "",
         json.dumps(questions, ensure_ascii=False) if questions else "",
         moment_text or "",
         parent_guide or "",
         audio_filename or "",
         poll_question or "",
         int(seed) if seed else 0,
         dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"),
    )
    qid = cur.lastrowid
    conn.commit()
    conn.close()
    log.info("queued story id=%d for sub=%d (seed=%s)", qid, sub_id, seed)
    return qid


def list_queue(db, status=None, sub_id=None, limit=50, offset=0):
    """Return queue items, newest first. Optional filters."""
    conn = db()
    where, params = [], []
    if status:
        where.append("q.status = ?"); params.append(status)
    if sub_id:
        where.append("q.subscriber_id = ?"); params.append(sub_id)
    sql = ("""SELECT q.*, s.email, s.child_name, s.plan, s.pro_tier
             FROM review_queue q
             JOIN subscribers s ON s.id = q.subscriber_id
             {where}
             ORDER BY q.created_at DESC
             LIMIT ? OFFSET ?""").format(
        where=("WHERE " + " AND ".join(where)) if where else ""
    )
    params += [limit, offset]
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


def get_queue_item(db, qid):
    conn = db()
    row = conn.execute(
        """SELECT q.*, s.email, s.child_name, s.plan, s.pro_tier, s.child_age
           FROM review_queue q
           JOIN subscribers s ON s.id = q.subscriber_id
           WHERE q.id = ?""",
        (qid,),
    ).fetchone()
    conn.close()
    return row


def approve_queue_item(db, qid, note=""):
    conn = db()
    conn.execute(
        "UPDATE review_queue SET status='approved', reviewed_at=?, reviewer_note=? WHERE id=? AND status='pending'",
        (dt.datetime.utcnow().isoformat(timespec="seconds") + "Z", note, qid),
    )
    conn.commit()
    conn.close()


def reject_queue_item(db, qid, note=""):
    conn = db()
    conn.execute(
        "UPDATE review_queue SET status='rejected', reviewed_at=?, reviewer_note=? WHERE id=? AND status='pending'",
        (dt.datetime.utcnow().isoformat(timespec="seconds") + "Z", note, qid),
    )
    conn.commit()
    conn.close()


def queue_counts(db):
    conn = db()
    counts = {}
    for status in ("pending", "approved", "rejected", "sent"):
        counts[status] = conn.execute(
            "SELECT COUNT(*) FROM review_queue WHERE status=?", (status,)
        ).fetchone()[0]
    counts["total"] = sum(counts.values())
    conn.close()
    return counts

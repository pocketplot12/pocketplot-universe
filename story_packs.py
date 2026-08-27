"""
PocketPlot — Story Packs (Phase 9)

Adds a 'theme of the month' mechanic for Pro subscribers. Each pack is a
small catalog override — a themed set of (character_pool, setting_pool,
problem_pool) that the night generator uses when the active monthly theme
matches the subscriber.

For now, this is the simpler 'rotating theme of the month' path the user
asked for (not one-time Stripe purchases — that's Phase 2). Pro subscribers
get the active month's pack automatically; the rotation is admin-driven.

The data model is in migrations_phase6.py (story_packs + subscriber_packs +
monthly_theme tables).
"""
import datetime as dt
import json
import logging

log = logging.getLogger("pocketplot.packs")


# ---- Default seed packs. The admin can add more via /admin. We seed the
# four starter packs here so a fresh install has something to rotate. ----
DEFAULT_PACKS = [
    {
        "name":        "Dinosaurs",
        "description": "Misty volcanoes, ferns, and one very small dino who's not so sure about being small.",
        "theme":       "dinosaurs",
        "characters":  ["Fern", "Pippa", "Clementine", "Otto", "Bramwell"],
        "settings":    ["Misty volcano clearing", "Fern valley at dawn", "Cave of echoes"],
        "problems":    ["Being the smallest in a very big family", "A noise in the dark", "Wanting to roar louder than you can"],
    },
    {
        "name":        "Space",
        "description": "A small spaceship, a very large sky, and a friend who keeps forgetting their helmet.",
        "theme":       "space",
        "characters":  ["Vivi", "Theo", "Clementine", "Felix", "Wren"],
        "settings":    ["A small spaceship cabin", "Moonlit crater", "Comet station"],
        "problems":    ["Missing home", "A noise the radio can't explain", "Being the slowest in the flight crew"],
    },
    {
        "name":        "Magic",
        "description": "A tiny spell book, a cat who is unhelpful on purpose, and one small wonder a day.",
        "theme":       "magic",
        "characters":  ["Hazel", "Pippa", "Bramwell", "Vivi", "Felix"],
        "settings":    ["Attic full of treasures", "Lantern garden at dusk", "Library of small spells"],
        "problems":    ["A spell that won't quite work", "The cat hid the wrong thing", "Magic that only works on Tuesdays"],
    },
    {
        "name":        "Underwater",
        "description": "A kelp forest, a polite octopus, and the art of being very, very still.",
        "theme":       "underwater",
        "characters":  ["Wren", "Felix", "Hazel", "Bram", "Otto"],
        "settings":    ["Kelp forest at low tide", "Coral garden", "Shipwreck library"],
        "problems":    ["The current won't sit still", "A noise the whales can't explain", "Running out of goodbyes"],
    },
]


def seed_default_packs(db) -> int:
    """Insert DEFAULT_PACKS into story_packs if they aren't already there.
    Returns the number of new packs created."""
    conn = db()
    existing = {r["theme"] for r in conn.execute("SELECT theme FROM story_packs").fetchall()}
    now = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    inserted = 0
    for pack in DEFAULT_PACKS:
        if pack["theme"] in existing:
            continue
        conn.execute(
            "INSERT INTO story_packs(name, description, price_usd, theme, "
            "character_pool_json, setting_pool_json, problem_pool_json, "
            "is_pro_bonus, active, created_at) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (pack["name"], pack["description"], 0, pack["theme"],
             json.dumps(pack["characters"]),
             json.dumps(pack["settings"]),
             json.dumps(pack["problems"]),
             1,  # all starter packs are Pro bonus (free for Pro)
             1, now),
        )
        inserted += 1
    conn.commit(); conn.close()
    return inserted


# ---- Pack access ----

def list_active_packs(db):
    """All currently active packs (used by /me Story Shop)."""
    conn = db()
    rows = conn.execute(
        "SELECT id, name, description, theme, price_usd, is_pro_bonus, active, created_at "
        "FROM story_packs WHERE active=1 ORDER BY id"
    ).fetchall()
    conn.close()
    return rows


def get_pack(db, pack_id: int):
    conn = db()
    row = conn.execute(
        "SELECT * FROM story_packs WHERE id=?", (pack_id,)
    ).fetchone()
    conn.close()
    return row


def get_owned_packs(db, subscriber_id: int):
    """All packs this subscriber has access to. Pro subs automatically get
    `is_pro_bonus=1` packs (via the monthly_theme rotation). One-time
    acquisitions come through subscriber_packs. Returns a list of pack rows."""
    conn = db()
    # Pack IDs they own (one-time)
    owned_ids = [r["pack_id"] for r in conn.execute(
        "SELECT pack_id FROM subscriber_packs WHERE subscriber_id=?",
        (subscriber_id,)
    ).fetchall()]
    # If Pro, also include the active monthly theme pack.
    sub = conn.execute("SELECT plan FROM subscribers WHERE id=?", (subscriber_id,)).fetchone()
    is_pro = (sub and sub["plan"] == "pro")
    if is_pro:
        cur = conn.execute("SELECT pack_id FROM monthly_theme ORDER BY id DESC LIMIT 1").fetchone()
        if cur:
            owned_ids.append(cur["pack_id"])
    if not owned_ids:
        conn.close()
        return []
    placeholders = ",".join(["?"] * len(owned_ids))
    rows = conn.execute(
        f"SELECT * FROM story_packs WHERE id IN ({placeholders}) ORDER BY id",
        owned_ids,
    ).fetchall()
    conn.close()
    return rows


# ---- Active monthly theme (admin-driven rotation) ----

def get_active_monthly_theme(db):
    """Return the pack dict for the active monthly theme, or None if none set."""
    conn = db()
    cur = conn.execute(
        "SELECT pack_id FROM monthly_theme ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not cur:
        conn.close()
        return None
    row = conn.execute("SELECT * FROM story_packs WHERE id=?", (cur["pack_id"],)).fetchone()
    conn.close()
    return row


def set_monthly_theme(db, year_month: str, pack_id: int):
    """Set the active theme pack for a given year-month (e.g. '2026-08').
    Overwrites any previous assignment for that month."""
    conn = db()
    conn.execute(
        "INSERT INTO monthly_theme(year_month, pack_id) VALUES(?, ?) "
        "ON CONFLICT(year_month) DO UPDATE SET pack_id=excluded.pack_id",
        (year_month, pack_id),
    )
    conn.commit(); conn.close()


# ---- Nightly integration: did the active monthly theme pick a pack?
# The nightly generator calls this and, if a pack is active, biases its
# random picks toward that pack's pools. ----

def theme_pack_for_nightly(db, today_iso: str | None = None) -> dict | None:
    """Return the pack dict (with character_pool/setting_pool/problem_pool
    parsed) for the active theme this month, or None if none set."""
    pack = get_active_monthly_theme(db)
    if not pack:
        return None
    out = dict(pack)
    try:
        out["character_pool"] = json.loads(pack["character_pool_json"]) if pack["character_pool_json"] else []
    except Exception:
        out["character_pool"] = []
    try:
        out["setting_pool"] = json.loads(pack["setting_pool_json"]) if pack["setting_pool_json"] else []
    except Exception:
        out["setting_pool"] = []
    try:
        out["problem_pool"] = json.loads(pack["problem_pool_json"]) if pack["problem_pool_json"] else []
    except Exception:
        out["problem_pool"] = []
    return out

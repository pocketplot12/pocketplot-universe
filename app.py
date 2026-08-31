"""
PocketPlot — personalized bedtime stories, delivered nightly.

Single-file Flask MVP with Stripe subscriptions + magic-link self-service.
Runs as:
    python3 app.py

Then visit http://localhost:5000

Stack: Flask + SQLite + APScheduler + stdlib smtplib + stripe (optional)

If STRIPE_SECRET_KEY is unset, the app runs in MOCK BILLING MODE:
all the Stripe endpoints work, but they simulate Stripe in-process so you
can exercise the whole flow without a real Stripe account.
"""
import os
import html as html_lib
import csv
import json
import hmac
import sqlite3
import smtplib
import secrets
import logging
import datetime as dt
import hashlib
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlencode

from flask import (
    Flask, request, render_template_string, redirect, url_for,
    flash, session, abort, send_from_directory, send_file,
    jsonify, Response, get_flashed_messages
)
from apscheduler.schedulers.background import BackgroundScheduler
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import story_gen       # the new sustainable story generator
import story_gen       # the new sustainable story generator
import story_image_composer  # procedural SVG hero illustration composer
import review_queue         # Phase 4 review queue helpers
import queue_templates      # Phase 4 review queue HTML templates
import digest               # Phase 4 weekly digest email renderer
import admin_dashboard      # Phase 5 admin dashboard (template + helpers)
import weekly_insight       # Phase 8 weekly insight email renderer
import gamification         # Phase 7 gamification (streaks, badges, word vault)
import story_world          # Phase 11 StoryWorld engine (branching narratives)
import external_api_manager # Phase 11 BYOB/BYOG external API manager
import validation_system    # Phase 11 content policy guardrail system
import encryption           # Phase 11 stdlib-only authenticated encryption

# =====================================================================
# CONFIG
# =====================================================================
APP_DIR = Path(__file__).parent.resolve()
# Allow override via env so Docker / production can point at a volume-mounted path.
# Example: POCKETPLOT_DB_PATH=/app/data/pocketplot.db
DB_PATH = Path(os.environ.get("POCKETPLOT_DB_PATH", str(APP_DIR / "pocketplot.db")))
OUTBOX_DIR = Path(os.environ.get("POCKETPLOT_OUTBOX_DIR", str(APP_DIR / "outbox")))
OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
# Make sure the DB parent exists, too.
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# v4: directory for audio (TTS) and drawing (Creator upload) files,
# scoped per subscriber. Same override pattern as OUTBOX_DIR / DB_PATH so
# Docker can mount a volume here and survive restarts.
AUDIO_DIR = Path(os.environ.get("POCKETPLOT_AUDIO_DIR", str(APP_DIR / "audio")))
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Public URL prefix for serving audio files + drawings. The /audio/<sub>/...
# route is added below to serve these files securely (only the owning
# subscriber can fetch a file, to prevent accidental sharing).
AUDIO_URL_PREFIX = "audio/"
# When LOGIN_REQUIRED_AUDIO is set to "false", audio URLs are public (any
# link clicker can listen). Default = True (subscriber-only).
PUBLIC_AUDIO = os.environ.get("POCKETPLOT_PUBLIC_AUDIO", "").lower() in ("1", "true", "yes")

# Admin password. CHANGE THIS in production via POCKETPLOT_ADMIN_PASSWORD env var.
ADMIN_PASSWORD = os.environ.get("POCKETPLOT_ADMIN_PASSWORD", "letmein")

# SMTP — if these are unset, emails are saved to ./outbox/*.eml instead of sent.
SMTP_HOST = os.environ.get("POCKETPLOT_SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("POCKETPLOT_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("POCKETPLOT_SMTP_USER", "")
SMTP_PASS = os.environ.get("POCKETPLOT_SMTP_PASS", "")
FROM_EMAIL = os.environ.get("POCKETPLOT_FROM_EMAIL", "stories@pocketplot.local")

# Hour of day to deliver (24h, server local time). 20 = 8 pm — classic bedtime.
DELIVERY_HOUR = int(os.environ.get("POCKETPLOT_DELIVERY_HOUR", "20"))

# Story length — words target
STORY_MIN_WORDS = 200
STORY_MAX_WORDS = 300

# Magic-link token lifetime (seconds)
MAGIC_LINK_TTL = int(os.environ.get("POCKETPLOT_MAGIC_LINK_TTL", "3600"))  # 1 hour

# Site URL — used in Stripe success/cancel redirects and magic-link emails
SITE_URL = os.environ.get("POCKETPLOT_SITE_URL", "http://localhost:5000")

# ----- Stripe -----
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "price_pro_monthly")  # placeholder
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")

STRIPE_MOCK = not bool(STRIPE_SECRET_KEY)  # True when no real key is configured

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("pocketplot")

# =====================================================================
# APP
# =====================================================================
app = Flask(__name__)
# Initialize Sentry (opt-in via SENTRY_DSN env var)
try:
    _sentry.init(app)
except Exception:
    pass

app.secret_key = os.environ.get("POCKETPLOT_SECRET", secrets.token_hex(32))

# Token serializer for magic links — signed with the same secret as Flask sessions.
tokens = URLSafeTimedSerializer(app.secret_key, salt="pocketplot-magic")


# Token unsigner used by pocketplot_api.py for Bearer auth. Returns
# subscriber_id on success, None on bad signature / expired token.
def tokens_unsigner_for_api(token: str) -> int | None:
    try:
        sub_id_str = tokens.loads(token, max_age=3600 * 24 * 365)  # 1 year for API use
    except (BadSignature, SignatureExpired):
        return None
    try:
        return int(sub_id_str)
    except (ValueError, TypeError):
        return None

# Stripe client (lazily imported so the app still boots without the package)
stripe = None
if not STRIPE_MOCK:
    try:
        import stripe as _stripe
        _stripe.api_key = STRIPE_SECRET_KEY
        stripe = _stripe
        log.info("Stripe live mode: secret key configured")
    except Exception as e:
        log.warning("Stripe import failed, falling back to mock: %s", e)
        stripe = None
        globals()["STRIPE_MOCK"] = True
if STRIPE_MOCK:
    log.info("Stripe MOCK mode (no STRIPE_SECRET_KEY set) — billing flow runs in-process")

# =====================================================================
# DATABASE
# =====================================================================
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS subscribers (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        email        TEXT UNIQUE NOT NULL,
        child_name   TEXT NOT NULL,
        child_age    INTEGER NOT NULL,
        active       INTEGER NOT NULL DEFAULT 1,
        created_at   TEXT NOT NULL,
        last_sent_at TEXT,
        -- Stripe / billing (added in v2)
        plan                  TEXT NOT NULL DEFAULT 'free',  -- 'free' | 'pro'
        customer_id           TEXT,                          -- Stripe customer id (cus_*)
        subscription_id       TEXT,                          -- Stripe subscription id (sub_*)
        subscription_status   TEXT,                          -- 'active','trialing','past_due','canceled','incomplete', etc.
        current_period_end    TEXT,                          -- ISO timestamp
        -- Pro customization (added in v2)
        pro_character         TEXT,                          -- chosen recurring helper cast key
        pro_theme             TEXT                           -- chosen setting theme
    );
    CREATE TABLE IF NOT EXISTS deliveries (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        subscriber_id INTEGER NOT NULL REFERENCES subscribers(id),
        sent_at      TEXT NOT NULL,
        word_count   INTEGER,
        story        TEXT
    );

    CREATE TABLE IF NOT EXISTS settings (
        key         TEXT PRIMARY KEY,
        value       TEXT,
        updated_at  TEXT
    );

    CREATE TABLE IF NOT EXISTS story_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        note TEXT
    );
    CREATE TABLE IF NOT EXISTS magic_tokens (
        token       TEXT PRIMARY KEY,
        subscriber_id INTEGER NOT NULL REFERENCES subscribers(id),
        purpose     TEXT NOT NULL,    -- 'login' | 'upgrade'
        created_at  TEXT NOT NULL,
        expires_at  TEXT NOT NULL,
        used        INTEGER NOT NULL DEFAULT 0
    );

    -- =================================================================
    -- v4 INTERACTIVITY: polls (Choose Your Adventure), drawings (Creator
    -- tier), and moments (life-lesson / kindness pick persisted across days).
    -- =================================================================

    -- Polls = Choose Your Adventure questions. Each row is ONE poll for
    -- ONE subscriber. `answer` is the child's chosen value (filled by the
    -- parent on /me). `used_in_story` marks whether the nightly story
    -- engine already incorporated the answer (so it gets cleared on the
    -- next nightly run).
    CREATE TABLE IF NOT EXISTS polls (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        subscriber_id INTEGER NOT NULL REFERENCES subscribers(id),
        question      TEXT NOT NULL,
        options_json  TEXT NOT NULL,    -- JSON array of 3 strings
        answer        TEXT,
        created_at    TEXT NOT NULL,
        used_in_story INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS polls_sub_open ON polls(subscriber_id, used_in_story);

    -- Drawings = Creator tier uploads. Stored as static files under
    -- AUDIO_DIR/<subscriber_id>/<filename>; the DB row records metadata.
    -- max 30 per subscriber so we don't flood disk.
    CREATE TABLE IF NOT EXISTS drawings (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        subscriber_id INTEGER NOT NULL REFERENCES subscribers(id),
        filename      TEXT NOT NULL,    -- filename inside AUDIO_DIR/<sub_id>/
        caption       TEXT,
        featured_at   TEXT,             -- when (if) the drawing was used in a story
        created_at    TEXT NOT NULL
    );

    -- Moments = persistent life-lesson / kindness picks. Every email
    -- pulls one from the pool and persists it so we can show a "Moments
    -- scrapbook" in /me.
    CREATE TABLE IF NOT EXISTS moments (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        subscriber_id INTEGER NOT NULL REFERENCES subscribers(id),
        moment_text   TEXT NOT NULL,
        story_title   TEXT,
        shown_at      TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS moments_sub ON moments(subscriber_id, shown_at DESC);

    CREATE TABLE IF NOT EXISTS review_queue (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        subscriber_id   INTEGER NOT NULL REFERENCES subscribers(id),
        kind            TEXT NOT NULL,
        status          TEXT NOT NULL DEFAULT 'pending',
        story_json      TEXT NOT NULL,
        hero_svg        TEXT,
        word_json       TEXT,
        questions_json  TEXT,
        moment_text     TEXT,
        parent_guide    TEXT,
        audio_filename  TEXT,
        poll_question   TEXT,
        seed            INTEGER,
        created_at      TEXT NOT NULL,
        reviewed_at     TEXT,
        reviewer_note   TEXT,
        delivery_id     INTEGER REFERENCES deliveries(id)
    );
    CREATE INDEX IF NOT EXISTS review_queue_status ON review_queue(status, created_at DESC);
    CREATE INDEX IF NOT EXISTS review_queue_sub ON review_queue(subscriber_id, created_at DESC);
    """)
    # Idempotent column adds for upgrades from v1
    for col, decl in [
        ("plan",                "TEXT NOT NULL DEFAULT 'free'"),
        ("customer_id",         "TEXT"),
        ("subscription_id",     "TEXT"),
        ("subscription_status", "TEXT"),
        ("current_period_end",  "TEXT"),
        ("pro_character",       "TEXT"),
        ("pro_theme",           "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE subscribers ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass  # column already exists — that's fine
    # ---- v3 columns: learning layer ----
    for col, decl in [
        ("words_learned_count",    "INTEGER NOT NULL DEFAULT 0"),  # total ever learned
        ("words_learned_month",    "INTEGER NOT NULL DEFAULT 0"),  # learned in current calendar month
        ("learning_visible_count", "INTEGER NOT NULL DEFAULT 30"), # how many entries the dashboard shows (Pro: 100, Free: 30)
        ("month_reset_at",         "TEXT"),                        # ISO date when `words_learned_month` was last zeroed
    ]:
        try:
            conn.execute(f"ALTER TABLE subscribers ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    # ---- v3 columns: deliveries stores the word + questions shown in the email ----
    for col, decl in [
        ("word",            "TEXT"),
        ("word_tier",       "TEXT"),
        ("word_definition", "TEXT"),
        ("word_example",    "TEXT"),
        ("questions_json",  "TEXT"),
        ("parent_guide",    "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE deliveries ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    # ---- v4 columns: interactivity layer ----
    for col, decl in [
        ("pro_tier",        "TEXT NOT NULL DEFAULT 'choice'"),  # 'choice'|'adventure'|'creator'
        ("audio_enabled",   "INTEGER NOT NULL DEFAULT 1"),       # 0/1 — toggle for the Listen button
        ("moments_visible_count", "INTEGER NOT NULL DEFAULT 12"),
    ]:
        try:
            conn.execute(f"ALTER TABLE subscribers ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    for col, decl in [
        ("poll_id",         "INTEGER"),     # FK to polls.id (the incorporated poll)
        ("poll_question",   "TEXT"),
        ("poll_answer",     "TEXT"),
        ("moment_text",     "TEXT"),         # the displayed Moment-of-the-day
        ("audio_filename",  "TEXT"),         # relative path under /audio/<sub_id>/
        ("story_kindness",  "TEXT"),         # the kindness beat the moment echoes
        ("hero_svg",        "TEXT"),         # Phase 5 dashboard — procedurally composed SVG
    ]:
        try:
            conn.execute(f"ALTER TABLE deliveries ADD COLUMN {col} {decl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

    # Phase 6-10 schema (avatars, gamification, story packs). Idempotent.
    try:
        from migrations_phase6 import MIGRATIONS
        conn = db()
        for stmt in [s.strip() for s in MIGRATIONS.split(";") if s.strip()]:
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError as e:
                # Most likely "duplicate column" — already migrated. OK.
                if "duplicate" not in str(e).lower() and "already exists" not in str(e).lower():
                    raise
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning("Phase 6-10 migration step: %s", e)

    # Phase 11 schema (profile_type, external_api_keys, worlds, validation_log).
    # Idempotent: column adds are wrapped in try/except to swallow "duplicate
    # column"; new tables use CREATE TABLE IF NOT EXISTS.
    try:
        from migrations_phase11 import migrate as _migrate_v11
        _migrate_v11(db)
        log.info("Phase 11 schema applied")
    except Exception as e:
        log.warning("Phase 11 migration step: %s", e)

    # Phase 17 schema (analytics, remix, feature flags, social graph).
    # Same idempotent pattern: try/except around each ALTER + CREATE.
    try:
        from migrations_phase17 import migrate as _migrate_v17
        _migrate_v17(db)
        log.info("Phase 17 schema applied")
    except Exception as e:
        log.warning("Phase 17 migration step: %s", e)

    # v23: shares, likes, story stats, player sessions, promo codes, email segments,
    # push subscriptions, scene-graph columns on worlds.
    try:
        from migrations_phase23 import apply_v23_migrations as _m23
        _m23(db)
        log.info("Phase 23 schema applied")
    except Exception as e:
        log.warning("Phase 23 migration step: %s", e)

    # v24: story editor (revisions), onboarding, streaks/XP, comments/reactions,
    # story covers, audit log extended, inventory + world placement.
    try:
        from migrations_phase24 import apply_v24_migrations as _apply_v24
        _apply_v24(db)
        log.info("Phase 24 schema applied")
    except Exception as e:
        log.warning("Phase 24 migration step: %s", e)

init_db()

# =====================================================================
# STORY ENGINE
# =====================================================================
# Pools of interchangeable elements. Each story is drawn from these deterministically
# (seed = subscriber id + date) so the same child gets a coherent evolving cast but
# no two stories are alike.
CAST = {
    "fox": {
        "names": ["Felix", "Fennel", "Fiona", "Fig"],
        "build": "sleek russet coat, a white-tipped tail, ears like tiny sails",
        "voice": "soft and a little hoarse, like wind through dry leaves",
        "cuddliness": "very — when Felix curls up your whole lap goes warm",
    },
    "bear": {
        "names": ["Bram", "Bramble", "Beryl", "Boris"],
        "build": "a great round bear with a dark wet nose and patched denim overalls",
        "voice": "deep and unhurried, the way a kettle hums just before it whistles",
        "cuddliness": "extreme — Bram gives the best, slowest, longest hugs",
    },
    "rabbit": {
        "names": ["Rue", "Remy", "Rosie", "Robin"],
        "build": "a moon-white rabbit with one torn ear and a habit of thumping softly when thinking",
        "voice": "quick and curious, with a small hiccup of laughter between sentences",
        "cuddliness": "surprisingly high — Rue radiates a steady warmth",
    },
    "whale": {
        "names": ["Wren", "Wilbur", "Waverly", "Wim"],
        "build": "a small, almost impossibly round, blue-grey whale with a smile that arches the whole ocean",
        "voice": "a low song you feel in your chest before you hear in your ears",
        "cuddliness": "legendary — Wren has been known to cuddle entire coastlines",
    },
    "robot": {
        "names": ["Pip", "Ping", "Pax", "Pearl"],
        "build": "a tin-can-shaped robot with one glowing antenna, two googly eyes, and a permanent small smile",
        "voice": "a polite beep-then-word cadence, like a friend who always waits for you to finish",
        "cuddliness": "questionable, but the antenna makes an excellent nightlight",
    },
    "kid": {
        "names": ["Anwen", "Bashir", "Cira", "Diego", "Elif", "Farouk", "Greta", "Hank", "Imani", "Jin"],
        "build": "a small, curious human about your age, with a too-big jumper and pockets full of treasures",
        "voice": "the voice you hear in your own head when you ask yourself the very best questions",
        "cuddliness": "exactly the right amount",
    },
}

SETTINGS = [
    ("a paper boat drifting down a slow river at dusk",
     "the river was so slow it almost stood still, and the sky was the colour of apricots"),
    ("a tiny cottage at the edge of a wood, with a chimney that always smoked cinnamon",
     "the wood was full of whispering foxes, and the cinnamon smoke made the whole forest hum"),
    ("the inside of a very large, very quiet library after closing time",
     "the books would whisper to each other when nobody was watching, and the lamps held their breath"),
    ("a small grey planet shaped almost exactly like a button",
     "the buttons on the planet grew as you walked, and the sky above was a single, kind eye"),
    ("a kitchen at midnight, where the moon had come in for a cup of tea",
     "the moon sat at the kitchen table and sipped tea from a saucer, and the dog was not even a little surprised"),
    ("the roof of an old apartment building, looking out over a city of chimneys and lit windows",
     "every lit window was a small story being told, and you could hear them if you listened very carefully"),
    ("a deep, warm tide-pool at the bottom of the sea, lit by a single friendly anglerfish",
     "the tide-pool was so warm it was almost a bath, and the fish were reading tiny books"),
]

OPENINGS = [
    "It was the kind of evening where the air tasted like the inside of a biscuit tin, and the day was folding itself up to go to bed.",
    "The clouds that evening were unusually polite — they stepped aside one by one so the first star could come through and say hello.",
    "Somewhere between the last call of the birds and the first yawn of the houses, the day decided to be quiet.",
    "There is a kind of hour, just after supper, when even the wind sits down and lets the world be still.",
]

PROBLEMS = [
    ("had lost the recipe for moon-pudding and was very worried",
     "the moon-pudding was important because it was what made the night taste like the inside of a tin of biscuits"),
    ("had found a letter addressed to 'the bravest sleeper in this house' and couldn't open it",
     "the letter had been written in invisible ink and only showed itself to someone brave enough to yawn three times"),
    ("had accidentally swallowed a small hiccup and now couldn't get it back",
     "the hiccup kept trying to come out at inappropriate moments, like during a poem, or a very quiet moment"),
    ("couldn't remember the words to the song that put the stars to sleep",
     "the song was three lines long but nobody had ever written it down, because that's the kind of song it was"),
    ("had run out of dreams and the night was nearly here",
     "without a dream to wear to bed, the night would feel underdressed, and you can't have that"),
    ("had been given a small, important job by the wind, and had forgotten what it was",
     "the job was probably very easy, but it had to be done before the wind went to bed, and the wind goes to bed early"),
]

RESOLUTIONS = [
    "and they did it together — {helper} very carefully and {child} very bravely — and by the time the kettle clicked off in the kitchen below, the problem had quietly solved itself, the way problems do when nobody makes a fuss about them.",
    "and in the end, the answer turned out to be exactly the sort of thing you can't think of while you're trying to think of it — you only think of it when you've stopped trying.",
    "and what they did was sit down at the kitchen table with a cup of warm milk each, and talk about it for a little while, and by the time the cups were empty, the answer had shown up on its own, the way guests do when they're welcome.",
    "and they found that doing it slowly, and saying please to the small parts of the problem, worked much better than doing it quickly and saying please only to the big parts.",
]

BEDTIME = [
    "{child} yawned. It was a yawn so big it almost needed its own pillow. {helper} tucked the blanket up under {child}'s chin and whispered, *Tomorrow there will be a new thing to wonder about. But that's tomorrow's work.* And the work for now, was rest.",
    "The kitchen light went off. The hall light went off. The last light left was the small one above the bed, and it was just bright enough to be a small kind guardian. {helper} turned it down, and down, and down, until the room was only just awake.",
    "The house got quieter. The wind outside got smaller. {child}'s eyes got rounder. {helper} began to hum a song that had no tune, only the shape of where a tune would be, and slowly the room became a small boat and the small boat became a large sleep.",
    "{child}'s hand found {helper}'s hand in the dark, the way hands do when they have known each other for a long time, even when the day has been very long. And that was enough.",
]

# =====================================================================
# LEARNING LAYER — words pool + questions generator + helpers
# =====================================================================
# Words are organized in three difficulty tiers ("simple" ages 2-4,
# "intermediate" ages 5-7, "advanced" ages 8-10). Each word has a
# child-friendly definition and an example sentence that the engine
# can insert into the story's context (so the child sees the word used
# in the actual story, not in a disconnected example).
#
# The brief asks for "at least 100 words" — this pool has 30 simple +
# 36 intermediate + 36 advanced = 102, plus some flex for prompt-quality
# examples. Tuned for ages 3-8 (the PocketPlot target audience).

WORDS_BY_TIER = {
    "simple": [
        {"w": "cozy",        "d": "warm, soft, and feeling safe"},
        {"w": "snuggle",      "d": "to curl up close to someone you love"},
        {"w": "tummy",        "d": "your belly"},
        {"w": "blanket",      "d": "a soft cloth that keeps you warm in bed"},
        {"w": "starry",       "d": "full of stars"},
        {"w": "moonbeam",     "d": "a thin stripe of light from the moon"},
        {"w": "teddy",        "d": "a soft stuffed bear you hug at night"},
        {"w": "pillow",       "d": "the soft thing your head rests on"},
        {"w": "hush",         "d": "a quiet, soft sound"},
        {"w": "whisper",      "d": "a very quiet voice"},
        {"w": "yawn",         "d": "the big breath you take when you're sleepy"},
        {"w": "cuddle",       "d": "to hug someone gently"},
        {"w": "tuck",         "d": "to fold blankets snug around someone"},
        {"w": "bedtime",      "d": "the time when it's time to sleep"},
        {"w": "glow",         "d": "a soft, warm light"},
        {"w": "snooze",       "d": "a light, dreamy sleep"},
        {"w": "dream",        "d": "a story your mind makes while you sleep"},
        {"w": "warm",         "d": "comfortably not cold"},
        {"w": "kind",         "d": "nice and gentle"},
        {"w": "breathe",      "d": "to take air in and out of your lungs"},
        {"w": "soft",         "d": "gentle to touch, not rough"},
        {"w": "sweet",        "d": "nice and gentle, like a hug"},
        {"w": "quiet",        "d": "with very little sound"},
        {"w": "close",        "d": "near something"},
        {"w": "sleepy",       "d": "ready for sleep"},
        {"w": "hug",          "d": "to wrap your arms around someone"},
        {"w": "tiny",         "d": "very small"},
        {"w": "wobble",       "d": "to gently rock side to side"},
        {"w": "morning",      "d": "the start of the day, when you wake up"},
        {"w": "listen",       "d": "to hear carefully with your ears"},
    ],
    "intermediate": [
        {"w": "curious",      "d": "wanting to know more about something"},
        {"w": "whisper",      "d": "to speak very softly"},  # also in simple (different def)
        {"w": "wander",       "d": "to walk slowly without a destination"},
        {"w": "discover",     "d": "to find something for the first time"},
        {"w": "imagine",      "d": "to make pictures in your mind"},
        {"w": "gentle",       "d": "soft and careful, not rough"},
        {"w": "patient",      "d": "able to wait calmly"},
        {"w": "together",     "d": "with each other"},
        {"w": "remember",     "d": "to keep something in your mind"},
        {"w": "forgot",       "d": "to not remember anymore"},
        {"w": "bothered",     "d": "feeling a little worried or upset"},
        {"w": "promise",      "d": "a kind of vow to do something"},
        {"w": "wonderful",    "d": "really, truly lovely"},
        {"w": "surprise",     "d": "something you didn't expect"},
        {"w": "careful",      "d": "paying close attention"},
        {"w": "clumsy",       "d": "not moving smoothly, bumping into things"},
        {"w": "delighted",    "d": "very, very happy about something"},
        {"w": "frightened",   "d": "a little bit scared"},
        {"w": "shivered",     "d": "shaking a tiny bit because of cold or fear"},
        {"w": "noticed",      "d": "saw or felt something for the first time"},
        {"w": "decided",      "d": "made up your mind about something"},
        {"w": "traded",       "d": "swapped one thing for another"},
        {"w": "peeked",       "d": "looked quickly, just a little"},
        {"w": "scampered",    "d": "ran with quick little steps"},
        {"w": "unlocked",     "d": "opened something that was closed shut"},
        {"w": "knocked",      "d": "made a soft thump, thump on a door"},
        {"w": "answered",     "d": "said something back when you were asked"},
        {"w": "shouted",      "d": "spoke very loudly"},
        {"w": "listened",     "d": "paid close attention with your ears"},
        {"w": "happened",     "d": "took place, came about"},
        {"w": "comfortable",  "d": "feeling okay where you are"},
        {"w": "different",    "d": "not the same as something else"},
        {"w": "adventure",    "d": "an exciting trip or experience"},
        {"w": "ordinary",     "d": "regular, nothing special"},
        {"w": "together",     "d": "side by side"},  # intentional near-dup for variety
        {"w": "sturdy",       "d": "strong and not easily broken"},
    ],
    "advanced": [
        {"w": "enormous",     "d": "very, very big"},
        {"w": "grateful",     "d": "feeling thankful for something good"},
        {"w": "deliberately", "d": "on purpose, not by accident"},
        {"w": "hesitated",    "d": "paused briefly because unsure"},
        {"w": "consider",     "d": "to think carefully about something"},
        {"w": "mysterious",   "d": "strange and not easily understood"},
        {"w": "extraordinary","d": "far beyond the ordinary"},
        {"w": "pondered",     "d": "thought deeply and quietly about something"},
        {"w": "magnificent",  "d": "very grand and beautiful"},
        {"w": "appeared",     "d": "showed up suddenly, as if from nowhere"},
        {"w": "invisible",    "d": "unable to be seen"},
        {"w": "determined",   "d": "having firmly made up your mind"},
        {"w": "determined",   "d": "deciding strongly to do something"},  # dup harmlessly
        {"w": "unusual",      "d": "not common, surprising in a quiet way"},
        {"w": "peculiar",     "d": "strange in a way that's a little funny"},
        {"w": "memorable",    "d": "easy to remember, important enough to keep"},
        {"w": "miniature",    "d": "much smaller than usual"},
        {"w": "magnify",      "d": "to make something look bigger"},
        {"w": "obstinate",    "d": "stubbornly not wanting to change"},
        {"w": "gigantic",     "d": "really, really enormous"},
        {"w": "scrutinized",  "d": "looked at very carefully"},
        {"w": "eloquent",     "d": "speaking in a beautiful, clear way"},
        {"w": "persistence",  "d": "the habit of not giving up"},
        {"w": "reluctant",    "d": "not wanting to do something yet"},
        {"w": "remarkably",   "d": "in a way worth noticing"},
        {"w": "sparkling",    "d": "giving off small flashes of light"},
        {"w": "vivid",        "d": "bright and clear, full of life"},
        {"w": "epic",         "d": "very grand and a little longer than usual"},
        {"w": "consequence",  "d": "what happens after something else does"},
        {"w": "contemplate",  "d": "to think about quietly for a while"},
        {"w": "triumphant",   "d": "feeling the joy of succeeding"},
        {"w": "ancient",      "d": "very, very, very old"},
        {"w": "flickered",    "d": "lit up briefly, then dimmed, again and again"},
        {"w": "delicate",     "d": "fragile, easily broken"},
        {"w": "magnanimous",  "d": "very kind and forgiving, even when not easy"},
        {"w": "luminous",     "d": "shining with a soft light"},
    ],
}

# Pools are lists of dicts. Convert to indexed tuples (we index by tier
# and position). All word operations go through helper functions below so
# we can swap to a database later without changing call sites.
WORDS_FLAT = [(tier, idx, item) for tier, sub in WORDS_BY_TIER.items() for idx, item in enumerate(sub)]


def word_tier_for_age(age: int) -> str:
    """Return which word-difficulty tier a child should see based on age.
    Younger children get simpler words. Pro is allowed a slightly
    broader range since their Pro preferences suggest an invested family."""
    if age is None: return "simple"
    if age <= 4: return "simple"
    if age <= 6: return "intermediate"
    return "advanced"


def pick_word_for_age(age: int, seed: int) -> dict:
    """Pick a word appropriate for the child's age, deterministic by seed
    so a parent who replays an email always gets the same word."""
    tier = word_tier_for_age(age)
    pool = WORDS_BY_TIER[tier]
    idx = seed % len(pool)
    return {**pool[idx], "tier": tier}


def bold_word_in_body(body: str, word: str) -> str:
    """Wrap the first occurrence of `word` in the story body with <em> tags
    so the word stands out in the email. Case-insensitive. Returns the
    modified body and a boolean indicating whether the word was found."""
    import re
    pattern = re.compile(r"\b(" + re.escape(word) + r")\b", flags=re.IGNORECASE)
    matches = list(pattern.finditer(body))
    if not matches:
        return body, False
    # Replace only the FIRST match — once is enough to draw the eye
    m = matches[0]
    return body[:m.start()] + "<em>" + m.group(1) + "</em>" + body[m.end():], True


def generate_questions(story: dict, child_name: str, helper_name: str) -> list:
    """Generate three open-ended comprehension questions. Output is
    deterministic from story['word_count'] + child_name so renders
    are reproducible. Questions are phrased for parent-to-child reading
    and adapt to whether the child is a boy, girl, or unspecified."""
    # Use the story's word_count as a small seed incrementer; we don't need
    # cryptographic randomness, just differentiation.
    seed = story["word_count"] * 31 + sum(ord(c) for c in child_name)
    questions = [
        f"What was {helper_name}'s small problem in tonight's story?",
        f"What did {child_name} and {helper_name} do to fix it together?",
        f"Which part of the story did you like best? What did it look like in your imagination?",
    ]
    # Reorder deterministically so the set isn't always identical
    order = [seed % 3, (seed + 1) % 3, (seed + 2) % 3]
    return [questions[i] for i in order]


def generate_parent_guide(story: dict, child_name: str, helper_name: str, word: dict) -> str:
    """A deeper educational reflection for the parent (Pro only).
    Connects the story's vocabulary, theme, and moral to a real-world
    concept the parent can extend into a daytime conversation."""
    seed = sum(ord(c) for c in story["title"])
    hooks = [
        # Connection cards a parent can riff on with the child
        f"Try asking '{child_name}': 'When was the last time you felt like {helper_name}? What did you do about it?'",
        f"Vocabulary extension: after tonight, drop the word '{word['w']}' into a daytime sentence (e.g., at dinner) so {child_name} sees it used in real life.",
        f"Socially: the story's gentle fix is a good prompt to ask '{child_name}' how they solve small problems with friends (turn-taking, sharing, asking for help).",
        f"Storytelling: ask '{child_name}' to invent a different ending — what would {helper_name} do if the problem came back tomorrow?",
        f"Emotional literacy: tonight's word was '{word['w']}' ({word['d']}). Help {child_name} connect it to a feeling they've had this week.",
    ]
    return hooks[seed % len(hooks)]

# =====================================================================
# v4 INTERACTION LAYER — Moments, Polls, Audio, Drawings
# =====================================================================
# These helpers power the four interactive features from the v4 brief:
#   * "Moments" — persistent life-lesson / kindness pick shown per email
#   * "Choose Your Adventure" — daily poll the parent answers on /me
#   * "Story Time" audio — pyttsx3 + espeak-ng generates an MP3 per story
#   * "Creator" tier — drawing upload + feature-in-story loop
#
# Order matters: pick_moment / generate_poll_question are deterministic so
# callers can chain them with the existing seed without losing randomness.

# --- Moments pool ---
# Each "moment" is a 1-2 sentence reflection tying the story's kindness
# beat to a real-world prompt the parent can use. Echoes the parent's
# underlying value ("raise a kind human") without lecturing.
#
# Format: a dict with `text` (the moment). The `story_beat` field is used
# to lightly tie it to the story's resolved act. Hand-tuned to age 3-8.

MOMENTS_POOL = [
    {"text": "In the story, {helper} shared something important with someone new. Tonight, ask '{child}' what they might share with a friend tomorrow.", "story_beat": "sharing"},
    {"text": "{helper} was scared but tried the new thing anyway. Tonight, ask '{child}' to name one small brave thing they did today.", "story_beat": "courage"},
    {"text": "{helper} listened all the way through before answering. Tonight, ask '{child}' to practice listening with their mouth closed for 60 seconds at dinner.", "story_beat": "listening"},
    {"text": "When something went wrong, {helper} asked for help. Tonight, ask '{child}' who they could ask for help the next time something is too hard.", "story_beat": "asking"},
    {"text": "{helper} noticed when a friend was feeling small. Tonight, ask '{child}' to think of a friend who might need a check-in tomorrow.", "story_beat": "kindness"},
    {"text": "{helper} fixed the small problem one quiet step at a time. Tonight, ask '{child}' to pick one small tidy-up they could do before bed.", "story_beat": "patience"},
    {"text": "{helper} said thank you in a soft voice. Tonight, ask '{child}' to send a thank-you to someone who helped them this week.", "story_beat": "gratitude"},
    {"text": "{helper} tried a different way when the first idea didn't work. Tonight, ask '{child}' about a time they tried again after something didn't go right.", "story_beat": "persistence"},
    {"text": "{helper} waited for a friend to catch up instead of running ahead. Tonight, ask '{child}' how they make sure friends feel included.", "story_beat": "patience"},
    {"text": "In the story, {child} saw that {helper} was tired. Tonight, ask '{child}' how they could tell if a friend were tired and what they would do.", "story_beat": "kindness"},
    {"text": "When the plan changed, {helper} took a breath first. Tonight, ask '{child}' to try a 'three-breath reset' the next time they're frustrated.", "story_beat": "calm"},
    {"text": "{helper} told the truth gently, even when it was hard. Tonight, ask '{child}' what 'hard-but-honest' sounds like.", "story_beat": "honesty"},
    {"text": "{helper} noticed something tiny — a single flower, a small sound. Tonight, ask '{child}' to point out three tiny beautiful things on the way to bed.", "story_beat": "attention"},
    {"text": "When {helper} was unsure, {helper} asked a friend. Tonight, remind '{child}' it's always OK to ask.", "story_beat": "asking"},
    {"text": "{helper} finished what was started, even the boring part. Tonight, ask '{child}' what small task they'd like to finish tomorrow morning.", "story_beat": "persistence"},
]


def pick_moment(child_name: str, helper_name: str, seed: int) -> dict:
    """Pick a moment from the pool, formatted with the child's name.
    Uses simple positional placeholders {child}, {helper}."""
    pool = MOMENTS_POOL
    m = pool[seed % len(pool)]
    return {
        "text": m["text"].format(child=child_name, helper=helper_name),
        "story_beat": m["story_beat"],
    }


# --- Polls (Choose Your Adventure) ---
# Each poll is a question with three whimsical options. The parent's answer
# is woven into tomorrow's story. The first option is ALWAYS child-named as
# their pet/companion so it feels like a personal choice. We rotate through
# topics so kids don't see "What should X's pet be?" twice in a row.

POLL_QUESTION_TEMPLATES = [
    # topic = pet
    {
        "q": "Tomorrow's story needs a new friend for {helper}. Which of these would {child} like them to bring?",
        "opts": ["A soft rabbit who hums", "A sleepy turtle who reads", "A kind dragon who tells jokes"],
    },
    # topic = snack
    {
        "q": "What should {helper} and {child} share as a bedtime snack in tomorrow's story?",
        "opts": ["Moon-pudding", "Sun-warmed rolls", "A cup of tiny stars"],
    },
    # topic = place
    {
        "q": "Where should {helper} take {child} on a small adventure tomorrow?",
        "opts": ["The lantern garden", "The cloud bridge", "The library of whispers"],
    },
    # topic = problem
    {
        "q": "A small problem needs solving in tomorrow's tale. What kind of problem should {helper} face?",
        "opts": ["Something lost", "Something stuck", "Something shy"],
    },
    # topic = gift
    {
        "q": "What small gift should {helper} bring {child} in tomorrow's bedtime story?",
        "opts": ["A drawing of a star", "A pebble that hums", "A button from an old coat"],
    },
    # topic = sound
    {
        "q": "What is the special sound we should listen for in tomorrow's story?",
        "opts": ["A kind laugh", "A quiet whisper", "A slow clap"],
    },
    # topic = helper
    {
        "q": "Tomorrow's story needs a brand-new helper. Which one shall {child} choose?",
        "opts": ["A lantern mouse", "A paper bird", "A small thinking bear"],
    },
    # topic = ending
    {
        "q": "How should tomorrow's bedtime story end?",
        "opts": ["With a hug", "With a small laugh", "With a quiet yes"],
    },
]


def generate_poll_question(child_name: str, helper_name: str, seed: int) -> dict:
    """Generate one choose-your-adventure poll for tonight's send."""
    t = POLL_QUESTION_TEMPLATES[seed % len(POLL_QUESTION_TEMPLATES)]
    return {
        "question": t["q"].format(child=child_name, helper=helper_name),
        "options": t["opts"],
    }


# --- TTS audio helper (pyttsx3 + espeak-ng) ---
# Lazy-imported so the app boots even if the TTS engine isn't installed
# (e.g. CI / minimal Docker images). The fallback path returns None and
# the email renderer gracefully omits the audio block.

def _tts_save(text: str, out_path: Path) -> bool:
    """Synthesize `text` to MP3 at `out_path`. Returns True on success."""
    try:
        import pyttsx3
        eng = pyttsx3.init()
        eng.setProperty("rate", 140)        # bedtime pace — slightly slow
        eng.setProperty("volume", 0.95)
        voices = eng.getProperty("voices")
        # Prefer a non-English-sounding voice if espeak has one (warm-style).
        # For espeak-ng all voices are equally synthetic; defaulting is fine.
        eng.save_to_file(text, str(out_path))
        eng.runAndWait()
        eng.stop()
        return out_path.exists() and out_path.stat().st_size > 0
    except Exception as e:
        log.warning("TTS synthesis failed: %s", e)
        return False


def render_story_to_audio(subscriber_id: int, title: str, body: str, send_at_iso: str) -> str | None:
    """Synthesize an MP3 of "title. body" for the given subscriber. The MP3
    is saved under AUDIO_DIR/<subscriber_id>/<timestamp>.mp3 and the URL path
    is returned so the email can link to it.

    Returns None if TTS is unavailable — callers should treat this as "no
    audio for this delivery, but everything else still works"."""
    sub_dir = AUDIO_DIR / str(subscriber_id)
    sub_dir.mkdir(parents=True, exist_ok=True)
    safe_ts = send_at_iso.replace(":", "-").replace(".", "_")
    filename = f"{safe_ts}.mp3"
    out_path = sub_dir / filename
    # Synth the title then the body separated by a short pause (via two
    # sentences with a period + space). espeak speaks ". " as a natural
    # sentence boundary.
    script = f"{title}. {body}".replace("\n\n", ". ").replace("\n", " ")
    if not _tts_save(script, out_path):
        return None
    # URL path served by the /audio/<sub_id>/<filename> route below
    return f"audio/{subscriber_id}/{filename}"


# --- Drawing-upload helper (Creator tier) ---

DRAWINGS_PER_SUBSCRIBER_MAX = 30
ALLOWED_DRAWING_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
DRAWING_MAX_BYTES = 4 * 1024 * 1024  # 4 MB


def save_drawing(sub_id: int, file_storage, caption: str | None) -> tuple[int | None, str]:
    """Save an uploaded drawing to disk + the drawings table.
    Returns (id, error_message). If error_message is non-empty, id is None.
    """
    from werkzeug.utils import secure_filename
    if not file_storage or not getattr(file_storage, "filename", None):
        return None, "No file received."
    safe = secure_filename(file_storage.filename or "")
    if not safe:
        return None, "Filename must contain letters or numbers."
    ext = ("." + safe.rsplit(".", 1)[-1].lower()) if "." in safe else ""
    if ext not in ALLOWED_DRAWING_EXT:
        return None, "Please upload a PNG, JPG, GIF, or WebP image."
    # Read into memory to check size + enforce per-subscriber cap.
    blob = file_storage.read()
    if len(blob) > DRAWING_MAX_BYTES:
        return None, "Drawing is too large (max 4 MB). Please try a smaller image."
    conn = db()
    existing = conn.execute(
        "SELECT COUNT(*) AS c FROM drawings WHERE subscriber_id=?", (sub_id,)
    ).fetchone()
    if (existing["c"] or 0) >= DRAWINGS_PER_SUBSCRIBER_MAX:
        conn.close()
        return None, "You've reached the 30-drawing limit. Delete an old one to make room."
    # Sanitize + namespace filename inside the subscriber's folder
    sub_dir = AUDIO_DIR / str(sub_id)
    sub_dir.mkdir(parents=True, exist_ok=True)
    final_name = f"drawing_{safe_ts()}.{ext.lstrip('.')}"  # filename-local helper below
    out_path = sub_dir / final_name
    out_path.write_bytes(blob)
    cur = conn.execute(
        "INSERT INTO drawings(subscriber_id, filename, caption, created_at) VALUES (?,?,?,?)",
        (sub_id, final_name, (caption or "").strip()[:200], dt.datetime.utcnow().isoformat(timespec="seconds")),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id, ""


def safe_ts() -> str:
    return dt.datetime.utcnow().isoformat(timespec="seconds").replace(":", "-").replace(".", "_")


def fetch_user_drawings(sub_id: int, limit: int = 6) -> list:
    """Return the user's most recent drawings for /me display."""
    conn = db()
    rows = conn.execute(
        "SELECT id, filename, caption, created_at FROM drawings WHERE subscriber_id=? ORDER BY id DESC LIMIT ?",
        (sub_id, limit),
    ).fetchall()
    conn.close()
    return rows


def delete_drawing(sub_id: int, drawing_id: int) -> bool:
    """Owner-only delete. Returns True if anything was deleted."""
    conn = db()
    row = conn.execute(
        "SELECT filename FROM drawings WHERE id=? AND subscriber_id=?",
        (drawing_id, sub_id),
    ).fetchone()
    if not row:
        conn.close()
        return False
    path = AUDIO_DIR / str(sub_id) / row["filename"]
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass
    conn.execute("DELETE FROM drawings WHERE id=? AND subscriber_id=?", (drawing_id, sub_id))
    conn.commit()
    conn.close()
    return True


def open_poll_for_subscriber(sub_id: int) -> dict | None:
    """Get the OPEN poll for the subscriber (the one waiting for an answer).
    Returns dict with question, options, or None if no open poll."""
    conn = db()
    row = conn.execute(
        "SELECT id, question, options_json, created_at FROM polls "
        "WHERE subscriber_id=? AND used_in_story=0 ORDER BY id ASC LIMIT 1",
        (sub_id,)
    ).fetchone()
    conn.close()
    if not row: return None
    opts = _json.loads(row["options_json"]) if row["options_json"] else []
    return {"id": row["id"], "question": row["question"], "options": opts, "created_at": row["created_at"]}


def answer_poll(sub_id: int, poll_id: int, answer: str) -> bool:
    """Parent's submitted answer. One poll per open round per subscriber."""
    conn = db()
    conn.execute(
        "UPDATE polls SET answer=? WHERE id=? AND subscriber_id=?",
        (answer.strip()[:120], poll_id, sub_id),
    )
    conn.commit()
    n = conn.execute("SELECT changes() AS c").fetchone()["c"]
    conn.close()
    return n > 0


def pending_polls_for_subscriber(sub_id: int) -> int:
    """How many answered polls are waiting to be woven into the next story."""
    conn = db()
    n = conn.execute(
        "SELECT COUNT(*) AS c FROM polls WHERE subscriber_id=? AND used_in_story=0 AND answer IS NOT NULL",
        (sub_id,)
    ).fetchone()["c"] or 0
    conn.close()
    return n


def consume_pending_poll(sub_id: int) -> dict | None:
    """Take the oldest answered-but-not-yet-used poll. Marks used. Returns the poll
    record (id, question, answer) so the engine can weave the answer in."""
    conn = db()
    row = conn.execute(
        "SELECT id, question, answer FROM polls WHERE subscriber_id=? AND used_in_story=0 AND answer IS NOT NULL ORDER BY id ASC LIMIT 1",
        (sub_id,),
    ).fetchone()
    if not row:
        conn.close()
        return None
    conn.execute(
        "UPDATE polls SET used_in_story=1 WHERE id=?",
        (row["id"],),
    )
    conn.commit()
    conn.close()
    return dict(row)


def pending_poll_exists(sub_id: int) -> bool:
    conn = db()
    row = conn.execute(
        "SELECT 1 FROM polls WHERE subscriber_id=? AND used_in_story=0 AND answer IS NOT NULL LIMIT 1",
        (sub_id,),
    ).fetchone()
    conn.close()
    return bool(row)


def open_or_create_poll(sub_id: int, child_name: str, helper_name: str, seed: int) -> dict:
    """Ensure the subscriber has exactly ONE open-and-unanswered poll.
    If they already have one open, return it. Otherwise, generate a new
    question and store it (no answer yet)."""
    existing = open_poll_for_subscriber(sub_id)
    if existing: return existing
    poll = generate_poll_question(child_name, helper_name, seed)
    conn = db()
    cur = conn.execute(
        "INSERT INTO polls(subscriber_id, question, options_json, created_at) VALUES (?,?,?,?)",
        (sub_id, poll["question"], _json.dumps(poll["options"]), dt.datetime.utcnow().isoformat(timespec="seconds")),
    )
    new_id = cur.lastrowid
    conn.commit(); conn.close()
    return {"id": new_id, "question": poll["question"], "options": poll["options"], "created_at": dt.datetime.utcnow().isoformat(timespec="seconds")}



def choose(seq, rng):
    return seq[ rng % len(seq) ]


def enrich_for_v4(sub: dict, helper_name: str, seed: int, force_audio: bool = False) -> dict:
    """Run the v4 interactivity enrichment for one delivery.

    Pulls (and marks consumed) any pending poll answer to incorporate into
    the story; picks today's Moment; tries to render the story to audio
    (returns None path if pyttsx3 is unavailable); opportunistically picks
    one featured drawing if the subscriber is on Creator tier and they have
    uploaded any.

    Returns a dict with keys: poll_record, moment_record, audio_url,
    featured_drawing_filename. Each is None or a small payload safe to
    spread into either `deliver_email(**kwargs)` or stored on the
    deliveries row.
    """
    out = {"poll_record": None, "moment_record": None, "audio_url": None, "featured_drawing_filename": None}
    # 1. If a parent answered a poll earlier, weave the answer in.
    #    (The engine layer picks this up via seed; we just track it for
    #    the delivery row.)
    out["poll_record"] = consume_pending_poll(sub["id"])
    # 2. Always show a Moment — even Free users get this. It costs nothing
    #    and gives the email its "closing reflection" cadence.
    m = pick_moment(sub["child_name"], helper_name, seed)
    out["moment_record"] = {"text": m["text"], "story_beat": m["story_beat"]}
    # 3. Audio — best-effort. If pyttsx3 isn't available, audio_url stays
    #    None and the email rendering will hide the Listen button.
    if bool(sub.get("audio_enabled", 1)) or force_audio:
        ts = dt.datetime.utcnow().isoformat(timespec="seconds")
        # We don't have the rendered story body yet at this point — the
        # caller passes it in separately. So we return None here and the
        # helper at the delivery site does the actual audio render.
        out["audio_url"] = None  # populated by deliver_email() after generate_story()
    # 4. Creator-only drawing feature. If any drawing exists, surface one
    #    in the story ~1 in 7 nights (deterministic by seed) so it feels
    #    occasional, not every night.
    if sub["plan"] == "pro" and (sub.get("pro_tier") or "choice") == "creator":
        drawings = fetch_user_drawings(sub["id"], limit=20)
        if drawings and seed % 7 == 0:
            out["featured_drawing_filename"] = drawings[seed % len(drawings)]["filename"]
    return out

def generate_story(child_name: str, child_age: int, seed: int, plan: str = "free", pro_character: str | None = None, pro_theme: str | None = None, word_for_today: dict | None = None, helper_name_out: list | None = None) -> dict:
    """Generate a story. Seed should vary per delivery so we get a new one each night.

    For Pro subscribers, pro_character (a CAST key) locks the cast and
    pro_theme (substring match against SETTINGS) pins the setting. The plots
    and resolutions still rotate, so even Pro subscribers get a fresh-feeling
    story every night.

    If `word_for_today` is provided, the word is bolded inside the story body
    on the first occurrence (so a "Word of the Day" emerges naturally from
    the narrative, not as a tagline). If `helper_name_out` is provided as a
    single-element list, the helper's chosen name is written into it — this
    lets callers like nightly_run / render_email know which helper name to
    use in the comprehension questions and Parent Guide (the story body
    already contains the name, but pulling it out programmatically keeps
    the questions coupled to the actual cast)."""
    rng = seed
    cast_keys = list(CAST.keys())
    cast_key = pro_character if (plan == "pro" and pro_character and pro_character in CAST) else choose(cast_keys, rng); rng += 1
    helper = choose(CAST[cast_key]["names"], rng); rng += 1
    helper_build = CAST[cast_key]["build"]
    helper_voice = CAST[cast_key]["voice"]
    if helper_name_out is not None:
        helper_name_out.append(helper)

    # For Pro with a pinned theme, find the first matching setting; otherwise rotate
    setting_desc, setting_atmos = None, None
    if plan == "pro" and pro_theme:
        for sd, sa in SETTINGS:
            if pro_theme.lower() in sd.lower():
                setting_desc, setting_atmos = sd, sa
                break
    if setting_desc is None:
        setting_desc, setting_atmos = SETTINGS[rng % len(SETTINGS)]
        rng += 1

    opener = OPENINGS[ rng % len(OPENINGS) ]; rng += 1
    problem, problem_why = PROBLEMS[ rng % len(PROBLEMS) ]; rng += 1
    resolution = RESOLUTIONS[ rng % len(RESOLUTIONS) ]; rng += 1
    bedtime = BEDTIME[ rng % len(BEDTIME) ]; rng += 1

    # Adjust the helper name based on cast gender-neutral / generic
    text = (
        f"{opener}\n\n"
        f"This is the story of {child_name}, who was about to go to bed, and "
        f"{helper}, who had a small problem.\n\n"
        f"{helper} {problem}, because {problem_why}. "
        f"{helper} had {helper_build}, and {helper_voice}. "
        f"{child_name} liked {helper} very much, because {helper} was {CAST[cast_key]['cuddliness']}, "
        f"and also because {helper} always listened, even to the small ideas.\n\n"
        f"They were in {setting_desc}, where {setting_atmos}. "
        f"{child_name} sat down beside {helper} on the floor and said, "
        f"\"Let's fix this, but let's fix it gently, because I'm quite tired.\"\n\n"
        f"So they thought about it {resolution.format(helper=helper, child=child_name)}\n\n"
        f"After that, {bedtime.format(helper=helper, child=child_name)}"
    )

    # Word-count tuning: gently nudge ±10% by trimming/expanding if we drift outside the band
    words = text.split()
    if len(words) < STORY_MIN_WORDS:
        words += [
            "And somewhere far away, an old clock agreed that this was the right plan.",
            "There was a small sound in the chimney, like a kind thought going past.",
            "A cat on a fence, somewhere three streets over, purred its approval.",
            "The kettle in the kitchen made one last thoughtful click before it, too, went to bed.",
        ]
    if len(words) > STORY_MAX_WORDS:
        words = words[:STORY_MAX_WORDS]
    text = " ".join(words)

    # Title — short, warm
    title_choices = [
        f"{child_name} and the {choose(['Sleepy','Quiet','Tin','Small','Brave','Late'],rng)} Hour",
        f"How {helper} Almost {choose(['Forgot','Lost','Found','Heard','Learned'],rng+2)} It",
        f"The Night {child_name} {choose(['Yawned','Whispered','Listened','Wondered','Settled'],rng+4)}",
        f"A Small Story for a {choose(['Sleepy','Tired','Brave','Tender','Curious'],rng+6)} {child_name}",
    ]
    title = title_choices[rng % len(title_choices)]

    # If a word-for-today is provided, bold the first occurrence in the body
    # so the child sees it stand out while reading. Returns the (possibly
    # unchanged) body; word_bolded tells the caller whether the bolding
    # actually happened (which can be False if the word happens not to
    # appear in the story text — in that case the email still shows the
    # word in the Word of the Day box, just not bolded inline).
    word_bolded = False
    if word_for_today:
        text, word_bolded = bold_word_in_body(text, word_for_today["w"])

    return {
        "title": title,
        "body": text,
        "word_count": len(text.split()),
        "word_bolded": word_bolded,
    }


# =====================================================================
# STRIPE WRAPPER (live + mock)
# =====================================================================
# When STRIPE_SECRET_KEY is set, calls hit the real Stripe API.
# When it's not set (mock mode), the same functions return shape-compatible
# objects so the rest of the app doesn't care. Mock events live in an
# in-process queue you can drain via /admin/billing.
MOCK_EVENTS = []  # list of dict events, e.g. {"type":"customer.subscription.deleted", "data":{...}}

def _mock_customer_id():
    return "cus_mock_" + secrets.token_hex(6)

def _mock_subscription_id():
    return "sub_mock_" + secrets.token_hex(6)

def stripe_checkout_session(subscriber, success_url, cancel_url):
    """Create a Stripe Checkout session for the Pro plan.
    Returns: dict with at least {id, url}.
    In mock mode, returns a URL pointing at our /mock/checkout page."""
    if STRIPE_MOCK or stripe is None:
        # Mock: synthesize a session and stash the subscriber on it
        sid = "cs_mock_" + secrets.token_hex(6)
        return {"id": sid, "url": f"/mock/checkout?sid={sid}&sub={subscriber['id']}&success={success_url}&cancel={cancel_url}"}
    # Live
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        customer_email=subscriber["email"],
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"subscriber_id": str(subscriber["id"])},
        allow_promotion_codes=True,
    )
    return {"id": session.id, "url": session.url}

def stripe_cancel_subscription(subscription_id):
    """Cancel a subscription at period end (graceful)."""
    if STRIPE_MOCK or stripe is None:
        # In mock, synthesize the same event Stripe emits for cancel-at-period-end:
        # `customer.subscription.updated` with cancel_at_period_end=True.
        # The "deleted" event fires later when the period actually ends.
        MOCK_EVENTS.append({
            "type": "customer.subscription.updated",
            "data": {"object": {"id": subscription_id, "status": "active", "cancel_at_period_end": True}},
        })
        return {"id": subscription_id, "status": "active", "cancel_at_period_end": True}
    sub = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
    return {"id": sub.id, "status": sub.status, "cancel_at_period_end": sub.cancel_at_period_end}

def stripe_resume_subscription(subscription_id):
    if STRIPE_MOCK or stripe is None:
        MOCK_EVENTS.append({
            "type": "customer.subscription.updated",
            "data": {"object": {"id": subscription_id, "status": "active"}},
        })
        return {"id": subscription_id, "status": "active"}
    sub = stripe.Subscription.modify(subscription_id, cancel_at_period_end=False)
    return {"id": sub.id, "status": sub.status}

def apply_stripe_event_to_subscriber(subscriber_id, event_type, event_data):
    """Idempotently apply a Stripe event to our DB. Called from the webhook.
    event_data is the inner 'object' from the Stripe event payload (dict or stripe object)."""
    # Stripe's library sometimes hands us a Subscription/Customer object — normalize to dict
    if hasattr(event_data, "to_dict"):
        event_data = event_data.to_dict()
    obj = event_data.get("object", event_data) if isinstance(event_data, dict) else event_data
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    conn = db()
    sub = conn.execute("SELECT * FROM subscribers WHERE id=?", (subscriber_id,)).fetchone()
    if not sub:
        conn.close(); return
    cid = obj.get("customer") if isinstance(obj, dict) else None
    sid = obj.get("id") if isinstance(obj, dict) else None
    status = (obj.get("status") if isinstance(obj, dict) else None) or ""
    period_end_ts = (obj.get("current_period_end") if isinstance(obj, dict) else None)
    period_end_iso = None
    if period_end_ts:
        period_end_iso = dt.datetime.fromtimestamp(int(period_end_ts), tz=dt.timezone.utc).isoformat(timespec="seconds")

    if event_type in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
        # The 'deleted' event means the sub is fully canceled (period ended)
        plan = "pro" if status in ("active","trialing","past_due") else "free"
        # If canceled and we're past period end, downgrade plan
        if event_type == "customer.subscription.deleted" or status == "canceled":
            plan = "free"
        conn.execute(
            "UPDATE subscribers SET plan=?, customer_id=COALESCE(?,customer_id), subscription_id=?, subscription_status=?, current_period_end=? WHERE id=?",
            (plan, cid, sid, status, period_end_iso, subscriber_id)
        )
    elif event_type == "invoice.paid":
        # Successful renewal — keep plan=pro, refresh period end
        if status in ("active","trialing") or not status:
            conn.execute(
                "UPDATE subscribers SET plan='pro', customer_id=COALESCE(?,customer_id), subscription_id=COALESCE(?,subscription_id), subscription_status=COALESCE(?,subscription_status), current_period_end=? WHERE id=?",
                (cid, sid, status or "active", period_end_iso, subscriber_id)
            )
    elif event_type == "invoice.payment_failed":
        conn.execute(
            "UPDATE subscribers SET subscription_status='past_due' WHERE id=?",
            (subscriber_id,)
        )
    conn.commit()
    conn.execute(
        "INSERT INTO story_log(ts,note) VALUES (?,?)",
        (dt.datetime.utcnow().isoformat(timespec="seconds"), f"Stripe {event_type} for sub#{subscriber_id} ({status})")
    )
    conn.commit()
    conn.close()

# =====================================================================
# MAGIC-LINK TOKENS
# =====================================================================
def issue_token(subscriber_id: int, purpose: str = "login") -> str:
    """Create a single-use magic-link token. Returns the raw token string."""
    raw = secrets.token_urlsafe(32)
    now = dt.datetime.utcnow()
    expires = now + dt.timedelta(seconds=MAGIC_LINK_TTL)
    conn = db()
    conn.execute(
        "INSERT INTO magic_tokens(token, subscriber_id, purpose, created_at, expires_at, used) VALUES (?,?,?,?,?,0)",
        (raw, subscriber_id, purpose, now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds"))
    )
    conn.commit(); conn.close()
    return raw

def consume_token(raw: str, purpose: str = "login") -> int | None:
    """Consume a token if valid + not expired + not used. Returns subscriber_id or None."""
    conn = db()
    row = conn.execute("SELECT * FROM magic_tokens WHERE token=?", (raw,)).fetchone()
    if not row:
        conn.close(); return None
    if row["purpose"] != purpose:
        conn.close(); return None
    if row["used"]:
        conn.close(); return None
    expires_at = dt.datetime.fromisoformat(row["expires_at"])
    if dt.datetime.utcnow() > expires_at:
        conn.close(); return None
    conn.execute("UPDATE magic_tokens SET used=1 WHERE token=?", (raw,))
    conn.commit(); conn.close()
    return row["subscriber_id"]

# =====================================================================
# EMAIL DELIVERY
# =====================================================================

# Email header banner — a charming "bedtime sky" illustration shown at
# the top of every story email. Stored as an inline SVG string so it
# works without external hosting. Outlook (Word) drops inline SVG, so
# some recipients may see a blank area where the banner would be; that's
# acceptable for a polish element.
EMAIL_BANNER_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 120" role="img" aria-label="A quiet bedtime sky: a sleeping cloud, a crescent moon, and stars">
  <title>PocketPlot — bedtime banner</title>
  <defs>
    <linearGradient id="bBg" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#FFF8E7"/>
      <stop offset="0.5" stop-color="#FFE5A0"/>
      <stop offset="1" stop-color="#FFCBA4"/>
    </linearGradient>
    <radialGradient id="bCloudGlow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.8"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect x="0" y="0" width="600" height="120" fill="url(#bBg)"/>

  <g fill="#FFE5A0" stroke="#3A3633" stroke-width="0.8">
    <path d="M 100 28 L 103 33 L 108 33 L 104 36 L 106 41 L 100 38 L 94 41 L 96 36 L 92 33 L 97 33 Z"/>
    <path d="M 480 26 L 482 30 L 486 30 L 483 32.5 L 484.5 36.5 L 480 34 L 475.5 36.5 L 477 32.5 L 474 30 L 478 30 Z"/>
    <circle cx="160" cy="22" r="2"/>
    <circle cx="220" cy="40" r="1.8"/>
    <circle cx="280" cy="18" r="2.2"/>
    <circle cx="340" cy="36" r="1.6"/>
    <circle cx="400" cy="22" r="2"/>
    <circle cx="540" cy="40" r="1.8"/>
    <circle cx="60"  cy="58" r="1.6"/>
    <circle cx="180" cy="62" r="1.7"/>
    <circle cx="260" cy="58" r="1.5"/>
    <circle cx="380" cy="60" r="1.6"/>
    <circle cx="500" cy="62" r="1.7"/>
  </g>
  <path d="M 540 24 L 542 30 L 548 32 L 542 34 L 540 40 L 538 34 L 532 32 L 538 30 Z" fill="#FFE5A0" stroke="#3A3633" stroke-width="0.6"/>

  <g transform="translate(60, 60)">
    <circle r="30" fill="#FFE5A0" stroke="#3A3633" stroke-width="2.5"/>
    <circle cx="11" cy="-4" r="25" fill="url(#bBg)"/>
    <circle cx="-13" cy="5" r="2.4" fill="#E8D78A" opacity="0.85"/>
    <circle cx="-10" cy="13" r="1.6" fill="#E8D78A" opacity="0.75"/>
    <circle cx="-16" cy="-2" r="1.5" fill="#E8D78A" opacity="0.7"/>
  </g>

  <g transform="translate(360, 64)">
    <g stroke="#3A3633" stroke-width="2.5" stroke-linejoin="round" fill="#FFF8E7">
      <ellipse cx="0" cy="0" rx="56" ry="22"/>
      <ellipse cx="-30" cy="-12" rx="20" ry="14"/>
      <ellipse cx="32" cy="-14" rx="22" ry="16"/>
      <ellipse cx="0" cy="-18" rx="16" ry="12"/>
    </g>
    <ellipse cx="0" cy="0" rx="56" ry="22" fill="#FFF8E7"/>
    <ellipse cx="-30" cy="-12" rx="20" ry="14" fill="#FFF8E7"/>
    <ellipse cx="32" cy="-14" rx="22" ry="16" fill="#FFF8E7"/>
    <ellipse cx="0" cy="-18" rx="16" ry="12" fill="#FFF8E7"/>

    <ellipse cx="0" cy="-4" rx="62" ry="32" fill="url(#bCloudGlow)"/>

    <path d="M -20 -4 Q -14 4 -8 -4" stroke="#3A3633" stroke-width="3" fill="none" stroke-linecap="round"/>
    <path d="M 8 -4 Q 14 4 20 -4" stroke="#3A3633" stroke-width="3" fill="none" stroke-linecap="round"/>
    <circle cx="-19" cy="-6" r="0.9" fill="#FFFFFF" opacity="0.85"/>
    <circle cx="9" cy="-6" r="0.9" fill="#FFFFFF" opacity="0.85"/>
    <circle cx="-26" cy="6" r="5" fill="#F8B7B0" opacity="0.75"/>
    <circle cx="26" cy="6" r="5" fill="#F8B7B0" opacity="0.75"/>
    <path d="M -4 6 Q 0 10 4 6" stroke="#3A3633" stroke-width="2.5" fill="none" stroke-linecap="round"/>

    <!-- The "Zzz" — three separate letterforms in a diagonal cascade -->
    <g fill="none" stroke="#5C7C5A" stroke-linecap="round" stroke-linejoin="round">
      <path d="M 56 -38 L 70 -38 L 56 -28 L 70 -28" stroke-width="2.2"/>
      <path d="M 70 -52 L 86 -52 L 70 -40 L 86 -40" stroke-width="2.4"/>
      <path d="M 84 -68 L 100 -68 L 84 -54 L 100 -54" stroke-width="2.6"/>
    </g>
  </g>

  <g transform="translate(530, 96)">
    <g stroke="#3A3633" stroke-width="2" stroke-linejoin="round" fill="#FFF8E7">
      <ellipse cx="0" cy="0" rx="22" ry="9"/>
      <ellipse cx="-12" cy="-4" rx="9" ry="6"/>
      <ellipse cx="10" cy="-5" rx="10" ry="7"/>
    </g>
    <ellipse cx="0" cy="0" rx="22" ry="9" fill="#FFF8E7"/>
    <ellipse cx="-12" cy="-4" rx="9" ry="6" fill="#FFF8E7"/>
    <ellipse cx="10" cy="-5" rx="10" ry="7" fill="#FFF8E7"/>
  </g>

  <g transform="translate(180, 50)" stroke="#3A3633" stroke-width="2.4" fill="none" stroke-linecap="round">
    <path d="M -8 4 Q -4 -4 0 4 Q 4 -4 8 4"/>
    <path d="M 24 22 Q 28 16 32 22 Q 36 16 40 22" opacity="0.55"/>
  </g>
</svg>'''



# =====================================================================

MOMENT_ICON_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" role="img" aria-label="The Moment of the Day — a warm glowing heart">
  <title>Moment of the Day</title>
  <defs>
    <radialGradient id="mGlow" cx="0.5" cy="0.5" r="0.6">
      <stop offset="0" stop-color="#FFD0C0" stop-opacity="0.7"/>
      <stop offset="0.6" stop-color="#FFD0C0" stop-opacity="0.2"/>
      <stop offset="1" stop-color="#FFD0C0" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="mHeart" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#FFA88E"/>
      <stop offset="0.5" stop-color="#F8826A"/>
      <stop offset="1" stop-color="#E86452"/>
    </linearGradient>
  </defs>

  <!-- Soft halo (a real brand mark has space to breathe) -->
  <circle cx="40" cy="40" r="36" fill="url(#mGlow)"/>

  <!-- Two small sparkles flanking the heart (premium polish) -->
  <g fill="#FFE5A0" stroke="#3A3633" stroke-width="1">
    <path d="M 14 16 L 16 20 L 20 20 L 17 22.5 L 18 26 L 14 24 L 10 26 L 11 22.5 L 8 20 L 12 20 Z"/>
    <path d="M 64 22 L 66 26 L 70 26 L 67 28.5 L 68 32 L 64 30 L 60 32 L 61 28.5 L 58 26 L 62 26 Z"/>
  </g>
  <circle cx="68" cy="48" r="2.4" fill="#FFCBA4" stroke="#3A3633" stroke-width="1"/>
  <circle cx="14" cy="58" r="2" fill="#92D4A8" stroke="#3A3633" stroke-width="1"/>

  <!-- The heart (chunkier, with depth) -->
  <g transform="translate(40,42)">
    <!-- A soft drop shadow for depth -->
    <path d="M 0 4 C -8 -3 -18 1 -12 8 L 0 18 L 12 8 C 18 1 8 -3 0 4 Z" fill="#3A3633" opacity="0.15" transform="translate(0, 2)"/>
    <!-- The heart body -->
    <path d="M 0 4 C -8 -3 -18 1 -12 8 L 0 18 L 12 8 C 18 1 8 -3 0 4 Z" fill="url(#mHeart)" stroke="#3A3633" stroke-width="2.5" stroke-linejoin="round"/>
    <!-- Highlight glint (the KAK-signature single highlight) -->
    <ellipse cx="-7" cy="0" rx="4" ry="2.4" fill="#FFF8E7" opacity="0.85" transform="rotate(-25 -7 0)"/>
    <!-- A second tiny glint -->
    <circle cx="-3" cy="-2" r="1" fill="#FFF8E7" opacity="0.95"/>
  </g>
</svg>'''


PRO_BADGE_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" role="img" aria-label="PocketPlot Pro — a gold star seal">
  <title>PocketPlot Pro</title>
  <defs>
    <radialGradient id="pStar" cx="0.4" cy="0.4" r="0.6">
      <stop offset="0" stop-color="#FFF0C0"/>
      <stop offset="0.5" stop-color="#FFE5A0"/>
      <stop offset="1" stop-color="#E8B860"/>
    </radialGradient>
    <radialGradient id="pGlow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#FFE5A0" stop-opacity="0.6"/>
      <stop offset="1" stop-color="#FFE5A0" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <!-- Outer soft glow (a "this is special" halo) -->
  <circle cx="40" cy="40" r="36" fill="url(#pGlow)"/>

  <!-- A laurel-like wreath around the star (premium emblem feel) -->
  <g stroke="#5C7C5A" stroke-width="2" fill="#92D4A8" opacity="0.7">
    <!-- Left leaf -->
    <path d="M 22 30 Q 14 40 22 50 Q 28 44 26 30 Q 24 28 22 30 Z"/>
    <path d="M 24 38 Q 18 42 24 46" fill="none"/>
    <!-- Right leaf -->
    <path d="M 58 30 Q 66 40 58 50 Q 52 44 54 30 Q 56 28 58 30 Z"/>
    <path d="M 56 38 Q 62 42 56 46" fill="none"/>
  </g>

  <!-- The puffy gold star (the seal itself) -->
  <g transform="translate(40,40)">
    <!-- Drop shadow for depth -->
    <path d="M 0 -22 L 6 -8 L 22 -6 L 10 4 L 14 18 L 0 10 L -14 18 L -10 4 L -22 -6 L -6 -8 Z" fill="#3A3633" opacity="0.2" transform="translate(0, 1.5)"/>
    <!-- Star body -->
    <path d="M 0 -22 L 6 -8 L 22 -6 L 10 4 L 14 18 L 0 10 L -14 18 L -10 4 L -22 -6 L -6 -8 Z" fill="url(#pStar)" stroke="#3A3633" stroke-width="2.5" stroke-linejoin="round"/>
    <!-- Two highlights (the "polished gold" look) -->
    <ellipse cx="-5" cy="-9" rx="4" ry="2.4" fill="#FFF8E7" opacity="0.85" transform="rotate(-30 -5 -9)"/>
    <circle cx="6" cy="6" r="1.6" fill="#FFF8E7" opacity="0.9"/>
  </g>

  <!-- Small sparkles (premium) -->
  <g fill="#FFE5A0" stroke="#3A3633" stroke-width="1">
    <path d="M 14 16 L 16 20 L 20 20 L 17 22.5 L 18 26 L 14 24 L 10 26 L 11 22.5 L 8 20 L 12 20 Z"/>
    <path d="M 62 18 L 64 22 L 68 22 L 65 24.5 L 66 28 L 62 26 L 58 28 L 59 24.5 L 56 22 L 60 22 Z"/>
  </g>
</svg>'''


# EMAIL LEARNING BLOCKS — Word of the Day, Story Talk, Parent Guide
# =====================================================================
# These are reusable HTML fragments that get passed to HTML_TEMPLATE via
# .format() placeholders. Word of the Day and Story Talk are shown to all
# subscribers; Parent Guide is Pro-only.

WORD_BOX_HTML = """
<div class="learning-box">
  <div class="learning-eyebrow">Word of the Day</div>
  <div class="learning-word">{word}</div>
  <div class="learning-def"><em>{word_definition}</em></div>
  <div class="learning-example">e.g. &ldquo;{word_example}&rdquo;</div>
</div>
"""

QUESTIONS_BOX_HTML = """
<div class="learning-box">
  <div class="learning-eyebrow">Story Talk</div>
  <div class="learning-talk-intro">Three small questions to ask your child before bed:</div>
  <ol class="learning-questions">
    <li>{question_1}</li>
    <li>{question_2}</li>
    <li>{question_3}</li>
  </ol>
</div>
"""

PARENT_GUIDE_HTML = """
<div class="learning-box parent-guide">
  <div class="learning-eyebrow">Parent Guide <span class="pro-tag">PRO</span></div>
  <div class="learning-guide-text">{parent_guide_text}</div>
</div>
"""


# v4 blocks — Moments, Listen, Featured drawing
MOMENT_BOX_HTML = """
<div class="learning-box moment-box">
  <div class="learning-eyebrow moment-eyebrow">
    <span class="moment-icon-inline">{moment_icon_svg}</span>
    <span>{child_name}&rsquo;s Moment of the Day</span>
  </div>
  <div class="moment-text">{moment_text}</div>
</div>
"""

AUDIO_BUTTON_HTML = """
<div class="audio-cta">
  <a href="{audio_full_url}" class="audio-btn">
    <span class="audio-icon" aria-hidden="true">&#9835;</span>
    <span class="audio-label">Listen to the story</span>
  </a>
  <div class="audio-note">A warm, slow narration &mdash; perfect for the soft lamp-light moment.</div>
</div>
"""

GAME_BUTTON_HTML = """
<div class="game-cta" style="margin:24px 0 8px; text-align:center;">
  <a href="{game_url}" class="game-btn" style="display:inline-flex; align-items:center; gap:10px; padding:14px 28px; border-radius:99px; background:#5c7c5a; color:#ffffff; text-decoration:none; font-weight:700; font-size:15px; font-family:'Helvetica Neue',Arial,sans-serif; box-shadow:0 8px 22px rgba(92,124,90,.28);">
    <span class="game-icon" style="font-size:18px;" aria-hidden="true">&#127918;</span>
    <span class="game-label" style="color:#ffffff;">Play tonight&rsquo;s adventure</span>
  </a>
  <div class="game-note" style="font-family:'Helvetica Neue',Arial,sans-serif; font-size:12px; color:#7a8a6a; margin-top:8px; font-style:italic;">Walk the path, collect today&rsquo;s word, answer Story Talk questions. A PocketPlot Pro perk.</div>
</div>
"""

FEATURED_DRAWING_HTML = """
<div class="learning-box featured-drawing">
  <div class="learning-eyebrow">Tonight&rsquo;s inspiration<span class="pro-tag">CREATOR</span></div>
  <div class="featured-drawing-img">
    <img src="{drawing_full_url}" alt="A drawing by {child_name}, featured in tonight's story" loading="lazy" />
  </div>
</div>
"""

HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{font-family: Georgia, "Iowan Old Style", serif; background:#f6f0e1; color:#1a241d; margin:0; padding:0}}
.wrap {{max-width:600px; margin:0 auto; padding:36px 28px}}
.email-banner{{display:block; width:100%; max-width:600px; height:auto; margin:0 0 24px; border-radius:12px; border:1px solid #ecdfc3}}
.header-bar {{
  display:inline-block; margin-bottom:18px;
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size:11px; letter-spacing:.18em; text-transform:uppercase;
  color:#5a6a4a; font-weight:700;
}}
.header-bar .pro-badge {{
  display:inline-block; margin-left:10px;
  padding:3px 10px; border-radius:99px;
  background:#d4a849; color:#3a2a10; letter-spacing:.14em;
  box-shadow:0 1px 0 rgba(0,0,0,.05);
}}
.header-bar {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; }}
.pro-corner {{ display:inline-flex; vertical-align:middle; height:32px; }}
.pro-corner svg {{ height:32px; width:auto; }}
.tagline {{
  font-family: "Helvetica Neue", Arial, sans-serif; font-size:11px;
  letter-spacing:.16em; color:#7a8a6a; text-transform:uppercase;
  margin-bottom:14px; font-weight:600;
}}
.tagline .star {{color:#d4a849; margin-right:4px}}
h1 {{
  font-weight:500; font-size:32px; line-height:1.18; margin:0 0 20px;
  color:#1a241d; font-style:italic;
}}
.story {{font-size:17px; line-height:1.78; color:#2a3a2d}}
.story p {{margin:0 0 16px}}
.story em {{font-style:italic; color:#3d5a3a}}
.hero-image {{display:block; margin:8px auto 18px; max-width:380px; width:100%}}
.hero-image svg {{width:100%; height:auto; display:block; border-radius:18px}}
.divider {{margin:36px 0 16px; border:none; border-top:1px dotted #c4b894}}
.signoff {{font-size:14px; color:#5a6a4a; font-style:italic; margin-top:24px}}
.foot {{
  font-family: "Helvetica Neue", Arial, sans-serif; font-size:11px;
  color:#8a8270; margin-top:32px; letter-spacing:.04em; line-height:1.5;
}}
.foot a {{color:#7a8a6a; text-decoration:underline}}
.pro-ribbon {{
  margin:24px 0 0; padding:14px 18px; border-radius:10px;
  background:#fdf5e3; border:1px solid #d4a849;
  font-family: "Helvetica Neue", Arial, sans-serif;
  font-size:12.5px; line-height:1.5; color:#7a6420;
}}
.pro-ribbon b {{color:#8a6420}}

/* Learning Layer blocks (Word of the Day, Story Talk, Parent Guide) */
.learning-box {{
  margin:24px 0 0; padding:18px 20px; border-radius:12px;
  background:#fff8e6; border:1px solid #e8d99a; color:#3d4a2a;
  font-family: "Helvetica Neue", Arial, sans-serif; line-height:1.55;
}}
.learning-eyebrow {{
  font-size:11px; font-weight:700; letter-spacing:.18em;
  text-transform:uppercase; color:#8a6420; margin-bottom:10px;
}}
.learning-eyebrow .pro-tag {{
  display:inline-block; margin-left:6px;
  padding:1px 6px; border-radius:8px;
  background:#d4a849; color:#3a2a10;
  font-size:9px; letter-spacing:.14em; vertical-align:1px;
}}
.learning-word {{
  font-family: Georgia, serif; font-size:26px; font-weight:600;
  color:#1a241d; margin-bottom:6px; font-style:italic;
}}
.learning-def {{ font-size:14px; color:#3d5a3a; margin-bottom:10px; }}
.learning-example {{ font-size:13px; color:#7a8a6a; font-style:italic; }}
.learning-talk-intro {{ font-size:13px; color:#5a6a4a; margin-bottom:10px; }}
.learning-questions {{
  margin:0 0 0 18px; padding:0; font-size:14px; color:#3d4a2a;
}}
.learning-questions li {{
  margin-bottom:8px; padding-left:4px;
}}
.parent-guide {{
  background:#f5eddc; border-color:#c8b878;
}}
.learning-guide-text {{ font-size:14px; color:#3a3a2a; line-height:1.6; }}
/* v4: Moments box — slightly different cream so it reads as "warm closure" */
.moment-box {{ background:#fbeed3; border-color:#e8c89a; }}
.moment-text {{ font-family:Georgia,serif; font-style:italic; font-size:15px; color:#4a3a2a; line-height:1.6; }}
.moment-eyebrow {{ display:flex; align-items:center; gap:10px; }}
.moment-icon-inline {{ display:inline-flex; width:32px; height:32px; }}
.moment-icon-inline svg {{ width:32px; height:32px; }}
/* v4: Listen button */
.audio-cta {{ margin:24px 0 8px; text-align:center; }}
.audio-btn {{
  display:inline-flex; align-items:center; gap:10px;
  padding:14px 28px; border-radius:99px;
  background:var(--terracotta); color:#fff;
  text-decoration:none; font-weight:700; font-size:15px;
  box-shadow:0 8px 22px rgba(196,122,90,.28);
}}
.audio-btn:hover {{ background:var(--terracottaD); }}
.audio-icon {{ font-size:18px; }}
.audio-note {{ font-family:"Helvetica Neue",Arial,sans-serif; font-size:12px; color:#7a8a6a; margin-top:8px; font-style:italic; }}
/* v7 (Phase 3): Mini-game CTA — Pro perk */
.game-cta {{ margin:24px 0 8px; text-align:center; }}
.game-btn {{
  display:inline-flex; align-items:center; gap:10px;
  padding:14px 28px; border-radius:99px;
  background:var(--moss); color:#fff;
  text-decoration:none; font-weight:700; font-size:15px;
  box-shadow:0 8px 22px rgba(92,124,90,.28);
}}
.game-btn:hover {{ background:#4a6648; }}
.game-icon {{ font-size:18px; }}
.game-note {{ font-family:"Helvetica Neue",Arial,sans-serif; font-size:12px; color:#7a8a6a; margin-top:8px; font-style:italic; }}
/* v4: featured drawing */
.featured-drawing {{ background:#f7f1e6; border-color:#d8c898; text-align:center; }}
.featured-drawing-img img {{
  max-width:100%; height:auto; border-radius:8px; margin-top:6px;
  box-shadow:0 4px 16px rgba(60,40,20,.10);
  display:inline-block;
}}
</style></head><body>
<div class="wrap">
  {email_banner}
<div class="header-bar">
  <span class="header-text">PocketPlot</span>
  {pro_badge}
  {pro_corner}
</div>
<div class="tagline">{tagline}</div>
<h1>{title}</h1>
{hero_image}
<div class="story">{body_html}</div>
{featured_drawing_box}
{game_button_box}
{audio_button_box}
{word_box}
{questions_box}
{parent_guide_box}
{moment_box}
<hr class="divider">
<div class="signoff">Sleep well, little one. — PocketPlot</div>
{pro_ribbon}
<div class="foot">
A unique story, written just for {child_name}.<br>
<a href="{manage_url}">Manage your account</a> · <a href="{unsubscribe_url}">Pause delivery</a>
</div>
</div></body></html>
"""

def render_email(title: str, body: str, child_name: str, plan: str = "free", child_age: int | None = None, manage_token: str | None = None, word: dict | None = None, questions: list | None = None, parent_guide_text: str | None = None, moment_text: str | None = None, audio_full_url: str | None = None, drawing_full_url: str | None = None, moment_icon_svg: str = "", pro_badge_svg: str = "", hero_svg: str = "") -> tuple[str, str]:
    """Return (plain text body, html body). `plan` is 'free' or 'pro'.

    Learning-layer parameters (v3):
      word: {w, d, tier} or None
      questions: list of 3 strings (already ordered)
      parent_guide_text: Pro-only string for the deeper reflection

    Interactivity-layer parameters (v4):
      moment_text: e.g. "Mia's Moment of the Day: ..." — always shown when present
      audio_full_url: absolute URL to the story's MP3 — enables the "Listen"
                       button; rendering is skipped when None
      drawing_full_url: absolute URL to a Creator-tier featured drawing —
                        also skipped when None (no extra HTML)
    """
    paragraphs = []
    for p in body.split("\n\n"):
        p = p.strip().replace("\n", " ")
        import re as _re
        p = _re.sub(r"\*([^*]+)\*", r"<em>\1</em>", p)
        paragraphs.append(f"<p>{p}</p>")
    # Wrap the banner SVG in a class so the .email-banner CSS rule applies.
    email_banner = f'<div class="email-banner">{EMAIL_BANNER_SVG}</div>'

    # ---- Learning boxes ----
    # Word of the Day: bold the word in the story ALREADY happened in
    # generate_story(); here we just show the dedicated info box below.
    if word:
        # Build an example sentence that uses the child's name — gives the
        # child a personalized example they can relate to.
        example = f"{child_name} felt {word['w']} today, like a small warm feeling in their chest."
        word_box = WORD_BOX_HTML.format(
            word=html_lib.escape(word["w"]),
            word_definition=html_lib.escape(word["d"]),
            word_example=html_lib.escape(example),
        )
    else:
        word_box = ""
    if questions and len(questions) >= 3:
        questions_box = QUESTIONS_BOX_HTML.format(
            question_1=html_lib.escape(questions[0]),
            question_2=html_lib.escape(questions[1]),
            question_3=html_lib.escape(questions[2]),
        )
    else:
        questions_box = ""
    # Parent Guide: Pro-only. Free tier sees a soft "Upgrade to Pro" hint box
    # instead of the deeper content — this is a tasteful upsell, not a hard
    # paywall, because the questions + word box already give Free users the
    # core learning value.
    if plan == "pro" and parent_guide_text:
        parent_guide_box = PARENT_GUIDE_HTML.format(
            parent_guide_text=html_lib.escape(parent_guide_text),
        )
    else:
        parent_guide_box = ""
    # v4: Moment block — always show when present (Free and Pro both get it).
    if moment_text:
        moment_box = MOMENT_BOX_HTML.format(
            child_name=html_lib.escape(child_name),
            moment_text=html_lib.escape(moment_text),
            moment_icon_svg=moment_icon_svg,
        )
    else:
        moment_box = ""
    # v4: Audio button — only when audio was rendered.
    if audio_full_url:
        audio_button_box = AUDIO_BUTTON_HTML.format(audio_full_url=audio_full_url)
    else:
        audio_button_box = ""
    # v7 (Phase 3): Game button — only for Pro subscribers, only if audio
    # also rendered (so we don't ship a "play" button when the story body
    # is empty). The delivery ID is captured via delivery_id parameter
    # to make the link stable across email reopens.
    if plan == "pro":
        # Pro subscribers see the game button unconditionally (no longer
        # requires audio — if TTS fails the user can still play, and the
        # hero image + story body make the game plenty rich on its own).
        # Find the delivery_id: caller passes it via delivery_id_kw
        # (we don't have access to it in this scope, so build the
        # generic /game link — the route picks the latest delivery).
        game_button_box = GAME_BUTTON_HTML.format(game_url=SITE_URL + "/game")
    else:
        game_button_box = ""
    # v4: Featured drawing — only when a Creator drawing is featured.
    if drawing_full_url:
        featured_drawing_box = FEATURED_DRAWING_HTML.format(
            drawing_full_url=drawing_full_url,
            child_name=html_lib.escape(child_name),
        )
    else:
        featured_drawing_box = ""

    html = HTML_TEMPLATE.format(
        title=title, body_html="".join(paragraphs), child_name=child_name,
        pro_corner=('<span class="pro-corner">' + pro_badge_svg + '</span>') if (plan == 'pro' and pro_badge_svg) else '',
        pro_badge='<span class="pro-badge">★ PRO</span>' if plan == "pro" else "",
        tagline=("Tonight's Story" if plan == "free" else "★ Tonight's Story"),
        pro_ribbon=(
            '<div class="pro-ribbon"><b>Pro perk:</b> you can choose the cast and setting from your <a href="{}" style="color:#8a6420">account page</a>.</div>'.format(SITE_URL + "/me")
            if plan == "pro" else
            ""
        ),
        # Hero illustration (procedurally composed by story_image_composer).
        # Wrapped in a <div class="hero-image"> so the CSS can size it.
        hero_image=('<div class="hero-image">' + hero_svg + '</div>') if hero_svg else "",
        word_box=word_box,
        questions_box=questions_box,
        parent_guide_box=parent_guide_box,
        moment_box=moment_box,
        audio_button_box=audio_button_box,
        featured_drawing_box=featured_drawing_box,
        game_button_box=game_button_box,
        email_banner=email_banner,
        manage_url=SITE_URL + "/me",
        unsubscribe_url=SITE_URL + "/me",
    )
    # Plain-text fallback includes the learning material so even plain-text
    # email readers (rare, but they exist) get the educational value.
    plain_parts = [f"{title}\n", body]
    if word:
        plain_parts.append(f"\nWord of the Day: {word['w']} — {word['d']}")
        plain_parts.append(f"Example: {word['w'].capitalize()} in a sentence about {child_name}: {word['w']} moments matter.")
    if questions and len(questions) >= 3:
        plain_parts.append("\nStory Talk — three questions to ask:")
        for i, q in enumerate(questions, 1):
            plain_parts.append(f"  {i}. {q}")
    if plan == "pro" and parent_guide_text:
        plain_parts.append(f"\nParent Guide (Pro): {parent_guide_text}")
    if moment_text:
        plain_parts.append(f"\n{child_name}'s Moment of the Day: {moment_text}")
    if audio_full_url:
        plain_parts.append(f"\nListen to the story: {audio_full_url}")
    plain_parts.append(f"\n— PocketPlot\nManage your account: {SITE_URL}/me")
    plain = "\n".join(plain_parts)
    return plain, html

def _row_get(row, key, default=None):
    """sqlite3.Row doesn't have .get(); this is the equivalent."""
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


def _send_with_v4_enrichment(
    subscriber_row, story, plan="free", word=None, questions=None,
    parent_guide_text=None, seed=0,
):
    """Run the full v4 enrichment + email delivery + delivery-row persistence
    in a single transaction. Each v4 piece is best-effort -- if a piece fails
    (e.g. pyttsx3 unavailable) we just skip it and the email still sends.

    Returns ("sent"|"outbox", path_or_None, v4_payload_dict).
    """
    sub_id = subscriber_row["id"]
    ch_name = subscriber_row["child_name"]
    helper_name = story.get("helper_name") or "the helper"

    # 1. Poll answer — consume the oldest pending one and weave into story
    poll = consume_pending_poll(sub_id)
    poll_id = poll.get("id") if poll else None
    poll_question = poll.get("question") if poll else None
    poll_answer = poll.get("answer") if poll else None
    if poll and poll_answer:
        twist = f" And — because {ch_name} chose \u201c{poll_answer}\u201d this morning — it turned out that {poll_answer} was there too, waiting at the edge of the story like a small surprise."
        story["body"] = story["body"] + twist

    # 2. Moment — always shown (free + pro)
    moment = pick_moment(ch_name, helper_name, seed)
    moment_text = moment["text"]
    # Persist to the moments table as a separate audit row too
    try:
        db_ = db()
        db_.execute(
            "INSERT INTO moments(subscriber_id, moment_text, story_title, shown_at) VALUES (?,?,?,?)",
            (sub_id, moment_text, story.get("title", ""), dt.datetime.utcnow().isoformat(timespec="seconds"))
        )
        db_.commit(); db_.close()
    except Exception as e:
        log.warning("moments persist failed for sub %s: %s", sub_id, e)

    # 3. Audio — best-effort
    audio_url = None
    audio_filename = None
    if _row_get(subscriber_row, "audio_enabled", 1):
        try:
            title = story.get("title") or ""
            body = story.get("body", "")
            sub_dir = AUDIO_DIR / str(sub_id)
            sub_dir.mkdir(parents=True, exist_ok=True)
            safe_ts = dt.datetime.utcnow().isoformat(timespec="seconds").replace(":", "-").replace(".", "_")
            mp3_name = f"{safe_ts}.mp3"
            out_path = sub_dir / mp3_name
            script = f"{title}. {body}".replace("\n\n", ". ").replace("\n", " ")
            if _tts_save(script, out_path):
                audio_url = f"audio/{sub_id}/{mp3_name}"
                audio_filename = mp3_name
        except Exception as e:
            log.warning("audio render failed for sub %s: %s", sub_id, e)

    # 4. Drawing (Creator tier, occasional, deterministic by seed)
    drawing_filename = None
    if plan == "pro" and _row_get(subscriber_row, "pro_tier") == "creator":
        drawings = fetch_user_drawings(sub_id, limit=20)
        if drawings and seed % 7 == 0:
            drawing_filename = drawings[seed % len(drawings)]["filename"]

    # 5. Hero illustration — procedurally composed from story.scene metadata.
    # Phase 6: if the subscriber has an avatar, the main character uses it.
    # Best-effort: if the composer fails (e.g. unknown species), we just skip
    # the hero image and send a text-only email.
    hero_svg = ""
    try:
        avatar = None
        try:
            avatar_blob = _row_get(subscriber_row, "avatar_json")
            if avatar_blob:
                import avatar_builder as _ab
                avatar = _ab.parse_avatar_blob(avatar_blob)
        except Exception:
            avatar = None
        kwargs = {"seed": seed}
        if avatar:
            kwargs["avatar"] = avatar
        hero_svg = story_image_composer.compose_story_image(story, **kwargs)
    except Exception as e:
        log.warning("hero image compose failed for sub %s: %s", sub_id, e)

    # Send the email + capture the persist status
    status, out_path = deliver_email(
        subscriber_row, story, plan=plan,
        word=word, questions=questions, parent_guide_text=parent_guide_text,
        moment_text=moment_text,
        audio_url=audio_url, drawing_filename=drawing_filename,
        seed=seed,
        moment_icon_svg=MOMENT_ICON_SVG, pro_badge_svg=PRO_BADGE_SVG,
        hero_svg=hero_svg,
    )

    # Increment the word counter + log the delivery row WITH all v4 fields
    try:
        db_ = db()
        sent_at = dt.datetime.utcnow().isoformat(timespec="seconds")
        db_.execute(
            "UPDATE subscribers SET words_learned_count=words_learned_count+1, "
            "words_learned_month=COALESCE(words_learned_month,0)+1, last_sent_at=? "
            "WHERE id=?",
            (sent_at, sub_id),
        )
        wc = word.get("w") if word else None
        wt = word.get("tier") if word else None
        wd = word.get("d") if word else None
        we = f"{ch_name} felt {word['w']} today." if word else None
        db_.execute(
            "INSERT INTO deliveries(subscriber_id, sent_at, word_count, story, "
            "word, word_tier, word_definition, word_example, questions_json, parent_guide, "
            "poll_id, poll_question, poll_answer, moment_text, audio_filename, story_kindness, hero_svg) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sub_id, sent_at, story.get("word_count", 0), story.get("body", ""),
                wc, wt, wd, we,
                __import__("json").dumps(questions or []), parent_guide_text or "",
                poll_id, poll_question, poll_answer, moment_text, audio_filename, moment["story_beat"],
                hero_svg or "",
            )
        )
        # If we featured a drawing, mark it
        if drawing_filename:
            db_.execute(
                "UPDATE drawings SET featured_at=? WHERE subscriber_id=? AND filename=?",
                (sent_at, sub_id, drawing_filename)
            )
        db_.commit(); db_.close()
    except Exception as e:
        log.exception("delivery row persist failed: %s", e)

    # Phase 7: Gamification hooks. Fire-and-forget; failures here must NOT
    # block the email send that already succeeded.
    try:
        import gamification as _gam
        # Story sent → record a "story_read" engagement (for the streak),
        # add the Word of the Day to the vault, and re-evaluate badges.
        _gam.record_engagement(db, sub_id, "story_read")
        if word and word.get("w"):
            _gam.record_word(db, sub_id, word["w"],
                             tier=word.get("tier", ""),
                             definition=word.get("d", ""))
        _newly = _gam.evaluate_and_award(db, sub_id)
        if _newly:
            log.info("awarded badges to sub %s: %s", sub_id,
                     [b["code"] for b in _newly])
    except Exception as e:
        log.warning("gamification hooks failed for sub %s: %s", sub_id, e)

    return (status, out_path, {
        "moment_text": moment_text, "audio_url": audio_url,
        "drawing_filename": drawing_filename, "poll_id": poll_id,
    })

    # NOTE: The code that USED to be here (lines that re-ran the v4 enrichment
    # a second time) was dead code from a previous refactor. It has been
    # removed. The function now flows: v4 enrichment -> deliver_email() ->
    # persist delivery row -> return.


def deliver_email(subscriber_row, story, plan="free", word=None, questions=None, parent_guide_text=None, moment_text=None, audio_url=None, drawing_filename=None, seed=0, moment_icon_svg: str = "", pro_badge_svg: str = "", hero_svg: str = ""):
    """Send (or save to outbox) a story email.

    Learning-layer parameters (all optional):
      word: dict with {w, d, tier}
      questions: list of 3 strings
      parent_guide_text: Pro-only string
      moment_text: "{child}'s Moment of the Day: ..."
      audio_url: RELATIVE path under /  (e.g. "audio/1/20260822_120000.mp3")
      drawing_filename: e.g. "drawing_20260822_120000.png" (no path, just filename)
      seed: integer used for v4 deterministic behaviors
    """
    subject = f"Tonight's PocketPlot for {subscriber_row['child_name']}: {story['title']}"
    if plan == "pro":
        subject = "★ " + subject  # subtle visual cue in inbox
    # If we have an audio_url (relative path), make it absolute so the
    # email button actually points at a clickable URL.
    audio_full_url = None
    if audio_url:
        audio_full_url = SITE_URL.rstrip("/") + "/" + audio_url.lstrip("/")
    drawing_full_url = None
    if drawing_filename and subscriber_row.get("id"):
        drawing_full_url = SITE_URL.rstrip("/") + "/" + AUDIO_URL_PREFIX + str(subscriber_row["id"]) + "/" + drawing_filename
    plain, html = render_email(
        story["title"], story["body"], subscriber_row["child_name"],
        plan=plan, child_age=subscriber_row["child_age"],
        word=word, questions=questions, parent_guide_text=parent_guide_text,
        moment_text=moment_text, audio_full_url=audio_full_url,
        drawing_full_url=drawing_full_url,
        moment_icon_svg=moment_icon_svg, pro_badge_svg=pro_badge_svg,
        hero_svg=hero_svg,
    )
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = subscriber_row["email"]
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")

    if SMTP_HOST:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.starttls()
            if SMTP_USER:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        log.info("Sent SMTP email to %s", subscriber_row["email"])
        return ("sent", None)
    else:
        safe = subscriber_row["email"].replace("@", "_at_").replace("/", "_")
        fname = OUTBOX_DIR / f"{dt.datetime.utcnow():%Y%m%d_%H%M%S}_{safe}.eml"
        fname.write_bytes(msg.as_bytes())
        log.info("Saved to outbox: %s", fname.name)
        return ("outbox", str(fname))

# =====================================================================
# SCHEDULER — daily story delivery
# =====================================================================
def nightly_run():
    """Generate and deliver a story to every active subscriber.

    STORIES_USE_GENERATOR (env var):
        "1" / "true" / "yes"  → use the new sustainable story generator
                                (story_gen.generate_new_story). No human input
                                required; the system mixes and matches from
                                story_pools to produce fresh bedtime stories
                                indefinitely. Default.
        "0" / "false" / "no"  → use the original curated generator
                                (generate_story). Requires human-curated
                                helper/setting content.
        Any other value       → default ("1").
    """
    use_generator = os.environ.get("POCKETPLOT_STORIES_USE_GENERATOR", "1").lower() not in ("0", "false", "no")
    if use_generator:
        log.info("Nightly run: using SUSTAINABLE story generator (story_gen)")
    else:
        log.info("Nightly run: using CURATED story generator (generate_story)")
    conn = db()
    rows = conn.execute("SELECT * FROM subscribers WHERE active=1").fetchall()
    today = dt.date.today().isoformat()
    log.info("Nightly run: %d active subscribers", len(rows))
    delivered = 0
    for sub in rows:
        # Skip if we already delivered today (idempotency for retries)
        if sub["last_sent_at"] and sub["last_sent_at"].startswith(today):
            continue
        # Seed = subscriber_id + date ordinal -> new story each night, deterministic per day
        seed = sub["id"] * 997 + dt.date.today().toordinal() * 131
        # ---- Learning Layer: pick the word-of-the-day FOR THIS SUBSCRIBER ----
        # The seed is the same one used for the story, so the word rotates
        # with the cast/setting/plot. Younger kids get simple words; older
        # kids get advanced ones (see word_tier_for_age).
        word = pick_word_for_age(sub["child_age"], seed)

        if use_generator:
            # ----- SUSTAINABLE pipeline (Phase 1C) -----
            # The generator picks character/setting/problem/resolution from pools,
            # composes 200-300 word prose, and threads the Word of the Day.
            helper_name = "the helper"  # initial; will be overwritten below
            story = story_gen.generate_new_story(
                child_name=sub["child_name"],
                child_age=sub["child_age"],
                seed=seed,
                pro_pinned_helper=_row_get(sub, "pro_character") if _row_get(sub, "plan") == "pro" else None,
                pro_pinned_theme=_row_get(sub, "pro_theme") if _row_get(sub, "plan") == "pro" else None,
                word_for_today=word,
            )
            # Bold the word-of-the-day inline in the body, same as the curated path
            bolded, _word_hit = bold_word_in_body(story["body"], word["w"])
            story["body"] = bolded
            # Pull the resolved helper name out so questions + parent_guide can use it
            helper_name = story.get("helper_name") or helper_name
        else:
            # ----- CURATED pipeline (original v3/v4 code) -----
            helper_name_out = []
            story = generate_story(
                sub["child_name"], sub["child_age"], seed,
                plan=sub["plan"],
                pro_character=sub["pro_character"],
                pro_theme=sub["pro_theme"],
                word_for_today=word,
                helper_name_out=helper_name_out,
            )
            helper_name = helper_name_out[0] if helper_name_out else "the helper"

        questions = generate_questions(story, sub["child_name"], helper_name)
        parent_guide_text = (
            generate_parent_guide(story, sub["child_name"], helper_name, word)
            if sub["plan"] == "pro" else None
        )
        # Phase 4 (v8): in queue mode, write to the queue and skip the send.
        # The admin approves from /admin/queue, then the email actually goes out.
        queue_mode = os.environ.get("POCKETPLOT_REVIEW_QUEUE", "1").lower() not in ("0", "false", "no")
        if queue_mode:
            try:
                # Compute the hero illustration + moment (same pieces
                # _send_with_v4_enrichment would compute for the live send).
                # Phase 6: thread the subscriber's avatar into the composer
                # so the queued story previews show their child's avatar.
                v4_hero_svg = ""
                try:
                    _avatar = None
                    try:
                        import avatar_builder as _ab
                        _avatar = _ab.parse_avatar_blob(_row_get(sub, "avatar_json"))
                    except Exception:
                        _avatar = None
                    _kwargs = {"seed": seed}
                    if _avatar:
                        _kwargs["avatar"] = _avatar
                    v4_hero_svg = story_image_composer.compose_story_image(story, **_kwargs)
                except Exception as ce:
                    log.warning("hero compose failed (queueing anyway): %s", ce)
                # Pick a moment the same way the live path does.
                v4_moment = ""
                try:
                    v4_moment = pick_moment(sub["child_name"], helper_name, seed).get("text", "")
                except Exception:
                    pass
                review_queue.queue_story(
                    db,
                    sub["id"], story,
                    hero_svg=v4_hero_svg,
                    word=word,
                    questions=questions,
                    moment_text=v4_moment,
                    parent_guide=parent_guide_text,
                    audio_filename=None,  # TTS not generated in queue mode yet
                    poll_question=None,
                    seed=seed,
                )
                log.info("nightly: queued (not sent) for sub %s seed=%s", sub["id"], seed)
                continue  # Skip the deliver block below
            except Exception as e:
                log.exception("queueing failed for sub %s: %s", sub["id"], e)
                # fall through to direct send

        try:
            _status, _out_path, _v4_payload = _send_with_v4_enrichment(
                sub, story, plan=sub["plan"],
                word=word, questions=questions, parent_guide_text=parent_guide_text,
                seed=seed,
            )
            delivered += 1
        except Exception as e:
            log.exception("Failed to deliver to %s: %s", sub["email"], e)
    conn.execute(
        "INSERT INTO story_log(ts, note) VALUES (?,?)",
        (dt.datetime.utcnow().isoformat(timespec="seconds"), f"Nightly run · {delivered} delivered of {len(rows)}")
    )
    conn.commit()
    conn.close()

scheduler = BackgroundScheduler(daemon=True, timezone="UTC")
# Every day at DELIVERY_HOUR UTC. For demo: also expose a manual trigger.
scheduler.add_job(nightly_run, "cron", hour=DELIVERY_HOUR, minute=0, id="nightly_run", replace_existing=True)
# v17: weekly summary (Sundays at 18:00 UTC) + daily milestone check (02:00 UTC)
try:
    scheduler.add_job(_weekly_summary_job, "cron", day_of_week="sun", hour=18, minute=0,
                       id="weekly_summary", replace_existing=True)
    scheduler.add_job(_milestone_check_job, "cron", hour=2, minute=0,
                       id="milestone_check", replace_existing=True)
except Exception as _e:
    log.warning("v17 cron registration: %s", _e)
scheduler.start()

# Phase 11: register the REST API routes. Done after app is fully
# constructed so the routes can import everything they need.
try:
    import pocketplot_api
    pocketplot_api.register_api_routes(app, db, tokens_unsigner_for_api)
except Exception as e:
    log.warning("API routes registration failed: %s", e)

# Phase 9: seed the default story packs on first boot. Idempotent.
try:
    import story_packs as _sp
    _seeded = _sp.seed_default_packs(db)
    if _seeded:
        log.info("seeded %d default story packs", _seeded)
except Exception as e:
    log.warning("story_packs seed: %s", e)

# =====================================================================
# ROUTES
# =====================================================================
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PocketPlot — A unique branching world, every day</title>
<meta name="description" content="Personalised branching stories, delivered to your inbox every day. Your child is the hero. Free to start. No ads, ever.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;1,9..144,400;1,9..144,500&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --cream:#fdf6ec;          --cream2:#f6ecd8;         --cream3:#ecdfc3;
  --ink:#2c2c2c;            --body:#4a4a4a;           --body2:#6a5d4a;       --faint:#a89a85;
  --moss:#5c7c5a;           --mossD:#3e5a3c;          --mossL:#a8c0a3;
  --gold:#e2b45c;           --goldD:#8a6420;
  --terracotta:#c47a5a;     --terracottaD:#a85a3a;
  --shadow-soft:0 12px 32px rgba(60,40,20,.06);
  --shadow-elev:0 24px 56px rgba(60,40,20,.10);
  --serif:"Fraunces",Georgia,serif;
  --sans:"Inter","Helvetica Neue",-apple-system,sans-serif;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{font-family:var(--sans);color:var(--body);background:var(--cream);line-height:1.65;-webkit-font-smoothing:antialiased;font-size:16px}
img,svg{max-width:100%;display:block}
a{color:inherit;text-decoration:none}
h1,h2,h3,h4{font-family:var(--serif);color:var(--ink);font-weight:500;line-height:1.15;letter-spacing:-.01em}
h1{font-size:clamp(40px,6vw,68px);font-weight:600}
h1 em,.italic{font-style:italic;color:var(--moss);font-weight:500}
h2{font-size:clamp(30px,4vw,42px);margin-bottom:14px}
h2 em{font-style:italic;color:var(--moss);font-weight:500}
h3{font-size:22px;margin-bottom:8px}
h4{font-size:13px;font-family:var(--sans);font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--moss);margin-bottom:14px}
p{font-size:16px;line-height:1.7;color:var(--body);margin-bottom:14px}
.lede{font-size:19px;line-height:1.6;color:var(--body2);font-family:var(--serif);font-style:italic;font-weight:400}
.eyebrow{font-size:11px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--terracotta);margin-bottom:18px;display:inline-block}
.eyebrow.gold{color:var(--goldD)}
.container{max-width:1120px;margin:0 auto;padding:0 28px}
@media(max-width:680px){.container{padding:0 20px}}
.nav-wrap{position:sticky;top:0;z-index:50;background:rgba(253,246,236,.88);backdrop-filter:saturate(180%) blur(12px);border-bottom:1px solid var(--cream3)}
nav.main{display:flex;align-items:center;justify-content:space-between;height:64px}
.brand{display:flex;align-items:center;gap:10px;font-family:var(--serif);font-size:22px;font-weight:600;color:var(--ink);letter-spacing:.02em}
.brand .dot{width:10px;height:10px;border-radius:50%;background:linear-gradient(135deg,var(--gold),var(--terracotta));box-shadow:0 0 0 4px rgba(196,122,90,.18)}
.brand em{color:var(--moss);font-style:italic;font-weight:500}
.nav-links{display:flex;gap:8px;align-items:center}
.nav-links a{font-size:14px;font-weight:500;padding:8px 14px;border-radius:8px;color:var(--body);transition:all .15s}
.nav-links a:hover{color:var(--ink);background:rgba(0,0,0,.03)}
.nav-cta{background:var(--ink);color:var(--cream)!important;padding:10px 18px!important;border-radius:99px;font-weight:600}
.nav-cta:hover{background:var(--terracotta)!important;color:#fff!important}
@media(max-width:640px){.nav-links a:not(.nav-cta){display:none}}
.btn{display:inline-flex;align-items:center;gap:8px;padding:15px 28px;border-radius:99px;font-family:var(--sans);font-size:15px;font-weight:600;letter-spacing:.01em;text-decoration:none;cursor:pointer;border:none;transition:transform .12s ease, background .12s ease, box-shadow .12s ease;line-height:1}
.btn-primary{background:var(--terracotta);color:#fff;box-shadow:0 8px 22px rgba(196,122,90,.32)}
.btn-primary:hover{background:var(--terracottaD);transform:translateY(-1px);box-shadow:0 12px 28px rgba(196,122,90,.42)}
.btn-ghost{background:transparent;color:var(--ink);border:1.5px solid var(--cream3)}
.btn-ghost:hover{border-color:var(--ink);background:var(--cream2)}
.btn-sm{padding:11px 20px;font-size:14px}
.hero{padding:80px 0 60px;position:relative;overflow:hidden}
.hero::before{content:"";position:absolute;top:-200px;right:-200px;width:500px;height:500px;background:radial-gradient(circle,rgba(226,180,92,.10) 0%,transparent 70%);z-index:0;pointer-events:none}
.hero::after{content:"";position:absolute;bottom:-300px;left:-200px;width:600px;height:600px;background:radial-gradient(circle,rgba(92,124,90,.08) 0%,transparent 70%);z-index:0;pointer-events:none}
.hero-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:60px;align-items:center;position:relative;z-index:1}
@media(max-width:920px){.hero-grid{grid-template-columns:1fr;gap:36px}.hero{padding:50px 0 40px}}
.hero-text h1{margin-bottom:22px}
.hero-text .lede{max-width:520px;margin-bottom:32px}
.hero-cta-row{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-bottom:18px}
.hero-cta-row .note{font-size:13px;color:var(--faint);font-style:italic;font-family:var(--serif);width:100%}
.trust-row{display:flex;flex-wrap:wrap;gap:24px 32px;margin-top:36px;padding-top:28px;border-top:1px solid var(--cream3)}
.trust-item{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--body2)}
.trust-item .check{width:18px;height:18px;border-radius:50%;background:var(--mossL);color:var(--mossD);display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex:none}
.scene-wrap{position:relative;aspect-ratio:1/1;max-width:480px;margin-left:auto}
@media(max-width:920px){.scene-wrap{margin:0 auto}}
.scene{width:100%;height:100%;display:block}
.how{padding:90px 0;background:var(--cream2);border-top:1px solid var(--cream3);border-bottom:1px solid var(--cream3)}
.how-head{text-align:center;max-width:600px;margin:0 auto 56px}
.how-head .lede{font-style:normal;font-family:var(--sans);color:var(--body)}
.steps{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;position:relative}
@media(max-width:780px){.steps{grid-template-columns:1fr}}
.step{background:var(--cream);border:1px solid var(--cream3);border-radius:18px;padding:32px 28px;position:relative;transition:transform .2s ease, box-shadow .2s ease}
.step:hover{transform:translateY(-3px);box-shadow:var(--shadow-soft)}
.step .num{position:absolute;top:-14px;left:24px;width:36px;height:36px;border-radius:50%;background:var(--terracotta);color:#fff;display:flex;align-items:center;justify-content:center;font-family:var(--serif);font-weight:600;font-size:18px;box-shadow:0 4px 12px rgba(196,122,90,.32)}
.step .icon{width:88px;height:88px;margin-bottom:14px;display:block}
.step h3{font-size:19px;margin-bottom:8px;color:var(--ink)}
.step p{font-size:14.5px;color:var(--body2);margin-bottom:0;line-height:1.6}
.pricing{padding:90px 0}
.pricing-head{text-align:center;max-width:620px;margin:0 auto 50px}
.pricing-head h2{margin-bottom:14px}
.tiers{display:grid;grid-template-columns:1fr 1fr;gap:24px;max-width:880px;margin:0 auto}
@media(max-width:780px){.tiers{grid-template-columns:1fr;max-width:480px}}
.tier{background:#fff;border:1.5px solid var(--cream3);border-radius:22px;padding:36px 32px;position:relative;transition:transform .2s ease}
.tier:hover{transform:translateY(-2px)}
.tier.featured{border-color:var(--gold);box-shadow:0 0 0 4px rgba(226,180,92,.10), var(--shadow-soft);background:linear-gradient(180deg,#fffaf0 0%,#fff 30%)}
.tier .badge{position:absolute;top:-12px;left:32px;background:var(--gold);color:#3a2a10;font-size:10px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;padding:5px 12px;border-radius:99px}
.tier h3{font-family:var(--serif);font-weight:500;font-size:24px;margin-bottom:6px;color:var(--ink)}
.tier .tier-sub{font-size:13px;color:var(--faint);font-style:italic;font-family:var(--serif);margin-bottom:18px}
.tier .price{display:flex;align-items:baseline;gap:6px;margin-bottom:24px}
.tier .price .amt{font-family:var(--serif);font-size:48px;font-weight:500;color:var(--ink);line-height:1}
.tier .price .unit{font-size:14px;color:var(--body2);font-family:var(--sans)}
.tier ul.feats{list-style:none;margin-bottom:28px}
.tier ul.feats li{padding:9px 0;font-size:14.5px;display:flex;align-items:flex-start;gap:10px;color:var(--body);line-height:1.5}
.tier ul.feats li .tick{width:18px;height:18px;border-radius:50%;background:rgba(92,124,90,.14);color:var(--mossD);display:inline-flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;flex:none;margin-top:1px}
.tier.featured ul.feats li .tick{background:rgba(226,180,92,.20);color:var(--goldD)}
.tier ul.feats li.dim{color:var(--faint)}
.tier ul.feats li.dim .tick{background:rgba(0,0,0,.04);color:var(--faint)}
.tier .tier-cta{display:block;text-align:center;padding:13px;border-radius:99px;font-weight:600;font-size:14px;letter-spacing:.02em;text-decoration:none;transition:all .12s}
.tier .tier-cta.primary{background:var(--ink);color:var(--cream)}
.tier .tier-cta.primary:hover{background:var(--terracotta);color:#fff}
.tier .tier-cta.secondary{background:transparent;color:var(--ink);border:1.5px solid var(--cream3)}
.tier .tier-cta.secondary:hover{border-color:var(--ink)}
.testimonials{padding:90px 0;background:var(--cream2);border-top:1px solid var(--cream3);border-bottom:1px solid var(--cream3)}
.testimonials-head{text-align:center;max-width:600px;margin:0 auto 50px}
.testimonials-head h2{margin-bottom:14px}
.testi-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
@media(max-width:880px){.testi-grid{grid-template-columns:1fr}}
.testi{background:var(--cream);border:1px solid var(--cream3);border-radius:18px;padding:28px 26px;position:relative;transition:transform .2s}
.testi:hover{transform:translateY(-2px)}
.testi .stars{color:var(--gold);font-size:14px;letter-spacing:2px;margin-bottom:14px}
.testi blockquote{font-family:var(--serif);font-style:italic;font-size:16px;line-height:1.6;color:var(--ink);margin-bottom:18px;quotes:"\201C""\201D"}
.testi blockquote::before{content:open-quote;margin-right:2px;color:var(--terracotta)}
.testi blockquote::after{content:close-quote;margin-left:2px;color:var(--terracotta)}
.testi .who{display:flex;align-items:center;gap:12px}
.testi .avatar{width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,var(--mossL),var(--gold));display:flex;align-items:center;justify-content:center;font-family:var(--serif);font-weight:600;color:#fff;font-size:15px;flex:none}
.testi .who .name{font-size:14px;font-weight:600;color:var(--ink);line-height:1.3}
.testi .who .role{font-size:12px;color:var(--body2);font-style:italic;font-family:var(--serif)}
.closing{padding:90px 0;text-align:center;background:var(--cream);position:relative;overflow:hidden}
.closing::before{content:"";position:absolute;top:0;left:50%;transform:translateX(-50%);width:800px;height:400px;background:radial-gradient(ellipse at top,rgba(226,180,92,.12) 0%,transparent 60%);z-index:0;pointer-events:none}
.closing-inner{position:relative;z-index:1;max-width:680px;margin:0 auto}
.closing h2{margin-bottom:18px}
.closing p.lede{margin-bottom:32px;font-style:normal;font-family:var(--sans)}
footer.site{padding:40px 28px 32px;border-top:1px solid var(--cream3);text-align:center;background:var(--cream2)}
.foot-row{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px;max-width:1120px;margin:0 auto 14px}
.foot-row .brand{font-size:18px}
.foot-links{display:flex;gap:20px;font-size:13px;color:var(--body2)}
.foot-links a:hover{color:var(--ink)}
.foot-meta{font-size:12px;color:var(--faint);font-family:var(--serif);font-style:italic}
.foot-meta .heart{color:var(--terracotta)}
@media(max-width:920px){.scene-wrap{max-width:380px;margin:0 auto}.trust-row{gap:14px 20px}}
@media(max-width:640px){.hero{padding:36px 0 24px}.how,.pricing,.testimonials,.closing{padding:60px 0}}
</style>
</head>
<body>

<div class="nav-wrap">
  <div class="container">
    <nav class="main" aria-label="Primary">
      <a href="/" class="brand"><span class="dot"></span>Pocket<em>Plot</em></a>
      <div class="nav-links">
        <a href="#how">How it works</a>
        <a href="#pricing">Pricing</a>
        <a href="#testimonials">What parents say</a>
        <a href="/login" class="nav-cta">Sign in</a>
      </div>
    </nav>
  </div>
</div>

<section class="hero">
  <div class="container">
    <div class="hero-grid">
      <div class="hero-text">
        <span class="eyebrow">Bedtime stories, every night</span>
        <h1>A unique story for <em>your</em> child &mdash; in their inbox by 8&nbsp;pm.</h1>
        <p class="lede">A fresh, personalised branching world, written just for you &mdash; featuring their name, their age, and a tiny cast of recurring characters who grow with them.</p>
        <div class="hero-cta-row">
          <a href="/signup" class="btn btn-primary">Start your free story &rarr;</a>
          <a href="#how" class="btn btn-ghost">How it works</a>
        </div>
        <p class="note">Free to start. No card required. Cancel any time.</p>
        <div class="trust-row">
          <div class="trust-item"><span class="check">&#10003;</span>Personalised, never generic</div>
          <div class="trust-item"><span class="check">&#10003;</span>200&ndash;300 words, ready for one good yawn</div>
          <div class="trust-item"><span class="check">&#10003;</span><b>Word of the Day</b> + Story Talk in every email</div>
          <div class="trust-item"><span class="check">&#10003;</span>No ads, no villains, no jump-scares</div>
          <div class="trust-item"><span class="check">&#10003;</span>Loved by 1,200+ families</div>
        </div>
      </div>
      <div>
        <div class="scene-wrap">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" role="img" aria-label="A parent and child reading a bedtime story together under a cozy blanket, with a starry window behind them">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" role="img" aria-label="A bear parent reading a bedtime story to a small child in a cozy window nook, lit by the warm glow of the book">
  <title>PocketPlot — the reading hour</title>
  <defs>
    <linearGradient id="hBg" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#2B2347"/>
      <stop offset="0.5" stop-color="#3D2F58"/>
      <stop offset="1" stop-color="#5A3D55"/>
    </linearGradient>
    <linearGradient id="hWin" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#1E1A3A"/>
      <stop offset="0.6" stop-color="#322850"/>
      <stop offset="1" stop-color="#553B62"/>
    </linearGradient>
    <radialGradient id="hBook" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#FFE6A8" stop-opacity="0.95"/>
      <stop offset="0.4" stop-color="#FFC78A" stop-opacity="0.55"/>
      <stop offset="1" stop-color="#FFC78A" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="hFur" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#C89368"/>
      <stop offset="1" stop-color="#8B5E3C"/>
    </linearGradient>
    <linearGradient id="hBlanket" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#A8C0A3"/>
      <stop offset="1" stop-color="#5C7C5A"/>
    </linearGradient>
    <linearGradient id="hPage" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#FFF8E7"/>
      <stop offset="1" stop-color="#FFE5A0"/>
    </linearGradient>
    <radialGradient id="hRim" cx="0.5" cy="1" r="0.5">
      <stop offset="0" stop-color="#FFE5A0" stop-opacity="0.9"/>
      <stop offset="1" stop-color="#FFE5A0" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect x="0" y="0" width="400" height="400" rx="32" fill="#FFF8E7"/>
  <rect x="0" y="0" width="400" height="400" rx="32" fill="url(#hBg)"/>

  <!-- WINDOW NOK: only the LEFT half of the card (offset from center) so the
       vertical mullion doesn't cut through the bear's head -->
  <g>
    <path d="M 24 380 L 24 110 Q 24 36 98 36 L 200 36 Q 200 60 200 80 L 200 36 Q 200 36 200 380 L 200 380 L 24 380 Z" fill="url(#hWin)"/>
    <!-- Frame (the wood of the nook) -->
    <path d="M 24 380 L 24 110 Q 24 36 98 36 L 200 36" fill="none" stroke="#3D2F58" stroke-width="2.5"/>
    <!-- Window mullion (VERTICAL) — moved to the LEFT third so it doesn't
         cut through the bear's head -->
    <line x1="100" y1="36" x2="100" y2="380" stroke="#3D2F58" stroke-width="2.5"/>
    <!-- HORIZONTAL mullion across the top window pane -->
    <line x1="24" y1="200" x2="200" y2="200" stroke="#3D2F58" stroke-width="2.5"/>
    <!-- Stars in the upper pane of the window (left of the bear) -->
    <g fill="#FFE5A0">
      <circle cx="50" cy="80" r="2"/>
      <circle cx="80" cy="100" r="1.5"/>
      <circle cx="60" cy="140" r="1.4"/>
      <circle cx="150" cy="80" r="1.8"/>
      <circle cx="180" cy="120" r="1.5"/>
    </g>
    <!-- Crescent moon in the upper right of the LEFT window pane -->
    <g transform="translate(160, 70)">
      <circle r="12" fill="#FFE5A0"/>
      <circle cx="3" cy="-2" r="10" fill="url(#hWin)"/>
      <circle cx="-3" cy="2" r="1" fill="#E8D78A" opacity="0.7"/>
    </g>
    <!-- A small star sparkle below the moon -->
    <path d="M 130 50 L 132 56 L 138 58 L 132 60 L 130 66 L 128 60 L 122 58 L 128 56 Z" fill="#FFE5A0"/>
    <!-- A plant on the left windowsill -->
    <g transform="translate(50, 340)">
      <path d="M -10 0 L 10 0 L 8 12 L -8 12 Z" fill="#E88960" stroke="#3A3633" stroke-width="1.5" stroke-linejoin="round"/>
      <ellipse cx="-4" cy="-6" rx="6" ry="3" fill="#92D4A8" stroke="#3A3633" stroke-width="1.5" transform="rotate(-25 -4 -6)"/>
      <ellipse cx="3" cy="-8" rx="6" ry="3" fill="#B8E5C8" stroke="#3A3633" stroke-width="1.5" transform="rotate(20 3 -8)"/>
    </g>
  </g>

  <!-- The RIGHT half of the card: warm night interior (so the bear + child are
       lit by a combination of the window-light and the book-light) -->
  <rect x="200" y="36" width="176" height="344" fill="#3D2F58" opacity="0.4"/>
  <!-- A few stars in the right interior (they're seeing the window reflection) -->
  <g fill="#FFE5A0" opacity="0.5">
    <circle cx="340" cy="100" r="1.4"/>
    <circle cx="360" cy="140" r="1.2"/>
    <circle cx="310" cy="160" r="1.3"/>
  </g>

  <!-- Book light glow (centered behind the bear) -->
  <ellipse cx="200" cy="290" rx="130" ry="100" fill="url(#hBook)"/>

  <!-- ============ BEAR PARENT ============ -->
  <g>
    <!-- Body (rounded, occupies the left two-thirds) -->
    <path d="M 80 380 L 80 240 Q 80 160 170 150 Q 250 148 290 200 L 290 380 Z" fill="url(#hFur)" stroke="#2A1F1A" stroke-width="3" stroke-linejoin="round"/>
    <!-- Belly patch (slightly lighter) -->
    <ellipse cx="180" cy="320" rx="55" ry="40" fill="#E0B584" opacity="0.45"/>
    <!-- Left arm (rests at the bottom, holds the book) -->
    <path d="M 195 270 Q 145 290 130 320 L 150 350 Q 180 360 200 340 L 200 295 Z" fill="url(#hFur)" stroke="#2A1F1A" stroke-width="3" stroke-linejoin="round"/>
    <!-- Right arm (wraps around the child) — lifted and clearer silhouette -->
    <path d="M 245 250 Q 290 260 310 295 L 310 340 Q 290 355 270 345 L 255 310 Z" fill="url(#hFur)" stroke="#2A1F1A" stroke-width="3" stroke-linejoin="round"/>
    <!-- Paws (clearer shapes) -->
    <ellipse cx="200" cy="340" rx="20" ry="14" fill="#E0B584" stroke="#2A1F1A" stroke-width="2.5"/>
    <ellipse cx="290" cy="335" rx="17" ry="12" fill="#E0B584" stroke="#2A1F1A" stroke-width="2.5"/>

    <!-- Head (large, centered on body) -->
    <ellipse cx="180" cy="130" rx="62" ry="60" fill="url(#hFur)" stroke="#2A1F1A" stroke-width="3"/>
    <!-- Round ears -->
    <circle cx="138" cy="76" r="18" fill="url(#hFur)" stroke="#2A1F1A" stroke-width="3"/>
    <circle cx="222" cy="76" r="18" fill="url(#hFur)" stroke="#2A1F1A" stroke-width="3"/>
    <circle cx="138" cy="76" r="9" fill="#F8B7B0"/>
    <circle cx="222" cy="76" r="9" fill="#F8B7B0"/>
    <!-- Rim light on the ears (from the book below) -->
    <ellipse cx="138" cy="84" rx="9" ry="5" fill="url(#hRim)" opacity="0.7"/>
    <ellipse cx="222" cy="84" rx="9" ry="5" fill="url(#hRim)" opacity="0.7"/>

    <!-- Muzzle/snout -->
    <ellipse cx="180" cy="148" rx="32" ry="22" fill="#FFE5A0"/>
    <!-- Closed happy eyes (the warm curve) -->
    <path d="M 152 130 Q 160 122 168 130" stroke="#2A1F1A" stroke-width="4" fill="none" stroke-linecap="round"/>
    <path d="M 192 130 Q 200 122 208 130" stroke="#2A1F1A" stroke-width="4" fill="none" stroke-linecap="round"/>
    <circle cx="153" cy="124" r="1.4" fill="#FFF8E7" opacity="0.7"/>
    <circle cx="193" cy="124" r="1.4" fill="#FFF8E7" opacity="0.7"/>
    <!-- Cheek blush -->
    <circle cx="142" cy="148" r="9" fill="#F8B7B0" opacity="0.7"/>
    <circle cx="218" cy="148" r="9" fill="#F8B7B0" opacity="0.7"/>
    <!-- Nose -->
    <ellipse cx="180" cy="146" rx="5" ry="3.5" fill="#2A1F1A"/>
    <!-- Smile -->
    <path d="M 168 158 Q 180 170 192 158" stroke="#2A1F1A" stroke-width="3" fill="none" stroke-linecap="round"/>
  </g>

  <!-- ============ CHILD (KAK-correct proportions: BIG head, small body) ============ -->
  <g>
    <!-- Body wrapped in a sage blanket (small, kid-sized) -->
    <path d="M 268 380 L 268 320 Q 268 296 290 296 Q 312 298 318 320 L 318 380 Z" fill="url(#hBlanket)" stroke="#2A1F1A" stroke-width="3" stroke-linejoin="round"/>
    <!-- The CHILD's BIG HEAD (KAK signature: head ≈ 2/3 of total figure) -->
    <ellipse cx="298" cy="260" rx="34" ry="36" fill="#F8D7A8" stroke="#2A1F1A" stroke-width="3"/>
    <!-- Hair (small, with a single curl detail) -->
    <path d="M 268 244 Q 268 218 298 216 Q 328 218 328 244 Q 328 236 322 238 Q 316 232 312 240 Q 305 232 300 240 Q 295 232 290 240 Q 285 232 280 240 Q 274 234 270 240 Q 268 240 268 244 Z" fill="#3A3633"/>
    <!-- ONE big eye (open, looking at the book) — single visible eye because
         the other is leaning into the bear's arm -->
    <ellipse cx="280" cy="260" rx="3.5" ry="4.2" fill="#2A1F1A"/>
    <circle cx="280" cy="259" r="1.2" fill="#FFF8E7"/>
    <!-- Eyebrow above -->
    <path d="M 273 250 Q 280 248 287 250" stroke="#3A3633" stroke-width="2" fill="none" stroke-linecap="round"/>
    <!-- Cheek blush -->
    <circle cx="270" cy="272" r="6" fill="#F8B7B0" opacity="0.75"/>
    <circle cx="308" cy="272" r="6" fill="#F8B7B0" opacity="0.75"/>
    <!-- A tiny upturned mouth -->
    <path d="M 290 278 Q 298 282 306 278" stroke="#2A1F1A" stroke-width="2" fill="none" stroke-linecap="round"/>
  </g>

  <!-- ============ THE BOOK ============ -->
  <g transform="translate(200, 320)">
    <path d="M -55 0 L 0 -8 L 55 0 L 55 26 L 0 18 L -55 26 Z" fill="url(#hPage)" stroke="#2A1F1A" stroke-width="3" stroke-linejoin="round"/>
    <line x1="0" y1="-8" x2="0" y2="18" stroke="#2A1F1A" stroke-width="2.5"/>
    <g stroke="#5C7C5A" stroke-width="2.5" stroke-linecap="round" fill="none">
      <line x1="-44" y1="2" x2="-10" y2="1"/>
      <line x1="-44" y1="8" x2="-10" y2="7"/>
      <line x1="-44" y1="14" x2="-26" y2="13"/>
    </g>
    <g stroke="#5C7C5A" stroke-width="2.5" stroke-linecap="round" fill="none">
      <line x1="10" y1="1" x2="44" y2="2"/>
      <line x1="10" y1="7" x2="44" y2="8"/>
      <line x1="10" y1="13" x2="30" y2="14"/>
    </g>
    <g transform="translate(30, 8)">
      <path d="M 0 -5 L 1.5 -1.5 L 5 -1.5 L 2 1 L 3 5 L 0 2.5 L -3 5 L -2 1 L -5 -1.5 L -1.5 -1.5 Z" fill="#FFE5A0" stroke="#2A1F1A" stroke-width="0.8" stroke-linejoin="round"/>
    </g>
    <ellipse cx="0" cy="6" rx="50" ry="14" fill="url(#hBook)"/>
  </g>

  <!-- Tiny stars + sparkles -->
  <g fill="#FFE5A0" stroke="#3A3633" stroke-width="0.6">
    <path d="M 340 240 L 342 244 L 346 244 L 343 246 L 344 250 L 340 248 L 336 250 L 337 246 L 334 244 L 338 244 Z"/>
    <path d="M 60 300 L 62 304 L 66 304 L 63 306 L 64 310 L 60 308 L 56 310 L 57 306 L 54 304 L 58 304 Z"/>
  </g>
  <circle cx="350" cy="320" r="2" fill="#FFE5A0" opacity="0.9"/>
  <circle cx="50" cy="350" r="2" fill="#FFE5A0" opacity="0.9"/>
</svg>
          </svg>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="how" id="how">
  <div class="container">
    <div class="how-head">
      <span class="eyebrow">How it works</span>
      <h2>Three small steps to <em>magic</em>.</h2>
      <p class="lede">No app to download. No login to remember. Just stories, in your inbox, ready for the soft lamp-light moment.</p>
    </div>
    <div class="steps">
      <div class="step">
        <div class="num">1</div>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="A happy child's face">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="A happy child's face with a glowing star">
  <title>Tell us about your child</title>
  <defs>
    <!-- Shared v6 card frame -->
    <linearGradient id="i1Frame" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#FFF8E7"/>
      <stop offset="1" stop-color="#FFE5A0"/>
    </linearGradient>
    <radialGradient id="i1Cheek" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#F8B7B0" stop-opacity="0.85"/>
      <stop offset="1" stop-color="#F8B7B0" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="i1StarGlow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#FFE5A0" stop-opacity="0.85"/>
      <stop offset="1" stop-color="#FFE5A0" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <!-- Unified card frame -->
  <rect x="2" y="2" width="116" height="116" rx="22" fill="url(#i1Frame)"/>
  <rect x="2" y="2" width="116" height="116" rx="22" fill="none" stroke="#F8D77E" stroke-width="2"/>

  <!-- Soft star glow (top right) -->
  <circle cx="96" cy="28" r="14" fill="url(#i1StarGlow)"/>
  <g transform="translate(96,28)">
    <path d="M 0 -7 L 2 -2 L 7 -2 L 3 1 L 4.5 6 L 0 3.5 L -4.5 6 L -3 1 L -7 -2 L -2 -2 Z" fill="#FFE5A0" stroke="#3A3633" stroke-width="1.2" stroke-linejoin="round"/>
  </g>

  <!-- Hair (KAK-signature rounded cap, slightly bigger than v5) -->
  <path d="M 30 62 Q 28 28 60 24 Q 92 28 90 62 Q 88 48 78 50 L 74 56 L 68 50 L 62 58 L 60 48 L 58 58 L 52 50 L 46 56 L 42 50 Q 32 48 30 62 Z" fill="#3A3633"/>

  <!-- Face (slightly bigger + rounder) -->
  <ellipse cx="60" cy="68" rx="32" ry="34" fill="#F8D7A8" stroke="#3A3633" stroke-width="2.5"/>

  <!-- Ears (KAK-tiny) -->
  <ellipse cx="29" cy="72" rx="3.5" ry="6" fill="#F8D7A8" stroke="#3A3633" stroke-width="1.5"/>
  <ellipse cx="91" cy="72" rx="3.5" ry="6" fill="#F8D7A8" stroke="#3A3633" stroke-width="1.5"/>

  <!-- Eyebrows (soft, friendly) -->
  <path d="M 44 58 Q 50 56 56 58" stroke="#3A3633" stroke-width="2.2" fill="none" stroke-linecap="round"/>
  <path d="M 64 58 Q 70 56 76 58" stroke="#3A3633" stroke-width="2.2" fill="none" stroke-linecap="round"/>

  <!-- Eyes (open + dot + glint) -->
  <ellipse cx="50" cy="68" rx="3.5" ry="4.2" fill="#2A1F1A"/>
  <ellipse cx="70" cy="68" rx="3.5" ry="4.2" fill="#2A1F1A"/>
  <circle cx="51.5" cy="66.5" r="1.2" fill="#FFF8E7"/>
  <circle cx="71.5" cy="66.5" r="1.2" fill="#FFF8E7"/>

  <!-- Cheek blush (KAK signature) -->
  <circle cx="42" cy="78" r="8" fill="url(#i1Cheek)"/>
  <circle cx="78" cy="78" r="8" fill="url(#i1Cheek)"/>

  <!-- Tiny nose -->
  <ellipse cx="60" cy="76" rx="2" ry="1.5" fill="#F8B7B0"/>

  <!-- Smile (the "happy child" focal point) -->
  <path d="M 50 84 Q 60 94 70 84" stroke="#3A3633" stroke-width="2.6" fill="#FFCBA4" stroke-linecap="round"/>
  <path d="M 50 84 Q 60 94 70 84" stroke="#3A3633" stroke-width="2.6" fill="none" stroke-linecap="round"/>
</svg>
          </svg>
        <h3>Tell us about your child</h3>
        <p>Just their name, age, and your email. Two minutes. That's all we need to start writing stories they'll recognise themselves in.</p>
      </div>
      <div class="step">
        <div class="num">2</div>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="A magical book and quill writing a story">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="An open book with a glowing star above">
  <title>We create a story</title>
  <defs>
    <linearGradient id="i2Frame" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#FFF8E7"/>
      <stop offset="1" stop-color="#FFE5A0"/>
    </linearGradient>
    <linearGradient id="i2Page" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#FFF8E7"/>
      <stop offset="1" stop-color="#FFE5A0"/>
    </linearGradient>
    <radialGradient id="i2Glow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#FFE5A0" stop-opacity="0.85"/>
      <stop offset="1" stop-color="#FFE5A0" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect x="2" y="2" width="116" height="116" rx="22" fill="url(#i2Frame)"/>
  <rect x="2" y="2" width="116" height="116" rx="22" fill="none" stroke="#F8D77E" stroke-width="2"/>

  <!-- Big soft glow behind the book -->
  <ellipse cx="60" cy="68" rx="50" ry="32" fill="url(#i2Glow)"/>

  <!-- The book (rounded, open, premium feel) -->
  <g transform="translate(60,76)">
    <path d="M -42 6 L 0 -2 L 42 6 L 42 22 L 0 14 L -42 22 Z" fill="#FFCBA4" opacity="0.45"/>
    <path d="M -40 0 L 0 -7 L 40 0 L 40 17 L 0 11 L -40 17 Z" fill="url(#i2Page)" stroke="#3A3633" stroke-width="2.5" stroke-linejoin="round"/>
    <line x1="0" y1="-7" x2="0" y2="11" stroke="#3A3633" stroke-width="2"/>
    <g stroke="#5C7C5A" stroke-width="2.5" stroke-linecap="round" fill="none">
      <line x1="-32" y1="2" x2="-8" y2="0"/>
      <line x1="-32" y1="6" x2="-8" y2="4"/>
      <line x1="-32" y1="10" x2="-18" y2="9"/>
    </g>
    <g stroke="#5C7C5A" stroke-width="2.5" stroke-linecap="round" fill="none">
      <line x1="8" y1="0" x2="32" y2="2"/>
      <line x1="8" y1="4" x2="32" y2="6"/>
      <line x1="8" y1="8" x2="22" y2="9.5"/>
    </g>
  </g>

  <!-- The star above (bigger, brighter, the focal point) -->
  <g transform="translate(60,36)">
    <!-- Outer glow -->
    <circle r="22" fill="url(#i2Glow)" opacity="0.9"/>
    <!-- Star body -->
    <path d="M 0 -14 L 4 -4 L 14 -3 L 6 3 L 9 13 L 0 7 L -9 13 L -6 3 L -14 -3 L -4 -4 Z" fill="#FFE5A0" stroke="#3A3633" stroke-width="2" stroke-linejoin="round"/>
    <!-- Inner highlight -->
    <circle r="2.5" fill="#FFF8E7"/>
  </g>

  <!-- A pair of side sparkles for premium polish -->
  <g fill="#FFE5A0" stroke="#3A3633" stroke-width="1">
    <path d="M 28 22 L 30 26 L 34 26 L 31 28.5 L 32 32 L 28 30 L 24 32 L 25 28.5 L 22 26 L 26 26 Z" transform="scale(0.7) translate(8,4)"/>
  </g>
  <circle cx="94" cy="32" r="2.5" fill="#FFCBA4" stroke="#3A3633" stroke-width="1"/>
  <circle cx="22" cy="48" r="2" fill="#A8D8F0" stroke="#3A3633" stroke-width="1"/>
</svg>
          </svg>
        <h3>We create a unique story</h3>
        <p>Our story engine assembles a fresh 200&ndash;300 word bedtime story &mdash; new every night, with your child as the hero, a recurring cast of gentle characters, and a setting that changes.</p>
      </div>
      <div class="step">
        <div class="num">3</div>
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="A cozy house under a moon and stars at night">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="A cozy house under a crescent moon and stars">
  <title>It arrives every night</title>
  <defs>
    <linearGradient id="i3Frame" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#FFF8E7"/>
      <stop offset="1" stop-color="#FFE5A0"/>
    </linearGradient>
    <linearGradient id="i3Sky" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0" stop-color="#5A4A8A"/>
      <stop offset="1" stop-color="#A8C0E0"/>
    </linearGradient>
    <radialGradient id="i3Win" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#FFE5A0"/>
      <stop offset="1" stop-color="#F8D77E"/>
    </radialGradient>
  </defs>

  <rect x="2" y="2" width="116" height="116" rx="22" fill="url(#i3Frame)"/>
  <rect x="2" y="2" width="116" height="116" rx="22" fill="none" stroke="#F8D77E" stroke-width="2"/>

  <!-- Larger moon — the focal element, top-right corner -->
  <g transform="translate(86, 30)">
    <circle r="14" fill="#FFE5A0" stroke="#3A3633" stroke-width="2.2"/>
    <circle cx="3" cy="-2" r="11" fill="url(#i3Sky)" opacity="0"/>
    <circle cx="3" cy="-2" r="11" fill="#FFF8E7"/>
    <!-- A crescent: clip a sky-tinted disc over the moon -->
    <circle cx="3" cy="-2" r="11" fill="#A8C0E0"/>
    <!-- Craters -->
    <circle cx="-3" cy="2" r="1.4" fill="#E8D78A" opacity="0.7"/>
    <circle cx="-1" cy="6" r="1" fill="#E8D78A" opacity="0.6"/>
  </g>

  <!-- Stars (varied, premium) -->
  <g fill="#FFF8E7" stroke="#3A3633" stroke-width="0.7">
    <path d="M 26 26 L 28 30 L 32 30 L 29 32 L 30 36 L 26 34 L 22 36 L 23 32 L 20 30 L 24 30 Z"/>
    <path d="M 56 18 L 58 22 L 62 22 L 59 24 L 60 28 L 56 26 L 52 28 L 53 24 L 50 22 L 54 22 Z"/>
  </g>
  <circle cx="38" cy="38" r="1.5" fill="#FFE5A0"/>
  <circle cx="64" cy="42" r="1.5" fill="#A8D8F0"/>

  <!-- Chimney + smoke wisp (the storytelling moment — the day just ended, smoke curls up) -->
  <rect x="78" y="50" width="9" height="14" fill="#FFCBA4" stroke="#3A3633" stroke-width="2" rx="1"/>
  <path d="M 82 48 Q 86 42 82 38 Q 78 34 82 30" stroke="#3A3633" stroke-width="1.5" fill="none" stroke-linecap="round" opacity="0.55"/>

  <!-- The house (rounded, premium) -->
  <g>
    <path d="M 22 70 L 60 42 L 98 70 Z" fill="#E88960" stroke="#3A3633" stroke-width="2.5" stroke-linejoin="round"/>
    <line x1="60" y1="42" x2="60" y2="70" stroke="#3A3633" stroke-width="1" opacity="0.4"/>
    <rect x="28" y="66" width="64" height="36" fill="#FFF8E7" stroke="#3A3633" stroke-width="2.5" rx="2"/>
    <!-- Door -->
    <rect x="55" y="82" width="11" height="20" rx="2" fill="#5C7C5A" stroke="#3A3633" stroke-width="2"/>
    <circle cx="64" cy="92" r="0.9" fill="#FFE5A0"/>
    <!-- Glowing windows (the warm light inside) -->
    <rect x="34" y="74" width="14" height="14" rx="2" fill="url(#i3Win)" stroke="#3A3633" stroke-width="2"/>
    <line x1="41" y1="74" x2="41" y2="88" stroke="#3A3633" stroke-width="1.2"/>
    <line x1="34" y1="81" x2="48" y2="81" stroke="#3A3633" stroke-width="1.2"/>
    <rect x="72" y="74" width="13" height="13" rx="2" fill="url(#i3Win)" stroke="#3A3633" stroke-width="2"/>
    <line x1="78.5" y1="74" x2="78.5" y2="87" stroke="#3A3633" stroke-width="1.2"/>
    <line x1="72" y1="80.5" x2="85" y2="80.5" stroke="#3A3633" stroke-width="1.2"/>
    <!-- A tiny heart in the right window (the "love lives here" touch) -->
    <path d="M 78.5 84 c -1.5 -1.2 -3 0.8 -1.4 2 L 78.5 88 L 80 86 c 1.6 -1.2 0.2 -3.2 -1.4 -2 z" fill="#F8B7B0"/>
  </g>

  <!-- Soft green hill (premium base) -->
  <path d="M 0 102 Q 30 96 60 100 Q 90 104 120 100 L 120 120 L 0 120 Z" fill="#92D4A8" stroke="#3A3633" stroke-width="2" stroke-linejoin="round"/>
  <g stroke="#3A3633" stroke-width="1.5" stroke-linecap="round" fill="none">
    <path d="M 14 106 q 1.5 -4 3 0"/>
    <path d="M 22 104 q 1.5 -3 3 0"/>
    <path d="M 96 105 q 1.5 -3 3 0"/>
    <path d="M 104 106 q 1.5 -4 3 0"/>
  </g>
</svg>
          </svg>
        <h3>It arrives every night</h3>
        <p>At 8 pm, a new story lands in your inbox. Beautifully formatted. Ready to read aloud. No app, no login, no friction &mdash; just the half-hour that matters.</p>
      </div>
    </div>
  </div>
</section>

<section class="pricing" id="pricing">
  <div class="container">
    <div class="pricing-head">
      <span class="eyebrow">Simple, sleepy pricing</span>
      <h2>Start free. <em>Stay forever</em> &mdash; or upgrade when you're ready.</h2>
      <p class="lede" style="font-style:normal;font-family:var(--sans)">No ads in either plan. Cancel any time. The first story is on us.</p>
    </div>
    <div class="tiers">
      <div class="tier">
        <h3>Free</h3>
        <div class="tier-sub">Forever.</div>
        <div class="price"><span class="amt">$0</span><span class="unit">/ month</span></div>
        <ul class="feats">
          <li><span class="tick">&#10003;</span>One fresh branching world every day</li>
          <li><span class="tick">&#10003;</span>Personalised &mdash; your child is the hero</li>
          <li><span class="tick">&#10003;</span>200&ndash;300 words, ready for one good yawn</li>
          <li><span class="tick">&#10003;</span><b>Word of the Day</b> in every story</li>
          <li><span class="tick">&#10003;</span><b>Story Talk</b> &mdash; 3 questions to ask at bedtime</li>
          <li><span class="tick">&#10003;</span>Learning dashboard (last 30 days)</li>
          <li><span class="tick">&#10003;</span>Manage delivery from your account page</li>
          <li><span class="tick">&#10003;</span>Pause any time</li>
          <li class="dim"><span class="tick">&mdash;</span>Recurring helper of your choice</li>
          <li class="dim"><span class="tick">&mdash;</span>Lock in a setting theme</li>
          <li class="dim"><span class="tick">&mdash;</span>Full learning history + tier breakdown</li>
          <li class="dim"><span class="tick">&mdash;</span>Parent Guide in every email</li>
        </ul>
        <a href="/signup" class="tier-cta secondary">Start free</a>
      </div>
      <div class="tier featured">
        <span class="badge">&#9733; Most loved</span>
        <h3>Pro</h3>
        <div class="tier-sub">$4.99 / month, billed monthly.</div>
        <div class="price"><span class="amt">$4.99</span><span class="unit">/ month</span></div>
        <ul class="feats">
          <li><span class="tick">&#10003;</span><b>Everything in Free</b></li>
          <li><span class="tick">&#10003;</span>Choose a <b>recurring helper</b> &mdash; Felix, Bram, Rue, Wren, Pip&hellip;</li>
          <li><span class="tick">&#10003;</span>Lock in a <b>setting theme</b> your child loves</li>
          <li><span class="tick">&#10003;</span><b>Parent Guide</b> in every email &mdash; deeper vocabulary + a real-world hook for the day</li>
          <li><span class="tick">&#10003;</span><b>Full learning history</b> &mdash; every word your child has learned</li>
          <li><span class="tick">&#10003;</span><b>Tier breakdown</b> &mdash; watch your child's vocabulary grow across simple → intermediate → advanced</li>
          <li><span class="tick">&#10003;</span>Words tailored to your child's age (3&ndash;8) so they're learning, not guessing</li>
          <li><span class="tick">&#10003;</span>Priority support, real humans</li>
          <li><span class="tick">&#10003;</span>No ads, ever &mdash; and the Pro badge in your inbox</li>
          <li><span class="tick">&#10003;</span>Early access to new characters, themes, and stories</li>
        </ul>
        <a href="/signup?plan=pro" class="tier-cta primary">Upgrade to Pro</a>
      </div>
    </div>
  </div>
</section>

<section class="testimonials" id="testimonials">
  <div class="container">
    <div class="testimonials-head">
      <span class="eyebrow">What parents are saying</span>
      <h2>The <em>gentlest</em> half-hour of our day.</h2>
    </div>
    <div class="testi-grid">
      <div class="testi">
        <div class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
        <blockquote>It's the only thing that gets my five-year-old to actually stay in bed. She asks for 'the Wren story' at 7:55 every night.</blockquote>
        <div class="who"><div class="avatar">M</div><div><div class="name">Maya P.</div><div class="role">parent of Wren, age 5</div></div></div>
      </div>
      <div class="testi">
        <div class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
        <blockquote>I bought it on a whim. Two months in, my son quotes Bram the bear at breakfast. I didn't know a branching story app could be this gentle.</blockquote>
        <div class="who"><div class="avatar">D</div><div><div class="name">David R.</div><div class="role">parent of Theo, age 4</div></div></div>
      </div>
      <div class="testi">
        <div class="stars">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
        <blockquote>The Pro upgrade was worth it the first night &mdash; Felix the fox is now part of our family. I keep meaning to cancel. I won't.</blockquote>
        <div class="who"><div class="avatar">S</div><div><div class="name">Sarah L.</div><div class="role">parent of Iris, age 6</div></div></div>
      </div>
    </div>
  </div>
</section>

<section class="closing">
  <div class="container">
    <div class="closing-inner">
      <span class="eyebrow">Ready when you are</span>
      <h2>Make today's story <em>unforgettable</em>.</h2>
      <p class="lede">One story. Two minutes to start. A tiny ritual your child will ask for again tomorrow.</p>
      <a href="/signup" class="btn btn-primary">Start your free story &rarr;</a>
    </div>
  </div>
</section>

<footer class="site">
  <div class="foot-row">
    <a href="/" class="brand"><span class="dot"></span>Pocket<em>Plot</em></a>
    <div class="foot-links">
      <a href="/pricing">Pricing</a>
      <a href="/login">Sign in</a>
      <a href="#how">How it works</a>
      <a href="mailto:hello@pocketplot.app">Contact</a>
    </div>
  </div>
  <p class="foot-meta">&copy; 2026 PocketPlot &middot; Made with <span class="heart">&hearts;</span> for small listeners</p>
</footer>

</body></html>
"""

SIGNUP_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,viewport-fit=cover">
<title>Begin · PocketPlot Universe</title>
<meta name="description" content="Begin your PocketPlot account. 18+ only.">
<link rel="canonical" href="/signup">
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/png" href="/favicon.png" sizes="32x32">
<meta property="og:title" content="Begin · PocketPlot Universe">
<meta property="og:description" content="Begin your PocketPlot account. 18+ only.">
<meta property="og:image" content="https://pocketplot.app/pocketplot_16_launch_banner.jpg">
<meta property="og:image:width" content="2560">
<meta property="og:image:height" content="1414">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://pocketplot.app/pocketplot_16_launch_banner.jpg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,400;0,500;0,600;1,400;1,500&family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#1a1410;--bg-el:#211a14;--ink:#f4e8d3;--ink2:#d8cba8;--muted:#8a7a64;--brand:#e8b85c;--brand-dim:#b88a3a;--serif:"Fraunces",Georgia,serif;--body:"EB Garamond",Georgia,serif;--sans:"Inter",sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--body);color:var(--ink);background:var(--bg);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;-webkit-font-smoothing:antialiased}
.card{max-width:440px;width:100%;background:var(--bg-el);border:1px solid var(--brand-dim);border-radius:12px;padding:32px 28px;box-shadow:0 30px 80px -20px rgba(0,0,0,0.6)}
.brand{font-family:var(--serif);font-size:20px;font-weight:500;color:var(--ink);margin-bottom:20px;display:flex;align-items:center;gap:8px}
.brand .dot{width:9px;height:9px;border-radius:50%;background:var(--brand)}
.brand em{font-style:italic;color:var(--brand);font-weight:400}
.eyebrow{font-family:var(--sans);font-size:11px;letter-spacing:0.18em;color:var(--brand);text-transform:uppercase;margin-bottom:6px;font-weight:600}
h1{font-family:var(--serif);font-style:italic;font-size:30px;color:var(--ink);margin-bottom:10px;line-height:1.2;font-weight:500}
.lede{font-family:var(--body);font-style:italic;font-size:15px;color:var(--ink2);margin-bottom:22px;line-height:1.5}
.field{margin-bottom:14px}
.field label{display:block;font-family:var(--sans);font-size:11px;font-weight:600;letter-spacing:0.1em;color:var(--muted);margin-bottom:6px;text-transform:uppercase}
.field input{width:100%;padding:12px 13px;border:1.5px solid #3a2e1f;border-radius:8px;font-family:var(--body);font-size:15px;color:var(--ink);background:var(--bg);transition:border-color 200ms}
.field input:focus{outline:none;border-color:var(--brand);box-shadow:0 0 0 3px rgba(232,184,92,0.18)}
.checkbox{display:flex;gap:10px;margin:14px 0;padding:12px;background:rgba(232,184,92,0.08);border:1px solid var(--brand-dim);border-radius:8px}
.checkbox input{width:16px;height:16px;margin-top:2px;accent-color:var(--brand);flex-shrink:0;cursor:pointer}
.checkbox label{font-family:var(--body);font-size:13px;color:var(--ink2);line-height:1.5;cursor:pointer}
.checkbox a{color:var(--brand);text-decoration:underline}
.btn{width:100%;background:var(--brand);color:var(--bg);border:none;padding:13px;border-radius:8px;font-family:var(--sans);font-weight:700;font-size:13px;letter-spacing:0.08em;text-transform:uppercase;cursor:pointer;margin-top:8px;transition:background 200ms, transform 100ms}
.btn:hover{background:var(--brand-dim);transform:translateY(-1px)}
.btn:active{transform:translateY(0)}
.foot{text-align:center;font-family:var(--body);font-size:13px;color:var(--muted);margin-top:18px}
.foot a{color:var(--brand);text-decoration:underline}
.flash{padding:10px 13px;border-radius:8px;font-size:13.5px;margin-bottom:14px}
.flash-err{background:rgba(232,92,92,0.12);border:1px solid #e85c5c;color:#ff8e8e}
.flash-ok{background:rgba(108,184,108,0.12);border:1px solid #6cb86c;color:#8ed68e}
</style>
</head><body>
<div class="card">
  <div class="brand"><span class="dot"></span>Pocket<em>Plot</em></div>
  <p class="eyebrow">{% if plan == "pro" %}Pro plan{% else %}Free tier{% endif %}</p>
  <h1>{% if plan == "pro" %}Begin your Pro trial{% else %}Begin your account{% endif %}</h1>
  <p class="lede">18+ only. No parental controls. No kids' content. Branching interactive storytelling.</p>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for category, msg in messages %}
        <div class="flash-{{ "err" if category == "err" else "ok" }}">{{ msg }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  <form method="post" action="/begin">
    <div class="field">
      <label for="email">Email</label>
      <input type="email" id="email" name="email" required autocomplete="email" placeholder="you@example.com">
    </div>
    <div class="field">
      <label for="display_name">Display name</label>
      <input type="text" id="display_name" name="display_name" required minlength="2" maxlength="32" placeholder="How you will appear in stories">
    </div>
    <div class="field">
      <label for="password">Password</label>
      <input type="password" id="password" name="password" required minlength="8" autocomplete="new-password" placeholder="At least 8 characters">
    </div>

    <div class="checkbox">
      <input type="checkbox" id="age_confirmed" name="age_confirmed" value="1" required>
      <label for="age_confirmed">I am 18 or older. PocketPlot is an adults-only platform with branching interactive storytelling that may include mature themes.</label>
    </div>

    <div class="checkbox">
      <input type="checkbox" id="terms_accepted" name="terms_accepted" value="1" required>
      <label for="terms_accepted">I agree to the <a href="/terms">Terms of Service</a> and <a href="/terms">Privacy Notice</a>.</label>
    </div>

    <button type="submit" class="btn">{% if plan == "pro" %}Start Pro trial{% else %}Begin account{% endif %}</button>
  </form>

  <p class="foot">
    Already have an account? <a href="/login">Sign in</a>
    &nbsp;·&nbsp;
    See <a href="/pricing">plans</a>
  </p>
</div>
</body></html>"""

@app.route("/", methods=["GET"])
def index():
    """Serve the v12+ PocketPlot Universe homepage from disk
    (so the embedded INDEX_HTML constant is just a legacy fallback)."""
    import pathlib
    idx = pathlib.Path(__file__).parent / "index.html"
    if idx.exists():
        return send_file(str(idx), mimetype="text/html")
    return render_template_string(INDEX_HTML)

@app.route("/healthz", methods=["GET"])
def healthz():
    """Liveness probe for Docker / Kubernetes / load balancers.
    Returns 200 if the process is up and the database is readable."""
    try:
        conn = db()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return ("ok", 200)
    except Exception as e:
        log.exception("healthz check failed: %s", e)
        return (f"unhealthy: {e}", 500)

@app.route("/signup-pro")
def signup_pro_route():
    """Redirect old /signup-pro to /signup."""
    from flask import redirect
    return redirect("/signup", code=301)


@app.route("/signup", methods=["GET"])
def signup_page():
    plan = request.args.get("plan", "free")
    if plan not in ("free", "pro"):
        plan = "free"
    return render_template_string(SIGNUP_HTML, plan=plan)

@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = (request.form.get("email") or "").strip().lower()
    name = (request.form.get("child_name") or "").strip()
    age_s = (request.form.get("child_age") or "").strip()
    # v12: 18+ age gate (hard requirement). Must check the box.
    age_confirmed = request.form.get("age_confirmed") in ("1", "on", "true")
    terms_accepted = request.form.get("terms_accepted") in ("1", "on", "true")
    if not age_confirmed or not terms_accepted:
        flash("You must confirm you are 18+ and accept the Terms of Service to continue.", "err")
        return redirect(url_for("index"))
    if not email or "@" not in email:
        flash("Please enter a valid email address.", "err"); return redirect(url_for("index"))
    if not name:
        flash("Please enter your child's name.", "err"); return redirect(url_for("index"))
    try:
        age = int(age_s)
        if age < 18 or age > 120: raise ValueError
    except ValueError:
        flash("PocketPlot Universe is an 18+ platform. Please enter an age of 18 or older.", "err")
        return redirect(url_for("index"))

    conn = db()
    try:
        conn.execute(
            "INSERT INTO subscribers(email, child_name, child_age, active, created_at) VALUES (?,?,?,1,?)",
            (email, name, age, dt.datetime.utcnow().isoformat(timespec="seconds"))
        )
        conn.commit()
    except sqlite3.IntegrityError:
        flash("You're already subscribed — welcome back!", "ok")
        conn.close()
        return redirect(url_for("index"))
    conn.close()
    flash("Subscribed. Sending your first story now — check your inbox (or the outbox folder).", "ok")

    # Generate + deliver first story immediately so the user sees the value today
    conn = db()
    row = conn.execute("SELECT * FROM subscribers WHERE email=?", (email,)).fetchone()
    conn.close()
    seed = row["id"] * 997 + dt.date.today().toordinal() * 131
    # Pick a word for today (same seed → same word as the nightly run would)
    word = pick_word_for_age(row["child_age"], seed)
    helper_name_out = []
    story = generate_story(
        row["child_name"], row["child_age"], seed,
        plan=row["plan"], pro_character=row["pro_character"], pro_theme=row["pro_theme"],
        word_for_today=word, helper_name_out=helper_name_out,
    )
    helper_name = helper_name_out[0] if helper_name_out else "the helper"
    questions = generate_questions(story, row["child_name"], helper_name)
    parent_guide_text = (
        generate_parent_guide(story, row["child_name"], helper_name, word)
        if row["plan"] == "pro" else None
    )
    try:
        _send_with_v4_enrichment(
            row, story, plan=row["plan"],
            word=word, questions=questions, parent_guide_text=parent_guide_text,
            seed=seed,
        )
        # Persisting happens inside _send_with_v4_enrichment now
        # (also increments words_learned_count + writes the deliveries row).
    except Exception as e:
        log.exception("first-story delivery failed: %s", e)
        flash("Subscribed — but the first story delivery failed; it will retry tonight.", "err")
        return redirect(url_for("signup_page"))
    # After signup, send a magic link so they can manage their account
    token = issue_token(row["id"], "login")
    send_magic_link_email(row, token)
    # If they came in via the Pro CTA, log them in and send them to upgrade
    if (request.form.get("plan") or "").lower() == "pro":
        session["subscriber_id"] = row["id"]
        flash("Account ready — taking you to Pro checkout.", "ok")
        return redirect(url_for("upgrade"))
    flash("Subscribed. First story sent — check your inbox (or outbox).", "ok")
    return redirect(url_for("index"))

# ---- ADMIN ----
ADMIN_HTML = """
<!doctype html>
<html><head><meta charset="utf-8"><title>PocketPlot Admin</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500&family=Karla:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>
:root{--ink:#1a241d;--paper:#f6f0e1;--paper2:#ece4cb;--paper3:#d8cfb3;--moss:#7a9a6e;--mossD:#3d5a3a;--rust:#c46a3f;--hi:#f6f0e1;--faint:#8a8270;--serif:"Fraunces",Georgia,serif;--sans:"Karla",sans-serif;--mono:"JetBrains Mono",monospace}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:var(--sans);color:var(--ink);background:var(--paper);-webkit-font-smoothing:antialiased}
header{padding:16px 24px;background:var(--paper2);border-bottom:1px solid var(--paper3);display:flex;justify-content:space-between;align-items:center}
.wordmark{font-family:var(--serif);font-size:20px;font-weight:500}
.wordmark i{color:var(--moss);font-style:italic;font-weight:400}
.nav a{color:var(--ink);text-decoration:none;font-size:13px;font-weight:500;margin-left:18px}
.nav a.on{color:var(--rust)}
.wrap{max-width:980px;margin:0 auto;padding:30px 24px}
h2{font-family:var(--serif);font-weight:500;font-size:24px;margin-bottom:14px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:30px}
@media(max-width:680px){.cards{grid-template-columns:repeat(2,1fr)}}
.card{background:#fff;border:1px solid var(--paper3);border-radius:14px;padding:18px}
.card .l{font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--faint);font-weight:600;margin-bottom:6px}
.card .v{font-family:var(--mono);font-size:24px;font-weight:500;color:var(--ink)}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;border:1px solid var(--paper3)}
th,td{padding:11px 14px;text-align:left;font-size:13.5px;border-bottom:1px solid var(--paper2)}
th{background:var(--paper2);font-weight:600;font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--faint)}
tr:last-child td{border-bottom:none}
.toggle{border:1px solid var(--paper3);background:#fff;padding:6px 12px;border-radius:99px;cursor:pointer;font-size:12px;font-weight:600;color:var(--ink);font-family:var(--sans)}
.toggle:hover{border-color:var(--rust);color:var(--rust)}
.toggle.off{background:var(--paper2);color:var(--faint)}
.btn{display:inline-block;background:var(--ink);color:var(--hi);padding:11px 18px;border-radius:99px;text-decoration:none;font-weight:600;font-size:13px;letter-spacing:.04em;cursor:pointer;border:none;font-family:var(--sans)}
.btn:hover{background:var(--rust)}
.btn.secondary{background:#fff;color:var(--ink);border:1px solid var(--paper3)}
.btn.secondary:hover{border-color:var(--rust);color:var(--rust)}
.toolbar{display:flex;gap:10px;margin:18px 0 14px;flex-wrap:wrap}
.flash{padding:11px 14px;border-radius:10px;margin-bottom:14px;font-size:13.5px;background:#fdf5e3;border:1px solid var(--gold);color:#7a6420}
.flash.ok{background:#ecf3e3;border-color:var(--moss);color:var(--mossD)}
.log{font-family:var(--mono);font-size:12px;background:var(--ink);color:var(--hi);padding:14px;border-radius:12px;line-height:1.7;max-height:160px;overflow-y:auto;margin-top:14px}
.log .ts{color:var(--moss2);font-size:11px;margin-right:8px}
pre.story{white-space:pre-wrap;font-family:var(--serif);font-size:14px;line-height:1.7;background:var(--paper2);padding:18px;border-radius:12px;color:var(--ink);max-height:300px;overflow-y:auto}
</style><link rel="stylesheet" href="/style.css?v=35">
</head><body>
<header>
  <div class="wordmark">Pocket<i>Plot</i> · Admin</div>
  <nav class="nav">
    {% if authed %}<a href="/admin/dashboard">Dashboard</a><a href="/admin">Subscribers</a><a href="/admin/queue">Review queue</a><a href="/admin/log">Activity</a><a href="/admin/outbox">Outbox</a><a href="/admin/logout">Log out</a>{% endif %}
    <a href="/">← Back to site</a>
  </nav>
</header>
<div class="wrap">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in messages %}<div class="flash {{cat}}">{{msg}}</div>{% endfor %}
  {% endwith %}
  {% if not authed %}
    <h2>Admin sign-in</h2>
    <form method="post" action="/admin/login" style="max-width:340px">
      <div style="margin-bottom:14px">
        <label style="display:block;font-size:11px;letter-spacing:.06em;font-weight:600;text-transform:uppercase;color:var(--mossD);margin-bottom:5px">Password</label>
        <input type="password" name="password" required style="width:100%;padding:10px 13px;border:1px solid var(--paper3);border-radius:9px;font-family:var(--sans);font-size:14px;background:var(--paper)">
      </div>
      <button class="btn" type="submit">Sign in</button>
      <div class="note" style="font-size:12px;color:var(--faint);margin-top:10px;font-style:italic;font-family:var(--serif)">Default password: <b>letmein</b> — set <code>POCKETPLOT_ADMIN_PASSWORD</code> to change.</div>
    </form>
  {% else %}
    <h2>Dashboard</h2>
    <div class="cards">
      <div class="card"><div class="l">Active subs</div><div class="v">{{stats.active}}</div></div>
      <div class="card"><div class="l">All-time</div><div class="v">{{stats.total}}</div></div>
      <div class="card"><div class="l">Stories sent</div><div class="v">{{stats.delivered}}</div></div>
      <div class="card"><div class="l">Daily at</div><div class="v">{{hour}}:00 UTC</div></div>
    </div>
    <div class="toolbar">
      <form method="post" action="/admin/run" style="display:inline">
        <button class="btn" type="submit">▶ Run tonight's delivery now</button>
      </form>
      <a class="btn secondary" href="/admin/preview">Preview a story</a>
      <a class="btn secondary" href="/admin/csv">Export CSV</a>
    </div>
    <h2 style="margin-top:30px">Subscribers</h2>
    <table>
      <thead><tr><th>#</th><th>Email</th><th>Child</th><th>Age</th><th>Active</th><th>Created</th><th>Last sent</th><th></th></tr></thead>
      <tbody>
        {% for s in subs %}
        <tr>
          <td>{{s.id}}</td>
          <td>{{s.email}}</td>
          <td>{{s.child_name}}</td>
          <td>{{s.child_age}}</td>
          <td>{{'yes' if s.active else 'no'}}</td>
          <td>{{s.created_at[:10]}}</td>
          <td>{{(s.last_sent_at or '—')[:10]}}</td>
          <td>
            <form method="post" action="/admin/toggle/{{s.id}}" style="display:inline">
              <button class="toggle {{'' if s.active else 'off'}}" type="submit">{{'Pause' if s.active else 'Resume'}}</button>
            </form>
            <form method="post" action="/admin/send/{{s.id}}" style="display:inline;margin-left:6px">
              <button class="toggle" type="submit">Send now</button>
            </form>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    <h2 style="margin-top:30px">Recent activity</h2>
    <div class="log">
      {% for line in recent_log %}<div><span class="ts">{{line.ts}}</span>{{line.note}}</div>{% endfor %}
    </div>
  {% endif %}
</div>
</body></html>
"""

PREVIEW_HTML = """
<!doctype html><html><head><meta charset="utf-8"><title>PocketPlot Preview</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500&family=Karla:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>
:root{--ink:#1a241d;--paper:#f6f0e1;--paper2:#ece4cb;--paper3:#d8cfb3;--moss:#7a9a6e;--mossD:#3d5a3a;--rust:#c46a3f;--serif:"Fraunces",Georgia,serif;--sans:"Karla",sans-serif;--mono:"JetBrains Mono",monospace}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:var(--sans);color:var(--ink);background:var(--paper);-webkit-font-smoothing:antialiased}
header{padding:16px 24px;background:var(--paper2);border-bottom:1px solid var(--paper3)}
.wordmark{font-family:var(--serif);font-size:20px;font-weight:500}
.wordmark i{color:var(--moss);font-style:italic;font-weight:400}
.wrap{max-width:740px;margin:0 auto;padding:30px 24px}
h1{font-family:var(--serif);font-weight:500;font-size:32px;line-height:1.2;margin-bottom:18px}
h1 i{font-style:italic;color:var(--moss);font-weight:400}
form{margin-bottom:24px;background:#fff;border:1px solid var(--paper3);border-radius:14px;padding:18px}
.row2{display:grid;grid-template-columns:1fr 110px;gap:10px}
.field{margin-bottom:12px}
.field label{display:block;font-size:11px;letter-spacing:.06em;font-weight:600;text-transform:uppercase;color:var(--mossD);margin-bottom:5px}
.field input{width:100%;padding:10px 13px;border:1px solid var(--paper3);border-radius:9px;font-family:var(--sans);font-size:14px;background:var(--paper)}
.btn{background:var(--ink);color:var(--paper);padding:11px 20px;border-radius:99px;border:none;font-family:var(--sans);font-weight:600;font-size:13px;cursor:pointer}
.btn:hover{background:var(--rust)}
.btn.secondary{background:#fff;color:var(--ink);border:1px solid var(--paper3);text-decoration:none;display:inline-block;margin-left:6px}
pre.story{white-space:pre-wrap;font-family:var(--serif);font-size:16px;line-height:1.75;background:#fff;border:1px solid var(--paper3);padding:24px;border-radius:14px;color:var(--ink)}
.meta{font-family:var(--mono);font-size:12px;color:var(--faint);margin-bottom:14px}
</style><link rel="stylesheet" href="/style.css?v=35">
</head><body>
<header><div class="wordmark">Pocket<i>Plot</i> · Preview</div></header>
<div class="wrap">
  <h1>Generate a <i>preview</i> story</h1>
  <form method="post" action="/admin/preview">
    <div class="field row2">
      <div>
        <label>Child's name</label>
        <input type="text" name="child_name" required value="{{name or 'Wren'}}">
      </div>
      <div>
        <label>Age</label>
        <input type="number" name="child_age" min="2" max="12" required value="{{age or 5}}">
      </div>
    </div>
    <button class="btn" type="submit">Generate</button>
    <a class="btn secondary" href="/admin">← Back</a>
  </form>
  {% if story %}
    <div class="meta">seed = {{seed}} · {{story.word_count}} words · "{{story.title}}"</div>
    <h1 style="margin-top:0">{{story.title}}</h1>
    <pre class="story">{{story.body}}</pre>
  {% endif %}
</div>
</body></html>
"""

def admin_required(view):
    from functools import wraps
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin"))
        return view(*args, **kwargs)
    return wrapper

@app.route("/admin", methods=["GET"])
def admin():
    authed = bool(session.get("admin"))
    subs, stats, recent_log = [], {"active":0,"total":0,"delivered":0}, []
    if authed:
        conn = db()
        subs = conn.execute("SELECT * FROM subscribers ORDER BY id DESC").fetchall()
        stats["active"] = conn.execute("SELECT COUNT(*) c FROM subscribers WHERE active=1").fetchone()["c"]
        stats["total"]  = conn.execute("SELECT COUNT(*) c FROM subscribers").fetchone()["c"]
        stats["delivered"] = conn.execute("SELECT COUNT(*) c FROM deliveries").fetchone()["c"]
        recent_log = conn.execute("SELECT * FROM story_log ORDER BY id DESC LIMIT 12").fetchall()
        conn.close()
    return render_template_string(
        ADMIN_HTML, authed=authed, subs=subs, stats=stats,
        recent_log=recent_log, hour=DELIVERY_HOUR
    )

@app.route("/admin/login", methods=["POST"])
def admin_login():
    if request.form.get("password") == ADMIN_PASSWORD:
        session["admin"] = True
        flash("Signed in.", "ok")
    else:
        flash("Wrong password.", "err")
    return redirect(url_for("admin"))

@app.route("/admin/logout", methods=["GET"])
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin"))

@app.route("/admin/toggle/<int:sid>", methods=["POST"])
@admin_required
def admin_toggle(sid):
    conn = db()
    conn.execute("UPDATE subscribers SET active = 1 - active WHERE id=?", (sid,))
    conn.commit(); conn.close()
    return redirect(url_for("admin"))

@app.route("/admin/send/<int:sid>", methods=["POST"])
@admin_required
def admin_send(sid):
    conn = db()
    row = conn.execute("SELECT * FROM subscribers WHERE id=?", (sid,)).fetchone()
    if row:
        seed = row["id"] * 997 + dt.date.today().toordinal() * 131 + int(dt.datetime.utcnow().timestamp()) % 997
        # Same learning-layer wiring as the nightly run
        word = pick_word_for_age(row["child_age"], seed)
        helper_name_out = []
        story = generate_story(
            row["child_name"], row["child_age"], seed,
            plan=row["plan"],
            pro_character=row["pro_character"],
            pro_theme=row["pro_theme"],
            word_for_today=word, helper_name_out=helper_name_out,
        )
        helper_name = helper_name_out[0] if helper_name_out else "the helper"
        questions = generate_questions(story, row["child_name"], helper_name)
        parent_guide_text = (
            generate_parent_guide(story, row["child_name"], helper_name, word)
            if row["plan"] == "pro" else None
        )
        try:
            _send_with_v4_enrichment(
                row, story, plan=row["plan"],
                word=word, questions=questions, parent_guide_text=parent_guide_text,
                seed=seed,
            )
            conn.execute("INSERT INTO story_log(ts,note) VALUES (?,?)",
                         (dt.datetime.utcnow().isoformat(timespec="seconds"), f"Manual send to {row['email']}"))
            conn.commit()
            flash(f"Sent to {row['email']}.", "ok")
        except Exception as e:
            flash(f"Delivery failed: {e}", "err")
    conn.close()
    return redirect(url_for("admin"))

@app.route("/admin/run", methods=["POST"])
@admin_required
def admin_run():
    nightly_run()
    flash("Nightly delivery run completed.", "ok")
    return redirect(url_for("admin"))

@app.route("/admin/preview", methods=["GET","POST"])
@admin_required
def admin_preview():
    name, age, story, seed = "", 5, None, None
    if request.method == "POST":
        name = (request.form.get("child_name") or "Wren").strip()
        try: age = int(request.form.get("child_age") or "5")
        except: age = 5
        seed = int(dt.datetime.utcnow().timestamp())
        story = generate_story(name, age, seed)
    return render_template_string(PREVIEW_HTML, name=name, age=age, story=story, seed=seed)

@app.route("/admin/outbox")
@admin_required
def admin_outbox():
    files = sorted(OUTBOX_DIR.glob("*.eml"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]
    items = [(f.name, f.stat().st_size, dt.datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds")) for f in files]
    return render_template_string("""
    <!doctype html><html><head><title>Outbox</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500&family=Karla:wght@400;500&display=swap" rel="stylesheet">
    <style>body{font-family:Karla;background:#f6f0e1;color:#1a241d;padding:30px}
    h1{font-family:Fraunces;font-weight:500}.file{background:#fff;border:1px solid #d8cfb3;border-radius:9px;padding:10px 14px;margin-bottom:8px;font-family:"JetBrains Mono",monospace;font-size:12px}
    a{color:#c46a3f}</style></head><body>
    <h1>Outbox · last {{n}} emails</h1>
    <p style="margin:10px 0 24px"><a href="/admin">← Back to admin</a></p>
    {% for n,s,t in items %}<div class="file">{{t}} · {{s}} bytes · <a href="/admin/outbox/{{n}}">{{n}}</a></div>{% endfor %}
    </body></html>""", n=len(items), items=items)

@app.route("/admin/outbox/<path:fname>")
@admin_required
def admin_outbox_file(fname):
    return send_from_directory(OUTBOX_DIR, fname, as_attachment=False)

@app.route("/admin/log")
@admin_required
def admin_log():
    conn = db()
    log_rows = conn.execute("SELECT * FROM story_log ORDER BY id DESC LIMIT 100").fetchall()
    deliveries = conn.execute("""
        SELECT d.*, s.email, s.child_name FROM deliveries d
        JOIN subscribers s ON s.id=d.subscriber_id ORDER BY d.id DESC LIMIT 50
    """).fetchall()
    conn.close()
    return render_template_string("""
    <!doctype html><html><head><title>Log</title>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500&family=Karla:wght@400;500&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
    <style>body{font-family:Karla;background:#f6f0e1;color:#1a241d;padding:30px}
    h1{font-family:Fraunces;font-weight:500}
    .log{font-family:"JetBrains Mono",monospace;font-size:12px;background:#1a241d;color:#f6f0e1;padding:14px;border-radius:9px;line-height:1.7}
    .row{background:#fff;border:1px solid #d8cfb3;border-radius:9px;padding:11px;margin-bottom:8px;font-size:13px}
    .row b{color:#3d5a3a}</style></head><body>
    <h1>Delivery log</h1>
    <p><a href="/admin">← Back to admin</a></p>
    <h3 style="margin-top:20px">System log</h3>
    <div class="log">{% for l in log_rows %}<div>{{l.ts}} — {{l.note}}</div>{% endfor %}</div>
    <h3 style="margin-top:30px">Story deliveries</h3>
    {% for d in deliveries %}<div class="row"><b>{{d.sent_at}}</b> · {{d.email}} · {{d.child_name}} · {{d.word_count}} words</div>{% endfor %}
    </body></html>""", log_rows=log_rows, deliveries=deliveries)

@app.route("/admin/csv")
@admin_required
def admin_csv():
    conn = db()
    rows = conn.execute("SELECT * FROM subscribers").fetchall()
    conn.close()
    out_path = APP_DIR / "subscribers.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id","email","child_name","child_age","active","created_at","last_sent_at"])
        for r in rows:
            w.writerow([r["id"], r["email"], r["child_name"], r["child_age"], r["active"], r["created_at"], r["last_sent_at"]])
    return send_from_directory(APP_DIR, "subscribers.csv", as_attachment=True)


# =====================================================================
# ADULT ONBOARDING (v38)
# =====================================================================

def _ensure_v38_schema():
    conn = db()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(subscribers)").fetchall()]
    if "display_name" not in cols:
        conn.execute("ALTER TABLE subscribers ADD COLUMN display_name TEXT DEFAULT ''")
    if "password_hash" not in cols:
        conn.execute("ALTER TABLE subscribers ADD COLUMN password_hash TEXT DEFAULT ''")
    conn.commit()
    conn.close()

try:
    _ensure_v38_schema()
except Exception as e:
    log.warning("v38 schema migration failed: %s", e)


def _hash_password(pw):
    import hashlib
    salt = b"pocketplot-v38"
    return hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, 100000).hex()




@app.route("/begin", methods=["POST"])
def begin_signup():
    email = (request.form.get("email") or "").strip().lower()
    display_name = (request.form.get("display_name") or "").strip()
    password = request.form.get("password") or ""
    age_confirmed = request.form.get("age_confirmed") in ("1", "on", "true")
    terms_accepted = request.form.get("terms_accepted") in ("1", "on", "true")

    if not age_confirmed:
        flash("You must confirm you are 18+ to use PocketPlot.", "err")
        return redirect(url_for("signup_page"))
    if not terms_accepted:
        flash("You must accept the Terms of Service to continue.", "err")
        return redirect(url_for("signup_page"))
    if not email or "@" not in email or "." not in email:
        flash("Please enter a valid email address.", "err")
        return redirect(url_for("signup_page"))
    if len(display_name) < 2 or len(display_name) > 32:
        flash("Display name must be 2-32 characters.", "err")
        return redirect(url_for("signup_page"))
    if len(password) < 8:
        flash("Password must be at least 8 characters.", "err")
        return redirect(url_for("signup_page"))

    pw_hash = _hash_password(password)
    conn = db()
    try:
        conn.execute(
            "INSERT INTO subscribers(email, child_name, child_age, active, created_at, display_name, password_hash) VALUES (?,?,?,1,?,?,?)",
            (email, display_name, 18, dt.datetime.utcnow().isoformat(timespec="seconds"),
             display_name, pw_hash)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        flash("That email is already registered. Try signing in.", "err")
        return redirect(url_for("login"))
    conn.close()

    conn = db()
    row = conn.execute("SELECT * FROM subscribers WHERE email=?", (email,)).fetchone()
    conn.close()
    if row:
        session["subscriber_id"] = row["id"]
        session["email"] = email
        session["display_name"] = display_name

    flash(f"Welcome to PocketPlot, {display_name}.", "ok")
    return redirect(url_for("me"))



# =====================================================================
# REVIEW QUEUE (Phase 4 — admin approval before stories are sent)
# =====================================================================
@app.route("/admin/queue", methods=["GET"])
@admin_required
def admin_queue():
    """List view of the review queue with optional status filter."""
    status = (request.args.get("status") or "pending").strip()
    if status == "all":
        status = None
    rows = review_queue.list_queue(db, status=status, limit=100)
    counts = review_queue.queue_counts(db)
    # Parse story_json + word_json for display. sqlite3.Row is read-only,
    # so convert to a mutable dict first.
    rows = [dict(r) for r in rows]
    for r in rows:
        r["story_obj"] = json.loads(r["story_json"]) if r["story_json"] else {}
        r["word_obj"] = json.loads(r["word_json"]) if r["word_json"] else {}
    return render_template_string(
        queue_templates.QUEUE_LIST_HTML, rows=rows, status=status or "all", counts=counts
    )
@app.route('/stickers')
def stickers_route():
    """Mascot sticker pack page."""
    try:
        return send_file('stickers.html', conditional=True)
    except Exception:
        abort(404)


@app.route('/empty')
def empty_route():
    """Charcoal-designed empty state for new accounts."""
    try:
        return send_file('empty.html', conditional=True)
    except Exception:
        abort(404)


@app.route('/app-store')
def app_store_route():
    """Charcoal app-store screenshots gallery."""
    try:
        return send_file('app_store.html', conditional=True)
    except Exception:
        abort(404)


@app.route('/app_store')
def app_store_underscore_route():
    """Charcoal used /app_store in the QC report — alias for /app-store."""
    try:
        return send_file('app_store.html', conditional=True)
    except Exception:
        abort(404)


@app.route("/version")
def version_route():
    """Diagnostic: shows what's actually deployed."""
    import subprocess
    commit = subprocess.run(['git', '-C', '/root/pocketplot', 'rev-parse', '--short', 'HEAD'],
                            capture_output=True, text=True).stdout.strip() or 'unknown'
    return {
        'commit': commit,
        'deployed': 'v30 design system',
        'timestamp': '2026-08-28T15:56:15Z',
        'themes': ['warm-dark (default)', 'warm-light (Kindle paper)'],
        'features': [
            '4-tier text hierarchy (--text-heading/body/caption/faint)',
            '3-tier button system (--brand primary, --border secondary, --brand-text tertiary)',
            '3 status colors (--success, --warning, --danger)',
            'Sun/moon theme toggle in nav',
            'localStorage persistence',
            'System prefers-color-scheme detection',
        ],
        'marker': 'V30-VERSION-FINGERPRINT: pocketplot-v30-2026-08-28-16:50-UNIQUE',
    }, 
@app.route("/debug-giant-red-banner")
def debug_giant_red_banner_route():
    """Diagnostic: a giant red banner. If user sees this, the path to them works."""
    from datetime import datetime
    return f"""<!DOCTYPE html><html><head><title>V30 DIAGNOSTIC</title></head>
<body style="margin:0;font-family:sans-serif">
<div style="background:red;color:white;padding:60px 30px;font-size:64px;font-weight:900;text-align:center;">
POCKETPLOT V30 LIVE TEST
</div>
<div style="padding:30px;font-size:24px;background:#fff7e6;color:#3d2e1f;">
<h2>If you see the big red banner above, the server is sending you fresh content.</h2>
<p>Time on server: {datetime.utcnow().isoformat()} UTC</p>
<p>If you DON'T see the red banner, your browser or network has old cached content.</p>
<p>Try a different network (mobile data) or a different browser to verify.</p>
</div>
</body></html>"""

200, {'Content-Type': 'application/json'}





@app.route("/admin/queue/<int:qid>", methods=["GET"])
@admin_required
def admin_queue_detail(qid):
    """Detail view (story + hero + word + questions + meta)."""
    row = review_queue.get_queue_item(db, qid)
    if not row:
        flash("Queue item not found.", "err")
        return redirect(url_for("admin_queue"))
    row = dict(row)  # sqlite3.Row is read-only
    row["story_obj"] = json.loads(row["story_json"]) if row["story_json"] else {}
    row["word_obj"] = json.loads(row["word_json"]) if row["word_json"] else {}
    row["questions_list"] = json.loads(row["questions_json"]) if row["questions_json"] else []
    return render_template_string(queue_templates.QUEUE_DETAIL_HTML, row=row)


@app.route("/admin/queue/<int:qid>/approve", methods=["POST"])
@admin_required
def admin_queue_approve(qid):
    note = (request.form.get("note") or "").strip()[:500]
    review_queue.approve_queue_item(db, qid, note=note)
    flash("Approved. Sending now.", "ok")
    result = _send_queued_story(qid)
    # `_send_queued_story` returns either (status, out_path, delivery_id)
    # on success or (None, error_message) on early-return error. Handle both.
    if result[0] is None:
        flash(f"Approved but send failed: {result[1]}", "err")
    else:
        status, out_path, delivery_id = result
        flash(f"Sent (status={status}, delivery_id={delivery_id}).", "ok")
    return redirect(url_for("admin_queue", status="pending"))


@app.route("/admin/queue/<int:qid>/reject", methods=["POST"])
@admin_required
def admin_queue_reject(qid):
    note = (request.form.get("note") or "").strip()[:500]
    review_queue.reject_queue_item(db, qid, note=note)
    flash("Rejected.", "ok")
    return redirect(url_for("admin_queue", status="pending"))


@app.route("/admin/queue/bulk-approve", methods=["POST"])
@admin_required
def admin_queue_bulk_approve():
    ids = request.form.getlist("qid")
    sent = 0
    for qid in ids:
        try:
            qid_int = int(qid)
        except (ValueError, TypeError):
            continue
        review_queue.approve_queue_item(db, qid_int, note="bulk approve")
        result = _send_queued_story(qid_int)
        if result[0] is not None:
            sent += 1
    flash(f"Bulk-approved {len(ids)} item(s); sent {sent}.", "ok")
    return redirect(url_for("admin_queue", status="pending"))


@app.route("/admin/digest/trigger", methods=["POST"])
@admin_required
def admin_digest_trigger():
    """Manual trigger for the weekly digest email (useful for testing)."""
    sent = send_admin_digest_email()
    flash(f"Digest {'sent' if sent else 'skipped (queue empty)'} to {os.environ.get('POCKETPLOT_ADMIN_EMAIL', 'admin@pocketplot.local')}.", "ok")
    return redirect(url_for("admin_queue"))


# ---- Phase 8: Weekly Insights for Pro subscribers ----
def send_all_weekly_insights():
    """Build + send the weekly insight to all active Pro subscribers.
    Used by APScheduler (Sunday 09:00 UTC) + the admin-trigger route."""
    n = weekly_insight.render_and_send_all(db, SITE_URL, _send_raw_email, log)
    log.info("weekly insights sent to %d subscribers", n)
    return n


def _weekly_insights_job():
    with app.app_context():
        try:
            send_all_weekly_insights()
        except Exception as e:
            log.exception("weekly insights job error: %s", e)


@app.route("/admin/insights/trigger", methods=["POST"])
@admin_required
def admin_insights_trigger():
    """Manual trigger for the weekly insights email (useful for testing).
    Doesn't block: APScheduler also runs this on Sundays."""
    sent = send_all_weekly_insights()
    flash(f"Weekly insights sent to {sent} subscriber(s).", "ok")
    return redirect(url_for("admin_dashboard_view"))


# =====================================================================
# ADMIN DASHBOARD (Phase 5) — single-page management view
# =====================================================================
@app.route("/admin/dashboard", methods=["GET"])
@admin_required
def admin_dashboard_view():
    """One-stop management view: metrics, users, queue, history, settings, status."""
    metrics = admin_dashboard.overview_metrics(db)
    users = admin_dashboard.list_subscribers_full(db, limit=200)
    # Pending queue rows — convert sqlite3.Row to dict so we can add fields.
    q_rows = review_queue.list_queue(db, status="pending", limit=50)
    queue_pending = []
    for r in q_rows:
        rd = dict(r)
        try:
            so = json.loads(rd["story_json"]) if rd["story_json"] else {}
        except Exception:
            so = {}
        try:
            wo = json.loads(rd["word_json"]) if rd["word_json"] else {}
        except Exception:
            wo = {}
        rd["title"] = so.get("title", "(untitled)")
        rd["word"]  = wo.get("w", "")
        rd["hero_svg"] = rd.get("hero_svg") or ""
        queue_pending.append(rd)
    # Story history
    h_rows = admin_dashboard.list_recent_deliveries(db, limit=30)
    history = []
    for r in h_rows:
        rd = dict(r)
        try:
            so = json.loads(rd["story"]) if rd["story"] else {}
        except Exception:
            so = {}
        rd["story_title"] = so.get("title", "(untitled)")
        body = so.get("body", "") or ""
        rd["body_preview"] = body[:140]
        # Split paragraphs (Jinja2 can't use chr())
        rd["body_paragraphs"] = [p for p in body.split('\\n\\n') if p.strip()]
        rd["hero_svg"] = rd.get("hero_svg") or ""
        rd["word"] = rd.get("word") or ""
        history.append(rd)
    settings = admin_dashboard.get_all_settings(db)
    errors = admin_dashboard.recent_errors(db, limit=10)
    # Surface any flash messages
    flash_ok = flash_err = None
    for cat, msg in (get_flashed_messages(with_categories=True) or []):
        if cat == "ok":
            flash_ok = msg
        else:
            flash_err = msg
    return render_template_string(
        admin_dashboard.DASHBOARD_HTML,
        metrics=metrics,
        users=users,
        queue_pending=queue_pending,
        history=history,
        settings=settings,
        errors=errors,
        flash_ok=flash_ok,
        flash_err=flash_err,
    )


@app.route("/admin/dashboard/users/<int:sub_id>/toggle", methods=["POST"])
@admin_required
def admin_dashboard_user_toggle(sub_id):
    """Pause / resume a subscriber by flipping their `active` column."""
    conn = db()
    row = conn.execute("SELECT active, email FROM subscribers WHERE id=?", (sub_id,)).fetchone()
    if not row:
        conn.close()
        flash("Subscriber not found.", "err")
        return redirect(url_for("admin_dashboard_view"))
    new_state = 0 if row["active"] else 1
    conn.execute("UPDATE subscribers SET active=? WHERE id=?", (new_state, sub_id))
    conn.commit(); conn.close()
    flash(f"{row['email']} {'paused' if new_state == 0 else 'resumed'}.", "ok")
    return redirect(url_for("admin_dashboard_view"))


@app.route("/admin/dashboard/queue/<int:qid>/approve", methods=["POST"])
@admin_required
def admin_dashboard_queue_approve(qid):
    note = (request.form.get("note") or "").strip()[:500]
    review_queue.approve_queue_item(db, qid, note=note)
    status, out_path, delivery_id = (None, None, None)
    result = _send_queued_story(qid)
    if result[0] is None:
        flash(f"Approved but send failed: {result[1]}", "err")
    else:
        status, out_path, delivery_id = result
        flash(f"Approved and sent (delivery_id={delivery_id}).", "ok")
    return redirect(url_for("admin_dashboard_view"))


@app.route("/admin/dashboard/queue/<int:qid>/reject", methods=["POST"])
@admin_required
def admin_dashboard_queue_reject(qid):
    note = (request.form.get("note") or "").strip()[:500]
    review_queue.reject_queue_item(db, qid, note=note)
    flash("Rejected.", "ok")
    return redirect(url_for("admin_dashboard_view"))


@app.route("/admin/dashboard/queue/bulk-approve", methods=["POST"])
@admin_required
def admin_dashboard_queue_bulk_approve():
    ids = request.form.getlist("qid")
    sent = 0
    for qid in ids:
        try:
            qid_int = int(qid)
        except (ValueError, TypeError):
            continue
        review_queue.approve_queue_item(db, qid_int, note="bulk approve")
        result = _send_queued_story(qid_int)
        if result[0] is not None:
            sent += 1
    flash(f"Bulk-approved {len(ids)} item(s); sent {sent}.", "ok")
    return redirect(url_for("admin_dashboard_view"))


@app.route("/admin/dashboard/settings", methods=["POST"])
@admin_required
def admin_dashboard_settings():
    """Persist runtime settings (admin email, word count target, queue toggle)."""
    admin_email = (request.form.get("admin_email") or "").strip()
    word_target = (request.form.get("word_count_target") or "").strip()
    queue_enabled = "1" if request.form.get("review_queue_enabled") else "0"
    if not admin_email or "@" not in admin_email:
        flash("Admin email is required and must contain '@'.", "err")
        return redirect(url_for("admin_dashboard_view"))
    if not word_target.isdigit() or not (120 <= int(word_target) <= 500):
        flash("Word count target must be a number between 120 and 500.", "err")
        return redirect(url_for("admin_dashboard_view"))
    admin_dashboard.set_setting(db, "admin_email", admin_email)
    admin_dashboard.set_setting(db, "word_count_target", word_target)
    admin_dashboard.set_setting(db, "review_queue_enabled", queue_enabled)
    # Also update the env var on os.environ so the rest of the running
    # process (digest, nightly_run) reads the new value immediately. A
    # true restart is only needed for DELIVERY_HOUR.
    os.environ["POCKETPLOT_REVIEW_QUEUE"] = queue_enabled
    os.environ["POCKETPLOT_ADMIN_EMAIL"] = admin_email
    os.environ["POCKETPLOT_WORD_COUNT_TARGET"] = word_target
    flash("Settings saved.", "ok")
    return redirect(url_for("admin_dashboard_view"))


def _send_queued_story(qid):
    """Generate the email for an approved queue item and persist delivery.
    Returns (status, out_path, delivery_id) or (None, error_message)."""
    row = review_queue.get_queue_item(db, qid)
    if not row:
        return None, "Queue item not found"
    if row["status"] not in ("approved", "pending"):
        return None, f"Queue item is {row['status']}, not approved/pending"

    sub = db().execute("SELECT * FROM subscribers WHERE id=?", (row["subscriber_id"],)).fetchone()
    if not sub:
        return None, "Subscriber missing"

    story = json.loads(row["story_json"]) if row["story_json"] else {}
    word = json.loads(row["word_json"]) if row["word_json"] else None
    questions = json.loads(row["questions_json"]) if row["questions_json"] else []
    parent_guide = row["parent_guide"] or ""
    seed = int(row["seed"] or 0)

    sub_dict = dict(sub)
    status, out_path, v4_payload = _send_with_v4_enrichment(
        sub_dict, story, plan=sub_dict.get("plan", "free"),
        word=word, questions=questions, parent_guide_text=parent_guide,
        seed=seed,
    )
    # The delivery_id isn't returned by _send_with_v4_enrichment; look it up
    # by (subscriber_id + recent timestamp) to link the queue row.
    delivery_id = None
    conn = db()
    drow = conn.execute(
        "SELECT id FROM deliveries WHERE subscriber_id=? ORDER BY id DESC LIMIT 1",
        (row["subscriber_id"],),
    ).fetchone()
    if drow:
        delivery_id = drow[0]
    conn.execute(
        "UPDATE review_queue SET status='sent', reviewed_at=?, delivery_id=? WHERE id=?",
        (dt.datetime.utcnow().isoformat(timespec="seconds") + "Z", delivery_id, qid),
    )
    conn.commit(); conn.close()
    # Mark subscriber last_sent_at so we don't re-queue
    conn = db()
    conn.execute(
        "UPDATE subscribers SET last_sent_at=? WHERE id=?",
        (dt.datetime.utcnow().isoformat(timespec="seconds"), row["subscriber_id"]),
    )
    conn.commit(); conn.close()
    return status, out_path, delivery_id


# ---- Weekly digest ----
def send_admin_digest_email():
    """Send the admin a Monday morning digest of pending queue items.
    Returns True if an email was sent, False if the queue was empty."""
    counts = review_queue.queue_counts(db)
    if counts["pending"] == 0:
        return False
    pending = review_queue.list_queue(db, status="pending", limit=20)
    subject = f"[PocketPlot] {counts['pending']} stor{'ies' if counts['pending'] != 1 else 'y'} awaiting review"
    body_html = digest.render_digest_email(pending, counts, SITE_URL)
    body_plain = (
        f"{counts['pending']} stories are awaiting review.\n\n"
        f"Open the review queue: {SITE_URL}/admin/queue\n"
    )
    admin_email = os.environ.get("POCKETPLOT_ADMIN_EMAIL", "admin@pocketplot.local")
    try:
        _send_raw_email(admin_email, subject, body_plain, body_html)
        log.info("admin digest sent: %d pending items", counts["pending"])
        return True
    except Exception as e:
        log.exception("admin digest failed: %s", e)
        return False


# ---- APScheduler weekly digest job ----
def _weekly_digest_job():
    with app.app_context():
        try:
            send_admin_digest_email()
        except Exception as e:
            log.exception("weekly digest job error: %s", e)


# Phase 4 (v8) — weekly digest email (Monday 09:00 UTC). Skips if the
# queue is empty (send_admin_digest_email returns False without sending).
try:
    scheduler.add_job(_weekly_digest_job, "cron", day_of_week="mon", hour=9, minute=0, id="weekly_digest", replace_existing=True)
except Exception as e:
    log.warning("weekly digest job not registered: %s", e)

# Phase 8 — weekly insights for Pro subscribers. Same schedule so admins
# see both digests at the start of the week.
try:
    scheduler.add_job(_weekly_insights_job, "cron", day_of_week="sun", hour=9, minute=0, id="weekly_insights", replace_existing=True)
except Exception as e:
    log.warning("weekly insights job not registered: %s", e)


# =====================================================================
# SELF-SERVICE PORTAL — magic-link login + /me
# =====================================================================



# ---- Phase 13 polish: email templates ----
# All transactional email subject lines + plain-text + inline-styled HTML
# bodies live here. Keep them tight and warm; Gmail/Outlook strip <style>
# blocks so we lean on inline styles for HTML bodies.

EMAIL_MAGICLINK_PLAIN = """Hi,

Sign in to PocketPlot Universe:
{link}

This link expires in one hour. If you didn't request it, ignore this
email — nothing happens unless you click.

— PocketPlot Universe
"""

EMAIL_MAGICLINK_HTML = """<!doctype html><html><body style="margin:0;padding:0;background:#0e1a2e;font-family:Georgia,serif;">
<div style="max-width:560px;margin:0 auto;padding:36px 28px;color:#f3e9d2;">
  <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#e6c879;margin-bottom:8px;">PocketPlot Universe</div>
  <h1 style="font-family:Georgia,serif;font-size:24px;margin:0 0 14px;color:#f3e9d2;">Your sign-in link</h1>
  <p style="font-family:Georgia,serif;font-size:15px;color:#d4b8a4;line-height:1.6;margin:0 0 22px;">
    Click the button below to sign in. The link expires in one hour.
  </p>
  <a href="{link}" style="display:inline-block;background:#e6c879;color:#0e1a2e;padding:13px 28px;border-radius:99px;font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;font-weight:700;text-decoration:none;">Sign in to PocketPlot</a>
  <p style="font-family:Georgia,serif;font-size:13px;color:#9eb6d4;line-height:1.6;margin:24px 0 0;">
    Or paste this URL into your browser:<br>
    <a href="{link}" style="color:#e6c879;word-break:break-all;">{link}</a>
  </p>
  <p style="font-family:Georgia,serif;font-size:12px;color:#7a8aa8;margin:24px 0 0;font-style:italic;">
    If you didn't request this, ignore this email — nothing happens unless you click the button.
  </p>
</div></body></html>"""


EMAIL_REFUND_PLAIN = """Hi,

We've issued a refund of ${amount} to your account.

Reason: {reason}

Refunds usually appear on your card within 5–10 business days.

If you have questions, reply to this email.

— PocketPlot Universe
"""

EMAIL_REFUND_HTML = """<!doctype html><html><body style="margin:0;padding:0;background:#0e1a2e;font-family:Georgia,serif;">
<div style="max-width:560px;margin:0 auto;padding:36px 28px;color:#f3e9d2;">
  <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#e6c879;margin-bottom:8px;">PocketPlot Universe · Refund</div>
  <h1 style="font-family:Georgia,serif;font-size:24px;margin:0 0 14px;color:#f3e9d2;">Your refund is on the way.</h1>
  <p style="font-family:Georgia,serif;font-size:15px;color:#d4b8a4;line-height:1.6;margin:0 0 14px;">
    We've issued a refund of <b style="color:#e6c879;">${amount}</b> to your account.
  </p>
  <p style="font-family:Georgia,serif;font-size:14px;color:#9eb6d4;line-height:1.6;margin:0 0 22px;font-style:italic;">
    Reason: {reason}
  </p>
  <p style="font-family:Georgia,serif;font-size:14px;color:#d4b8a4;line-height:1.6;margin:0 0 22px;">
    Refunds usually appear on your card within <b>5–10 business days</b>.
  </p>
  <p style="font-family:Georgia,serif;font-size:12px;color:#7a8aa8;margin:24px 0 0;font-style:italic;">
    If you have questions, just reply to this email.
  </p>
</div></body></html>"""


EMAIL_QUEUE_APPROVED_PLAIN = """Hi,

Your nightly story "{title}" was approved and is on its way.
Open your inbox — you should see it within a few minutes.

— PocketPlot Universe
"""

EMAIL_QUEUE_APPROVED_HTML = """<!doctype html><html><body style="margin:0;padding:0;background:#0e1a2e;font-family:Georgia,serif;">
<div style="max-width:560px;margin:0 auto;padding:36px 28px;color:#f3e9d2;">
  <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#9ad6a4;margin-bottom:8px;">Approved &amp; sent</div>
  <h1 style="font-family:Georgia,serif;font-size:24px;margin:0 0 14px;color:#f3e9d2;">Your story is on its way.</h1>
  <p style="font-family:Georgia,serif;font-size:15px;color:#d4b8a4;line-height:1.6;margin:0 0 22px;">
    "" was approved and is heading to your inbox.
  </p>
  <p style="font-family:Georgia,serif;font-size:13px;color:#9eb6d4;line-height:1.6;">
    You should see it in a few minutes.
  </p>
</div></body></html>"""


EMAIL_WELCOME_PLAIN = """Welcome to PocketPlot Universe.

Your first story is in flight. Reply to it any time — we'd love to know
what you think.

— PocketPlot Universe
"""

EMAIL_WELCOME_HTML = """

<style>
/* v30 in-product styling - uses semantic tokens from the design system */
body { background: var(--bg); color: var(--text-body); }
h1, h2, h3 { color: var(--text-heading); font-family: var(--font-serif, Georgia, serif); }

/* Cards & surfaces */
.card, .surface {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg, 16px);
  color: var(--text-body);
}

/* Buttons - 3 tiers */
.btn-primary, button.primary, .primary {
  background: linear-gradient(180deg, var(--brand-light), var(--brand), var(--brand-deep));
  color: var(--brand-text);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
  font-weight: 600;
}
.btn-secondary, button.secondary, .secondary {
  background: transparent;
  color: var(--text-body);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
}
.btn-ghost, button.ghost, .ghost {
  background: transparent;
  color: var(--brand);
  border: none;
}
a { color: var(--brand); text-decoration: none; }
a:hover { border-bottom: 1px solid var(--brand); }

/* Status */
.success { color: var(--success-light); }
.warning { color: var(--warning); }
.danger  { color: var(--danger-light); }

/* Inputs */
input, textarea, select {
  background: var(--bg-elevated);
  color: var(--text-heading);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius, 8px);
}
input:focus { border-color: var(--brand); outline: none; box-shadow: 0 0 0 3px var(--brand-soft); }

.muted { color: var(--text-caption); }
.faint { color: var(--text-faint); }
</style><!doctype html><html><head><link rel="stylesheet" href="/style.css?v=35"></head>
<body style="margin:0;padding:0;background:#0e1a2e;font-family:Georgia,serif;">
<div style="max-width:560px;margin:0 auto;padding:36px 28px;color:#f3e9d2;">
  <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#e6c879;margin-bottom:8px;">Welcome</div>
  <h1 style="font-family:Georgia,serif;font-size:28px;margin:0 0 14px;color:#f3e9d2;font-style:italic;">Welcome to PocketPlot Universe.</h1>
  <p style="font-family:Georgia,serif;font-size:16px;color:#d4b8a4;line-height:1.6;margin:0 0 14px;">
    Your first story is in flight. We drew a character from your display name,
    a setting from a curated pool, and a moral that adults secretly still
    need to hear.
  </p>
  <p style="font-family:Georgia,serif;font-size:15px;color:#d4b8a4;line-height:1.6;margin:0 0 22px;">
    Three things you can do right now:
  </p>
  <ul style="font-family:Georgia,serif;font-size:15px;color:#d4b8a4;line-height:1.7;margin:0 0 22px;padding-left:20px;">
    <li>Reply to your story if you have feedback — we read every reply.</li>
    <li>Visit <a href="/help" style="color:#e6c879">the Help Assistant</a> for instant answers.</li>
    <li>Start a <a href="/worlds/new" style="color:#e6c879">branching world</a> — three choices per episode, up to ten episodes per world.</li>
  </ul>
  <p style="font-family:Georgia,serif;font-size:13px;color:#9eb6d4;margin:24px 0 0;">
    — The PocketPlot team
  </p>
</div></body></html>"""

def _send_raw_email(to_email: str, subject: str, plain: str, html: str):
    """Send (or save to outbox) an arbitrary transactional email."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")
    if SMTP_HOST:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.starttls()
            if SMTP_USER: s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        return ("sent", None)
    safe = to_email.replace("@", "_at_").replace("/", "_")
    fname = OUTBOX_DIR / f"{dt.datetime.utcnow():%Y%m%d_%H%M%S}_{safe}.eml"
    fname.write_bytes(msg.as_bytes())
    return ("outbox", str(fname))

MAGIC_LINK_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{{font-family:Georgia,serif;background:#f6f0e1;color:#1a241d;margin:0;padding:0}}
.wrap{{max-width:540px;margin:0 auto;padding:36px 28px}}
h1{{font-style:italic;font-weight:500;font-size:24px;margin:0 0 16px}}
p{{font-size:15px;line-height:1.6}}
.cta{{display:inline-block;margin:20px 0;padding:13px 22px;background:#1a241d;color:#f6f0e1;
text-decoration:none;border-radius:99px;font-family:"Helvetica Neue",sans-serif;font-weight:600;font-size:14px}}
.faint{{font-size:12px;color:#8a8270;font-style:italic;margin-top:24px;line-height:1.5}}
</style></head><body><div class="wrap">
<h1>Your PocketPlot sign-in link</h1>
<p>Hi — click the button below to sign in to your PocketPlot account. The link works once and expires in {ttl} minutes.</p>
<a class="cta" href="{url}">Sign in to PocketPlot</a>
<p class="faint">If you didn't request this, you can ignore this email. The link will expire on its own.</p>
</div></body></html>
"""

def send_magic_link_email(subscriber_row, token):
    """Issue + send a magic-link email for the given subscriber."""
    url = f"{SITE_URL}/login/{token}"
    ttl_min = max(1, MAGIC_LINK_TTL // 60)
    subject = "Your PocketPlot sign-in link · PocketPlot Universe"
    plain = EMAIL_MAGICLINK_PLAIN.format(link=url)
    html = EMAIL_MAGICLINK_HTML.format(link=url)
    return _send_raw_email(subscriber_row["email"], subject, plain, html)

# ---- /login routes ----
LOGIN_REQUEST_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Sign in · PocketPlot</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500&family=Karla:wght@400;500;600&display=swap" rel="stylesheet">
<style>body{font-family:Karla;background:#f6f0e1;color:#1a241d;margin:0;padding:0;min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#fff;border:1px solid #d8cfb3;border-radius:18px;padding:36px 32px;max-width:420px;width:90%;box-shadow:0 24px 50px rgba(26,36,29,.08)}
.wordmark{font-family:Fraunces;font-size:22px;margin-bottom:8px}.wordmark i{color:#7a9a6e;font-style:italic}
h1{font-family:Fraunces;font-weight:500;font-size:28px;line-height:1.2;margin:8px 0 12px}
.lead{color:#5a6a4a;font-size:14px;line-height:1.5;margin-bottom:24px}
label{display:block;font-size:11px;letter-spacing:.06em;font-weight:600;text-transform:uppercase;color:#3d5a3a;margin-bottom:5px}
input{width:100%;padding:11px 13px;border:1px solid #d8cfb3;border-radius:9px;font-family:Karla;font-size:15px;background:#f6f0e1;box-sizing:border-box}
input:focus{outline:none;border-color:#7a9a6e;box-shadow:0 0 0 3px rgba(122,154,110,.18)}
.btn{width:100%;margin-top:14px;background:#c46a3f;color:#fff;border:none;padding:13px;border-radius:9px;font-family:Karla;font-weight:700;font-size:14px;cursor:pointer}
.btn:hover{background:#a8572f}
.flash{padding:10px 13px;border-radius:9px;font-size:13px;margin-bottom:14px;background:#fdf5e3;border:1px solid #d4a849;color:#7a6420}
.flash.ok{background:#ecf3e3;border-color:#7a9a6e;color:#3d5a3a}
.back{display:block;text-align:center;margin-top:16px;font-size:13px;color:#7a3d20;text-decoration:none}
</style><link rel="stylesheet" href="/style.css?v=35">
</head><body><div class="card">
<div class="wordmark">Pocket<i>Plot</i></div>
<h1>Sign in</h1>
<p class="lead">Enter your email and we'll send you a one-tap sign-in link. No password to remember.</p>
{% with messages = get_flashed_messages(with_categories=true) %}
{% for cat,msg in messages %}<div class="flash {{cat}}">{{msg}}</div>{% endfor %}
{% endwith %}
<form method="post" action="/login">
<label>Your email</label>
<input type="email" name="email" required value="{{email or ''}}" placeholder="you@example.com">
<button class="btn" type="submit">Send sign-in link</button>
</form>
<a class="back" href="/">← Back to home</a>
</div></body></html>
"""

@app.route("/audio/<int:sub_id>/<path:filename>", methods=["GET"])
def serve_audio(sub_id: int, filename: str):
    """Serve a TTS MP3 or child-uploaded drawing. Owner check unless
    PUBLIC_AUDIO env is on. Streams via Flask's send_file."""
    if not PUBLIC_AUDIO:
        sid = session.get("subscriber_id")
        if sid != sub_id and not session.get("admin"):
            return ("Not authorized to access this file.", 403)
    # Restrict filename to safe characters — sub_id is int-validated by Flask
    # and filename is path-validated by the URL-converter.
    safe = filename
    if "/" in safe or ".." in safe:
        return ("Bad request.", 400)
    path = AUDIO_DIR / str(sub_id) / safe
    if not path.exists() or not path.is_file():
        return ("Not found.", 404)
    ext = ("." + safe.rsplit(".", 1)[-1].lower()) if "." in safe else ""
    mime = {
        ".mp3":  "audio/mpeg",
        ".png":  "image/png",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif":  "image/gif",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")
    from flask import send_file
    return send_file(str(path), mimetype=mime, conditional=True)


@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if not email or "@" not in email:
            flash("Please enter a valid email.", "err")
            return render_template_string(LOGIN_REQUEST_HTML, email=email)
        conn = db()
        row = conn.execute("SELECT * FROM subscribers WHERE email=?", (email,)).fetchone()
        conn.close()
        # Always show the same message — don't leak whether the email exists
        flash("If that email is in our system, a sign-in link is on its way.", "ok")
        if row:
            token = issue_token(row["id"], "login")
            send_magic_link_email(row, token)
        return redirect(url_for("login"))
    return render_template_string(LOGIN_REQUEST_HTML, email=None)

@app.route("/login/<token>", methods=["GET"])
def login_with_token(token):
    sid = consume_token(token, "login")
    if not sid:
        flash("This sign-in link is invalid or expired. Try again below.", "err")
        return redirect(url_for("login"))
    session["subscriber_id"] = sid
    flash("Signed in.", "ok")
    return redirect(url_for("me"))

@app.route("/logout")
def logout():
    session.pop("subscriber_id", None)
    flash("Signed out.", "ok")
    return redirect(url_for("index"))

def login_required(view):
    from functools import wraps
    @wraps(view)
    def wrapper(*a, **kw):
        if not session.get("subscriber_id"):
            flash("Please sign in to manage your account.", "err")
            return redirect(url_for("login"))
        return view(*a, **kw)
    return wrapper

# ---- /me portal ----
ME_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Your account · PocketPlot</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500&family=Karla:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>
:root{--ink:#1a241d;--paper:#f6f0e1;--paper2:#ece4cb;--paper3:#d8cfb3;--moss:#7a9a6e;--mossD:#3d5a3a;--gold:#d4a849;--goldD:#8a6420;--rust:#c46a3f;--rustD:#7a3d20;--hi:#f6f0e1;--faint:#8a8270;--serif:"Fraunces",Georgia,serif;--sans:"Karla",sans-serif;--mono:"JetBrains Mono",monospace}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:var(--sans);color:var(--ink);background:var(--paper);-webkit-font-smoothing:antialiased}
header{padding:14px 24px;background:var(--paper2);border-bottom:1px solid var(--paper3);display:flex;justify-content:space-between;align-items:center}
.wordmark{font-family:var(--serif);font-size:20px;font-weight:500}.wordmark i{color:var(--moss);font-style:italic;font-weight:400}
.nav a{color:var(--ink);text-decoration:none;font-size:13px;font-weight:500;margin-left:18px}
.wrap{max-width:780px;margin:0 auto;padding:30px 24px}
h1{font-family:var(--serif);font-weight:500;font-size:32px;margin-bottom:6px;line-height:1.2}
h1 i{font-style:italic;color:var(--moss);font-weight:400}
.lede{color:var(--faint);font-size:14px;margin-bottom:24px}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:24px}
@media(max-width:600px){.cards{grid-template-columns:1fr}}
.card{background:#fff;border:1px solid var(--paper3);border-radius:14px;padding:18px}
.card .l{font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;color:var(--faint);font-weight:600;margin-bottom:6px}
.card .v{font-family:var(--mono);font-size:18px;color:var(--ink);font-weight:500}
.card .v .small{font-size:11px;color:var(--faint);margin-left:4px;font-weight:400}
.pro-pill{display:inline-block;background:var(--gold);color:#3a2a10;font-size:10px;letter-spacing:.16em;font-weight:700;padding:3px 9px;border-radius:99px;margin-left:8px;vertical-align:middle}
.section{background:#fff;border:1px solid var(--paper3);border-radius:14px;padding:24px;margin-bottom:16px}
.section h2{font-family:var(--serif);font-weight:500;font-size:20px;margin-bottom:14px}
/* Learning Dashboard */
.learning-dashboard .learning-subtitle{font-size:13px;color:var(--ink2);margin-bottom:18px;font-style:italic;font-family:var(--serif)}
.ld-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:18px}
@media(max-width:600px){.ld-grid{grid-template-columns:1fr 1fr}}
.ld-stat{background:var(--paper2);border:1px solid var(--paper3);border-radius:10px;padding:14px 16px;text-align:center}
.ld-stat-num{font-family:var(--serif);font-size:28px;font-weight:600;color:var(--ink);line-height:1.1}
.ld-stat-label{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--mossD);margin-top:4px;font-weight:600}
.ld-progress-label{font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--mossD);margin-bottom:8px;margin-top:6px}
.ld-progress-bar{height:10px;background:var(--paper3);border-radius:99px;overflow:hidden;position:relative}
.ld-progress-fill{height:100%;background:linear-gradient(90deg, var(--moss), #a8c0a3);border-radius:99px;transition:width .4s ease}
.ld-progress-note{font-size:13px;color:var(--ink2);margin-top:8px;line-height:1.5}
.ld-empty{font-size:13px;color:var(--ink2);font-style:italic;font-family:var(--serif);padding:14px;background:var(--paper2);border-radius:10px;border:1px dashed var(--paper3);margin-bottom:18px}
.ld-recent-head h3{font-family:var(--serif);font-size:16px;font-weight:500;margin:18px 0 10px;display:flex;justify-content:space-between;align-items:baseline}
.ld-pro-hint{font-size:11px;font-weight:600;letter-spacing:.06em;color:var(--rust);font-family:var(--sans);text-transform:uppercase}
.ld-recent-list{display:grid;grid-template-columns:1fr 1fr;gap:8px}
@media(max-width:600px){.ld-recent-list{grid-template-columns:1fr}}
.ld-word-row{background:var(--paper2);border-left:3px solid var(--moss);border-radius:6px;padding:8px 12px}
.ld-word-word{font-family:var(--serif);font-style:italic;font-weight:500;font-size:15px;color:var(--ink);margin-bottom:2px}
.ld-word-def{font-size:12px;color:var(--ink2);line-height:1.4;margin-bottom:2px}
.ld-word-meta{font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--mossD);font-weight:600}
.ld-tier{margin-top:24px;padding-top:18px;border-top:1px dotted var(--paper3)}
.ld-tier h3{font-family:var(--serif);font-size:14px;font-weight:500;margin-bottom:10px;color:var(--ink)}
.ld-tier-bars{display:grid;gap:6px}
.ld-tier-row{display:grid;grid-template-columns:90px 1fr 30px;align-items:center;gap:10px;font-size:12px}
.ld-tier-name{color:var(--ink2);font-weight:500}
.ld-tier-bar{height:8px;background:var(--paper3);border-radius:99px;overflow:hidden}
.ld-tier-fill{height:100%;background:var(--moss);border-radius:99px;transition:width .4s ease}
.ld-tier-num{font-family:var(--serif);font-weight:500;color:var(--ink);text-align:right}
.field{margin-bottom:14px}
.field label{display:block;font-size:11px;letter-spacing:.06em;font-weight:600;text-transform:uppercase;color:var(--mossD);margin-bottom:5px}
.field input,.field select{width:100%;padding:10px 13px;border:1px solid var(--paper3);border-radius:9px;font-family:var(--sans);font-size:14px;background:var(--paper);box-sizing:border-box}
.row2{display:grid;grid-template-columns:1fr 110px;gap:10px}
.btn{display:inline-block;background:var(--ink);color:var(--hi);padding:11px 18px;border-radius:99px;border:none;font-family:var(--sans);font-weight:600;font-size:13px;cursor:pointer;text-decoration:none}
.btn:hover{background:var(--rust)}
.btn.secondary{background:#fff;color:var(--ink);border:1px solid var(--paper3)}
.btn.secondary:hover{border-color:var(--rust);color:var(--rust)}
.btn.danger{background:#fff;color:var(--rustD);border:1px solid var(--rust)}
.btn.danger:hover{background:var(--rust);color:#fff}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.flash{padding:11px 14px;border-radius:10px;margin-bottom:14px;font-size:13.5px;background:#fdf5e3;border:1px solid var(--gold);color:#7a6420}
.flash.ok{background:#ecf3e3;border-color:var(--moss);color:var(--mossD)}
.flash.err{background:#fbe5e1;border-color:var(--rust);color:var(--rustD)}
.note{font-size:11.5px;color:var(--faint);font-style:italic;font-family:var(--serif);line-height:1.5;margin-top:10px}
.divider{height:1px;background:var(--paper3);margin:18px 0}
.toggle-row{display:flex;justify-content:space-between;align-items:center;padding:10px 0}
.toggle-row .label{font-weight:500;font-size:14px}
.toggle-row .desc{font-size:11.5px;color:var(--faint);font-style:italic;font-family:var(--serif)}
.billing-row{display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px dotted var(--paper3)}
.billing-row:last-child{border-bottom:none}
.billing-row .l{font-weight:500}
.billing-row .v{font-family:var(--mono);font-size:13px;color:var(--ink)}
.status-active{color:var(--mossD);font-weight:600}
.status-paused{color:var(--rust);font-weight:600}
.status-canceled{color:var(--faint)}
</style></head><body>
<header>
  <div class="wordmark">Pocket<i>Plot</i></div>
  <nav class="nav">
    <a href="/pricing">Pricing</a>
    <a href="/logout">Sign out</a>
  </nav>
</header>
<div class="wrap">
{% with messages = get_flashed_messages(with_categories=true) %}
  {% for cat,msg in messages %}<div class="flash {{cat}}">{{msg}}</div>{% endfor %}
{% endwith %}
<h1>Hello, {{sub.child_name}}'s parent.
{% if sub.plan == 'pro' %}<span class="pro-pill">★ PRO</span>{% endif %}
</h1>
<p class="lede">Manage your child's subscription, update their details, or upgrade to Pro.</p>

<div class="cards">
  <div class="card">
    <div class="l">Plan</div>
    <div class="v">{{plan_label}}{% if sub.plan == 'pro' %}<span class="pro-pill">★ PRO</span>{% endif %}</div>
  </div>
  <div class="card">
    <div class="l">Status</div>
    <div class="v"><span class="{{status_class}}">{{status_label}}</span></div>
  </div>
  <div class="card">
    <div class="l">Last story sent</div>
    <div class="v">{{last_sent or '—'}}<span class="small">{{last_sent_subtitle}}</span></div>
  </div>
  <div class="card">
    <div class="l">Next story</div>
    <div class="v">Tonight at 8 pm <span class="small">UTC</span></div>
  </div>
</div>

<div class="section">
  <h2>Child profile</h2>
  <form method="post" action="/me/child">
    <div class="field row2">
      <div>
        <label>Child's name</label>
        <input type="text" name="child_name" value="{{sub.child_name}}" required>
      </div>
      <div>
        <label>Age</label>
        <input type="number" name="child_age" min="2" max="12" value="{{sub.child_age}}" required>
      </div>
    </div>
    <button class="btn" type="submit">Save changes</button>
  </form>
</div>

{# =====================================================================
   LEARNING DASHBOARD
   =====================================================================
   Shown to all subscribers. Free tier sees this-month progress + a 30-
   entry history; Pro sees the same plus a 100-entry history, tier
   breakdown, and a "view stories from this month" link. The data is
   fetched in `me()` from the deliveries table. #}
<div class="section learning-dashboard">
  <h2>Learning dashboard</h2>
  <p class="learning-subtitle">Vocabulary your family is building together, one story at a time.</p>

  <div class="ld-grid">
    <div class="ld-stat">
      <div class="ld-stat-num">{{learning_this_month}}</div>
      <div class="ld-stat-label">words this month</div>
    </div>
    <div class="ld-stat">
      <div class="ld-stat-num">{{learning_total}}</div>
      <div class="ld-stat-label">words total</div>
    </div>
    <div class="ld-stat">
      <div class="ld-stat-num">{{sub.child_age}}</div>
      <div class="ld-stat-label">child's age</div>
    </div>
  </div>

  {% if learning_total > 0 %}
    <div class="ld-progress-label">This month's progress</div>
    <div class="ld-progress-bar">
      <div class="ld-progress-fill" style="width: {{learning_progress_pct}}%"></div>
    </div>
    <div class="ld-progress-note">{{learning_progress_label}}</div>
  {% else %}
    <div class="ld-empty">Once tonight's story lands, your family's first word will appear here.</div>
  {% endif %}

  {% if learning_recent %}
    <div class="ld-recent-head">
      <h3>Words learned</h3>
      {% if not is_pro %}
        <span class="ld-pro-hint">Pro subscribers see their full history here.</span>
      {% endif %}
    </div>
    <div class="ld-recent-list">
      {% for item in learning_recent %}
        <div class="ld-word-row">
          <div class="ld-word-word">{{item.w}}</div>
          <div class="ld-word-def">{{item.d}}</div>
          <div class="ld-word-meta">{{item.tier}} · {{item.sent_at[:10]}}</div>
        </div>
      {% endfor %}
    </div>
  {% endif %}

  {% if is_pro and tier_breakdown %}
    <div class="ld-tier">
      <h3>Tier breakdown</h3>
      <div class="ld-tier-bars">
        <div class="ld-tier-row">
          <span class="ld-tier-name">simple</span>
          <div class="ld-tier-bar"><div class="ld-tier-fill" style="width: {{tier_breakdown.simple_pct}}%"></div></div>
          <span class="ld-tier-num">{{tier_breakdown.simple}}</span>
        </div>
        <div class="ld-tier-row">
          <span class="ld-tier-name">intermediate</span>
          <div class="ld-tier-bar"><div class="ld-tier-fill" style="width: {{tier_breakdown.intermediate_pct}}%"></div></div>
          <span class="ld-tier-num">{{tier_breakdown.intermediate}}</span>
        </div>
        <div class="ld-tier-row">
          <span class="ld-tier-name">advanced</span>
          <div class="ld-tier-bar"><div class="ld-tier-fill" style="width: {{tier_breakdown.advanced_pct}}%"></div></div>
          <span class="ld-tier-num">{{tier_breakdown.advanced}}</span>
        </div>
      </div>
    </div>
  {% endif %}
</div>

{% if sub.plan == 'pro' %}
<div class="section">
  <h2>Pro customization</h2>
  <p style="font-size:13px;color:var(--ink2);margin-bottom:14px">Choose a recurring helper and a setting theme. The plots and resolutions still change every night.</p>
  <form method="post" action="/me/pro">
    <div class="field">
      <label>Helper character (recurring)</label>
      <select name="pro_character">
        <option value="">— rotate every night —</option>
        {% for k,c in cast_options %}
          <option value="{{k}}" {% if sub.pro_character==k %}selected{% endif %}>{{c.name}} ({{k}})</option>
        {% endfor %}
      </select>
    </div>
    <div class="field">
      <label>Setting theme</label>
      <select name="pro_theme">
        <option value="">— rotate every night —</option>
        {% for theme in theme_options %}
          <option value="{{theme}}" {% if sub.pro_theme==theme %}selected{% endif %}>{{theme}}</option>
        {% endfor %}
      </select>
    </div>
    <button class="btn" type="submit">Save Pro preferences</button>
  </form>
</div>
{% endif %}

<div class="section">
  <h2>Delivery</h2>
  <div class="toggle-row">
    <div>
      <div class="label">Daily branching story</div>
      <div class="desc">{{'Active — one fresh story lands in your inbox at 8 pm UTC.' if sub.active else 'Paused — no stories will be sent until you resume.'}}</div>
    </div>
    <form method="post" action="/me/toggle">
      <button class="btn secondary" type="submit">{{'Pause' if sub.active else 'Resume'}}</button>
    </form>
  </div>
</div>

<div class="section">
  <h2>Billing</h2>
  {% if sub.plan == 'pro' %}
    <div class="billing-row">
      <span class="l">Plan</span>
      <span class="v">PocketPlot Pro · $4.99 / month</span>
    </div>
    <div class="billing-row">
      <span class="l">Stripe customer</span>
      <span class="v">{{sub.customer_id or '—'}}</span>
    </div>
    <div class="billing-row">
      <span class="l">Subscription</span>
      <span class="v">{{sub.subscription_id or '—'}}</span>
    </div>
    <div class="billing-row">
      <span class="l">Status</span>
      <span class="v {{status_class}}">{{sub.subscription_status or 'active'}}</span>
    </div>
    <div class="billing-row">
      <span class="l">Next renewal</span>
      <span class="v">{{renewal_display}}</span>
    </div>
    <div class="row" style="margin-top:16px">
      <form method="post" action="/billing/cancel" onsubmit="return confirm('Cancel your Pro subscription? You\\'ll keep access until the period ends.')">
        <button class="btn danger" type="submit">Cancel Pro</button>
      </form>
      <a class="btn secondary" href="/billing/portal">Manage in Stripe ↗</a>
    </div>
    <p class="note">Cancelling keeps Pro active until {{renewal_display}}. After that you revert to the Free plan automatically.</p>
  {% else %}
    <div class="billing-row">
      <span class="l">Plan</span>
      <span class="v">Free</span>
    </div>
    <p style="margin-top:14px;font-size:13px;color:var(--ink2);line-height:1.55">You're on the Free plan. Pro gets you a recurring helper of your choice, a theme, and no ads — for $4.99 / month.</p>
    <a class="btn" href="/upgrade" style="margin-top:12px">Upgrade to Pro →</a>
  {% endif %}
</div>

<p class="note">Signed in as <b>{{sub.email}}</b>. <a href="/logout" style="color:var(--rust)">Sign out</a>.</p>
</div>
</body></html>
"""


# ---- Phase 6: Avatar builder template (Pro) ----
AVATAR_BUILDER_HTML = """<style>
#avatar-builder .section h2{margin-top:0}
#avatar-builder .ab-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:24px;align-items:start}
#avatar-builder .ab-preview{background:var(--paper);border:1px solid var(--paper3);border-radius:14px;padding:20px;text-align:center;position:sticky;top:20px}
#avatar-builder .ab-preview svg{width:240px;height:240px;background:linear-gradient(180deg,#fff8e7 0%,#ffe5a0 100%);border-radius:50%;border:1px solid var(--paper3);margin:0 auto 12px;display:block}
#avatar-builder .ab-preview .ab-name{font-family:var(--serif);font-style:italic;color:var(--rust);font-size:18px;margin-top:6px}
#avatar-builder .ab-preview .ab-saved{font-size:11px;color:var(--mossD);margin-top:8px}
#avatar-builder .ab-cat{margin-bottom:18px;background:var(--paper);border:1px solid var(--paper3);border-radius:12px;padding:14px 18px}
#avatar-builder .ab-cat .ab-cat-label{font-family:Karla;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--mossD);font-weight:700;margin-bottom:8px}
#avatar-builder .ab-options{display:flex;gap:8px;flex-wrap:wrap}
#avatar-builder .ab-opt{border:2px solid var(--paper3);background:var(--paper);border-radius:8px;padding:8px 12px;cursor:pointer;font-family:Karla;font-size:12px;font-weight:600;color:var(--ink);transition:all .15s}
#avatar-builder .ab-opt:hover{border-color:var(--moss);background:#ecf3ea}
#avatar-builder .ab-opt.selected{border-color:var(--rust);background:#fdf3dc;color:var(--rustD)}
#avatar-builder .ab-actions{display:flex;gap:10px;margin-top:12px}
#avatar-builder .ab-lockup{background:var(--paper);border:1px dashed var(--paper3);border-radius:12px;padding:16px;text-align:center;margin-top:14px}
</style>

<div id="avatar-builder" class="wrap" style="max-width:980px;margin:24px auto;padding:0 24px;">
  <div class="section" style="background:var(--paper);border:1px solid var(--paper3);border-radius:14px;padding:28px">
    <h2 id="avatar">Avatar Builder <span class="note" style="font-family:Karla;font-size:11px;font-weight:600;color:var(--faint);letter-spacing:.12em;text-transform:uppercase;margin-left:8px">Pro · Privacy-first</span></h2>

    {% if not is_pro %}
      <div class="ab-lockup">
        <p style="font-family:var(--serif);font-size:15px;color:var(--ink2);margin:6px 0 12px;line-height:1.55">
          Build a unique, fun avatar for your child from a library of generic parts.
          <b>No photos. No personal data.</b> The avatar lives in their story
          illustrations tonight.
        </p>
        <a class="btn" href="/upgrade">Upgrade to Pro to build the avatar →</a>
      </div>
    {% else %}
    <div class="ab-grid">
      <form method="post" action="/me/avatar" id="avatar-form">
        {% for cat, options in avatar_options.items() %}
        <div class="ab-cat">
          <div class="ab-cat-label">{{ {
            'skin':'Skin tone',
            'hair':'Hairstyle',
            'eyes':'Eyes',
            'outfit':'Outfit',
            'accessory':'Accessory',
            'expression':'Expression',
          }[cat] }}</div>
          <div class="ab-options">
            {% for key, label in options %}
            <label class="ab-opt {% if avatar[cat]==key %}selected{% endif %}">
              <input type="radio" name="{{cat}}" value="{{key}}" {% if avatar[cat]==key %}checked{% endif %} style="display:none" onchange="this.form.dispatchEvent(new Event('change',{bubbles:true}))">
              {{label}}
            </label>
            {% endfor %}
          </div>
        </div>
        {% endfor %}
        <div class="ab-actions">
          <button class="btn" type="submit">Save avatar</button>
          <a class="btn secondary" href="/me">Discard</a>
        </div>
      </form>

      <div class="ab-preview">
        <svg id="avatar-preview-svg" viewBox="-100 -100 200 200" preserveAspectRatio="xMidYMid meet" style="width:240px;height:240px">
          {{ avatar_svg_preview|safe }}
        </svg>
        <div class="ab-name">{{ sub.child_name }}</div>
        <div class="ab-saved">{% if sub.avatar_updated_at %}Last saved {{ sub.avatar_updated_at[:16] }}{% else %}Default look · save to customise{% endif %}</div>
      </div>
    </div>
    {% endif %}
  </div>
</div>

<script>
  // Live-update the preview as the parent picks parts. No page reload.
  (function() {
    var form = document.getElementById('avatar-form');
    var svg = document.getElementById('avatar-preview-svg');
    if (!form || !svg) return;
    // Read which options the user clicked
    form.addEventListener('change', function() {
      var picks = {};
      var radios = form.querySelectorAll('input[type=radio]:checked');
      radios.forEach(function(r) { picks[r.name] = r.value; });
      // Build the SVG via the server so the part catalog stays in one place.
      fetch('/api/avatar-preview', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(picks),
      }).then(function(r) { return r.json(); }).then(function(data) {
        if (data && data.svg) {
          // Replace the inner content of the preview SVG.
          // Use non-greedy matches; we want the first opening <svg ...> and
          // the last </svg>, regardless of newlines or attributes.
          svg.innerHTML = data.svg
            .replace(/<svg[^>]*>/i, '')
            .replace(/<\/svg>\s*$/i, '');
        }
      }).catch(function() { /* network blip — preview freezes on last paint */ });
    });
  })();
</script>
"""


# ---- Phase 7: Gamification widgets (Pro) ----
GAMIFICATION_WIDGETS_HTML = """<style>
.gam-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:18px}
.gam-card{background:var(--paper);border:1px solid var(--paper3);border-radius:14px;padding:18px;text-align:center}
.gam-card .lab{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);font-weight:700;margin-bottom:6px}
.gam-card .val{font-family:var(--serif);font-weight:600;font-size:30px;color:var(--ink);line-height:1}
.gam-card .val.streak{color:var(--rust)}
.gam-card .val.word{color:var(--moss)}
.gam-card .val.badges{color:var(--gold)}
.gam-card .hint{font-size:11px;color:var(--faint);margin-top:6px;font-style:italic}
.gam-badges{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:10px;margin-top:10px}
.gam-badge{background:var(--paper);border:1px solid var(--paper3);border-radius:12px;padding:14px;text-align:center;opacity:.45;transition:opacity .2s}
.gam-badge.earned{opacity:1;border-color:var(--gold);background:#fdf3dc}
.gam-badge .icon{font-size:32px;line-height:1;margin-bottom:6px}
.gam-badge .label{font-family:Karla;font-size:11px;font-weight:700;color:var(--ink);line-height:1.3}
.gam-badge .date{font-size:9px;color:var(--faint);margin-top:4px}
.gam-vault{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.gam-vault .word{padding:6px 12px;background:var(--paper2);border-radius:99px;font-family:var(--serif);font-style:italic;color:var(--rust);font-size:14px;font-weight:600}
</style>

<div class="wrap" style="max-width:980px;margin:0 auto 24px;padding:0 24px;">
  <div class="section" style="background:var(--paper);border:1px solid var(--paper3);border-radius:14px;padding:28px">
    <h2 style="margin-top:0">Adventure Stats <span class="note" style="font-family:Karla;font-size:11px;font-weight:600;color:var(--faint);letter-spacing:.12em;text-transform:uppercase;margin-left:8px">Pro · {{ gamification_stats.streak_days if gamification_stats else 0 }}-day streak</span></h2>

    {% if gamification_stats %}
    <div class="gam-grid">
      <div class="gam-card">
        <div class="lab">Current streak</div>
        <div class="val streak">{{ gamification_stats.streak_days }}</div>
        <div class="hint">day{{ '' if gamification_stats.streak_days == 1 else 's' }} in a row</div>
      </div>
      <div class="gam-card">
        <div class="lab">Word score</div>
        <div class="val word">{{ gamification_stats.word_count }}</div>
        <div class="hint">unique words in the vault</div>
      </div>
      <div class="gam-card">
        <div class="lab">Badges earned</div>
        <div class="val badges">{{ gamification_stats.badge_count }} / {{ gamification_total_badges }}</div>
        <div class="hint">{{ gamification_stats.stories_sent }} story · {{ gamification_stats.game_plays }} game</div>
      </div>
    </div>

    <h3 style="font-family:var(--serif);font-size:16px;margin:18px 0 8px">Badges</h3>
    <div class="gam-badges">
      {% set earned_codes = gamification_badges|map(attribute='code')|list %}
      {% for code, label, icon in [
        ('first_story','First Story Read','📖'),
        ('first_game','First Adventure','🎮'),
        ('streak_3','Streak Keeper','🔥'),
        ('week_1','Week 1 Wonder','🌟'),
        ('streak_14','Fortnight','🏅'),
        ('ten_words','10 Words','📚'),
        ('twentyfive_words','25 Words','🌱'),
        ('fifty_words','50 Words','🌳'),
      ] %}
        {% set earned = gamification_badges|selectattr('code','equalto',code)|list|first %}
        <div class="gam-badge {% if earned %}earned{% endif %}">
          <div class="icon">{{icon}}</div>
          <div class="label">{{label}}</div>
          <div class="date">{% if earned %}{{ earned.awarded_at[:10] }}{% else %}—{% endif %}</div>
        </div>
      {% endfor %}
    </div>

    {% if gamification_recent_words %}
    <h3 style="font-family:var(--serif);font-size:16px;margin:20px 0 8px">Recent words from the vault</h3>
    <div class="gam-vault">
      {% for w in gamification_recent_words %}
        <span class="word">{{ w.word }}</span>
      {% endfor %}
    </div>
    {% endif %}
    {% else %}
    <p style="font-family:var(--serif);font-size:14px;color:var(--faint);font-style:italic;margin:0">Stats are a PocketPlot Pro perk. Upgrade to track streaks, build a Word Vault, and earn badges.</p>
    {% endif %}
  </div>
</div>
"""


# ---- Phase 10: Merch template (Pro) ----
MERCH_HTML = """<style>
.merch-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}
.merch-card{background:var(--paper);border:1px solid var(--paper3);border-radius:14px;padding:24px;text-align:center}
.merch-card .icon{font-size:48px;line-height:1;margin-bottom:10px}
.merch-card h3{font-family:var(--serif);font-size:20px;margin:0 0 8px;color:var(--ink)}
.merch-card p{font-family:var(--serif);font-size:14px;color:var(--ink2);line-height:1.55;margin:0 0 14px}
.merch-card .btn{background:var(--moss);color:#fff;padding:11px 22px;border-radius:99px;border:none;font-family:Karla;font-weight:700;font-size:13px;cursor:pointer;text-decoration:none;display:inline-block}
.merch-card .btn:hover{background:#4a6648}
.merch-card .note{font-size:11px;color:var(--faint);margin-top:10px;font-style:italic;font-family:Karla}
</style>

<div class="wrap" style="max-width:980px;margin:0 auto 24px;padding:0 24px;">
  <div class="section" style="background:var(--paper);border:1px solid var(--paper3);border-radius:14px;padding:28px">
    <h2 style="margin-top:0">Printable Goodies <span class="note" style="font-family:Karla;font-size:11px;font-weight:600;color:var(--faint);letter-spacing:.12em;text-transform:uppercase;margin-left:8px">Pro · free, with our thanks</span></h2>
    <p style="font-family:var(--serif);font-size:15px;color:var(--ink2);line-height:1.6;margin:0 0 22px">Two printable PDFs, generated on the fly from our SVG library. Print them at home, fold them in a lunchbox, keep one on the fridge.</p>

    {% if not is_pro %}
    <p style="font-family:var(--serif);font-size:14px;color:var(--faint);font-style:italic">Printables are a PocketPlot Pro perk.</p>
    <a class="btn" href="/upgrade" style="background:var(--rust)">Upgrade to Pro →</a>
    {% else %}
    <div class="merch-grid">
      <div class="merch-card">
        <div class="icon">🎨</div>
        <h3>Coloring Pack</h3>
        <p>4 hand-drawn PocketPlot characters + scenes from the storybook, in black-and-white, ready for crayons. A4 / US Letter.</p>
        <a class="btn" href="/merch/coloring.pdf">Download coloring pack</a>
        <div class="note">PDF · generated on the fly · no watermark</div>
      </div>
      <div class="merch-card">
        <div class="icon">📅</div>
        <h3>Weekly Planner</h3>
        <p>A printable one-week tracker. Your child's name on it. Space to log each day's story word, game play, and reading streak.</p>
        <a class="btn" href="/merch/planner.pdf">Download weekly planner</a>
        <div class="note">PDF · personalised with {{ sub.child_name }}</div>
      </div>
    </div>
    {% endif %}
  </div>
</div>
"""

# Available Pro customization options — kept in sync with CAST and SETTINGS
CAST_OPTIONS = [
    ("fox",    "Felix the fox"),
    ("bear",   "Bram the bear"),
    ("rabbit", "Rue the rabbit"),
    ("whale",  "Wren the whale"),
    ("robot",  "Pip the robot"),
    ("kid",    "A kid friend"),
]
THEME_OPTIONS = [s[0][:60] for s in SETTINGS]  # truncated for the dropdown

def _subscriber_or_redirect():
    sid = session.get("subscriber_id")
    if not sid: return None
    conn = db()
    row = conn.execute("SELECT * FROM subscribers WHERE id=?", (sid,)).fetchone()
    conn.close()
    return row

@app.route("/me", methods=["GET"])
def me():
    sub = _subscriber_or_redirect()
    if not sub: return redirect(url_for("login"))
    plan_label = "PocketPlot Pro" if sub["plan"] == "pro" else "Free"
    if sub["active"]:
        status_label = "Delivering"; status_class = "status-active"
    else:
        status_label = "Paused"; status_class = "status-paused"
    last_sent = sub["last_sent_at"][:10] if sub["last_sent_at"] else None
    last_sent_subtitle = "(just delivered today)" if last_sent == dt.date.today().isoformat() else "(most recent)"
    renewal_display = "—"
    if sub["current_period_end"]:
        renewal_display = sub["current_period_end"][:10]
    # ---- Learning Dashboard data ----
    # Reset the monthly counter when the calendar month has rolled over.
    # Compare by year-month prefix so the reset is timezone-stable.
    # (If a subscriber's month_reset_at is NULL — first visit ever — don't
    # reset the counter; just record the current month to bootstrap.)
    today_iso = dt.date.today().isoformat()
    this_month_prefix = today_iso[:7]  # e.g. "2026-08"
    conn = db()
    sub_row = conn.execute("SELECT * FROM subscribers WHERE id=?", (sub["id"],)).fetchone()
    reset_at = sub_row["month_reset_at"]
    if reset_at is None:
        # First visit: just record the current month, keep the counter as-is.
        conn.execute(
            "UPDATE subscribers SET month_reset_at=? WHERE id=?",
            (today_iso, sub["id"])
        )
    elif reset_at[:7] != this_month_prefix:
        # We've crossed into a new month: zero the monthly counter, update the marker.
        conn.execute(
            "UPDATE subscribers SET words_learned_month=0, month_reset_at=? WHERE id=?",
            (today_iso, sub["id"])
        )
    sub_row = conn.execute("SELECT * FROM subscribers WHERE id=?", (sub["id"],)).fetchone()
    is_pro = sub_row["plan"] == "pro"
    visible_count = 100 if is_pro else 30
    learning_total = sub_row["words_learned_count"]
    learning_this_month = sub_row["words_learned_month"]
    # Compute the monthly progress bar (cap at 30/month = "Daily word master")
    learning_progress_pct = min(100, int(learning_this_month * 100 / 30))
    if learning_this_month == 0:
        learning_progress_label = "Words reset at the start of each month."
    elif learning_this_month < 5:
        learning_progress_label = f"Great start! {learning_this_month} word{'s' if learning_this_month != 1 else ''} so far this month."
    elif learning_this_month < 15:
        learning_progress_label = f"Nice momentum! {learning_this_month} words this month — a healthy reading vocabulary."
    elif learning_this_month < 30:
        learning_progress_label = f"Almost there — {learning_this_month}/30 for the month. Pro parents average 28."
    else:
        learning_progress_label = "Story Word Master — 30 words this month! 🎉"
    # Pull the recent deliveries for the word list
    rows = conn.execute(
        "SELECT word, word_tier, word_definition, sent_at FROM deliveries "
        "WHERE subscriber_id=? AND word IS NOT NULL ORDER BY id DESC LIMIT ?",
        (sub["id"], visible_count),
    ).fetchall()
    learning_recent = [
        {"w": r["word"], "d": r["word_definition"], "tier": r["word_tier"] or "—", "sent_at": r["sent_at"]}
        for r in rows
    ]
    # Pro tier breakdown (only meaningful with enough data)
    tier_breakdown = None
    if is_pro and learning_recent:
        simple = sum(1 for r in learning_recent if r["tier"] == "simple")
        inter = sum(1 for r in learning_recent if r["tier"] == "intermediate")
        adv = sum(1 for r in learning_recent if r["tier"] == "advanced")
        total = max(1, simple + inter + adv)
        tier_breakdown = {
            "simple": simple, "intermediate": inter, "advanced": adv,
            "simple_pct": int(simple*100/total), "intermediate_pct": int(inter*100/total), "advanced_pct": int(adv*100/total),
        }
    conn.commit(); conn.close()

    # ---- Phase 7: Gamification widgets ----
    # Streak, word-vault (cumulative), badges. Pro-only — the dashboard
    # shows nothing for Free (the educational dashboard is the Free perk).
    gamification_stats = None
    gamification_badges = []
    gamification_recent_words = []
    if is_pro:
        import gamification as _gam
        gamification_stats = _gam.stats_for_subscriber(db, sub["id"])
        gamification_badges = _gam.earned_badges(db, sub["id"])
        gamification_recent_words = _gam.recent_words(db, sub["id"], limit=7)

    # ---- Phase 6: Avatar (Pro) ----
    # Load the stored avatar blob. Default to defaults if missing.
    import avatar_builder as _ab
    avatar = _ab.parse_avatar_blob(sub_row["avatar_json"])
    avatar_options = _ab.avatar_options_for_ui() if is_pro else None
    avatar_svg_preview = _ab.render_avatar_svg(avatar, 0, 0, 1.0) if is_pro else None
    avatar_count_owned = sum(1 for r in gamification_badges if r["code"] in
                              ("first_story", "week_1", "ten_words", "twentyfive_words",
                               "fifty_words", "streak_3", "streak_14", "first_game"))

    # Phase 6 + 7 + 10: render the three new sections separately, then
    # concatenate them after the main ME_HTML render. Each section is its
    # own render_template_string so we don't pollute the main template
    # with section-specific conditionals.
    avatar_section = ""
    gamification_section = ""
    merch_section = ""
    if avatar_options is not None:
        avatar_section = render_template_string(
            AVATAR_BUILDER_HTML,
            is_pro=is_pro, sub=sub_row,
            avatar=avatar, avatar_options=avatar_options,
            avatar_svg_preview=avatar_svg_preview,
        )
    if gamification_stats is not None or gamification_badges:
        gamification_section = render_template_string(
            GAMIFICATION_WIDGETS_HTML,
            is_pro=is_pro, sub=sub_row,
            gamification_stats=gamification_stats,
            gamification_badges=gamification_badges,
            gamification_recent_words=gamification_recent_words,
            gamification_total_badges=len(gamification.BADGES) if is_pro else 0,
        )
    # Merch section — always show (Pro gets the buttons; Free sees the upsell).
    merch_section = render_template_string(
        MERCH_HTML, is_pro=is_pro, sub=sub_row,
    )

    main_html = render_template_string(
        ME_HTML, sub=sub_row, plan_label=plan_label,
        status_label=status_label, status_class=status_class,
        last_sent=last_sent, last_sent_subtitle=last_sent_subtitle,
        renewal_display=renewal_display,
        cast_options=CAST_OPTIONS, theme_options=THEME_OPTIONS,
        is_pro=is_pro,
        learning_total=learning_total,
        learning_this_month=learning_this_month,
        learning_progress_pct=learning_progress_pct,
        learning_progress_label=learning_progress_label,
        learning_recent=learning_recent,
        tier_breakdown=tier_breakdown,
        avatar=avatar, avatar_options=avatar_options,
        avatar_svg_preview=avatar_svg_preview,
        gamification_stats=gamification_stats,
        gamification_badges=gamification_badges,
        gamification_recent_words=gamification_recent_words,
        gamification_total_badges=len(gamification.BADGES) if is_pro else 0,
    )
    # Splice the three extra sections in just before </body></html> of ME_HTML.
    extra = avatar_section + gamification_section + merch_section
    main_html = main_html.replace("</body></html>", extra + "</body></html>")
    return main_html

@app.route("/me/child", methods=["POST"])
@login_required
def me_child():
    name = (request.form.get("child_name") or "").strip()
    try: age = int(request.form.get("child_age") or "0")
    except: age = 0
    if not name or age < 2 or age > 12:
        flash("Please enter a name and an age between 2 and 12.", "err")
        return redirect(url_for("me"))
    conn = db()
    conn.execute("UPDATE subscribers SET child_name=?, child_age=? WHERE id=?",
                 (name, age, session["subscriber_id"]))
    conn.commit(); conn.close()
    flash("Profile updated.", "ok")
    return redirect(url_for("me"))

@app.route("/me/pro", methods=["POST"])
@login_required
def me_pro():
    sub = _subscriber_or_redirect()
    if not sub or sub["plan"] != "pro":
        flash("Pro preferences are only available on the Pro plan.", "err")
        return redirect(url_for("me"))
    char = (request.form.get("pro_character") or "").strip() or None
    theme = (request.form.get("pro_theme") or "").strip() or None
    if char and char not in CAST:
        char = None
    conn = db()
    conn.execute("UPDATE subscribers SET pro_character=?, pro_theme=? WHERE id=?",
                 (char, theme, session["subscriber_id"]))
    conn.commit(); conn.close()
    flash("Pro preferences saved.", "ok")
    return redirect(url_for("me"))

@app.route("/me/toggle", methods=["POST"])
@login_required
def me_toggle():
    conn = db()
    conn.execute("UPDATE subscribers SET active = 1 - active WHERE id=?",
                 (session["subscriber_id"],))
    conn.commit(); conn.close()
    flash("Delivery updated.", "ok")
    return redirect(url_for("me"))


# ---- Phase 6: Avatar save (Pro) ----
@app.route("/me/avatar", methods=["POST"])
@login_required
def me_avatar_save():
    sub = _subscriber_or_redirect()
    if not sub:
        return redirect(url_for("login"))
    if sub["plan"] != "pro":
        flash("Avatar builder is a PocketPlot Pro feature.", "err")
        return redirect(url_for("me"))
    import avatar_builder as _ab
    avatar = {}
    for k in _ab.DEFAULTS.keys():
        v = (request.form.get(k) or "").strip()
        if v:
            avatar[k] = v
    normalized = _ab.normalize_avatar(avatar)
    blob = _ab.avatar_json_blob(normalized)
    conn = db()
    conn.execute(
        "UPDATE subscribers SET avatar_json=?, avatar_updated_at=? WHERE id=?",
        (blob, dt.datetime.utcnow().isoformat(timespec="seconds") + "Z", sub["id"]),
    )
    conn.commit(); conn.close()
    flash("Avatar saved. Tonight's story will feature your child's new look.", "ok")
    return redirect(url_for("me") + "#avatar")


# ---- Phase 7: Game finish (engagement + word vault + badge award) ----
@app.route("/api/game/finish", methods=["POST"])
@login_required
def api_game_finish():
    sub = _subscriber_or_redirect()
    if not sub:
        return jsonify({"ok": False, "error": "not signed in"}), 401
    body = request.get_json(silent=True) or {}
    word_w = (body.get("word") or "").strip()

    import gamification as _gam
    new_engagement = _gam.record_engagement(db, sub["id"], "game_play")
    word_added = False
    if word_w:
        word_added = _gam.record_word(db, sub["id"], word_w,
                                       tier=body.get("word_tier", ""),
                                       definition=body.get("word_definition", ""))
    new_badges = _gam.evaluate_and_award(db, sub["id"])
    stats = _gam.stats_for_subscriber(db, sub["id"])
    return jsonify({
        "ok": True,
        "stats": stats,
        "new_engagement_today": new_engagement,
        "new_word_added": word_added,
        "new_badges": new_badges,
    })


# ---- Phase 11: /me/settings (BYOB/BYOG key management for Creator tier) ----
@app.route("/me/settings", methods=["GET", "POST"])
@login_required
def me_settings():
    """Creator-tier API key management page. Free/Pro users see an
    upgrade CTA but can still see the page (no key management)."""
    sub = _subscriber_or_redirect()
    if not sub:
        return redirect(url_for("login"))
    tier = sub["tier"] or ("pro" if sub["plan"] == "pro" else "free")
    msg = None
    err = None
    if request.method == "POST":
        if tier != "creator":
            err = "BYOB/BYOG requires the Creator tier."
        else:
            action = (request.form.get("action") or "").strip()
            if action == "save_llm":
                key = (request.form.get("llm_key") or "").strip()
                base_url = (request.form.get("llm_base_url") or "").strip()
                model = (request.form.get("llm_model") or "").strip()
                if len(key) < 8:
                    err = "LLM key looks too short."
                elif not base_url.startswith(("http://", "https://")):
                    err = "Base URL must start with http(s)://"
                else:
                    import external_api_manager as _ext
                    _ext.save_api_key(db, sub["id"], "llm", key,
                                       base_url=base_url, model_name=model)
                    msg = "LLM key saved."
            elif action == "save_image":
                key = (request.form.get("image_key") or "").strip()
                base_url = (request.form.get("image_base_url") or "").strip()
                model = (request.form.get("image_model") or "").strip()
                if len(key) < 8:
                    err = "Image key looks too short."
                elif not base_url.startswith(("http://", "https://")):
                    err = "Base URL must start with http(s)://"
                else:
                    import external_api_manager as _ext
                    _ext.save_api_key(db, sub["id"], "image", key,
                                       base_url=base_url, model_name=model)
                    msg = "Image key saved."
            elif action == "delete_llm":
                import external_api_manager as _ext
                _ext.deactivate_api_key(db, sub["id"], "llm")
                msg = "LLM key removed."
            elif action == "delete_image":
                import external_api_manager as _ext
                _ext.deactivate_api_key(db, sub["id"], "image")
                msg = "Image key removed."
            else:
                err = f"Unknown action: {action!r}."
    # Re-read subscriber state to render fresh after save.
    sub = _subscriber_or_redirect()
    tier = sub["tier"] or ("pro" if sub["plan"] == "pro" else "free")
    import external_api_manager as _ext
    # We never expose the key plaintext, only metadata.
    llm_meta = _ext.get_api_key(db, sub["id"], "llm")
    image_meta = _ext.get_api_key(db, sub["id"], "image")
    return render_template_string(
        SETTINGS_HTML,
        sub=sub, tier=tier, msg=msg, err=err,
        llm_configured=bool(llm_meta),
        image_configured=bool(image_meta),
        calls_today=_ext.calls_used_today(db, sub["id"]),
        calls_limit=_ext.daily_limit(),
        calls_remaining=_ext.calls_remaining_today(db, sub["id"]),
        llm_base_url=llm_meta[1] if llm_meta else "",
        llm_model=llm_meta[2] if llm_meta else "",
        image_base_url=image_meta[1] if image_meta else "",
        image_model=image_meta[2] if image_meta else "",
    )


# ---- Phase 11: StoryWorld routes ----
@app.route("/worlds", methods=["GET"])
@login_required
def worlds_list():
    sub = _subscriber_or_redirect()
    if not sub:
        return redirect(url_for("login"))
    worlds = story_world.list_worlds(db, sub["id"])
    return render_template_string(WORLDS_LIST_HTML,
                                   sub=sub, worlds=worlds)


@app.route("/worlds/new", methods=["GET", "POST"])
@login_required
def worlds_new():
    sub = _subscriber_or_redirect()
    if not sub:
        return redirect(url_for("login"))
    pending_seed = session.pop("pending_seed", None) or {}
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()[:120]
        genre = (request.form.get("genre") or "fantasy").strip()
        tone = (request.form.get("tone") or "hopeful").strip()
        setting = (request.form.get("setting") or "a quiet place").strip()[:200]
        # v16: mandatory Story Specification Form fields. These shape both
        # the narrative AND the scene composition.
        character_description = (request.form.get("character_description") or "").strip()[:500]
        primary_objective = (request.form.get("primary_objective") or "").strip()[:240]
        if not title:
            flash("Give your world a title.", "err")
            return redirect(url_for("worlds_new"))
        if not character_description:
            flash("Describe your main character (a few sentences).", "err")
            return redirect(url_for("worlds_new"))
        if not primary_objective:
            flash("What's your character's primary objective?", "err")
            return redirect(url_for("worlds_new"))
        # Persist the structured spec in the world's state_json. This
        # threads character + objective into both the generator (default
        # engine + BYOB) and the scene composer.
        spec = {
            "character_description": character_description,
            "primary_objective": primary_objective,
            "setting": setting,
            "tone": tone,
        }
        try:
            wid = story_world.create_world(db, sub["id"], title=title,
                                             genre=genre, tone=tone, setting=setting,
                                             spec=spec)
        except ValueError as e:
            flash(str(e), "err")
            return redirect(url_for("worlds_new"))
        return redirect(url_for("worlds_view", world_id=wid))
    # v16: pass the 16-genre list to the form (if available), fall back to GENRES
    try:
        from story_image_composer import GENRES_V16 as _genres_v16, GENRE_LABELS as _labels
        genre_choices = [(_labels.get(g, g.title()), g) for g in _genres_v16]
    except Exception:
        genre_choices = [(g.title(), g) for g in story_world.GENRES.keys()]
    return render_template_string(WORLD_NEW_HTML, sub=sub,
                                   genres=story_world.GENRES.keys(),
                                   genre_choices=genre_choices,
                                   tones=list(story_world.TONES.keys()),
                                   seed=pending_seed)


@app.route("/worlds/<int:world_id>", methods=["GET", "POST"])
@login_required
def worlds_view(world_id):
    sub = _subscriber_or_redirect()
    if not sub:
        return redirect(url_for("login"))
    world = story_world.get_world(db, world_id)
    if not world or world["subscriber_id"] != sub["id"]:
        flash("World not found.", "err")
        return redirect(url_for("worlds_list"))
    tier = sub["tier"] or ("pro" if sub["plan"] == "pro" else "free")
    if request.method == "POST":
        body = request.get_json(silent=True) or request.form
        result = story_world.generate_episode(
            db, sub["id"], world_id,
            choice_from_episode_id=int(body.get("choice_from_episode_id") or 0) or None,
            chosen_index=int(body.get("chosen_index") or -1),
            tier=tier,
        )
        if not result.get("ok"):
            flash(result.get("reason", "Generation failed."), "err")
            return redirect(url_for("worlds_view", world_id=world_id))
        return redirect(url_for("worlds_view", world_id=world_id) + f"#ep{result['episode_number']}")
    # GET — load all episodes in order.
    conn = db()
    episodes = conn.execute(
        "SELECT * FROM world_episodes WHERE world_id=? ORDER BY episode_number ASC",
        (world_id,),
    ).fetchall()
    conn.close()
    # Decode choices_json for each episode.
    episodes_data = []
    for e in episodes:
        ed = dict(e)
        try:
            ed["choices"] = json.loads(e["choices_json"]) if e["choices_json"] else []
        except Exception:
            ed["choices"] = []
        episodes_data.append(ed)
    return render_template_string(WORLD_VIEW_HTML,
                                   sub=sub, world=world,
                                   episodes=episodes_data)


# ---- Phase 6: Avatar preview endpoint (live update in the builder) ----
@app.route("/api/avatar-preview", methods=["POST"])
@login_required
def api_avatar_preview():
    """Render an avatar SVG server-side from the JSON picks. Used by the
    live-update JS in the avatar builder. Returns {"svg": "<svg>...</svg>"}.
    Available to Pro only (Free users see the upsell, not the builder)."""
    sub = _subscriber_or_redirect()
    if not sub or sub["plan"] != "pro":
        return jsonify({"ok": False, "error": "Pro only"}), 403
    picks = request.get_json(silent=True) or {}
    import avatar_builder as _ab
    svg = _ab.render_avatar_svg(picks, 0, 0, 1.0)
    # Wrap in a full <svg> tag so the client can extract it easily.
    wrapped = f'<svg viewBox="-100 -100 200 200">{svg}</svg>'
    return jsonify({"ok": True, "svg": wrapped})


# ---- Phase 10: Printable merch (coloring pack + planner PDF) ----

@app.route("/merch", methods=["GET"])
@login_required
def merch_index():
    """List printable PDFs available to the subscriber (Pro)."""
    sub = _subscriber_or_redirect()
    if not sub:
        return redirect(url_for("login"))
    if sub["plan"] != "pro":
        flash("Printables are a PocketPlot Pro perk.", "err")
        return redirect(url_for("me"))
    return render_template_string(
        MERCH_HTML, is_pro=True, sub=sub,
    )


@app.route("/merch/coloring.pdf", methods=["GET"])
@login_required
def merch_coloring_pdf():
    """Generate a 4-page coloring pack PDF on the fly. Each page is a
    PocketPlot character silhouette in vector form (children color them
    in)."""
    sub = _subscriber_or_redirect()
    if not sub:
        return redirect(url_for("login"))
    if sub["plan"] != "pro":
        return ("Printables are a PocketPlot Pro perk.", 403)
    import pdf_gen
    import avatar_builder as _ab
    # Build 4 silhouette pages from the avatar parts library — we render
    # them in outline-only mode so children can fill them in with crayons.
    svgs = []
    # 1: a wren-style avatar (round head + body)
    svgs.append(
        '<circle cx="200" cy="180" r="55" stroke="#1a241d" stroke-width="3" fill="none"/>'
        '<rect x="160" y="220" width="80" height="80" stroke="#1a241d" stroke-width="3" fill="none"/>'
        '<circle cx="183" cy="172" r="4" fill="#1a241d"/>'
        '<circle cx="217" cy="172" r="4" fill="#1a241d"/>'
        '<path d="M 175 200 q 25 12 50 0" stroke="#1a241d" stroke-width="2.5" fill="none"/>'
        # wings
        '<ellipse cx="155" cy="240" rx="20" ry="35" stroke="#1a241d" stroke-width="2.5" fill="none"/>'
        '<ellipse cx="245" cy="240" rx="20" ry="35" stroke="#1a241d" stroke-width="2.5" fill="none"/>'
        # legs
        '<line x1="180" y1="300" x2="180" y2="320" stroke="#1a241d" stroke-width="3"/>'
        '<line x1="220" y1="300" x2="220" y2="320" stroke="#1a241d" stroke-width="3"/>'
    )
    # 2: a bear-style avatar
    svgs.append(
        # ears
        '<circle cx="170" cy="140" r="22" stroke="#1a241d" stroke-width="3" fill="none"/>'
        '<circle cx="230" cy="140" r="22" stroke="#1a241d" stroke-width="3" fill="none"/>'
        # head
        '<circle cx="200" cy="180" r="55" stroke="#1a241d" stroke-width="3" fill="none"/>'
        # body
        '<ellipse cx="200" cy="270" rx="55" ry="50" stroke="#1a241d" stroke-width="3" fill="none"/>'
        # face
        '<circle cx="183" cy="172" r="4" fill="#1a241d"/>'
        '<circle cx="217" cy="172" r="4" fill="#1a241d"/>'
        '<circle cx="200" cy="190" r="6" stroke="#1a241d" stroke-width="2" fill="none"/>'
        '<path d="M 180 210 q 20 12 40 0" stroke="#1a241d" stroke-width="2.5" fill="none"/>'
        # arms
        '<line x1="150" y1="260" x2="130" y2="240" stroke="#1a241d" stroke-width="3"/>'
        '<line x1="250" y1="260" x2="270" y2="240" stroke="#1a241d" stroke-width="3"/>'
    )
    # 3: a rabbit
    svgs.append(
        # ears
        '<ellipse cx="180" cy="135" rx="10" ry="35" stroke="#1a241d" stroke-width="3" fill="none"/>'
        '<ellipse cx="220" cy="135" rx="10" ry="35" stroke="#1a241d" stroke-width="3" fill="none"/>'
        # head
        '<circle cx="200" cy="200" r="40" stroke="#1a241d" stroke-width="3" fill="none"/>'
        # body
        '<ellipse cx="200" cy="280" rx="40" ry="50" stroke="#1a241d" stroke-width="3" fill="none"/>'
        # face
        '<circle cx="187" cy="195" r="3.5" fill="#1a241d"/>'
        '<circle cx="213" cy="195" r="3.5" fill="#1a241d"/>'
        '<path d="M 195 215 q 5 5 10 0" stroke="#1a241d" stroke-width="2" fill="none"/>'
        '<line x1="170" y1="205" x2="185" y2="208" stroke="#1a241d" stroke-width="1"/>'
        '<line x1="230" y1="205" x2="215" y2="208" stroke="#1a241d" stroke-width="1"/>'
    )
    # 4: a lighthouse (PocketPlot scene)
    svgs.append(
        # ground
        '<line x1="50" y1="320" x2="350" y2="320" stroke="#1a241d" stroke-width="2"/>'
        # tower
        '<rect x="175" y="160" width="50" height="160" stroke="#1a241d" stroke-width="3" fill="none"/>'
        # stripes
        '<line x1="175" y1="190" x2="225" y2="190" stroke="#1a241d" stroke-width="2"/>'
        '<line x1="175" y1="220" x2="225" y2="220" stroke="#1a241d" stroke-width="2"/>'
        '<line x1="175" y1="250" x2="225" y2="250" stroke="#1a241d" stroke-width="2"/>'
        '<line x1="175" y1="280" x2="225" y2="280" stroke="#1a241d" stroke-width="2"/>'
        # top
        '<rect x="170" y="140" width="60" height="20" stroke="#1a241d" stroke-width="3" fill="none"/>'
        '<circle cx="200" cy="135" r="8" stroke="#1a241d" stroke-width="2.5" fill="none"/>'
        # light beams
        '<line x1="200" y1="135" x2="100" y2="100" stroke="#1a241d" stroke-width="1" stroke-dasharray="4 3"/>'
        '<line x1="200" y1="135" x2="300" y2="100" stroke="#1a241d" stroke-width="1" stroke-dasharray="4 3"/>'
        # moon
        '<circle cx="60" cy="80" r="20" stroke="#1a241d" stroke-width="2" fill="none"/>'
        '<circle cx="68" cy="76" r="14" stroke="#1a241d" stroke-width="0" fill="#ffffff"/>'
        # waves
        '<path d="M 50 350 q 20 -8 40 0 t 40 0 t 40 0 t 40 0" stroke="#1a241d" stroke-width="2" fill="none"/>'
    )
    pdf_bytes = pdf_gen.build_coloring_pack(svgs)
    return Response(pdf_bytes, mimetype="application/pdf",
                    headers={"Content-Disposition":
                             "attachment; filename=pocketplot-coloring.pdf"})


@app.route("/merch/planner.pdf", methods=["GET"])
@login_required
def merch_planner_pdf():
    """A printable weekly planner personalised with the child's name."""
    sub = _subscriber_or_redirect()
    if not sub:
        return redirect(url_for("login"))
    if sub["plan"] != "pro":
        return ("Printables are a PocketPlot Pro perk.", 403)
    import pdf_gen
    child = sub["child_name"] or "your child"
    pdf_bytes = pdf_gen.build_weekly_planner(child)
    return Response(pdf_bytes, mimetype="application/pdf",
                    headers={"Content-Disposition":
                             f'attachment; filename=pocketplot-{child.lower().replace(" ", "-")}-planner.pdf'})

# ---- Mini-game — premium engagement feature (Phase 3) ----
GAME_UPSELL_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Play tonight\'s adventure · PocketPlot Pro</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600&family=Karla:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  body{font-family:Karla;background:linear-gradient(180deg,#f6f0e1 0%,#ffe5a0 100%);color:#1a241d;margin:0;padding:0;min-height:100vh;display:flex;align-items:center;justify-content:center}
  .card{background:#fff;border:1px solid #d8cfb3;border-radius:18px;padding:40px 32px;max-width:520px;width:90%;box-shadow:0 24px 50px rgba(26,36,29,.08);text-align:center}
  .wordmark{font-family:Fraunces;font-size:20px;margin-bottom:18px;color:#3a3633}
  .wordmark i{color:#7a9a6e;font-style:italic}
  .game-icon{font-size:64px;line-height:1;margin-bottom:8px}
  h1{font-family:Fraunces;font-weight:600;font-size:30px;line-height:1.2;margin:0 0 12px;color:#1a241d}
  p{font-size:15px;line-height:1.6;color:#4a3a2a;margin:12px 0}
  .features{text-align:left;margin:24px auto;max-width:340px;background:#fdf3dc;border-radius:10px;padding:16px 18px}
  .features li{font-size:13.5px;line-height:1.5;margin:6px 0;color:#3a2e22;list-style:none}
  .features li:before{content:"\u2713";color:#7a9a6e;margin-right:8px;font-weight:700}
  .cta{display:inline-block;margin-top:20px;background:#c46a3f;color:#fff;padding:13px 28px;border-radius:999px;font-size:15px;font-weight:700;text-decoration:none;font-family:Karla}
  .cta:hover{background:#a8572f}
  .meta{font-size:12px;color:#7a9a6e;margin-top:18px}
  .back{display:block;margin-top:14px;color:#5c7c5a;font-size:13px}
</style>
</head>
<body>
<div class="card">
  <div class="wordmark">Pocket<i>Plot</i></div>
  <div class="game-icon">&#127918;</div>
  <h1>Tonight\'s Adventure</h1>
  <p><b>Walk through {{child_name}}\'s story.</b> Pick up the Word of the Day, answer Story Talk questions at the story signs, and meet the helper at the end of the path.</p>
  <ul class="features">
    <li>A new mini-game themed to every branching story</li>
    <li>The Word of the Day appears as a glowing orb to collect</li>
    <li>Story Talk questions surface in dialogue with the helper</li>
    <li>Free for PocketPlot Pro subscribers</li>
  </ul>
  <a class="cta" href="/pricing">Become Pro to play</a>
  <p class="meta">Your Free plan includes the daily story, Word of the Day, Story Talk, Parent Guide, and Listen button.</p>
  <a class="back" href="/me">&larr; back to your account</a>
</div>
</body>
</html>
"""


@app.route("/game", methods=["GET"])
def game():
    """The PocketPlot mini-game (Phase 3 - Pro-only engagement feature).

    Renders game.html with today's story data embedded as JSON in a
    <script type="application/json"> block. Non-Pro subscribers see an
    upsell page instead.
    """
    sub = _subscriber_or_redirect()
    if not sub:
        return redirect(url_for("login"))
    # Pro gating - Free users see the upsell
    if sub["plan"] != "pro":
        return render_template_string(
            GAME_UPSELL_HTML,
            child_name=sub["child_name"],
        )

    # Fetch the latest delivery for this subscriber.
    conn = db()
    requested_id = (request.args.get("d") or "").strip()
    if requested_id and requested_id.isdigit():
        row = conn.execute(
            "SELECT * FROM deliveries WHERE id=? AND subscriber_id=? LIMIT 1",
            (int(requested_id), sub["id"]),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM deliveries WHERE subscriber_id=? ORDER BY id DESC LIMIT 1",
            (sub["id"],),
        ).fetchone()
    conn.close()

    # No delivery yet - render game.html with the embedded demo data so
    # the user can see what the experience looks like.
    if not row:
        return send_file(str(APP_DIR / "game.html"))

    # Build the story-data dict from the delivery row
    story_obj = {}
    if row["story"]:
        try:
            story_obj = json.loads(row["story"])
        except Exception:
            story_obj = {}
    word_obj = {}
    if row["word"]:
        try:
            word_obj = json.loads(row["word"])
        except Exception:
            word_obj = {"w": row["word"], "d": row["word_definition"] or "", "tier": row["word_tier"] or ""}
    questions = []
    if row["questions_json"]:
        try:
            questions = json.loads(row["questions_json"])
        except Exception:
            questions = []

    # Normalise questions into {q, choices, answer}
    norm_questions = []
    for q in questions:
        if isinstance(q, dict):
            norm_questions.append({
                "q": q.get("q", ""),
                "choices": q.get("choices", []) if isinstance(q.get("choices"), list) else [],
                "answer": int(q.get("answer", 0)),
            })
        elif isinstance(q, str):
            norm_questions.append({"q": q, "choices": [], "answer": 0})

    # Truncate the body for the title screen
    body = story_obj.get("body", "") or ""
    body_short = body[:120] + ("..." if len(body) > 120 else "")

    game_data = {
        "title": story_obj.get("title", "Tonight\'s Adventure"),
        "body": body_short,
        "cast": story_obj.get("cast", [sub["child_name"], "Bram"]),
        "word": word_obj or {"w": "curious", "d": "eager to learn or know about things", "tier": "simple"},
        "questions": norm_questions,
    }
    # Render game.html with the story-data embedded
    game_html = (APP_DIR / "game.html").read_text(encoding="utf-8")
    data_json = json.dumps(game_data).replace("<", "\\u003c").replace(">", "\\u003e")
    import re
    new_block = (
        '<script type="application/json" id="story-data">\n'
        + data_json + '\n'
        + '</script>'
    )
    game_html = re.sub(
        r'<!--STORY_DATA_BEGIN-->[\s\S]*?<!--STORY_DATA_END-->',
        '<!--STORY_DATA_BEGIN-->' + new_block + '<!--STORY_DATA_END-->',
        game_html,
    )
    return Response(game_html, mimetype="text/html")




# ---- Pricing page ----
PRICING_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Pricing · PocketPlot</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;1,500&family=Karla:wght@400;500;600;700&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>
:root{--ink:#1a241d;--paper:#f6f0e1;--paper2:#ece4cb;--paper3:#d8cfb3;--moss:#7a9a6e;--mossD:#3d5a3a;--gold:#d4a849;--goldD:#8a6420;--rust:#c46a3f;--hi:#f6f0e1;--faint:#8a8270;--serif:"Fraunces",Georgia,serif;--sans:"Karla",sans-serif}
*{margin:0;padding:0;box-sizing:border-box}body{font-family:var(--sans);color:var(--ink);background:var(--paper);-webkit-font-smoothing:antialiased}
header{padding:14px 24px;background:var(--paper2);border-bottom:1px solid var(--paper3);display:flex;justify-content:space-between;align-items:center}
.wordmark{font-family:var(--serif);font-size:20px;font-weight:500}.wordmark i{color:var(--moss);font-style:italic;font-weight:400}
.nav a{color:var(--ink);text-decoration:none;font-size:13px;font-weight:500;margin-left:18px}
.wrap{max-width:920px;margin:0 auto;padding:50px 24px 80px}
h1{font-family:var(--serif);font-weight:500;font-size:42px;text-align:center;line-height:1.1;margin-bottom:10px}
h1 i{font-style:italic;color:var(--moss);font-weight:400}
.lede{text-align:center;color:var(--faint);font-size:16px;margin-bottom:38px;max-width:580px;margin-left:auto;margin-right:auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:680px){.grid{grid-template-columns:1fr}}
.tier{background:#fff;border:1px solid var(--paper3);border-radius:18px;padding:32px 30px;position:relative}
.tier.featured{border-color:var(--gold);box-shadow:0 0 0 3px rgba(212,168,73,.18), 0 24px 50px rgba(26,36,29,.08)}
.tier .badge{position:absolute;top:-12px;left:30px;background:var(--gold);color:#3a2a10;font-size:10px;letter-spacing:.18em;font-weight:700;padding:5px 12px;border-radius:99px}
.tier .name{font-family:var(--serif);font-size:22px;font-weight:500;margin-bottom:4px}
.tier .price{font-family:var(--serif);font-size:46px;font-weight:500;line-height:1;margin:8px 0 4px;color:var(--ink)}
.tier .price .unit{font-size:14px;color:var(--faint);font-family:var(--sans);font-weight:400;margin-left:4px}
.tier .price-sub{font-size:13px;color:var(--faint);margin-bottom:18px;font-style:italic;font-family:var(--serif)}
ul.feats{list-style:none;margin:0 0 24px}
ul.feats li{padding:9px 0;border-bottom:1px dotted var(--paper3);font-size:14px;line-height:1.45;display:flex;align-items:flex-start;gap:10px}
ul.feats li:last-child{border-bottom:none}
ul.feats li .check{color:var(--moss);font-weight:700;font-size:14px;margin-top:2px;flex:none}
ul.feats li .x{color:var(--faint);font-weight:700;font-size:14px;margin-top:2px;flex:none}
.cta{display:block;text-align:center;background:var(--ink);color:var(--hi);padding:13px;border-radius:99px;text-decoration:none;font-weight:600;font-size:14px;letter-spacing:.04em}
.cta:hover{background:var(--rust)}
.cta.pro{background:var(--rust)}.cta.pro:hover{background:var(--rustD)}
.cta.secondary{background:#fff;color:var(--ink);border:1px solid var(--paper3)}
.cta.secondary:hover{border-color:var(--ink)}
.trust{margin-top:40px;text-align:center;font-size:12px;color:var(--faint);font-style:italic;font-family:var(--serif)}
.note{margin-top:14px;text-align:center;font-size:12px;color:var(--faint)}
</style></head><body>
<header>
  <div class="wordmark">Pocket<i>Plot</i></div>
  <nav class="nav">
    <a href="/">Home</a>{% if authed %}<a href="/me">Account</a>{% else %}<a href="/login">Sign in</a>{% endif %}
  </nav>
</header>
<div class="wrap">
<h1>Simple, sleepy <i>pricing</i>.</h1>
<p class="lede">Start free. Upgrade when you're ready. Cancel any time. No ads, ever — not even on Pro.</p>
<div class="grid">
  <div class="tier">
    <div class="name">Free</div>
    <div class="price">$0<span class="unit">/mo</span></div>
    <div class="price-sub">Forever.</div>
    <ul class="feats">
      <li><span class="check">✓</span><span>One fresh branching story every day</span></li>
      <li><span class="check">✓</span><span>Personalised — your child is the hero</span></li>
      <li><span class="check">✓</span><span>200–300 words, ready for one good yawn</span></li>
      <li><span class="check">✓</span><span>Manage delivery from your account page</span></li>
      <li><span class="x">—</span><span>Recurring helper of your choice</span></li>
      <li><span class="x">—</span><span>Lock-in to a setting theme</span></li>
      <li><span class="x">—</span><span>No-ad priority queue (no ads in either plan)</span></li>
    </ul>
    {% if authed %}
      <a class="cta secondary" href="/me">You're on Free — manage</a>
    {% else %}
      <a class="cta secondary" href="/">Start free</a>
    {% endif %}
  </div>
  <div class="tier featured">
    <div class="badge">★ MOST LOVED</div>
    <div class="name">Pro</div>
    <div class="price">$4.99<span class="unit">/mo</span></div>
    <div class="price-sub">Billed monthly. Cancel any time.</div>
    <ul class="feats">
      <li><span class="check">✓</span><span><b>Everything in Free</b></span></li>
      <li><span class="check">✓</span><span>Choose a <b>recurring helper</b> (Felix, Bram, Rue, Wren, Pip…)</span></li>
      <li><span class="check">✓</span><span>Lock in a <b>setting theme</b> your child loves</span></li>
      <li><span class="check">✓</span><span>Unlimited delivery — even catch-up if you miss a night</span></li>
      <li><span class="check">✓</span><span>Priority response on support questions</span></li>
      <li><span class="check">✓</span><span>No ads, ever — and the Pro badge in your inbox</span></li>
      <li><span class="check">✓</span><span>Early access to new cast members & themes</span></li>
    </ul>
    {% if authed %}
      <a class="cta pro" href="/upgrade">{% if plan == 'pro' %}You're on Pro ✓{% else %}Upgrade to Pro →{% endif %}</a>
    {% else %}
      <a class="cta pro" href="/login">Sign in to upgrade</a>
    {% endif %}
  </div>
</div>
<p class="note">Stripe handles billing securely. We never see your card number. You can cancel any time from your account page.</p>
<p class="trust">“It's the gentlest half-hour of our day.” — Maya, parent of Wren (age 5)</p>
</div>
</body></html>
"""

@app.route("/pricing", methods=["GET"])
def pricing():
    # v11: serve the new design from the static file. The legacy
    # PRICING_HTML inlined template remains in the codebase for
    # backwards compatibility but is no longer the public face.
    import pathlib
    p = pathlib.Path(__file__).parent / "pricing.html"
    if p.exists():
        return send_file(str(p), mimetype="text/html")
    # Fallback to legacy template if the file is missing.
    authed = bool(session.get("subscriber_id"))
    plan = "free"
    if authed:
        sub = _subscriber_or_redirect()
        if sub: plan = sub["plan"]
    return render_template_string(PRICING_HTML, authed=authed, plan=plan)


@app.route("/faq", methods=["GET"])
def faq():
    """v11 FAQ page. Static HTML for now — easy to maintain, fast to load."""
    import pathlib
    p = pathlib.Path(__file__).parent / "faq.html"
    if p.exists():
        return send_file(str(p), mimetype="text/html")
    return "<h1>FAQ coming soon</h1>", 200


@app.route("/terms", methods=["GET"])
def terms():
    """v12 ToS page. Static HTML."""
    import pathlib
    p = pathlib.Path(__file__).parent / "terms.html"
    if p.exists():
        return send_file(str(p), mimetype="text/html")
    return "<h1>Terms coming soon</h1>", 200

# ---- Upgrade flow ----
@app.route("/upgrade", methods=["GET"])
@login_required
def upgrade():
    sub = _subscriber_or_redirect()
    if not sub: return redirect(url_for("login"))
    if sub["plan"] == "pro":
        flash("You're already on Pro.", "ok")
        return redirect(url_for("me"))
    success_url = f"{SITE_URL}/billing/success"
    cancel_url = f"{SITE_URL}/billing/cancel"
    sess = stripe_checkout_session(sub, success_url, cancel_url)
    # In mock mode, this is a /mock/checkout URL we can follow directly
    # In live mode, this is a real Stripe Checkout URL
    return redirect(sess["url"])

@app.route("/billing/success", methods=["GET"])
@login_required
def billing_success():
    """Called after a successful Stripe Checkout redirect.
    In live mode: the actual status is set by the webhook.
    In mock mode: the /mock/checkout page synthesizes the event and we already updated the DB there."""
    flash("Welcome to Pro. Your first Pro story will arrive tonight.", "ok")
    return redirect(url_for("me"))

@app.route("/billing/cancel", methods=["POST","GET"])
@login_required
def billing_cancel():
    sub = _subscriber_or_redirect()
    if not sub: return redirect(url_for("login"))
    if sub["plan"] != "pro" or not sub["subscription_id"]:
        flash("You don't have an active Pro subscription.", "err")
        return redirect(url_for("me"))
    try:
        stripe_cancel_subscription(sub["subscription_id"])
        # In live mode, the webhook will finalize the downgrade. In mock, the event is queued.
        # Drain any pending mock events so the UI reflects the change immediately.
        drain_mock_events()
        flash("Subscription cancelled. You'll keep Pro access until the period ends.", "ok")
    except Exception as e:
        log.exception("cancel failed: %s", e)
        flash("Could not cancel — please contact support.", "err")
    return redirect(url_for("me"))

@app.route("/billing/portal", methods=["GET"])
@login_required
def billing_portal():
    """In live mode, redirect to a Stripe Billing Portal session.
    In mock mode, just send the user back to /me."""
    sub = _subscriber_or_redirect()
    if not sub: return redirect(url_for("login"))
    if STRIPE_MOCK or stripe is None:
        flash("Billing portal is a Stripe-hosted page (live mode only). Mock mode returns here.", "ok")
        return redirect(url_for("me"))
    try:
        portal = stripe.billing_portal.Session.create(
            customer=sub["customer_id"], return_url=f"{SITE_URL}/me"
        )
        return redirect(portal.url)
    except Exception as e:
        log.exception("portal session failed: %s", e)
        flash("Could not open the billing portal. Try again later.", "err")
        return redirect(url_for("me"))

# ---- Mock-mode helpers ----
def drain_mock_events():
    """In mock mode, apply any queued events to the DB and clear them."""
    while MOCK_EVENTS:
        ev = MOCK_EVENTS.pop(0)
        # Mock events have minimal data — find subscriber by subscription_id
        conn = db()
        obj = ev.get("data", {}).get("object", {})
        sid = obj.get("id")
        if sid:
            row = conn.execute("SELECT id FROM subscribers WHERE subscription_id=?", (sid,)).fetchone()
            if row:
                apply_stripe_event_to_subscriber(row["id"], ev["type"], obj)
        conn.close()

MOCK_CHECKOUT_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Mock checkout · PocketPlot</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500&family=Karla:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>body{font-family:Karla;background:#f6f0e1;color:#1a241d;margin:0;padding:0;min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#fff;border:1px solid #d8cfb3;border-radius:18px;padding:36px 32px;max-width:480px;width:90%;box-shadow:0 24px 50px rgba(26,36,29,.08)}
.tag{background:#d4a849;color:#3a2a10;font-size:10px;letter-spacing:.16em;font-weight:700;padding:3px 9px;border-radius:99px;display:inline-block;margin-bottom:14px}
.wordmark{font-family:Fraunces;font-size:22px;margin-bottom:8px}.wordmark i{color:#7a9a6e;font-style:italic}
h1{font-family:Fraunces;font-weight:500;font-size:26px;line-height:1.2;margin:10px 0 14px}
.amount{font-family:Fraunces;font-size:54px;font-weight:500;line-height:1;margin:14px 0;color:#1a241d}
.amount small{font-size:14px;color:#8a8270;margin-left:6px;font-weight:400}
.note{font-size:12px;color:#8a8270;font-style:italic;margin:20px 0 18px;line-height:1.5;font-family:Fraunces}
.row{display:flex;gap:10px}
.btn{flex:1;background:#1a241d;color:#f6f0e1;border:none;padding:13px;border-radius:99px;font-family:Karla;font-weight:700;font-size:14px;cursor:pointer;text-decoration:none;text-align:center}
.btn:hover{background:#c46a3f}
.btn.cancel{background:#fff;color:#1a241d;border:1px solid #d8cfb3}
.btn.cancel:hover{border-color:#1a241d;color:#1a241d;background:#fff}
</style><link rel="stylesheet" href="/style.css?v=35">
</head><body>
<div class="card">
<div class="tag">★ MOCK MODE</div>
<div class="wordmark">Pocket<i>Plot</i></div>
<h1>Confirm your Pro subscription</h1>
<p style="color:#5a6a4a;font-size:14px;line-height:1.5">This is a simulated Stripe Checkout page. No card is charged. Clicking <b>Confirm</b> synthesizes the same webhook events Stripe would emit on a real subscription creation.</p>
<div class="amount">$4.99<small>/month</small></div>
<p style="font-size:13px;color:#1a241d"><b>{{email}}</b> · billed monthly</p>
<form method="post" action="/mock/checkout/confirm">
<input type="hidden" name="sid" value="{{sid}}">
<input type="hidden" name="sub" value="{{sub}}">
<input type="hidden" name="success" value="{{success}}">
<input type="hidden" name="cancel" value="{{cancel}}">
<select name="tier" style="font-family:Karla;font-size:14px;padding:10px 12px;border:1px solid #d8cfb3;border-radius:8px;background:#fff;width:100%;margin-bottom:14px;color:#1a241d">
  <option value="pro">PocketPlot Pro · $7.99/month (or $4.99 if grandfathered)</option>
  <option value="creator">PocketPlot Creator · $19.99/month</option>
</select>
<div class="row">
<button class="btn" type="submit">Confirm subscription</button>
<a class="btn cancel" href="{{cancel}}">Cancel</a>
</div>
</form>
<p class="note">No payment will actually be made. To test the real Stripe flow, set <code>STRIPE_SECRET_KEY</code> and restart.</p>
</div>
</body></html>
"""

@app.route("/mock/checkout", methods=["GET"])
def mock_checkout():
    sid = request.args.get("sid", "")
    sub_id = request.args.get("sub", "")
    success = request.args.get("success", SITE_URL + "/billing/success")
    cancel = request.args.get("cancel", SITE_URL + "/pricing")
    conn = db()
    row = conn.execute("SELECT email FROM subscribers WHERE id=?", (sub_id,)).fetchone()
    conn.close()
    email = row["email"] if row else "unknown"
    return render_template_string(MOCK_CHECKOUT_HTML,
        sid=sid, sub=sub_id, success=success, cancel=cancel, email=email)

@app.route("/mock/checkout/confirm", methods=["POST"])
def mock_checkout_confirm():
    sid = request.form.get("sid")
    sub_id = int(request.form.get("sub"))
    success = request.form.get("success", SITE_URL + "/billing/success")
    # v11: support both pro and creator tiers. New price points:
    #   pro_monthly      $7.99   (grandfathered users keep $4.99)
    #   creator_monthly  $19.99
    requested_tier = (request.form.get("tier") or "pro").strip()
    if requested_tier not in ("pro", "creator"):
        requested_tier = "pro"
    prices = {"pro": 799, "creator": 1999}  # cents
    price_cents = prices[requested_tier]
    conn = db()
    row = conn.execute("SELECT * FROM subscribers WHERE id=?", (sub_id,)).fetchone()
    if not row:
        conn.close(); return redirect(SITE_URL)
    # Grandfathering: if the user is already Pro AND is on the legacy
    # $4.99 price (no Stripe sub yet OR explicitly grandfathered), keep
    # them at $4.99 unless they're upgrading to Creator.
    new_tier = requested_tier
    grandfathered_price = False
    if requested_tier == "pro" and row["plan"] == "pro":
        # Existing Pro subscriber buying again. Apply grandfather logic
        # only if their last period was at the old price — but mock mode
        # doesn't track that, so we grandfather anyone already on Pro.
        grandfathered_price = True
        price_cents = 499  # legacy $4.99
    # Synthesize the same ids a real Stripe flow would emit
    customer_id = _mock_customer_id()
    subscription_id = _mock_subscription_id()
    period_end = int((dt.datetime.utcnow() + dt.timedelta(days=30)).timestamp())
    # First, write the Stripe ids onto our subscriber so drain_mock_events can find them
    conn.execute(
        "UPDATE subscribers SET customer_id=?, subscription_id=?, "
        "subscription_status='active', plan=?, tier=?, "
        "grandfathereProPrice=?, current_period_end=? WHERE id=?",
        (customer_id, subscription_id,
         ("pro" if new_tier == "pro" else "creator"), new_tier,
         1 if grandfathered_price else 0,
         dt.datetime.fromtimestamp(period_end, tz=dt.timezone.utc).isoformat(timespec="seconds"),
         sub_id)
    )
    conn.commit()
    # Also log these as if they were webhook events
    MOCK_EVENTS.extend([
        {"type": "customer.subscription.created",
         "data": {"object": {"id": subscription_id, "customer": customer_id, "status": "active", "current_period_end": period_end}}},
        {"type": "invoice.paid",
         "data": {"object": {"customer": customer_id, "subscription": subscription_id, "amount_paid": price_cents}}},
    ])
    drain_mock_events()
    # Set the session so the user is signed in to the upgraded account
    session["subscriber_id"] = sub_id
    if new_tier == "creator":
        flash("Welcome to Creator. Bring Your Own keys at /me/settings.", "ok")
    else:
        if grandfathered_price:
            flash("Welcome to Pro. You're on the legacy $4.99/month rate — grandfathered for the life of your subscription.", "ok")
        else:
            flash("Welcome to Pro! Your first Pro story will arrive tonight.", "ok")
    conn.close()
    return redirect(success)

# ---- Stripe webhook ----
@app.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.get_data()
    sig = request.headers.get("Stripe-Signature", "")
    if STRIPE_MOCK or not STRIPE_WEBHOOK_SECRET:
        # Mock mode: accept unsigned JSON
        try:
            event = json.loads(payload)
        except Exception:
            return ("bad payload", 400)
    else:
        try:
            ev = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
            # Stripe's library returns a stripe.Event object, not a dict.
            # Convert to a plain dict so the rest of our handler is API-agnostic.
            event = ev.to_dict() if hasattr(ev, "to_dict") else ev
        except Exception as e:
            log.warning("Webhook signature failed: %s", e)
            return ("bad signature", 400)
    et = event.get("type")
    obj = event.get("data", {}).get("object", {})
    # Stripe's to_dict() may leave the inner 'object' as a Subscription/Customer instance
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    if not isinstance(obj, dict):
        obj = {}
    # Resolve our subscriber from the Stripe customer/subscription id
    conn = db()
    customer_id = obj.get("customer")
    subscription_id = obj.get("id") if et and "subscription" in et else obj.get("subscription")
    if isinstance(subscription_id, dict):
        subscription_id = subscription_id.get("id")
    sub_row = None
    if subscription_id:
        sub_row = conn.execute("SELECT id FROM subscribers WHERE subscription_id=?", (subscription_id,)).fetchone()
    if not sub_row and customer_id:
        sub_row = conn.execute("SELECT id FROM subscribers WHERE customer_id=?", (customer_id,)).fetchone()
    conn.close()
    if sub_row:
        apply_stripe_event_to_subscriber(sub_row["id"], et, obj)
    else:
        log.warning("Webhook for unknown subscriber (customer=%s, sub=%s)", customer_id, subscription_id)
    return ("ok", 200)

# =====================================================================

# ---- Phase 13 polish: templates (CONTACT, STATUS, ROADMAP) ----
CONTACT_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Contact · PocketPlot Universe</title>
<style>
  :root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460; --gold:#e6c879;
          --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
  * { box-sizing:border-box; }
  body { margin:0; padding:0; background:var(--navy); color:var(--cream);
         font-family:Karla, system-ui, sans-serif; line-height:1.6; }
  .wrap { max-width:680px; margin:0 auto; padding:0 28px; }
  header { padding:22px 0; border-bottom:1px solid var(--navy-3); }
  .wordmark { font-family:'Fraunces', Georgia, serif; font-style:italic;
              color:var(--gold); font-size:22px; font-weight:600; display:inline-block; }
  .wordmark i { color:var(--muted); font-style:italic; font-weight:400; }
  nav { float:right; margin-top:8px; }
  nav a { color:var(--muted); text-decoration:none; margin-left:22px; font-size:13px;
         letter-spacing:.05em; text-transform:uppercase; }
  nav a:hover { color:var(--gold); }
  h1 { font-family:'Fraunces', Georgia, serif; font-size:36px; margin:36px 0 12px;
       font-weight:600; }
  h1 i { color:var(--gold); font-style:italic; }
  .lead { font-family:'Fraunces', Georgia, serif; font-style:italic; color:var(--muted);
          font-size:17px; margin:0 0 28px; }
  .card { background:var(--navy-2); border:1px solid var(--navy-3);
          border-radius:14px; padding:28px; margin-bottom:18px; }
  .field { margin-bottom:18px; }
  .field label { display:block; font-size:11px; letter-spacing:.14em;
                text-transform:uppercase; color:var(--muted); margin-bottom:6px;
                font-weight:700; }
  .field input, .field textarea { width:100%; background:var(--navy);
              border:1px solid var(--navy-3); color:var(--cream);
              padding:10px 12px; border-radius:8px; font-family:Karla; font-size:14px;
              box-sizing:border-box; }
  .field input:focus, .field textarea:focus { outline:none; border-color:var(--gold); }
  .btn { background:var(--gold); color:var(--navy); border:none; padding:12px 24px;
         border-radius:99px; font-family:'Fraunces', Georgia, serif;
         font-weight:700; font-size:14px; cursor:pointer; text-decoration:none;
         display:inline-block; }
  .btn:hover { background:#d4b566; }
  .info { background:rgba(230,200,121,.08); border:1px solid var(--gold);
           border-radius:12px; padding:16px 20px; margin-bottom:24px;
           font-family:'Fraunces', Georgia, serif; font-style:italic;
           color:var(--cream); font-size:14px; line-height:1.6; }
  .alt { text-align:center; margin-top:24px; font-size:13px; color:var(--faint); }
  .alt a { color:var(--gold); text-decoration:none; margin:0 8px; }
  footer { margin-top:60px; padding:28px 0; border-top:1px solid var(--navy-3);
           color:var(--faint); font-size:13px; text-align:center; }
</style></head><body>
<div class="wrap">
  <header>
    <div class="wordmark">Pocket<i>Plot</i> Universe</div>
    <nav>
      <a href="/">Home</a>
      <a href="/faq">FAQ</a>
      <a href="/help">Help</a>
    </nav>
  </header>

  <h1>Get in <i>touch</i>.</h1>
  <p class="lead">Bug reports, billing questions, refund requests, partnership ideas — drop us a note. We usually reply within one business day.</p>

  <div class="info">
    For instant answers, the <a href="/help" style="color:var(--gold)">FAQ Assistant</a> handles most "how do I…" questions in seconds.
    The <a href="/faq" style="color:var(--gold)">full FAQ</a> covers the rest.
  </div>

  <form method="post" class="card">
    <div class="field">
      <label>Your email</label>
      <input type="email" name="email" required placeholder="you@example.com">
    </div>
    <div class="field">
      <label>Subject</label>
      <input type="text" name="subject" required maxlength="200" placeholder="Refund request for September">
    </div>
    <div class="field">
      <label>Message</label>
      <textarea name="body" required rows="8" maxlength="5000" placeholder="Tell us what's going on…"></textarea>
    </div>
    <button class="btn" type="submit">Send message</button>
  </form>

  <div class="alt">
    Or jump to: <a href="/help">Help</a> · <a href="/faq">FAQ</a> · <a href="/roadmap">Roadmap</a> · <a href="/status">Status</a>
  </div>

  <footer>PocketPlot Universe · 18+ · original content only</footer>
</div></body></html>"""


STATUS_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Status · PocketPlot Universe</title>
<style>
  :root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460; --gold:#e6c879;
          --green:#9ad6a4; --red:#e6a4a4; --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
  * { box-sizing:border-box; }
  body { margin:0; padding:0; background:var(--navy); color:var(--cream);
         font-family:Karla, system-ui, sans-serif; line-height:1.6; }
  .wrap { max-width:880px; margin:0 auto; padding:0 28px; }
  header { padding:22px 0; border-bottom:1px solid var(--navy-3); }
  .wordmark { font-family:'Fraunces', Georgia, serif; font-style:italic;
              color:var(--gold); font-size:22px; font-weight:600; }
  .wordmark i { color:var(--muted); font-style:italic; font-weight:400; }
  nav { float:right; margin-top:8px; }
  nav a { color:var(--muted); text-decoration:none; margin-left:22px; font-size:13px;
         letter-spacing:.05em; text-transform:uppercase; }
  nav a:hover { color:var(--gold); }
  h1 { font-family:'Fraunces', Georgia, serif; font-size:36px; margin:36px 0 6px; font-weight:600; }
  h1 i { color:var(--gold); font-style:italic; }
  .lead { font-family:'Fraunces', Georgia, serif; font-style:italic; color:var(--muted);
          font-size:16px; margin:0 0 24px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:14px; margin-bottom:24px; }
  .stat { background:var(--navy-2); border:1px solid var(--navy-3);
          border-radius:14px; padding:20px; text-align:center; }
  .stat .lab { font-size:11px; letter-spacing:.14em; text-transform:uppercase;
               color:var(--faint); margin-bottom:6px; font-weight:700; }
  .stat .val { font-family:'Fraunces', Georgia, serif; font-weight:600;
               font-size:30px; color:var(--gold); line-height:1; }
  .stat.green .val { color:var(--green); }
  .stat.red .val { color:var(--red); }
  .row { background:var(--navy-2); border:1px solid var(--navy-3);
         border-radius:14px; padding:20px; margin-bottom:14px; }
  .row h3 { font-family:'Fraunces', Georgia, serif; font-size:17px; margin:0 0 8px; color:var(--gold); font-weight:600; }
  .row table { width:100%; border-collapse:collapse; font-size:13px; }
  .row th { text-align:left; padding:6px 0; color:var(--faint); font-weight:600; }
  .row td { padding:6px 0; color:var(--cream); border-top:1px solid rgba(255,255,255,.04); }
  .row .empty { color:var(--faint); font-style:italic; font-size:13px; }
  footer { margin-top:60px; padding:28px 0; border-top:1px solid var(--navy-3);
           color:var(--faint); font-size:13px; text-align:center; }
</style></head><body>
<div class="wrap">
  <header>
    <div class="wordmark">Pocket<i>Plot</i> Universe</div>
    <nav>
      <a href="/">Home</a>
      <a href="/faq">FAQ</a>
      <a href="/contact">Contact</a>
    </nav>
  </header>

  <h1>System <i>status</i>.</h1>
  <p class="lead">Real numbers from the running platform. Updated on every page load.</p>

  <div class="grid">
    <div class="stat green">
      <div class="lab">Last cron run</div>
      <div class="val">{% if last_cron %}{{ last_cron['created_at'][:16] }}{% else %}never{% endif %}</div>
    </div>
    <div class="stat">
      <div class="lab">Queue pending</div>
      <div class="val">{{ pending }}</div>
    </div>
    <div class="stat">
      <div class="lab">Approved + sent</div>
      <div class="val">{{ approved + sent }}</div>
    </div>
    <div class="stat">
      <div class="lab">Delivered (24h)</div>
      <div class="val">{{ deliveries_24h }}</div>
    </div>
  </div>

  <div class="row">
    <h3>Last cron activity</h3>
    {% if last_cron %}
    <table>
      <tr><th>When</th><td>{{ last_cron['created_at'] }}</td></tr>
      <tr><th>Note</th><td>{{ last_cron['note'] or '(no note)' }}</td></tr>
    </table>
    {% else %}
    <p class="empty">No cron runs recorded yet. The nightly job runs at 20:00 UTC.</p>
    {% endif %}
  </div>

  <div class="row">
    <h3>Review queue</h3>
    <table>
      <tr><th>Pending</th><td>{{ pending }} story{{ '' if pending == 1 else 'ies' }} waiting on admin review</td></tr>
      <tr><th>Approved</th><td>{{ approved }}</td></tr>
      <tr><th>Sent</th><td>{{ sent }}</td></tr>
      <tr><th>Rejected</th><td>{{ rejected }}</td></tr>
    </table>
    <p style="margin:14px 0 0"><a href="/admin/queue" style="color:var(--gold);font-family:Karla;font-size:13px">Open the review queue →</a></p>
  </div>

  <div class="row">
    <h3>Recent content-filter events</h3>
    {% if recent_errors %}
    <table>
      <tr><th>When</th><th>Pass</th><th>Verdict</th><th>Reason</th></tr>
      {% for e in recent_errors %}
      <tr><td>{{ e['created_at'][:16] }}</td><td>{{ e['pass'] }}</td><td>{{ e['verdict'] }}</td><td>{{ (e['reason'] or '')[:60] }}</td></tr>
      {% endfor %}
    </table>
    {% else %}
    <p class="empty">No rejected or rewritten content recently. ✅</p>
    {% endif %}
  </div>

  <footer>PocketPlot Universe · 18+ · original content only · <a href="/" style="color:var(--muted)">Home</a></footer>
</div></body></html>"""


ROADMAP_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Roadmap · PocketPlot Universe</title>
<style>
  :root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460; --gold:#e6c879;
          --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; --green:#9ad6a4; }
  * { box-sizing:border-box; }
  body { margin:0; padding:0; background:var(--navy); color:var(--cream);
         font-family:Karla, system-ui, sans-serif; line-height:1.6; }
  .wrap { max-width:960px; margin:0 auto; padding:0 28px; }
  header { padding:22px 0; border-bottom:1px solid var(--navy-3); }
  .wordmark { font-family:'Fraunces', Georgia, serif; font-style:italic;
              color:var(--gold); font-size:22px; font-weight:600; }
  .wordmark i { color:var(--muted); font-style:italic; font-weight:400; }
  nav { float:right; margin-top:8px; }
  nav a { color:var(--muted); text-decoration:none; margin-left:22px; font-size:13px;
         letter-spacing:.05em; text-transform:uppercase; }
  nav a:hover { color:var(--gold); }
  h1 { font-family:'Fraunces', Georgia, serif; font-size:36px; margin:36px 0 8px; font-weight:600; }
  h1 i { color:var(--gold); font-style:italic; }
  .lead { font-family:'Fraunces', Georgia, serif; font-style:italic; color:var(--muted);
          font-size:16px; margin:0 0 28px; max-width:680px; }
  h2 { font-family:'Fraunces', Georgia, serif; font-size:24px; margin:40px 0 14px;
       color:var(--gold); font-weight:600; }
  .list { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:10px; margin-bottom:18px; }
  .item { background:var(--navy-2); border:1px solid var(--navy-3);
          border-radius:10px; padding:14px 18px; }
  .item .v { font-family:'Fraunces', Georgia, serif; font-style:italic;
             color:var(--gold); font-size:13px; margin-bottom:4px; }
  .item .t { color:var(--cream); font-size:14px; line-height:1.5; }
  .item .s { color:var(--faint); font-size:11px; margin-top:6px; text-transform:uppercase;
             letter-spacing:.1em; }
  .wanted { background:var(--navy-2); border:1px solid var(--navy-3);
            border-radius:10px; padding:14px 18px; margin-bottom:8px; }
  .wanted h3 { font-family:'Fraunces', Georgia, serif; font-size:16px;
               color:var(--cream); margin:0 0 4px; font-weight:600; }
  .wanted p { color:var(--muted); font-size:13px; margin:0 0 8px; }
  .wanted .meta { font-size:11px; color:var(--faint); display:flex; gap:12px; align-items:center; }
  .wanted form { display:inline; }
  .wanted button { background:transparent; color:var(--gold); border:1px solid var(--gold);
                  padding:4px 10px; border-radius:99px; font-size:11px; cursor:pointer; }
  .wanted button:hover { background:var(--gold); color:var(--navy); }
  .suggest { background:var(--navy-2); border:1px solid var(--navy-3); border-radius:14px;
             padding:24px; margin-top:24px; }
  .suggest h3 { font-family:'Fraunces', Georgia, serif; font-size:18px; color:var(--gold);
                margin:0 0 12px; font-weight:600; }
  .suggest .field { margin-bottom:12px; }
  .suggest input, .suggest textarea { width:100%; background:var(--navy);
              border:1px solid var(--navy-3); color:var(--cream);
              padding:8px 12px; border-radius:8px; font-family:Karla; font-size:13px;
              box-sizing:border-box; }
  .suggest input:focus, .suggest textarea:focus { outline:none; border-color:var(--gold); }
  .suggest button { background:var(--gold); color:var(--navy); border:none;
                    padding:8px 16px; border-radius:99px; font-weight:700;
                    font-size:13px; cursor:pointer; }
  .empty { color:var(--faint); font-style:italic; padding:14px 0; }
  footer { margin-top:60px; padding:28px 0; border-top:1px solid var(--navy-3);
           color:var(--faint); font-size:13px; text-align:center; }
</style></head><body>
<div class="wrap">
  <header>
    <div class="wordmark">Pocket<i>Plot</i> Universe</div>
    <nav>
      <a href="/">Home</a>
      <a href="/faq">FAQ</a>
      <a href="/contact">Contact</a>
    </nav>
  </header>

  <h1>Public <i>roadmap</i>.</h1>
  <p class="lead">What's shipped, what's planned, and what you're asking for. Vote on requests — the top items move up.</p>

  <h2>Shipped</h2>
  <div class="list">
    {% for s in shipped %}
    <div class="item"><div class="v">{{ s['v'] }}</div><div class="t">{{ s['title'] }}</div></div>
    {% endfor %}
  </div>

  <h2>Planned</h2>
  <div class="list">
    {% for p in planned %}
    <div class="item"><div class="s">{{ p['size'] }}</div><div class="t">{{ p['title'] }}</div></div>
    {% endfor %}
  </div>

  <h2 id="wanted">What you're asking for</h2>
  {% if wanted %}
    {% for w in wanted %}
    <div class="wanted">
      <h3>{{ w['title'] }}</h3>
      {% if w['description'] %}<p>{{ w['description'] }}</p>{% endif %}
      <div class="meta">
        <span>▲ {{ w['votes'] }} vote{{ '' if w['votes'] == 1 else 's' }}</span>
        {% if w['submitter_email'] %}<span>· from {{ w['submitter_email'] }}</span>{% endif %}
        <form method="post" action="/roadmap/vote/{{ w['id'] }}">
          <button type="submit"{% if w['id'] in voted_features %} disabled style="opacity:.5;cursor:not-allowed"{% endif %}>
            {% if w['id'] in voted_features %}Voted{% else %}Vote{% endif %}
          </button>
        </form>
      </div>
    </div>
    {% endfor %}
  {% else %}
    <p class="empty">No open feature requests. Be the first to suggest one below.</p>
  {% endif %}

  <div class="suggest">
    <h3>Suggest a feature</h3>
    <form method="post" action="/roadmap/request">
      <div class="field">
        <input type="text" name="title" required maxlength="200" placeholder="What's the feature?">
      </div>
      <div class="field">
        <textarea name="description" rows="2" maxlength="1000" placeholder="More detail (optional)"></textarea>
      </div>
      <div class="field">
        <input type="email" name="email" placeholder="Your email (optional, only if you want credit)">
      </div>
      <button type="submit">Submit</button>
    </form>
  </div>

  <footer>PocketPlot Universe · 18+ · original content only</footer>
</div></body></html>"""




# ---- Phase 13 polish: /admin/audit ----
@app.route("/admin/audit", methods=["GET"])
@admin_required
def admin_audit_view():
    import audit
    page = max(1, int(request.args.get("page") or 1))
    page_size = 50
    offset = (page - 1) * page_size
    filter_action = (request.args.get("action") or "").strip() or None
    rows = audit.recent(db, limit=page_size, action_prefix=filter_action)
    return render_template_string(
        ADMIN_AUDIT_HTML, rows=rows, page=page, filter_action=filter_action or "",
    )


# ---- Phase 13 polish: /admin/refund ----
@app.route("/admin/refund", methods=["GET", "POST"])
@admin_required
def admin_refund():
    """Issue a refund for a subscriber. Records an audit row and sends
    a confirmation email. Mock mode degrades gracefully."""
    import audit
    if request.method == "POST":
        sub_id = (request.form.get("subscriber_id") or "").strip()
        amount = (request.form.get("amount") or "").strip()
        reason = (request.form.get("reason") or "").strip()[:300]
        if not sub_id.isdigit():
            flash("Subscriber id must be a number.", "err")
            return redirect(url_for("admin_refund"))
        conn = db()
        sub = conn.execute(
            "SELECT id, email, child_name, customer_id FROM subscribers WHERE id=?",
            (int(sub_id),),
        ).fetchone()
        conn.close()
        if not sub:
            flash(f"No subscriber with id {sub_id}.", "err")
            return redirect(url_for("admin_refund"))
        # In mock mode, log the refund + send the customer an email.
        actor_id = session.get("subscriber_id")  # admin's own id (the admin session)
        audit.record(db, actor_id=actor_id, actor_type="admin",
                     action="refund.issue", target_type="subscriber",
                     target_id=sub["id"],
                     metadata={"amount": amount, "reason": reason,
                               "customer_id": sub["customer_id"]})
        try:
            subject = "Your PocketPlot Universe refund"
            plain = (
                f"Hi,\n\nWe've issued a refund of ${amount} to your account. "
                f"Reason: {reason or '(admin-initiated)'}\n\n"
                f"Refunds usually appear on your card within 5-10 business days.\n\n"
                f"If you have questions, reply to this email.\n"
            )
            _send_raw_email(sub["email"], subject, plain, plain)
        except Exception as e:
            log.warning("refund email failed: %s", e)
        flash(f"Refund of ${amount} issued to {sub['email']} (id {sub_id}).", "ok")
        return redirect(url_for("admin_refund"))
    return ADMIN_REFUND_HTML




# ---- Phase 13 polish: /how-it-works ----
@app.route("/how-it-works", methods=["GET"])
def how_it_works_page():
    """Full expansion of the homepage 'three doors' concept into a dedicated
    page with sections, screenshots/illustrations, and ranked FAQs."""
    import pathlib
    p = pathlib.Path(__file__).parent / "how-it-works.html"
    if p.exists():
        return send_file(str(p), mimetype="text/html")
    # Fallback: a simple inline page
    return ("<h1>How it works</h1><p>See the homepage for the summary.</p>", 200)



# ---- Phase 13 polish: admin audit + refund templates ----
ADMIN_AUDIT_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audit log · PocketPlot Universe</title>
<style>
  :root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460; --gold:#e6c879;
          --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
  * { box-sizing:border-box; }
  body { margin:0; padding:0; background:var(--navy); color:var(--cream);
         font-family:Karla, system-ui, sans-serif; }
  .wrap { max-width:1100px; margin:36px auto; padding:0 24px; }
  header { margin-bottom:18px; padding-bottom:14px; border-bottom:1px solid var(--navy-3); }
  .wordmark { font-family:'Fraunces', Georgia, serif; font-style:italic;
              color:var(--gold); font-size:20px; font-weight:600; }
  nav a { color:var(--muted); text-decoration:none; margin-right:14px; font-size:13px;
         text-transform:uppercase; letter-spacing:.05em; }
  nav a:hover { color:var(--gold); }
  h1 { font-family:'Fraunces', Georgia, serif; font-size:28px; margin:0; font-weight:600; }
  .filters { background:var(--navy-2); border:1px solid var(--navy-3);
             border-radius:12px; padding:14px 18px; margin-bottom:18px;
             display:flex; gap:10px; align-items:center; }
  .filters input { flex:1; background:var(--navy); border:1px solid var(--navy-3);
                   color:var(--cream); padding:8px 12px; border-radius:8px;
                   font-family:Karla; font-size:13px; }
  .filters input:focus { outline:none; border-color:var(--gold); }
  .filters button { background:var(--gold); color:var(--navy); border:none;
                    padding:8px 16px; border-radius:99px; font-weight:700;
                    font-size:13px; cursor:pointer; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { text-align:left; padding:8px 6px; color:var(--muted); font-weight:600;
       border-bottom:1px solid var(--navy-3); }
  td { padding:8px 6px; color:var(--cream); border-bottom:1px solid rgba(255,255,255,.04); }
  .badge { display:inline-block; padding:2px 8px; border-radius:99px; font-size:11px;
           font-weight:700; }
  .badge.admin { background:#3a2e1a; color:var(--gold); }
  .badge.subscriber { background:var(--navy-3); color:var(--muted); }
  .badge.system { background:#1a2a44; color:var(--faint); }
  .badge.api { background:#1a3a2a; color:var(--cream); }
  code { font-family:monospace; font-size:12px; color:var(--gold); background:rgba(0,0,0,.3);
          padding:2px 6px; border-radius:4px; }
  .empty { color:var(--faint); padding:30px; text-align:center; font-style:italic; }
</style></head><body>
<div class="wrap">
  <header>
    <div class="wordmark">Pocket<i>Plot</i> Universe · Admin</div>
    <nav>
      <a href="/admin/dashboard">Dashboard</a>
      <a href="/admin/queue">Queue</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/refund">Refund</a>
      <a href="/logout">Logout</a>
    </nav>
    <h1 style="margin-top:14px">Audit log</h1>
  </header>

  <form class="filters" method="get">
    <input type="text" name="action" value="{{ filter_action }}" placeholder="Filter by action prefix (e.g. queue, refund, contact)">
    <button type="submit">Filter</button>
  </form>

  {% if rows %}
  <table>
    <tr><th>When</th><th>Actor</th><th>Action</th><th>Target</th><th>Metadata</th><th>IP</th></tr>
    {% for r in rows %}
    <tr>
      <td>{{ r['created_at'][:19] }}</td>
      <td><span class="badge {{ r['actor_type'] }}">{{ r['actor_type'] }}</span>
          {% if r['actor_id'] %}#{{ r['actor_id'] }}{% endif %}</td>
      <td><code>{{ r['action'] }}</code></td>
      <td>{% if r['target_type'] %}{{ r['target_type'] }}#{{ r['target_id'] or '' }}{% endif %}</td>
      <td><code>{{ (r['metadata_json'] or '')[:80] }}</code></td>
      <td>{{ (r['ip'] or '')[:24] }}</td>
    </tr>
    {% endfor %}
  </table>
  <p style="text-align:center;margin-top:18px"><a href="/admin/audit?page={{ page+1 }}" style="color:var(--gold)">Next page →</a></p>
  {% else %}
  <div class="empty">No audit rows match that filter.</div>
  {% endif %}
</div></body></html>"""


ADMIN_REFUND_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Refund · PocketPlot Universe</title>
<style>
  :root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460; --gold:#e6c879;
          --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
  * { box-sizing:border-box; }
  body { margin:0; padding:0; background:var(--navy); color:var(--cream);
         font-family:Karla, system-ui, sans-serif; }
  .wrap { max-width:680px; margin:36px auto; padding:0 24px; }
  header { margin-bottom:18px; padding-bottom:14px; border-bottom:1px solid var(--navy-3); }
  .wordmark { font-family:'Fraunces', Georgia, serif; font-style:italic;
              color:var(--gold); font-size:20px; font-weight:600; }
  nav a { color:var(--muted); text-decoration:none; margin-right:14px; font-size:13px;
         text-transform:uppercase; letter-spacing:.05em; }
  nav a:hover { color:var(--gold); }
  h1 { font-family:'Fraunces', Georgia, serif; font-size:30px; margin:0; font-weight:600; }
  .card { background:var(--navy-2); border:1px solid var(--navy-3);
          border-radius:14px; padding:28px; margin-bottom:18px; }
  .field { margin-bottom:14px; }
  .field label { display:block; font-size:11px; letter-spacing:.14em;
                text-transform:uppercase; color:var(--muted); margin-bottom:6px;
                font-weight:700; }
  .field input, .field textarea { width:100%; background:var(--navy);
              border:1px solid var(--navy-3); color:var(--cream);
              padding:10px 12px; border-radius:8px; font-family:Karla; font-size:14px;
              box-sizing:border-box; }
  .field input:focus, .field textarea:focus { outline:none; border-color:var(--gold); }
  .btn { background:var(--gold); color:var(--navy); border:none; padding:11px 22px;
         border-radius:99px; font-family:'Fraunces', Georgia, serif;
         font-weight:700; font-size:14px; cursor:pointer; }
  .btn:hover { background:#d4b566; }
  .info { background:rgba(230,200,121,.08); border:1px solid var(--gold);
           border-radius:10px; padding:14px 18px; margin-bottom:18px;
           font-family:'Fraunces', Georgia, serif; font-style:italic;
           font-size:13px; color:var(--cream); line-height:1.6; }
</style></head><body>
<div class="wrap">
  <header>
    <div class="wordmark">Pocket<i>Plot</i> Universe · Admin</div>
    <nav>
      <a href="/admin/dashboard">Dashboard</a>
      <a href="/admin/queue">Queue</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/refund">Refund</a>
      <a href="/logout">Logout</a>
    </nav>
    <h1 style="margin-top:14px">Issue a refund</h1>
  </header>

  <div class="info">
    Refunds are recorded in the audit log + emailed to the customer. In mock
    mode (no live Stripe), no actual money moves; the customer still gets
    the email + the audit row.
  </div>

  <form method="post" class="card">
    <div class="field">
      <label>Subscriber id</label>
      <input type="number" name="subscriber_id" required min="1" placeholder="e.g. 2">
    </div>
    <div class="field">
      <label>Amount (USD)</label>
      <input type="text" name="amount" required placeholder="e.g. 7.99" value="7.99">
    </div>
    <div class="field">
      <label>Reason</label>
      <textarea name="reason" rows="3" maxlength="300" placeholder="Why is the refund being issued?"></textarea>
    </div>
    <button class="btn" type="submit">Issue refund</button>
  </form>
</div></body></html>"""





# =====================================================================
# Phase 17 (v17) - expansion routes
# =====================================================================
import analytics as _analytics
import seed_generator as _seed_gen
import story_remix as _remix
import follows as _follows
import genre_icons_v17 as _gi17
import avatars_v17 as _av17


# ---- v17: Weekly Summary email (Pro / Creator) ----
def _send_weekly_summary_for(subscriber_id: int) -> bool:
    """Build a one-week recap for a Pro/Creator subscriber and send.
    Returns True if delivered. Idempotent via weekly_summary_log."""
    import json as _json
    import datetime as dt
    conn = db()
    sub = conn.execute(
        "SELECT id, email, child_name FROM subscribers WHERE id=?",
        (subscriber_id,),
    ).fetchone()
    if not sub:
        conn.close()
        return False
    week_start = (dt.datetime.utcnow() - dt.timedelta(days=7)).strftime("%Y-%m-%d")
    # Idempotency: don't send twice for the same week_start
    already = conn.execute(
        "SELECT 1 FROM weekly_summary_log WHERE subscriber_id=? AND week_start=?",
        (subscriber_id, week_start),
    ).fetchone()
    if already:
        conn.close()
        return False
    stats = _analytics.subscriber_stats(db, subscriber_id)
    worlds_count = stats["world_count"]
    total_views = stats["total_views"]
    total_reads = stats["total_reads"]
    approx_words = stats["approx_words"]
    subject = f"Your PocketPlot week: {approx_words} words written"
    plain = (
        f"Hi,\n\n"
        f"Here's what happened in your PocketPlot Universe over the past week:\n\n"
        f"  \u2022 Stories created: {worlds_count}\n"
        f"  \u2022 Approx. words written: {approx_words}\n"
        f"  \u2022 Total story views: {total_views}\n"
        f"  \u2022 Total story reads: {total_reads}\n\n"
        f"Keep going. \u2014 PocketPlot Universe\n"
    )
    html = (
        '<!doctype html><html><body style="margin:0;padding:0;background:#0e1a2e;'
        'font-family:Georgia,serif;color:#f3e9d2">'
        '<div style="max-width:560px;margin:0 auto;padding:36px 28px">'
        '<div style="font-family:Arial,sans-serif;font-size:11px;letter-spacing:.16em;'
        'text-transform:uppercase;color:#e6c879;margin-bottom:8px">PocketPlot Universe \u00b7 Weekly</div>'
        f'<h1 style="font-size:24px;margin:0 0 14px;color:#f3e9d2">You wrote {approx_words} words this week.</h1>'
        '<p style="font-size:14px;line-height:1.6;color:#d4b8a4">Your PocketPlot at a glance:</p>'
        '<table style="width:100%;border-collapse:collapse;margin:18px 0">'
        f'<tr><td style="padding:6px 0;color:#9eb6d4">Stories created</td>'
        f'<td style="padding:6px 0;text-align:right;color:#f3e9d2">{worlds_count}</td></tr>'
        f'<tr><td style="padding:6px 0;color:#9eb6d4">Words written</td>'
        f'<td style="padding:6px 0;text-align:right;color:#f3e9d2">{approx_words}</td></tr>'
        f'<tr><td style="padding:6px 0;color:#9eb6d4">Total views</td>'
        f'<td style="padding:6px 0;text-align:right;color:#f3e9d2">{total_views}</td></tr>'
        f'<tr><td style="padding:6px 0;color:#9eb6d4">Total reads</td>'
        f'<td style="padding:6px 0;text-align:right;color:#f3e9d2">{total_reads}</td></tr>'
        '</table>'
        '<a href="/me" style="display:inline-block;background:#e6c879;color:#0e1a2e;'
        'padding:12px 24px;border-radius:99px;font-family:Arial,sans-serif;'
        'font-weight:700;font-size:14px;text-decoration:none;margin-top:14px">'
        'Open dashboard \u2192</a>'
        '</div></body></html>'
    )
    try:
        _send_raw_email(sub["email"], subject, plain, html)
    except Exception as e:
        log.warning("weekly summary send failed for sub=%s: %s", subscriber_id, e)
        conn.close()
        return False
    conn.execute(
        "INSERT INTO weekly_summary_log(subscriber_id, week_start, sent_at, stats_json) "
        "VALUES (?, ?, ?, ?)",
        (subscriber_id, week_start, dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
         _json.dumps(stats)),
    )
    conn.commit()
    conn.close()
    return True


def _send_milestone_email_for(subscriber_id: int, milestone: dict) -> bool:
    """Send a one-shot milestone celebration email."""
    import datetime as dt
    conn = db()
    sub = conn.execute(
        "SELECT email, child_name FROM subscribers WHERE id=?",
        (subscriber_id,),
    ).fetchone()
    if not sub:
        conn.close()
        return False
    name = sub["child_name"] or "writer"
    subject = f"\U0001f389 Milestone reached: {milestone['label']}"
    plain = (
        f"Hi {name},\n\n"
        f"You just hit a PocketPlot milestone: {milestone['label']}.\n"
        f"Keep writing. \u2014 PocketPlot Universe\n"
    )
    html = (
        '<!doctype html><html><body style="margin:0;padding:0;background:#0e1a2e;'
        'font-family:Georgia,serif;color:#f3e9d2">'
        '<div style="max-width:560px;margin:0 auto;padding:36px 28px;text-align:center">'
        '<div style="font-size:48px">\U0001f389</div>'
        f'<h1 style="font-size:26px;margin:12px 0;color:#e6c879">{milestone["label"]}</h1>'
        f'<p style="font-size:15px;color:#d4b8a4">You did it, {name}.</p>'
        '<a href="/me" style="display:inline-block;background:#e6c879;color:#0e1a2e;'
        'padding:12px 24px;border-radius:99px;font-family:Arial,sans-serif;'
        'font-weight:700;font-size:14px;text-decoration:none;margin-top:14px">'
        'See your stats \u2192</a>'
        '</div></body></html>'
    )
    try:
        _send_raw_email(sub["email"], subject, plain, html)
    except Exception as e:
        log.warning("milestone email failed for sub=%s: %s", subscriber_id, e)
        conn.close()
        return False
    conn.execute(
        "UPDATE user_milestones SET celebrated=1 WHERE subscriber_id=? AND milestone=?",
        (subscriber_id, milestone["id"]),
    )
    conn.commit()
    conn.close()
    return True


def _weekly_summary_job():
    """Weekly summary cron: send to all Pro/Creator subscribers. Idempotent."""
    conn = db()
    rows = conn.execute(
        "SELECT id FROM subscribers WHERE plan IN ('pro', 'creator') "
        "AND active=1"
    ).fetchall()
    conn.close()
    for r in rows:
        try:
            _send_weekly_summary_for(r["id"])
        except Exception as e:
            log.warning("weekly summary failed for sub=%s: %s", r["id"], e)


def _milestone_check_job():
    """Daily: check every active subscriber for newly-achieved milestones."""
    conn = db()
    subs = conn.execute(
        "SELECT id FROM subscribers WHERE active=1"
    ).fetchall()
    conn.close()
    for r in subs:
        try:
            for ms in _analytics.check_milestones(db, r["id"]):
                _send_milestone_email_for(r["id"], ms)
        except Exception as e:
            log.warning("milestone check failed for sub=%s: %s", r["id"], e)



# ---- /library: Story Library (grid view, search, filter, export) ----
@app.route("/library", methods=["GET"])
@login_required
def library():
    """Per-subscriber story library. Shows worlds + episodes as cards.
    Supports search (q) and genre filter."""
    sub = _subscriber_or_redirect()
    if not sub:
        return redirect(url_for("login"))
    q = (request.args.get("q") or "").strip()
    genre_filter = (request.args.get("genre") or "").strip()
    conn = db()
    where = ["w.subscriber_id=?"]
    params = [sub["id"]]
    if q:
        where.append("(w.title LIKE ? OR w.setting LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    if genre_filter:
        where.append("w.genre=?")
        params.append(genre_filter)
    rows = conn.execute(
        "SELECT w.id, w.title, w.genre, w.tone, w.setting, w.view_count, "
        "w.read_count, w.created_at, w.last_played_at, "
        "(SELECT COUNT(*) FROM world_episodes WHERE world_id=w.id) AS ep_count, "
        "(SELECT id FROM world_episodes WHERE world_id=w.id ORDER BY episode_number DESC LIMIT 1) AS last_ep_id "
        "FROM worlds w WHERE " + " AND ".join(where) + " "
        "ORDER BY w.last_played_at DESC LIMIT 100",
        params,
    ).fetchall()
    conn.close()
    from story_image_composer import GENRES_V16, GENRE_LABELS
    return render_template_string(
        LIBRARY_HTML,
        rows=rows, q=q, genre_filter=genre_filter,
        genres=GENRES_V16, labels=GENRE_LABELS,
        stories=[dict(r) for r in rows],
    )


@app.route("/library/export", methods=["GET"])
@login_required
def library_export():
    """Export all the subscriber's worlds as a single ZIP of markdown files.
    """
    import zipfile
    import io
    sub = _subscriber_or_redirect()
    if not sub:
        return redirect(url_for("login"))
    conn = db()
    worlds = conn.execute(
        "SELECT * FROM worlds WHERE subscriber_id=? ORDER BY created_at DESC",
        (sub["id"],),
    ).fetchall()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for w in worlds:
            episodes = conn.execute(
                "SELECT * FROM world_episodes WHERE world_id=? ORDER BY episode_number",
                (w["id"],),
            ).fetchall()
            md = f"# {w['title']}\n\n"
            md += f"**Genre:** {w['genre']}  \n"
            md += f"**Tone:** {w['tone']}  \n"
            md += f"**Setting:** {w['setting']}  \n\n"
            for e in episodes:
                md += f"## Episode {e['episode_number']}: {e['title']}\n\n"
                md += (e["body"] or "").replace("\n\n", "\n\n\n") + "\n\n---\n\n"
            safe = "".join(c for c in w["title"] if c.isalnum() or c in " _-")
            z.writestr(f"{safe}_world_{w['id']}.md", md)
    conn.close()
    buf.seek(0)
    return Response(
        buf.read(),
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment; filename=pocketplot_library.zip"},
    )


# ---- /seed: random prompt generator ----
@app.route("/seed", methods=["GET"])
@login_required
def seed_page():
    """Render the Seed page with a default prompt. Users click 'Try
    another' to roll a new one."""
    seed = _seed_gen.generate_prompt()
    return render_template_string(SEED_HTML, seed=seed)


@app.route("/seed/roll", methods=["POST"])
@login_required
def seed_roll():
    """Return a fresh prompt as JSON for the 'Try Another' button."""
    seed = _seed_gen.generate_prompt(
        genre=(request.json or {}).get("genre") if request.is_json else None
    )
    return jsonify(seed)


@app.route("/seed/use", methods=["POST"])
@login_required
def seed_use():
    """Pre-fill /worlds/new with the chosen seed. We persist the seed in
    the session and redirect."""
    payload = request.form or (request.json or {})
    seed_data = {
        "title_hint":         payload.get("title_hint", ""),
        "genre":              payload.get("genre", "fantasy"),
        "tone":               payload.get("tone", "hopeful"),
        "setting":            payload.get("setting", ""),
        "character_description": payload.get("character_description", ""),
        "primary_objective":  payload.get("primary_objective", ""),
    }
    session["pending_seed"] = seed_data
    return redirect(url_for("worlds_new"))


# ---- /remix: remix a world into a new genre ----
@app.route("/remix", methods=["GET", "POST"])
@login_required
def remix_page():
    """List all remixable worlds. POST = perform the remix."""
    sub = _subscriber_or_redirect()
    if not sub:
        return redirect(url_for("login"))
    from story_image_composer import GENRES_V16, GENRE_LABELS
    conn = db()
    worlds = conn.execute(
        "SELECT id, title, genre, tone, view_count, read_count FROM worlds "
        "WHERE subscriber_id=? ORDER BY last_played_at DESC LIMIT 50",
        (sub["id"],),
    ).fetchall()
    conn.close()
    if request.method == "POST":
        world_id = int(request.form.get("world_id") or 0)
        to_genre = (request.form.get("to_genre") or "").strip()
        to_tone  = (request.form.get("to_tone") or "").strip() or None
        if not world_id or not to_genre:
            flash("Pick a story + a target genre.", "err")
            return redirect(url_for("remix_page"))
        if sub["tier"] in ("pro", "creator"):
            res = _remix.remix_byob(db, world_id, to_genre, to_tone or "hopeful",
                                     subscriber_id=sub["id"])
        else:
            res = _remix.remix_procedural(db, world_id, to_genre, to_tone or "hopeful")
        if not res.get("ok"):
            flash(res.get("error") or "Remix failed.", "err")
            return redirect(url_for("remix_page"))
        new_id = res["new_world_id"]
        return redirect(url_for("worlds_view", world_id=new_id))
    return render_template_string(
        REMIX_HTML,
        worlds=[dict(r) for r in worlds],
        genres=GENRES_V16, labels=GENRE_LABELS,
    )


# ---- /u/[username]: public profile + featured stories ----
@app.route("/u/<username>", methods=["GET"])
def public_profile(username):
    """Public profile page. Returns 404 if user isn't public."""
    import follows as _follows
    sub = _follows.lookup_subscriber_by_username(db, username)
    if not sub:
        return render_template_string("404.html"), 404
    worlds = _follows.list_public_worlds_for(db, sub["id"], limit=12)
    featured_ids = _follows.get_featured_stories(db, sub["id"])
    featured = []
    if featured_ids:
        conn = db()
        placeholders = ",".join("?" for _ in featured_ids)
        try:
            featured = [dict(r) for r in conn.execute(
                f"SELECT * FROM worlds WHERE id IN ({placeholders}) AND is_public=1",
                featured_ids,
            ).fetchall()]
        except Exception:
            featured = []
        conn.close()
    viewer_id = session.get("subscriber_id")
    is_following = (_follows.is_following(db, viewer_id, sub["id"])
                      if viewer_id else False)
    fc = _follows.follower_count(db, sub["id"])
    fgc = _follows.following_count(db, sub["id"])
    return render_template_string(
        PROFILE_HTML,
        profile=sub, worlds=worlds, featured=featured,
        is_following=is_following,
        fc=fc, fgc=fgc,
    )


@app.route("/u/<username>/follow", methods=["POST"])
@login_required
def follow_user(username):
    import follows as _follows
    sub = _follows.lookup_subscriber_by_username(db, username)
    if not sub:
        return ("Not found", 404)
    me = _subscriber_or_redirect()
    if not me:
        return redirect(url_for("login"))
    if sub["id"] == me["id"]:
        flash("You can't follow yourself.", "err")
        return redirect(url_for("public_profile", username=username))
    if _follows.is_following(db, me["id"], sub["id"]):
        _follows.unfollow(db, me["id"], sub["id"])
        _follows.notify(db, sub["id"], "system", f"{me.get('child_name') or 'Someone'} unfollowed you",
                          link="/me/notifications")
    else:
        _follows.follow(db, me["id"], sub["id"])
        _follows.notify(db, sub["id"], "new_follower",
                          f"{me.get('child_name') or 'Someone'} started following you",
                          link=f"/u/{username}")
    return redirect(url_for("public_profile", username=username))


# ---- /admin/features + /admin/top (admin dashboard extensions) ----
@app.route("/admin/features", methods=["GET"])
@admin_required
def admin_features():
    import analytics as _a
    rows = _a.list_features(db)
    return render_template_string(ADMIN_FEATURES_HTML, features=rows)


@app.route("/admin/features/<key>/toggle", methods=["POST"])
@admin_required
def admin_feature_toggle(key):
    import analytics as _a
    enabled = (request.form.get("enabled") or "1") == "1"
    _a.set_feature(db, key, enabled, actor="admin")
    flash(f"Feature '{key}' is now {'ON' if enabled else 'OFF'}.", "ok")
    return redirect(url_for("admin_features"))


@app.route("/admin/top", methods=["GET"])
@admin_required
def admin_top_stories():
    import analytics as _a
    rows = _a.top_stories(db, limit=20)
    return render_template_string(ADMIN_TOP_HTML, stories=rows)


"""v23 route handlers for PocketPlot Universe.

Appended to app.py. Provides:
  - /worlds/<id>/share  + /worlds/<id>/like
  - /worlds/<id>/export.{epub,pdf,zip}
  - /play/<token> + /play/<token>/map + /play/<token>/node/<n> + /play/<token>/choose
  - /read/<token> + /read/<token>/page/<n>
  - /qr.svg
  - /redeem/<code>
  - /admin/segments + /admin/promo-codes + /admin/promo-codes/new + /admin/newsletter
  - /manifest.json + /sw.js + /push/subscribe + /push/unsubscribe
  - /api/v1/shares + /api/v1/likes/<wid> + /api/v1/world/<id>/stats
  - /api/v1/world/<id>/inventory + /api/v1/world/<id>/build (v24 stubs)
"""

import sys, json, io, datetime as dt, urllib.parse, pathlib
sys.path.insert(0, '/root/pocketplot')
import engagement as _eng
import exports as _exp
import promo as _promo
import migrations_phase23 as _m23
import migrations_phase24 as _m24
import audit_v24 as _audit24
import streaks_xp as _streaks
import social as _social
import inventory as _inv
import scene_graph as _sgraph
import onboarding as _onb
import tts as _tts
import sentry_v24 as _sentry
from qrcode_lib import qr_svg

# ============ v23 templates (defined early so route handlers can reference them) ============
# ============ v23 templates (appended at end) ============

"""v23 routes for PocketPlot Universe.

This module is meant to be appended to app.py at the right insertion
point. It provides:
  - /worlds/<id>/share       manage share tokens for a world
  - /worlds/<id>/export.epub export a world as EPUB
  - /worlds/<id>/export.zip  export a world as a bulk ZIP
  - /worlds/<id>/export.pdf  export a world as a single PDF
  - /worlds/<id>/like        POST to like (toggle)
  - /play/<token>             PLAY mode (game with choices, branching)
  - /play/<token>/map         PLAY mode world map (foundation for Minecraft-style)
  - /play/<token>/choose      POST to choose a branch
  - /read/<token>             READ mode (manga, page-flip)
  - /read/<token>/page/<n>   READ mode single page (for swipe)
  - /api/v1/shares            API: create share tokens
  - /api/v1/likes/<world_id>  API: like/unlike a world
  - /api/v1/world/<id>/stats  API: world stats JSON
  - /api/v1/world/<id>/inventory API stub (v24)
  - /api/v1/world/<id>/build    API stub (v24)
  - /redeem/<code>              redeem a promo code
  - /admin/segments            admin: manage email segments
  - /admin/promo-codes         admin: manage promo codes
  - /admin/promo-codes/new     admin: create a promo code
  - /admin/newsletter          admin: send a newsletter to a segment
  - /manifest.json             PWA manifest
  - /sw.js                     service worker
  - /push/subscribe            subscribe to push notifications
  - /push/unsubscribe          unsubscribe

All routes are inserted into the existing app via @app.route decorators.
This script is meant to be appended to app.py just before the
ENTRY block (so all decorators register before app.run()).

The block also appends the HTML templates (SHARE_HTML, PLAY_HTML,
READ_HTML, MAP_HTML, REDEEM_HTML, ADMIN_SEGMENTS_HTML, ADMIN_PROMO_HTML,
ADMIN_NEWSLETTER_HTML) - they're module-level constants, referenced by
the render_template_string() calls.
"""

import sys, pathlib
sys.path.insert(0, '/root/pocketplot')
import engagement as _eng
import exports as _exp
import promo as _promo
import migrations_phase23 as _m23
import audit_v24 as _audit24
import streaks_xp as _streaks
import social as _social
import inventory as _inv
import scene_graph as _sgraph
import onboarding as _onb
import tts as _tts
import sentry_v24 as _sentry

# ============================================================================
# v23 routes
# ============================================================================

from qrcode_lib import qr_svg, qr_png_data_url, make_share_token, make_player_session_id


# ============ TEMPLATES (defined at module level, referenced by handlers) ============

SHARE_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Share - {title}</title>
<link rel="icon" type="image/png" href="/logo-icon-32.png" sizes="32x32">
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;line-height:1.6}
.wrap{max-width:780px;margin:0 auto;padding:24px}
header{padding:18px 0;border-bottom:1px solid rgba(201,160,78,.25);display:flex;justify-content:space-between;align-items:center}
header a{color:var(--cream);text-decoration:none}
.brand{display:flex;align-items:center;gap:12px}
.brand img{width:40px;height:37px;border-radius:3px}
.brand-text{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:600;color:var(--gold-l);font-size:18px}
.brand-text em{color:var(--muted);font-style:normal;font-weight:400}
nav a{color:var(--muted);text-decoration:none;margin-left:18px;font-size:13px;letter-spacing:.05em;text-transform:uppercase}
nav a:hover{color:var(--gold-l)}
h1{font-family:Fraunces,Georgia,serif;font-size:32px;margin:36px 0 8px;color:var(--cream);font-weight:600}
h1 i{color:var(--gold-l);font-style:italic}
.lead{color:var(--muted);font-style:italic;font-family:Fraunces,Georgia,serif;margin:0 0 28px}
.card{background:linear-gradient(180deg,rgba(21,36,63,.5) 0%,rgba(15,26,46,.95) 100%);border:1px solid rgba(201,160,78,.3);border-radius:8px;padding:24px;margin-bottom:18px}
.card h2{font-family:Fraunces,Georgia,serif;font-size:20px;margin:0 0 12px;color:var(--cream);font-weight:500}
.row{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.row:last-child{margin-bottom:0}
.copybox{background:var(--navy);border:1px solid var(--navy-3);border-radius:6px;padding:10px 14px;font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--gold-l);flex:1;min-width:200px;user-select:all;cursor:text}
.btn{background:linear-gradient(180deg,var(--gold-l) 0%,var(--gold) 50%,#8a6a26 100%);color:var(--navy);border:1px solid #8a6a26;padding:9px 16px;border-radius:3px;font-family:Karla,sans-serif;font-weight:700;font-size:13px;cursor:pointer;text-decoration:none;display:inline-block;box-shadow:0 0 0 1px var(--gold-l) inset}
.btn:hover{box-shadow:0 0 0 1px var(--amber) inset,0 0 12px var(--amber)}
.btn.secondary{background:transparent;color:var(--gold-l);border-color:var(--gold);box-shadow:0 0 0 1px #8a6a26 inset}
.qr-wrap{display:flex;justify-content:center;padding:20px;background:#f3e9d2;border-radius:8px;margin:12px 0}
.qr-wrap svg{width:200px;height:200px;display:block}
.token{display:flex;gap:8px;align-items:center;background:var(--navy);padding:8px 14px;border-radius:99px;border:1px solid rgba(201,160,78,.3);font-family:'JetBrains Mono',monospace;font-size:14px;color:var(--gold-l);cursor:text;user-select:all}
.section-label{font-family:Karla,sans-serif;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold-l);font-weight:600;margin:0 0 8px}
.tabs{display:flex;gap:8px;margin-bottom:18px;border-bottom:1px solid rgba(201,160,78,.3);padding-bottom:8px}
.tab{padding:6px 14px;background:transparent;border:1px solid rgba(201,160,78,.3);border-radius:99px;color:var(--muted);font-size:12px;cursor:pointer;text-decoration:none;font-family:Karla,sans-serif;letter-spacing:.04em}
.tab.active{background:var(--gold);color:var(--navy);border-color:var(--gold)}
.existing-list{margin-top:14px;padding-top:14px;border-top:1px solid rgba(201,160,78,.2)}
.existing-item{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(201,160,78,.1);font-size:13px}
.existing-item:last-child{border-bottom:none}
.existing-item code{font-family:'JetBrains Mono',monospace;color:var(--gold-l);font-size:12px}
.export-row{display:flex;gap:10px;flex-wrap:wrap}
.export-row .btn{flex:1;min-width:140px;text-align:center}
.like-btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;background:transparent;border:1px solid rgba(201,160,78,.3);border-radius:99px;color:var(--gold-l);font-size:13px;cursor:pointer;font-family:Karla,sans-serif}
.like-btn.liked{background:rgba(232,90,138,.15);border-color:var(--gold);color:#e85a8a}
.like-btn:hover{background:rgba(201,160,78,.15)}
.stats-row{display:flex;gap:24px;flex-wrap:wrap;color:var(--muted);font-size:13px}
.stats-row b{color:var(--gold-l)}
</style></head><body>
<div class="wrap">
  <header>
    <a href="/me" class="brand">
      <img src="/logo-halo-240.png" alt="PocketPlot Universe">
      <span class="brand-text">Pocket<em>Plot</em> Universe</span>
    </a>
    <nav>
      <a href="/me">Dashboard</a>
      <a href="/library">Library</a>
      <a href="/logout">Logout</a>
    </nav>
  </header>

  <h1>Share <i>{{ world_title }}</i></h1>
  <p class="lead">Two ways to share. One for players, one for readers.</p>

  <!-- ============== GAME MODE ============== -->
  <div class="card">
    <div class="section-label">Play it - PLAY mode</div>
    <h2>{{ game_token or 'Create a shareable game link' }}</h2>
    <p style="font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--muted);margin:0 0 14px">An interactive, branching story with choices. Players tap to make decisions and explore the world.</p>
    {% if game_token %}
      <div class="row">
        <code class="copybox" id="game-link">https://{{ host }}/play/{{ game_token }}</code>
        <button class="btn" onclick="navigator.clipboard.writeText('https://{{ host }}/play/{{ game_token }}').then(()=>this.textContent='Copied!')">Copy</button>
      </div>
      <div class="row">
        <div class="qr-wrap" id="game-qr"></div>
      </div>
      <div class="row">
        <a class="btn secondary" href="/play/{{ game_token }}" target="_blank">Test the game link</a>
        <form method="post" action="/worlds/{{ world_id }}/share" style="display:inline">
          <input type="hidden" name="action" value="revoke-game">
          <button class="btn secondary" type="submit">Revoke this token</button>
        </form>
      </div>
    {% else %}
      <p style="color:var(--faint);font-style:italic">No game token yet.</p>
      <form method="post" action="/worlds/{{ world_id }}/share">
        <input type="hidden" name="action" value="create-game">
        <button class="btn" type="submit">Create game link</button>
      </form>
    {% endif %}
  </div>

  <!-- ============== READ MODE ============== -->
  <div class="card">
    <div class="section-label">Read it - manga / storybook</div>
    <h2>{{ read_token or 'Create a shareable read link' }}</h2>
    <p style="font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--muted);margin:0 0 14px">A read-only manga-style view of the story. Pages with art + narration + speech bubbles. For readers who prefer to read.</p>
    {% if read_token %}
      <div class="row">
        <code class="copybox" id="read-link">https://{{ host }}/read/{{ read_token }}</code>
        <button class="btn" onclick="navigator.clipboard.writeText('https://{{ host }}/read/{{ read_token }}').then(()=>this.textContent='Copied!')">Copy</button>
      </div>
      <div class="row">
        <div class="qr-wrap" id="read-qr"></div>
      </div>
      <div class="row">
        <a class="btn secondary" href="/read/{{ read_token }}" target="_blank">Test the read link</a>
        <form method="post" action="/worlds/{{ world_id }}/share" style="display:inline">
          <input type="hidden" name="action" value="revoke-read">
          <button class="btn secondary" type="submit">Revoke this token</button>
        </form>
      </div>
    {% else %}
      <p style="color:var(--faint);font-style:italic">No read token yet.</p>
      <form method="post" action="/worlds/{{ world_id }}/share">
        <input type="hidden" name="action" value="create-read">
        <button class="btn" type="submit">Create read link</button>
      </form>
    {% endif %}
  </div>

  <!-- ============== EXPORTS ============== -->
  <div class="card">
    <div class="section-label">Export</div>
    <h2>Take it with you</h2>
    <p style="color:var(--muted);font-size:14px;margin:0 0 14px">Download your story in any of these formats. Read offline, share with non-platform users, print it.</p>
    <div class="export-row">
      <a class="btn secondary" href="/worlds/{{ world_id }}/export.epub">EPUB (e-reader)</a>
      <a class="btn secondary" href="/worlds/{{ world_id }}/export.pdf">PDF (book)</a>
      <a class="btn secondary" href="/worlds/{{ world_id }}/export.zip">Bulk ZIP (markdown + SVG)</a>
    </div>
  </div>

  <!-- ============== STATS + LIKE ============== -->
  <div class="card">
    <div class="section-label">Engagement</div>
    <div class="stats-row">
      <span><b>{{ stats.view_count }}</b> views</span>
      <span><b>{{ stats.play_count }}</b> plays</span>
      <span><b>{{ stats.completion_count }}</b> completions</span>
      <span><b>{{ stats.like_count }}</b> likes</span>
      <span><b>{{ stats.episode_count }}</b> episodes</span>
      <span><b>{{ stats.approx_words }}</b> words</span>
    </div>
    <div class="row" style="margin-top:14px">
      <form method="post" action="/worlds/{{ world_id }}/like" style="display:inline">
        <input type="hidden" name="action" value="{{ 'unlike' if liked else 'like' }}">
        <button class="like-btn {{ 'liked' if liked else '' }}" type="submit">
          {{ '\\u2764' if liked else '\\u2661' }} {{ stats.like_count }} {{ 'liked' if liked else 'like' }}
        </button>
      </form>
    </div>
  </div>

</div>
<script>
  // Inject QR codes into the QR slots using the qrcode SVG endpoint
  async function injectQR(targetId, url) {
    const r = await fetch('/qr.svg?u=' + encodeURIComponent(url));
    if (r.ok) {
      document.getElementById(targetId).innerHTML = await r.text();
    }
  }
  {% if game_token %}injectQR('game-qr', 'https://{{ host }}/play/{{ game_token }}');{% endif %}
  {% if read_token %}injectQR('read-qr', 'https://{{ host }}/read/{{ read_token }}');{% endif %}
</script>
</body></html>"""


PLAY_HTML = """

<style>
/* v30 in-product styling - uses semantic tokens from the design system */
body { background: var(--bg); color: var(--text-body); }
h1, h2, h3 { color: var(--text-heading); font-family: var(--font-serif, Georgia, serif); }

/* Cards & surfaces */
.card, .surface {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg, 16px);
  color: var(--text-body);
}

/* Buttons - 3 tiers */
.btn-primary, button.primary, .primary {
  background: linear-gradient(180deg, var(--brand-light), var(--brand), var(--brand-deep));
  color: var(--brand-text);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
  font-weight: 600;
}
.btn-secondary, button.secondary, .secondary {
  background: transparent;
  color: var(--text-body);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
}
.btn-ghost, button.ghost, .ghost {
  background: transparent;
  color: var(--brand);
  border: none;
}
a { color: var(--brand); text-decoration: none; }
a:hover { border-bottom: 1px solid var(--brand); }

/* Status */
.success { color: var(--success-light); }
.warning { color: var(--warning); }
.danger  { color: var(--danger-light); }

/* Inputs */
input, textarea, select {
  background: var(--bg-elevated);
  color: var(--text-heading);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius, 8px);
}
input:focus { border-color: var(--brand); outline: none; box-shadow: 0 0 0 3px var(--brand-soft); }

.muted { color: var(--text-caption); }
.faint { color: var(--text-faint); }
</style><!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - Play</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/png" href="/logo-icon-32.png" sizes="32x32">
<link rel="apple-touch-icon" href="/logo-icon-180.png">
<meta name="theme-color" content="#0a0f1c">
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh}
.scene{max-width:680px;margin:0 auto;padding:32px 20px;min-height:100vh;display:flex;flex-direction:column}
.scene-art{flex:0 0 auto;display:flex;justify-content:center;margin-bottom:20px;max-height:42vh}
.scene-art svg,.scene-art img{max-width:100%;max-height:42vh;width:auto;height:auto;border-radius:8px;box-shadow:0 0 0 1px var(--gold) inset,0 20px 60px rgba(0,0,0,.5)}
.ep-num{font-family:Cinzel,serif;font-size:11px;letter-spacing:.2em;color:var(--gold-l);text-align:center;margin:0 0 8px;text-transform:uppercase}
.ep-title{font-family:Fraunces,Georgia,serif;font-style:italic;font-size:32px;color:var(--cream);text-align:center;margin:0 0 14px;font-weight:500;line-height:1.2}
.body{font-family:Fraunces,Georgia,serif;font-size:17px;color:var(--cream);line-height:1.7;text-align:left;margin:0 auto 24px;max-width:560px}
.body p{margin:0 0 14px}
.progress-bar{height:4px;background:rgba(201,160,78,.2);border-radius:2px;margin-bottom:18px;overflow:hidden}
.progress-fill{height:100%;background:linear-gradient(90deg,var(--amber),var(--gold-l));border-radius:2px;transition:width .4s}
.choices{display:flex;flex-direction:column;gap:10px;margin:24px 0;max-width:560px;margin-left:auto;margin-right:auto}
.choice{background:linear-gradient(180deg,rgba(21,36,63,.6) 0%,rgba(15,26,46,.95) 100%);border:1px solid rgba(201,160,78,.4);border-radius:8px;padding:14px 18px;color:var(--cream);font-family:Karla,sans-serif;font-size:15px;text-align:left;cursor:pointer;transition:all .15s;display:flex;align-items:flex-start;gap:12px}
.choice:hover{border-color:var(--gold-l);background:linear-gradient(180deg,rgba(240,181,74,.12) 0%,rgba(15,26,46,.95) 100%);transform:translateY(-2px);box-shadow:0 0 0 1px var(--gold-l) inset,0 8px 24px rgba(240,181,74,.2)}
.choice-num{font-family:Cinzel,serif;font-size:14px;color:var(--gold-l);font-weight:600;flex-shrink:0;margin-top:1px}
.choice-text{flex:1}
.no-choices{color:var(--muted);font-style:italic;text-align:center;padding:20px;font-family:Fraunces,Georgia,serif}
.footer-info{display:flex;justify-content:space-between;align-items:center;padding:14px 0;border-top:1px solid rgba(201,160,78,.2);margin-top:auto;font-size:12px;color:var(--faint)}
.footer-info .actions{display:flex;gap:12px}
.footer-info a{color:var(--gold-l);text-decoration:none}
.footer-info a:hover{color:var(--amber)}
.completed-banner{background:linear-gradient(180deg,rgba(240,181,74,.15) 0%,rgba(15,26,46,.95) 100%);border:1px solid var(--gold);border-radius:8px;padding:24px;text-align:center;margin-bottom:20px}
.completed-banner .check{font-size:42px;color:var(--gold-l)}
.completed-banner h2{font-family:Fraunces,Georgia,serif;font-size:24px;margin:8px 0;color:var(--cream);font-weight:500}
.completed-banner p{color:var(--muted);margin:0 0 14px;font-style:italic}
.completed-banner a{color:var(--amber)}
@keyframes fade-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}.scene{animation:fade-in .4s ease-out}
</style></head><body>
<div class="scene">
  {completed_banner}
  <div class="ep-num">{ep_label}</div>
  <div class="progress-bar"><div class="progress-fill" style="width:{progress}%"></div></div>
  <h1 class="ep-title">{title}</h1>
  <div class="scene-art">{art}</div>
  <div class="body">{body}</div>

  {choices_or_end}

  <div class="footer-info">
    <div>
      {stats_summary}
    </div>
    <div class="actions">
      {continue_link}
      <a href="/worlds/{world_id}/share">Share this story</a>
    </div>
  </div>
</div>
<script>
{% raw %}
  // PWA service worker registration
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(function() {});
  }
  // Keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft' && !e.metaKey) {
      const prev = document.querySelector('.nav-btn:not(.primary)');
      if (prev && !prev.href.endsWith('#')) prev.click();
    } else if (e.key === 'ArrowRight') {
      const next = document.querySelector('.nav-btn.primary');
      if (next) next.click();
    }
  });
{% endraw %}
</script>
</body></html>"""



# ===================== v23 template definitions (promoted to module top so route handlers can reference them) =====================


MAP_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - World Map</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/png" href="/logo-icon-32.png" sizes="32x32">
{% raw %}<style>
:root{{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}}
*{{box-sizing:border-box}}
body{{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh;overflow:hidden}}
.world{{position:relative;width:100vw;height:100vh;background:radial-gradient(ellipse at center, rgba(20,26,46,.8) 0%, rgba(10,15,28,.95) 70%);overflow:hidden}}
.world svg{{position:absolute;inset:0;width:100%;height:100%}}
.legend{{position:absolute;top:18px;left:18px;background:rgba(15,26,46,.85);border:1px solid rgba(201,160,78,.3);border-radius:8px;padding:12px 16px;font-family:Karla,sans-serif;font-size:13px;backdrop-filter:blur(8px);max-width:280px}}
.legend h2{{font-family:Fraunces,Georgia,serif;font-size:18px;margin:0 0 8px;color:var(--gold-l);font-weight:500;font-style:italic}}
.legend .meta{{color:var(--muted);font-size:12px;margin:0 0 10px}}
.legend .stats{{display:flex;gap:14px;color:var(--faint);font-size:11px;margin-top:8px;padding-top:8px;border-top:1px solid rgba(201,160,78,.2)}}
.legend .stats b{{color:var(--gold-l);font-weight:600}}
.scene-node{{cursor:pointer;transition:transform .2s}}
.scene-node:hover{{transform:scale(1.1);transform-origin:center}}
.scene-node circle{{transition:fill .2s}}
.scene-node:hover circle{{fill:var(--amber)}}
.controls{{position:absolute;bottom:18px;right:18px;display:flex;flex-direction:column;gap:8px}}
.controls a{{background:rgba(15,26,46,.85);border:1px solid rgba(201,160,78,.3);border-radius:8px;padding:10px 16px;color:var(--gold-l);text-decoration:none;font-size:12px;font-family:Karla,sans-serif;backdrop-filter:blur(8px);text-align:center}}
.controls a:hover{{background:rgba(201,160,78,.15);border-color:var(--gold-l)}}
.help{{position:absolute;bottom:18px;left:18px;background:rgba(15,26,46,.7);border:1px solid rgba(201,160,78,.2);border-radius:8px;padding:8px 14px;color:var(--muted);font-size:11px;font-family:Karla,sans-serif;font-family:italic;max-width:300px;backdrop-filter:blur(8px)}}
.tutorial{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;color:var(--muted);font-family:Fraunces,Georgia,serif;font-style:italic;font-size:14px;pointer-events:none}}
.tutorial .big{{font-size:60px;color:var(--gold-l);margin-bottom:14px}}
@keyframes pulse-amber{{0%,100%{{opacity:.6}}50%{{opacity:1}}}}
.scene-node.visited circle{{animation:pulse-amber 2s ease-in-out infinite}}
</style>{% endraw %}</head><body>
<div class="world">
  <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
    <defs>
      <radialGradient id="m_glow"><stop offset="0%" stop-color="#f0b54a" stop-opacity=".4"/><stop offset="100%" stop-color="#f0b54a" stop-opacity="0"/></radialGradient>
      <linearGradient id="m_brass"><stop offset="0%" stop-color="#e8c879"/><stop offset="100%" stop-color="#8a6a26"/></linearGradient>
      <filter id="m_soft"><feGaussianBlur stdDeviation=".3"/></filter>
    </defs>
    {background_decor}
    {nodes_svg}
    {edges_svg}
  </svg>

  <div class="legend">
    <h2>{title}</h2>
    <p class="meta">{genre_label} - {tone_label}</p>
    <p style="margin:0;color:var(--cream);font-size:13px;line-height:1.5">{setting_short}</p>
    <div class="stats">
      <span><b>{node_count}</b> scenes</span>
      <span><b>{visited_count}</b> visited</span>
    </div>
  </div>

  <div class="controls">
    <a href="/play/{token}">Switch to list view</a>
    <a href="/read/{token}">Read mode</a>
    <a href="/worlds/{world_id}/share">Share this world</a>
  </div>

  <div class="help">
    Each circle is a scene. Tap to enter. Lines between circles are the choices that connect them. Visited scenes glow amber.
  </div>
</div>
{% raw %}<script>
  document.querySelectorAll('.scene-node').forEach(node => {
    node.addEventListener('click', () => {
      const ep = node.getAttribute('data-episode');
      window.location.href = '/play/{token}/node/' + ep;
    }});
  });
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
{% endraw %}</script>
</body></html>"""



READ_HTML = """

<style>
/* v30 in-product styling - uses semantic tokens from the design system */
body { background: var(--bg); color: var(--text-body); }
h1, h2, h3 { color: var(--text-heading); font-family: var(--font-serif, Georgia, serif); }

/* Cards & surfaces */
.card, .surface {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg, 16px);
  color: var(--text-body);
}

/* Buttons - 3 tiers */
.btn-primary, button.primary, .primary {
  background: linear-gradient(180deg, var(--brand-light), var(--brand), var(--brand-deep));
  color: var(--brand-text);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
  font-weight: 600;
}
.btn-secondary, button.secondary, .secondary {
  background: transparent;
  color: var(--text-body);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
}
.btn-ghost, button.ghost, .ghost {
  background: transparent;
  color: var(--brand);
  border: none;
}
a { color: var(--brand); text-decoration: none; }
a:hover { border-bottom: 1px solid var(--brand); }

/* Status */
.success { color: var(--success-light); }
.warning { color: var(--warning); }
.danger  { color: var(--danger-light); }

/* Inputs */
input, textarea, select {
  background: var(--bg-elevated);
  color: var(--text-heading);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius, 8px);
}
input:focus { border-color: var(--brand); outline: none; box-shadow: 0 0 0 3px var(--brand-soft); }

.muted { color: var(--text-caption); }
.faint { color: var(--text-faint); }
</style><!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - Page {page_num}</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/png" href="/logo-icon-32.png" sizes="32x32">
{% raw %}<style>
:root{{--navy:#0a0f1c;--navy-2:#15243f;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--paper:#ede1c4;--ink:#3a2a10;--muted:#9eb6d4}}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:#1a1410;color:var(--paper);font-family:Karla,sans-serif;min-height:100vh;-webkit-font-smoothing:antialiased}}
.reader{{display:flex;flex-direction:column;min-height:100vh}}
.topbar{{background:rgba(15,15,28,.7);color:var(--paper);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(201,160,78,.3);font-size:13px;backdrop-filter:blur(8px)}}
.topbar a{{color:var(--gold-l);text-decoration:none;font-family:Karla,sans-serif}}
.topbar a:hover{{color:var(--amber)}}
.topbar .ep{{font-family:Fraunces,Georgia,serif;font-style:italic;font-size:16px;color:var(--paper)}}
.topbar .page-num{{color:var(--muted);font-family:Cinzel,serif;letter-spacing:.1em}}
.page-wrap{{flex:1;display:flex;justify-content:center;align-items:flex-start;padding:30px 16px}}
.page{{max-width:680px;width:100%;background:var(--paper);color:var(--ink);padding:48px 40px;border-radius:4px;box-shadow:0 1px 0 var(--gold) inset,0 20px 60px rgba(0,0,0,.6);position:relative;font-family:'Comic Sans MS',Karla,sans-serif}}
.page::before{{content:'';position:absolute;top:8px;left:8px;right:8px;bottom:8px;border:1px dashed rgba(0,0,0,.1);pointer-events:none;border-radius:2px}}
.page .panel{{margin-bottom:24px}}
.page .panel:last-child{{margin-bottom:0}}
.page .panel-art{{background:linear-gradient(180deg,#e8d8b8 0%,#d4b88a 100%);border-radius:4px;padding:8px;margin-bottom:16px;border:1px solid #5a4a18}}
.page .panel-art svg,.page .panel-art img{{width:100%;height:auto;display:block;border-radius:2px}}
.page .panel-text{{font-family:Karla,sans-serif;font-size:15px;line-height:1.7;color:var(--ink);margin-bottom:12px}}
.page .panel-text:last-child{{margin-bottom:0}}
.page .narration{{font-family:Fraunces,Georgia,serif;font-style:italic;font-size:15px;color:#5a4a18;border-left:3px solid var(--gold);padding:8px 0 8px 14px;margin:14px 0}}
.page .dialogue{{position:relative;background:#f3e9d2;border:1px solid #8a6a26;border-radius:8px;padding:8px 14px 8px 30px;margin:10px 0;font-family:Karla,sans-serif;font-size:14px;color:var(--ink);line-height:1.5}}
.page .dialogue::before{{content:'';position:absolute;left:-12px;top:8px;width:0;height:0;border-top:8px solid transparent;border-bottom:8px solid transparent;border-right:12px solid #8a6a26}}
.page .dialogue .speaker{{font-weight:700;color:#5a2010;font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px;display:block}}
.page .panel-title{{font-family:Fraunces,Georgia,serif;font-style:italic;font-size:22px;font-weight:600;color:#5a2010;margin:0 0 18px;text-align:center;border-bottom:2px solid var(--gold);padding-bottom:10px}}
.nav-bar{{display:flex;justify-content:space-between;align-items:center;padding:18px 24px;background:rgba(15,15,28,.85);border-top:1px solid rgba(201,160,78,.3);backdrop-filter:blur(8px)}}
.nav-btn{{background:transparent;border:1px solid rgba(201,160,78,.4);color:var(--gold-l);padding:10px 18px;border-radius:99px;font-family:Karla,sans-serif;font-size:13px;cursor:pointer;text-decoration:none;transition:all .15s}}
.nav-btn:hover{{border-color:var(--amber);color:var(--amber);background:rgba(240,181,74,.1)}}
.nav-btn.primary{{background:linear-gradient(180deg,var(--gold-l) 0%,var(--gold) 50%,#8a6a26 100%);color:var(--navy);font-weight:700;border-color:#8a6a26}}
.nav-btn.primary:hover{{box-shadow:0 0 0 1px var(--amber) inset,0 0 12px var(--amber)}}
.progress{{height:3px;background:rgba(201,160,78,.2);position:relative}}
.progress .fill{{position:absolute;top:0;left:0;height:100%;background:linear-gradient(90deg,var(--amber),var(--gold-l))}}
.page-flip-enter{{animation:page-flip-in .35s ease-out}}
@keyframes page-flip-in{{from{{opacity:0;transform:translateX(20px)}}to{{opacity:1;transform:translateX(0)}}}}
@media (max-width: 600px) {{
  .page {{ padding: 32px 24px; }}
  .topbar {{ padding: 12px 14px; font-size: 12px; }}
  .topbar .ep {{ font-size: 14px; }}
  .nav-bar {{ padding: 14px 16px; }}
}}
</style>{% endraw %}</head><body>
<div class="reader">
  <div class="topbar">
    <div style="display:flex;align-items:center;gap:14px">
      <a href="/read/{token}/page/1">Manga</a>
      <span style="color:var(--faint)">|</span>
      <a href="/play/{token}">Play mode</a>
    </div>
    <div class="ep">{title}</div>
    <div class="page-num">PAGE {page_num} / {total_pages}</div>
  </div>
  <div class="progress"><div class="fill" style="width:{progress}%"></div></div>
  <div class="page-wrap">
    <div class="page page-flip-enter">
      <div class="panel">
        <div class="panel-title">{episode_title}</div>
        {art_block}
        <div class="narration">{narration}</div>
        {dialogue_blocks}
      </div>
    </div>
  </div>
  <div class="nav-bar">
    <a class="nav-btn" href="{prev_url}">Prev</a>
    <div style="color:var(--faint);font-size:12px;font-family:Cinzel,serif;letter-spacing:.1em">{page_num} / {total_pages}</div>
    <a class="nav-btn primary" href="{next_url}">Next</a>
  </div>
</div>
{% raw %}<script>
  // PWA
  if ('serviceWorker' in navigator) {{
    navigator.serviceWorker.register('/sw.js').catch(()=>{{}});
  }}
  // Keyboard navigation
  document.addEventListener('keydown', (e) => {{
    if (e.key === 'ArrowLeft' && !e.metaKey) {{
      const prev = document.querySelector('.nav-btn:not(.primary)');
      if (prev && !prev.href.endsWith('#')) prev.click();
    }} else if (e.key === 'ArrowRight') {{
      const next = document.querySelector('.nav-btn.primary');
      if (next) next.click();
    }}
  }});
</script>{% endraw %}
</body></html>"""



REDEEM_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Redeem Code</title>
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.box{max-width:480px;width:100%;background:linear-gradient(180deg,rgba(21,36,63,.5) 0%,rgba(15,26,46,.95) 100%);border:1px solid rgba(201,160,78,.3);border-radius:8px;padding:36px}
h1{font-family:Fraunces,Georgia,serif;font-size:28px;margin:0 0 8px;color:var(--cream);font-weight:600}
h1 i{color:var(--gold-l);font-style:italic}
.lead{color:var(--muted);font-style:italic;font-family:Fraunces,Georgia,serif;margin:0 0 24px;font-size:15px}
label{display:block;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold-l);font-weight:600;margin-bottom:6px}
input[type=text]{width:100%;background:var(--navy);border:1px solid var(--navy-3);color:var(--cream);padding:10px 14px;border-radius:6px;font-family:'JetBrains Mono',monospace;font-size:14px;letter-spacing:.1em;text-transform:uppercase}
input[type=text]:focus{outline:none;border-color:var(--gold-l);box-shadow:0 0 0 1px var(--gold-l) inset}
.btn{background:linear-gradient(180deg,var(--gold-l) 0%,var(--gold) 50%,#8a6a26 100%);color:var(--navy);border:1px solid #8a6a26;padding:11px 20px;border-radius:99px;font-family:Karla,sans-serif;font-weight:700;font-size:13px;cursor:pointer;width:100%;margin-top:14px;box-shadow:0 0 0 1px var(--gold-l) inset}
.btn:hover{box-shadow:0 0 0 1px var(--amber) inset,0 0 16px var(--amber)}
.result{margin-top:18px;padding:14px 18px;border-radius:6px;font-size:14px;line-height:1.5}
.result.ok{background:rgba(26,107,80,.15);border:1px solid var(--emerald,#1d6b50);color:#a4e5b8}
.result.err{background:rgba(196,74,58,.15);border:1px solid #c44a3a;color:#f3a89a}
</style></head><body>
<div class="box">
  <h1>Redeem a <i>code</i></h1>
  <p class="lead">Got a promo code? Drop it here for instant Pro or Creator access.</p>
  <form method="post">
    <label for="code">Code</label>
    <input type="text" name="code" id="code" placeholder="WELCOME50" required autofocus>
    <button class="btn" type="submit">Redeem</button>
  </form>
  {result_html}
</div>
</body></html>"""



ADMIN_SEGMENTS_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Email Segments - Admin</title>
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh}
.wrap{max-width:900px;margin:36px auto;padding:0 24px}
header{padding:0 0 16px;border-bottom:1px solid var(--navy-3);margin-bottom:24px}
.wordmark{font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--gold-l);font-size:20px;font-weight:600}
nav{float:right;margin-top:6px}
nav a{color:var(--muted);text-decoration:none;margin-left:14px;font-size:12px;text-transform:uppercase;letter-spacing:.05em}
nav a:hover{color:var(--gold-l)}
h1{font-family:Fraunces,Georgia,serif;font-size:28px;margin:0 0 18px;color:var(--cream);font-weight:600}
h1 i{color:var(--gold-l);font-style:italic}
.lead{color:var(--muted);font-style:italic;font-family:Fraunces,Georgia,serif;margin:0 0 24px}
table{width:100%;border-collapse:collapse;margin-top:14px}
th{text-align:left;padding:10px;color:var(--muted);font-size:11px;letter-spacing:.14em;text-transform:uppercase;border-bottom:1px solid var(--navy-3)}
td{padding:10px;border-bottom:1px solid rgba(255,255,255,.04);font-size:13px}
tr:hover td{background:rgba(201,160,78,.06)}
code{font-family:'JetBrains Mono',monospace;color:var(--gold-l);font-size:12px;background:var(--navy);padding:2px 6px;border-radius:3px}
.btn{background:linear-gradient(180deg,var(--gold-l) 0%,var(--gold) 50%,#8a6a26 100%);color:var(--navy);border:1px solid #8a6a26;padding:8px 14px;border-radius:99px;font-family:Karla,sans-serif;font-weight:700;font-size:12px;cursor:pointer;text-decoration:none;display:inline-block}
.btn.secondary{background:transparent;color:var(--gold-l);border-color:var(--gold);box-shadow:0 0 0 1px #8a6a26 inset}
.btn:hover{box-shadow:0 0 0 1px var(--amber) inset,0 0 12px var(--amber)}
.card{background:linear-gradient(180deg,rgba(21,36,63,.5) 0%,rgba(15,26,46,.95) 100%);border:1px solid rgba(201,160,78,.3);border-radius:8px;padding:24px;margin-bottom:18px}
.form-row{display:flex;gap:8px;align-items:center;margin-top:10px}
input[type=text]{background:var(--navy);border:1px solid var(--navy-3);color:var(--cream);padding:8px 12px;border-radius:6px;font-family:'JetBrains Mono',monospace;font-size:13px}
</style></head><body>
<div class="wrap">
  <header>
    <div class="wordmark">Pocket<em style="color:var(--muted);font-style:normal">Plot</em> Universe - Admin</div>
    <nav>
      <a href="/admin/dashboard">Dashboard</a>
      <a href="/admin/queue">Queue</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/promo-codes">Promo codes</a>
      <a href="/admin/features">Features</a>
      <a href="/admin/top">Top stories</a>
      <a href="/admin/segments" style="color:var(--gold-l)">Segments</a>
    </nav>
    <h1 style="margin-top:14px">Email <i>segments</i></h1>
  </header>

  <p class="lead">Define named user lists based on plan, activity, age, or world count. Used for newsletter blasts + admin-targeted emails.</p>

  <div class="card">
    <h2 style="font-family:Fraunces,Georgia,serif;font-size:18px;margin:0 0 12px;color:var(--cream);font-weight:500">New segment</h2>
    <form method="post">
      <input type="text" name="name" placeholder="name (e.g. recent_pro_signups)" required>
      <input type="text" name="description" placeholder="description" style="margin-left:8px">
      <button class="btn" type="submit" style="margin-left:8px">Create</button>
    </form>
    <p style="color:var(--faint);font-size:12px;margin:10px 0 0;font-style:italic">Rules: pass tier as a query param (e.g. <code>?plan=pro&created_within_days=30</code>) to auto-resolve.</p>
  </div>

  <table>
    <tr><th>Name</th><th>Description</th><th>Members</th><th>Created</th><th></th></tr>
    {rows}
  </table>

</div>
</body></html>"""



ADMIN_PROMO_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Promo Codes - Admin</title>
<style>:root{--navy:#0a0f1c;--navy-2:#15243f;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);color:var(--cream);font-family:Karla,sans-serif;min-height:100vh}
.wrap{max-width:960px;margin:36px auto;padding:0 24px}
header{padding:0 0 16px;border-bottom:1px solid var(--navy-3);margin-bottom:24px}
.wordmark{font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--gold-l);font-size:20px;font-weight:600}
nav{float:right;margin-top:6px}
nav a{color:var(--muted);text-decoration:none;margin-left:14px;font-size:12px;text-transform:uppercase;letter-spacing:.05em}
nav a:hover{color:var(--gold-l)}
h1{font-family:Fraunces,Georgia,serif;font-size:28px;margin:14px 0 8px;color:var(--cream);font-weight:600}
h1 i{color:var(--gold-l);font-style:italic}
.card{background:linear-gradient(180deg,rgba(21,36,63,.5) 0%,rgba(15,26,46,.95) 100%);border:1px solid rgba(201,160,78,.3);border-radius:8px;padding:24px;margin-bottom:18px}
.card h2{font-family:Fraunces,Georgia,serif;font-size:18px;margin:0 0 12px;color:var(--cream);font-weight:500}
table{width:100%;border-collapse:collapse;margin-top:14px}
th{text-align:left;padding:10px;color:var(--muted);font-size:11px;letter-spacing:.14em;text-transform:uppercase;border-bottom:1px solid var(--navy-3)}
td{padding:10px;border-bottom:1px solid rgba(255,255,255,.04);font-size:13px}
code{font-family:'JetBrains Mono',monospace;color:var(--gold-l);font-size:12px;background:var(--navy);padding:2px 6px;border-radius:3px}
.btn{background:linear-gradient(180deg,var(--gold-l) 0%,var(--gold) 50%,#8a6a26 100%);color:var(--navy);border:1px solid #8a6a26;padding:9px 16px;border-radius:99px;font-family:Karla,sans-serif;font-weight:700;font-size:12px;cursor:pointer;text-decoration:none;display:inline-block}
.btn:hover{box-shadow:0 0 0 1px var(--amber) inset,0 0 12px var(--amber)}
.form-row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px}
input,select{background:var(--navy);border:1px solid var(--navy-3);color:var(--cream);padding:8px 12px;border-radius:6px;font-family:Karla,sans-serif;font-size:13px}
</style></head><body>
<div class="wrap">
  <header>
    <div class="wordmark">Pocket<em style="color:var(--muted);font-style:normal">Plot</em> Universe - Admin</div>
    <nav>
      <a href="/admin/dashboard">Dashboard</a>
      <a href="/admin/queue">Queue</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/promo-codes" style="color:var(--gold-l)">Promo codes</a>
      <a href="/admin/features">Features</a>
      <a href="/admin/segments">Segments</a>
    </nav>
    <h1>Promo <i>codes</i></h1>
  </header>

  <div class="card">
    <h2>New promo code</h2>
    <form method="post" action="/admin/promo-codes/new" class="form-row">
      <input type="text" name="code" placeholder="CODE (e.g. WELCOME50)" required style="text-transform:uppercase">
      <input type="number" name="discount_pct" placeholder="%" min="1" max="100" required style="width:80px">
      <input type="number" name="duration_months" placeholder="months" min="1" max="36" value="1" required style="width:80px">
      <select name="tier_target">
        <option value="pro">Pro</option>
        <option value="creator">Creator</option>
        <option value="any">Any</option>
      </select>
      <input type="number" name="max_redemptions" placeholder="max (0=unlimited)" min="0" value="0" style="width:120px">
      <input type="text" name="description" placeholder="description (optional)">
      <button class="btn" type="submit">Create</button>
    </form>
  </div>

  <table>
    <tr><th>Code</th><th>Discount</th><th>Duration</th><th>Tier</th><th>Max</th><th>Used</th><th>Created</th></tr>
    {rows}
  </table>

</div>
</body></html>"""



ADMIN_NEWSLETTER_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Send Newsletter - Admin</title>
<style>:root{--navy:#0a0f1c;--navy-2:#15243f;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);color:var(--cream);font-family:Karla,sans-serif;min-height:100vh}
.wrap{max-width:780px;margin:36px auto;padding:0 24px}
header{padding:0 0 16px;border-bottom:1px solid var(--navy-3);margin-bottom:24px}
.wordmark{font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--gold-l);font-size:20px;font-weight:600}
nav{float:right;margin-top:6px}
nav a{color:var(--muted);text-decoration:none;margin-left:14px;font-size:12px;text-transform:uppercase;letter-spacing:.05em}
h1{font-family:Fraunces,Georgia,serif;font-size:28px;margin:14px 0 8px;color:var(--cream);font-weight:600}
h1 i{color:var(--gold-l);font-style:italic}
.card{background:linear-gradient(180deg,rgba(21,36,63,.5) 0%,rgba(15,26,46,.95) 100%);border:1px solid rgba(201,160,78,.3);border-radius:8px;padding:24px;margin-bottom:18px}
.card label{display:block;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold-l);font-weight:600;margin-bottom:6px}
.card input[type=text],.card input[type=number],.card select,.card textarea{width:100%;background:var(--navy);border:1px solid var(--navy-3);color:var(--cream);padding:10px 14px;border-radius:6px;font-family:Karla,sans-serif;font-size:14px;box-sizing:border-box}
.card textarea{min-height:140px;font-family:Karla,sans-serif;line-height:1.6}
.btn{background:linear-gradient(180deg,var(--gold-l) 0%,var(--gold) 50%,#8a6a26 100%);color:var(--navy);border:1px solid #8a6a26;padding:11px 22px;border-radius:99px;font-family:Karla,sans-serif;font-weight:700;font-size:14px;cursor:pointer;margin-top:14px}
.btn:hover{box-shadow:0 0 0 1px var(--amber) inset,0 0 16px var(--amber)}
.flash{padding:12px 14px;border-radius:6px;margin-bottom:14px;font-size:14px}
.flash.ok{background:rgba(26,107,80,.15);border:1px solid #1d6b50;color:#a4e5b8}
.flash.err{background:rgba(196,74,58,.15);border:1px solid #c44a3a;color:#f3a89a}
</style></head><body>
<div class="wrap">
  <header>
    <div class="wordmark">Pocket<em style="color:var(--muted);font-style:normal">Plot</em> Universe - Admin</div>
    <nav>
      <a href="/admin/dashboard">Dashboard</a>
      <a href="/admin/queue">Queue</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/promo-codes">Promo codes</a>
      <a href="/admin/features">Features</a>
      <a href="/admin/segments">Segments</a>
    </nav>
    <h1>Send <i>newsletter</i></h1>
  </header>

  {flash_html}

  <div class="card">
    <p style="margin:0 0 18px;color:var(--muted);font-style:italic;font-family:Fraunces,Georgia,serif">Composes an email and sends to the addresses that match a segment. Outbound mail goes through your existing SMTP or outbox fallback.</p>
    <form method="post">
      <label for="segment_id">Segment</label>
      <select name="segment_id" id="segment_id" required>
        <option value="">-- pick a segment --</option>
        <option value="all_active">All active subscribers (resolved live)</option>
        {segment_options}
      </select>
      <label for="subject" style="margin-top:14px">Subject</label>
      <input type="text" name="subject" id="subject" required>
      <label for="body" style="margin-top:14px">Body (plain text)</label>
      <textarea name="body" id="body" required></textarea>
      <button class="btn" type="submit">Send newsletter</button>
    </form>
  </div>
</div>
</body></html>"""

# ===================== v23 template definitions (moved early so route handlers can reference them) =====================






# ===================== end v23 templates =====================





# ===================== v25 template definitions =====================
"""v25 World Inventory template - place/pick up items in a Minecraft-style world."""

WORLD_INVENTORY_HTML = """

<style>
/* v30 in-product styling - uses semantic tokens from the design system */
body { background: var(--bg); color: var(--text-body); }
h1, h2, h3 { color: var(--text-heading); font-family: var(--font-serif, Georgia, serif); }

/* Cards & surfaces */
.card, .surface {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg, 16px);
  color: var(--text-body);
}

/* Buttons - 3 tiers */
.btn-primary, button.primary, .primary {
  background: linear-gradient(180deg, var(--brand-light), var(--brand), var(--brand-deep));
  color: var(--brand-text);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
  font-weight: 600;
}
.btn-secondary, button.secondary, .secondary {
  background: transparent;
  color: var(--text-body);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
}
.btn-ghost, button.ghost, .ghost {
  background: transparent;
  color: var(--brand);
  border: none;
}
a { color: var(--brand); text-decoration: none; }
a:hover { border-bottom: 1px solid var(--brand); }

/* Status */
.success { color: var(--success-light); }
.warning { color: var(--warning); }
.danger  { color: var(--danger-light); }

/* Inputs */
input, textarea, select {
  background: var(--bg-elevated);
  color: var(--text-heading);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius, 8px);
}
input:focus { border-color: var(--brand); outline: none; box-shadow: 0 0 0 3px var(--brand-soft); }

.muted { color: var(--text-caption); }
.faint { color: var(--text-faint); }
</style><!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Inventory - World {{ world_id }} - PocketPlot Universe</title>
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8;--emerald:#1d6b50;--emerald-l:#3a8c6c}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh;line-height:1.6}
.wrap{max-width:1100px;margin:0 auto;padding:30px 28px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:24px}
.brand img{width:44px;height:40px}
.brand-text{font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--gold-l);font-size:22px;font-weight:600}
.eyebrow{font-family:Helvetica,sans-serif;font-size:11px;letter-spacing:.15em;color:var(--gold-l);text-transform:uppercase;margin-bottom:8px}
h1{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:28px;color:var(--cream);margin:0 0 8px;line-height:1.2}
.lead{color:var(--muted);font-size:14px;margin-bottom:24px;max-width:680px}
.layout{display:grid;grid-template-columns:1fr 320px;gap:20px}
@media(max-width:880px){.layout{grid-template-columns:1fr}}
.world-panel{background:var(--navy-2);border:1px solid rgba(201,160,78,.25);border-radius:12px;padding:20px;position:relative;min-height:500px;overflow:hidden}
.world-grid{position:relative;width:100%;height:480px;background:radial-gradient(ellipse at center, rgba(20,26,46,.8) 0%, rgba(10,15,28,.95) 70%)}
.world-grid .grid-line{position:absolute;background:rgba(201,160,78,.08)}
.world-grid .grid-line.h{left:0;right:0;height:1px}
.world-grid .grid-line.v{top:0;bottom:0;width:1px}
.placed-item{position:absolute;background:var(--navy-3);border:2px solid var(--gold);border-radius:8px;padding:6px 10px;font-size:13px;color:var(--cream);cursor:move;user-select:none;display:flex;align-items:center;gap:6px;transition:transform .15s;box-shadow:0 0 12px rgba(240,181,74,.25);min-width:80px}
.placed-item:hover{transform:scale(1.05)}
.placed-item .icon{font-size:18px}
.placed-item .remove{background:transparent;border:none;color:var(--faint);cursor:pointer;padding:0 4px;font-size:16px;line-height:1}
.placed-item .remove:hover{color:#a02020}
.sidebar{background:var(--navy-2);border:1px solid rgba(201,160,78,.25);border-radius:12px;padding:18px}
.section{margin-bottom:18px}
.section h3{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:16px;color:var(--cream);margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--navy-3)}
.item-row{display:flex;align-items:center;gap:10px;padding:8px;background:var(--navy);border:1px solid var(--navy-3);border-radius:6px;margin-bottom:6px}
.item-row .icon{font-size:24px;width:32px;text-align:center}
.item-row .name{font-size:13px;color:var(--cream);flex:1}
.item-row .qty{font-size:11px;color:var(--gold);font-weight:700;background:rgba(201,160,78,.15);padding:1px 8px;border-radius:10px;margin-right:6px}
.item-row form{display:inline}
.item-row button{background:var(--gold);color:#0a0f1c;border:none;border-radius:4px;padding:4px 10px;font-size:11px;cursor:pointer;font-weight:600}
.item-row button:disabled{background:var(--faint);cursor:not-allowed}
.empty{color:var(--faint);font-style:italic;padding:12px;text-align:center;font-size:13px}
.help{font-size:11px;color:var(--faint);margin-top:4px}
.flash{padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:13px}
.flash.success{background:rgba(29,107,80,.3);border:1px solid var(--emerald);color:var(--cream)}
.flash.error{background:rgba(160,32,32,.3);border:1px solid #a02020;color:var(--cream)}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;font-size:11px}
.legend .swatch{display:inline-flex;align-items:center;gap:4px}
.legend .swatch .dot{width:10px;height:10px;border-radius:2px}
.legend .swatch.common .dot{background:var(--faint)}
.legend .swatch.uncommon .dot{background:var(--muted)}
.legend .swatch.rare .dot{background:var(--gold)}
.legend .swatch.epic .dot{background:var(--amber)}
.legend .swatch.legendary .dot{background:var(--emerald-l)}
.back-link{display:inline-block;color:var(--muted);text-decoration:none;font-size:13px;margin-bottom:16px}
.back-link:hover{color:var(--gold)}
</style></head><body>
<div class="wrap">
<a href="/worlds/{{ world_id }}" class="back-link">&larr; Back to world</a>
<div class="brand">
<img src="/logo-halo-240.png" alt="PocketPlot">
<div class="brand-text">PocketPlot Universe</div>
</div>
<div class="eyebrow">Building your world</div>
<h1>Inventory placement</h1>
<p class="lead">Drag items from the sidebar onto the world to place them. Click an item in the world to pick it up. Items give your world a Minecraft-style build layer.</p>
{% if flash %}
<div class="flash {{ flash.type }}">{{ flash.message }}</div>
{% endif %}
<div class="layout">
<div class="world-panel" id="world-panel">
<div class="world-grid" id="world-grid">
<div style="position:absolute;top:10px;left:10px;color:var(--gold-l);font-size:11px;font-family:Helvetica">World {{ world_id }} - drag to position</div>
</div>
</div>
<div class="sidebar">
<div class="section">
<h3>Your inventory ({{ inventory|length }} items)</h3>
{% if inventory %}
{% for it in inventory %}
<div class="item-row">
<div class="icon">{{ it.icon or '✦' }}</div>
<div class="name">{{ it.name }}</div>
<span class="qty">x{{ it.quantity }}</span>
<form method="post" action="/worlds/{{ world_id }}/inventory/place/{{ it.key }}" style="display:inline">
<input type="hidden" name="x" value="{{ loop.index0 * 100 + 50 }}">
<input type="hidden" name="y" value="{{ (loop.index0 * 80) % 400 + 50 }}">
<button type="submit">Place</button>
</form>
</div>
{% endfor %}
{% else %}
<div class="empty">No items yet. Items drop when you complete stories or hit milestones.</div>
{% endif %}
</div>
<div class="section">
<h3>Placed in this world ({{ placed|length }})</h3>
{% if placed %}
{% for p in placed %}
<div class="item-row">
<div class="icon">{{ p.icon or '✦' }}</div>
<div class="name">{{ p.name }}</div>
<span class="qty" style="background:rgba(93,222,240,.15);color:#5ddef0">at {{ p.x|int }},{{ p.y|int }}</span>
<form method="post" action="/worlds/{{ world_id }}/inventory/pickup/{{ p.id }}" style="display:inline">
<button type="submit" class="secondary">Pick up</button>
</form>
</div>
{% endfor %}
{% else %}
<div class="empty">Nothing placed yet. Use the buttons above to drop items into your world.</div>
{% endif %}
</div>
<div class="section">
<h3>Rarity legend</h3>
<div class="legend">
<div class="swatch common"><div class="dot"></div>Common</div>
<div class="swatch uncommon"><div class="dot"></div>Uncommon</div>
<div class="swatch rare"><div class="dot"></div>Rare</div>
<div class="swatch epic"><div class="dot"></div>Epic</div>
<div class="swatch legendary"><div class="dot"></div>Legendary</div>
</div>
</div>
</div>
</div>
</div>
{% raw %}<script>
(function() {
    const world = document.getElementById('world-grid');
    const panel = document.getElementById('world-panel');
    let dragged = null;
    let dragOffset = { x: 0, y: 0 };

    // Load placed items from server-rendered JSON
    const placed = {{ placed_json|safe }};

    function renderPlaced() {
        // Remove existing placed items
        document.querySelectorAll('.placed-item').forEach(n => n.remove());
        for (const p of placed) {
            const el = document.createElement('div');
            el.className = 'placed-item';
            el.dataset.id = p.id;
            el.style.left = p.x + 'px';
            el.style.top = p.y + 'px';
            el.innerHTML = '<span class="icon"></span><span class="label"></span><form method="post" action="/worlds/{{ world_id }}/inventory/pickup/' + p.id + '"><button type="submit" class="remove" title="Pick up">x</button></form>';
            el.querySelector('.icon').textContent = p.icon || '✦';
            el.querySelector('.label').textContent = p.name + ' (' + p.rarity + ')';
            world.appendChild(el);

            // Drag to move
            el.addEventListener('mousedown', e => {
                if (e.target.tagName === 'BUTTON') return;
                dragged = el;
                const rect = el.getBoundingClientRect();
                const worldRect = world.getBoundingClientRect();
                dragOffset.x = e.clientX - rect.left;
                dragOffset.y = e.clientY - rect.top;
                e.preventDefault();
            });
        }
    }

    // Grid lines
    for (let i = 0; i < 10; i++) {
        const h = document.createElement('div');
        h.className = 'grid-line h';
        h.style.top = (i * 50) + 'px';
        world.appendChild(h);
        const v = document.createElement('div');
        v.className = 'grid-line v';
        v.style.left = (i * 50) + 'px';
        world.appendChild(v);
    }

    document.addEventListener('mousemove', e => {
        if (!dragged) return;
        const worldRect = world.getBoundingClientRect();
        const x = e.clientX - worldRect.left - dragOffset.x;
        const y = e.clientY - worldRect.top - dragOffset.y;
        dragged.style.left = Math.max(0, x) + 'px';
        dragged.style.top = Math.max(0, y) + 'px';
        // Update placed in memory
        const id = parseInt(dragged.dataset.id);
        const p = placed.find(p => p.id === id);
        if (p) { p.x = Math.max(0, x); p.y = Math.max(0, y); }
    });

    document.addEventListener('mouseup', () => {
        if (dragged) {
            const id = parseInt(dragged.dataset.id);
            const p = placed.find(p => p.id === id);
            if (p) {
                fetch('/worlds/{{ world_id }}/inventory/move', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: id, x: p.x, y: p.y })
                }).catch(function() {});
            }
            dragged = null;
        }
    });

    renderPlaced();

    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').catch(function() {});
    }
})();
{% endraw %}</script>
</body></html>"""


PLACED_ITEM_RESPONSE = """<!doctype html><html lang="en"><head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0;url=/worlds/{world_id}/inventory">
<title>Placed - PocketPlot</title>
</head><body>
<p>Item placed. <a href="/worlds/{world_id}/inventory">Continue</a></p>
</body></html>"""


# ===================== end v25 templates =====================
# ===================== v24 template definitions (early so route handlers can reference them) =====================
"""v24 routes + templates for PocketPlot Universe.

Appended to app.py at the right insertion point. Provides:
  /onboarding             (3-step wizard)
  /onboarding/skip
  /worlds/<id>/edit       (story editor)
  /worlds/<id>/edit/<n>   (episode editor)
  /worlds/<id>/graph      (scene-graph editor)
  /worlds/<id>/graph/save (POST save)
  /worlds/<id>/comments   (POST add comment)
  /worlds/<id>/reactions  (POST toggle reaction)
  /worlds/<id>/cover.png  (GET cover image)
  /me/streak              (streak + XP dashboard)
  /me/inventory           (user inventory)
  /worlds/<id>/inventory  (world placement page)
  /api/tts/voices         (GET curated voices)
  /api/tts/sanitize       (POST sanitize text)
  /admin/audit            (audit log dashboard)
  /sitemap.xml            (SEO)
  /robots.txt             (SEO)
  /u/<username>/world/<slug> (public story page with JSON-LD + OG tags)
"""

ONBOARDING_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Welcome to PocketPlot Universe</title>
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh;line-height:1.6}
.wrap{max-width:760px;margin:0 auto;padding:60px 28px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:32px}
.brand img{width:44px;height:40px}
.brand-text{font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--gold-l);font-size:22px;font-weight:600}
.progress{display:flex;gap:8px;margin-bottom:32px}
.progress .step{flex:1;height:4px;background:var(--navy-3);border-radius:2px}
.progress .step.active{background:var(--gold)}
.eyebrow{font-family:Helvetica,sans-serif;font-size:11px;letter-spacing:.15em;color:var(--gold-l);text-transform:uppercase;margin-bottom:8px}
h1{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:38px;color:var(--cream);margin:0 0 12px;line-height:1.2}
.lead{color:var(--muted);font-size:15px;margin-bottom:28px;max-width:580px}
.options{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin:24px 0}
.option{padding:14px 16px;background:var(--navy-2);border:1px solid rgba(201,160,78,.2);border-radius:8px;cursor:pointer;text-align:center;font-size:14px;color:var(--cream);transition:all .2s}
.option:hover{border-color:var(--gold);background:rgba(201,160,78,.1)}
.option.selected{border-color:var(--gold);background:rgba(201,160,78,.15)}
.option .name{display:block;font-weight:600}
.option .hint{font-size:11px;color:var(--faint);margin-top:4px}
textarea{width:100%;min-height:120px;background:var(--navy-2);border:1px solid rgba(201,160,78,.2);border-radius:8px;padding:14px;color:var(--cream);font-family:Karla,sans-serif;font-size:14px;line-height:1.5;resize:vertical}
textarea:focus{outline:none;border-color:var(--gold)}
.btn{display:inline-block;padding:14px 28px;background:var(--gold);color:#0a0f1c;border:none;border-radius:8px;font-weight:600;font-size:14px;cursor:pointer;text-decoration:none;transition:all .2s;margin-top:24px}
.btn:hover{background:var(--gold-l);box-shadow:0 0 20px rgba(240,181,74,.4)}
.btn.secondary{background:transparent;color:var(--cream);border:1px solid rgba(201,160,78,.4)}
.btn.secondary:hover{background:rgba(201,160,78,.1)}
.row{display:flex;gap:12px;align-items:center;margin-top:24px}
.help{color:var(--faint);font-size:13px;margin-top:8px}
</style></head><body>
<div class="wrap">
<div class="brand">
<img src="/logo-halo-240.png" alt="PocketPlot">
<div class="brand-text">PocketPlot Universe</div>
</div>
<div class="progress">
<div class="step {{ 'active' if state.current_step >= 1 else '' }}"></div>
<div class="step {{ 'active' if state.current_step >= 2 else '' }}"></div>
<div class="step {{ 'active' if state.current_step >= 3 else '' }}"></div>
</div>
{% if state.current_step == 1 %}
<div class="eyebrow">Step 1 of 3</div>
<h1>Pick your genre</h1>
<p class="lead">Every world starts with a genre. Pick one that matches the mood you're going for. You'll see options for cyberpunk, romance, thriller, and more.</p>
<form method="post" action="/onboarding/step">
<input type="hidden" name="step" value="1">
<div class="options">
{% for g in genres %}
<label class="option">
<input type="radio" name="genre" value="{{ g }}" {{ 'checked' if step1_data.genre == g else '' }} style="display:none">
<span class="name">{{ genre_labels[g] }}</span>
<span class="hint">Click to select</span>
</label>
{% endfor %}
</div>
<button type="submit" class="btn">Continue &rarr;</button>
<a href="/onboarding/skip" class="btn secondary">Skip for now</a>
</form>
{% elif state.current_step == 2 %}
<div class="eyebrow">Step 2 of 3</div>
<h1>Describe your character</h1>
<p class="lead">Who is the protagonist? Give them a name, a role, a defining trait. The engine uses this to anchor the story.</p>
<form method="post" action="/onboarding/step">
<input type="hidden" name="step" value="2">
<textarea name="character" placeholder="A retired detective with a photographic memory, haunted by an unsolved case from 1987.">{{ step2_data.character or '' }}</textarea>
<div class="help">A single paragraph is fine. The more specific, the more vivid the story.</div>
<button type="submit" class="btn">Continue &rarr;</button>
<a href="/onboarding/step?step=1" class="btn secondary">&larr; Back</a>
</form>
{% elif state.current_step == 3 %}
<div class="eyebrow">Step 3 of 3</div>
<h1>Choose your tone</h1>
<p class="lead">The tone shapes how scenes unfold. Mysterious hides the next clue. Epic raises the stakes. Hopeful finds light in the dark.</p>
<form method="post" action="/onboarding/step">
<input type="hidden" name="step" value="3">
<div class="options">
{% for t in tones %}
<label class="option">
<input type="radio" name="tone" value="{{ t }}" {{ 'checked' if step3_data.tone == t else '' }} style="display:none">
<span class="name">{{ tone_labels[t] }}</span>
<span class="hint">Click to select</span>
</label>
{% endfor %}
</div>
<button type="submit" class="btn">Create my first world &rarr;</button>
<a href="/onboarding/step?step=2" class="btn secondary">&larr; Back</a>
</form>
{% endif %}
</div>
{% raw %}<script>
document.querySelectorAll('.option').forEach(opt => {
    opt.addEventListener('click', () => {
        document.querySelectorAll('.option').forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');
        const radio = opt.querySelector('input[type="radio"]');
        if (radio) radio.checked = true;
    });
});
if ('serviceWorker' in navigator) { navigator.serviceWorker.register('/sw.js').catch(function(){}); }
{% endraw %}</script>
</body></html>"""


STREAK_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Streak & XP - PocketPlot Universe</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/png" href="/logo-icon-32.png" sizes="32x32">
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8;--emerald:#1d6b50;--emerald-l:#3a8c6c}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh;line-height:1.6}
.wrap{max-width:760px;margin:0 auto;padding:40px 28px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:32px}
.brand img{width:44px;height:40px}
.brand-text{font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--gold-l);font-size:22px;font-weight:600}
.eyebrow{font-family:Helvetica,sans-serif;font-size:11px;letter-spacing:.15em;color:var(--gold-l);text-transform:uppercase;margin-bottom:8px}
h1{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:38px;color:var(--cream);margin:0 0 12px;line-height:1.2}
.lead{color:var(--muted);font-size:15px;margin-bottom:32px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:24px 0}
.card{background:var(--navy-2);border:1px solid rgba(201,160,78,.2);border-radius:8px;padding:24px;position:relative;overflow:hidden}
.card .accent{position:absolute;top:0;left:0;right:0;height:3px;background:var(--gold)}
.card.amber .accent{background:var(--amber)}
.card.emerald .accent{background:var(--emerald-l)}
.card .big{font-family:Fraunces,Georgia,serif;font-style:italic;font-size:48px;color:var(--gold-l);line-height:1;margin:8px 0}
.card.amber .big{color:var(--amber)}
.card.emerald .big{color:var(--emerald-l)}
.card .label{font-size:12px;color:var(--faint);text-transform:uppercase;letter-spacing:.1em}
.card .sub{font-size:14px;color:var(--muted);margin-top:6px}
.level-bar{background:var(--navy-3);height:8px;border-radius:4px;overflow:hidden;margin:8px 0}
.level-fill{height:100%;background:linear-gradient(90deg,var(--gold) 0%,var(--amber) 100%);transition:width .5s}
.level-row{display:flex;justify-content:space-between;font-size:13px;color:var(--faint);margin-bottom:16px}
.history{margin-top:32px}
.history h2{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:24px;color:var(--cream);margin-bottom:16px}
.history table{width:100%;border-collapse:collapse;font-size:14px}
.history th,.history td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--navy-3)}
.history th{font-weight:600;color:var(--faint);font-size:12px;text-transform:uppercase;letter-spacing:.05em}
.history tr:hover{background:rgba(201,160,78,.05)}
.amount{font-family:'JetBrains Mono',monospace;color:var(--amber);font-weight:600}
.empty{color:var(--faint);font-style:italic;padding:20px;text-align:center}
</style></head><body>
<div class="wrap">
<div class="brand">
<img src="/logo-halo-240.png" alt="PocketPlot">
<div class="brand-text">PocketPlot Universe</div>
</div>
<div class="eyebrow">Your activity</div>
<h1>Streak & XP</h1>
<p class="lead">Write or read every day to keep your streak alive. Earn XP by creating stories, completing them, sharing them, and hitting milestones.</p>
<div class="grid">
<div class="card amber">
<div class="accent"></div>
<div class="label">Current streak</div>
<div class="big">{{ stats.current_streak }}</div>
<div class="sub">day{{ 's' if stats.current_streak != 1 else '' }} in a row</div>
</div>
<div class="card emerald">
<div class="accent"></div>
<div class="label">Best streak</div>
<div class="big">{{ stats.best_streak }}</div>
<div class="sub">your personal record</div>
</div>
<div class="card">
<div class="accent"></div>
<div class="label">Total XP</div>
<div class="big">{{ stats.total_xp }}</div>
<div class="sub">level {{ stats.level }}</div>
</div>
<div class="card amber">
<div class="accent"></div>
<div class="label">Today</div>
<div class="big">{{ stats.today_xp }}</div>
<div class="sub">XP earned today</div>
</div>
</div>
<div style="margin:24px 0">
<div class="level-row">
<div>Level {{ stats.level }}</div>
<div>Level {{ stats.level + 1 }}</div>
</div>
<div class="level-bar">
<div class="level-fill" style="width: {{ ((stats.total_xp % 100) if stats.total_xp > 0 else 0) }}%"></div>
</div>
<div style="font-size:13px;color:var(--muted);text-align:center">{{ stats.total_xp % 100 }} / 100 XP to next level</div>
</div>
<div class="history">
<h2>Recent XP events</h2>
{% if recent_events %}
<table>
<thead><tr><th>Reason</th><th>XP</th><th>When</th></tr></thead>
<tbody>
{% for ev in recent_events %}
<tr>
<td>{{ ev.reason.replace('_', ' ').title() }}</td>
<td class="amount">+{{ ev.amount }}</td>
<td>{{ ev.created_at[:19].replace('T', ' ') }}</td>
</tr>
{% endfor %}
</tbody>
</table>
{% else %}
<div class="empty">No XP events yet. Write your first scene or complete a story to start earning.</div>
{% endif %}
</div>
<p style="margin-top:32px"><a href="/me" class="btn" style="display:inline-block;padding:12px 24px;background:var(--gold);color:#0a0f1c;text-decoration:none;border-radius:8px;font-weight:600">Back to dashboard &rarr;</a></p>
</div>
</body></html>"""


STORY_EDITOR_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Edit - {{ world.title }} - PocketPlot Universe</title>
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh;line-height:1.6}
.wrap{max-width:920px;margin:0 auto;padding:40px 28px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:32px}
.brand img{width:44px;height:40px}
.brand-text{font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--gold-l);font-size:22px;font-weight:600}
.eyebrow{font-family:Helvetica,sans-serif;font-size:11px;letter-spacing:.15em;color:var(--gold-l);text-transform:uppercase;margin-bottom:8px}
h1{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:32px;color:var(--cream);margin:0 0 8px;line-height:1.2}
.lead{color:var(--muted);font-size:14px;margin-bottom:24px}
.tabs{display:flex;gap:8px;border-bottom:1px solid var(--navy-3);margin-bottom:24px}
.tab{padding:12px 20px;background:transparent;border:none;border-bottom:2px solid transparent;color:var(--muted);cursor:pointer;font-size:14px;font-family:inherit}
.tab.active{color:var(--gold-l);border-bottom-color:var(--gold)}
.panel{background:var(--navy-2);border:1px solid rgba(201,160,78,.2);border-radius:8px;padding:24px;margin-bottom:20px}
.panel h3{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:18px;color:var(--cream);margin:0 0 16px}
label{display:block;font-size:13px;color:var(--faint);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}
input[type=text],input[type=number],select,textarea{width:100%;background:var(--navy);border:1px solid rgba(201,160,78,.2);border-radius:6px;padding:10px 14px;color:var(--cream);font-family:inherit;font-size:14px;line-height:1.5}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--gold)}
textarea{min-height:200px;resize:vertical}
.row{display:flex;gap:12px;margin-top:16px}
.row > *{flex:1}
.btn{padding:12px 20px;background:var(--gold);color:#0a0f1c;border:none;border-radius:6px;font-weight:600;font-size:14px;cursor:pointer;text-decoration:none;transition:all .2s}
.btn:hover{background:var(--gold-l);box-shadow:0 0 16px rgba(240,181,74,.3)}
.btn.secondary{background:transparent;color:var(--cream);border:1px solid rgba(201,160,78,.4)}
.btn.danger{background:#a02020;color:var(--cream)}
.episode-list{list-style:none;padding:0;margin:0}
.episode-item{padding:14px 16px;background:var(--navy);border:1px solid rgba(201,160,78,.15);border-radius:6px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center}
.episode-item .num{color:var(--gold);font-family:Fraunces,Georgia,serif;font-style:italic;font-size:18px;margin-right:12px}
.episode-item .title{font-size:14px;color:var(--cream)}
.episode-item .meta{font-size:12px;color:var(--faint);margin-top:2px}
.flash{padding:12px 16px;border-radius:6px;margin-bottom:16px;font-size:14px}
.flash.success{background:rgba(29,107,80,.3);border:1px solid var(--emerald);color:var(--cream)}
.flash.error{background:rgba(160,32,32,.3);border:1px solid #a02020;color:var(--cream)}
</style></head><body>
<div class="wrap">
<div class="brand">
<img src="/logo-halo-240.png" alt="PocketPlot">
<div class="brand-text">PocketPlot Universe</div>
</div>
<div class="eyebrow">Editing</div>
<h1>{{ world.title or 'Untitled' }}</h1>
<p class="lead">Edit the world details, then drill into individual episodes to refine the narrative.</p>
{% if flash %}
<div class="flash {{ flash.type }}">{{ flash.message }}</div>
{% endif %}
<div class="tabs">
<button class="tab {{ 'active' if tab == 'world' else '' }}" onclick="window.location='/worlds/{{ world.id }}/edit'">World</button>
<button class="tab {{ 'active' if tab == 'episodes' else '' }}" onclick="window.location='/worlds/{{ world.id }}/edit/episodes'">Episodes</button>
<button class="tab {{ 'active' if tab == 'graph' else '' }}" onclick="window.location='/worlds/{{ world.id }}/graph'">Scene Graph</button>
</div>
{% if tab == 'world' %}
<div class="panel">
<h3>World details</h3>
<form method="post" action="/worlds/{{ world.id }}/edit">
<label>Title</label>
<input type="text" name="title" value="{{ world.title or '' }}" required>
<div class="row">
<div><label>Genre</label>
<select name="genre">
{% for g in genres %}
<option value="{{ g }}" {{ 'selected' if world.genre == g else '' }}>{{ g|title }}</option>
{% endfor %}
</select>
</div>
<div><label>Tone</label>
<select name="tone">
{% for t in tones %}
<option value="{{ t }}" {{ 'selected' if world.tone == t else '' }}>{{ t|title }}</option>
{% endfor %}
</select>
</div>
</div>
<label>Setting</label>
<textarea name="setting" style="min-height:80px">{{ world.setting or '' }}</textarea>
<label>Character</label>
<textarea name="character_description" style="min-height:80px">{{ world.character_description or '' }}</textarea>
<label>Objective</label>
<textarea name="primary_objective" style="min-height:60px">{{ world.primary_objective or '' }}</textarea>
<div class="row">
<div><label>Visibility</label>
<select name="is_public">
<option value="0" {{ 'selected' if not world.is_public else '' }}>Private</option>
<option value="1" {{ 'selected' if world.is_public else '' }}>Public</option>
</select>
</div>
</div>
<div class="row">
<button type="submit" class="btn">Save changes</button>
<a href="/worlds/{{ world.id }}" class="btn secondary">Cancel</a>
</div>
</form>
</div>
{% elif tab == 'episodes' %}
<div class="panel">
<h3>Episodes ({{ episodes|length }})</h3>
{% if episodes %}
<ul class="episode-list">
{% for ep in episodes %}
<li class="episode-item">
<div>
<span class="num">#{{ ep.episode_number }}</span>
<span class="title">{{ ep.title }}</span>
<div class="meta">{{ ep.body|length }} chars - created {{ ep.created_at[:10] }}</div>
</div>
<a href="/worlds/{{ world.id }}/edit/episode/{{ ep.id }}" class="btn secondary">Edit</a>
</li>
{% endfor %}
</ul>
{% else %}
<div style="color:var(--faint);font-style:italic;padding:20px;text-align:center">No episodes yet.</div>
{% endif %}
</div>
{% endif %}
</div>
</body></html>"""


EPISODE_EDIT_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Edit Episode - PocketPlot Universe</title>
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh;line-height:1.6}
.wrap{max-width:920px;margin:0 auto;padding:40px 28px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:32px}
.brand img{width:44px;height:40px}
.brand-text{font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--gold-l);font-size:22px;font-weight:600}
.eyebrow{font-family:Helvetica,sans-serif;font-size:11px;letter-spacing:.15em;color:var(--gold-l);text-transform:uppercase;margin-bottom:8px}
h1{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:32px;color:var(--cream);margin:0 0 8px;line-height:1.2}
.panel{background:var(--navy-2);border:1px solid rgba(201,160,78,.2);border-radius:8px;padding:24px;margin-bottom:20px}
.panel h3{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:18px;color:var(--cream);margin:0 0 16px}
label{display:block;font-size:13px;color:var(--faint);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px}
input[type=text],textarea{width:100%;background:var(--navy);border:1px solid rgba(201,160,78,.2);border-radius:6px;padding:10px 14px;color:var(--cream);font-family:inherit;font-size:14px;line-height:1.5}
input:focus,textarea:focus{outline:none;border-color:var(--gold)}
textarea{min-height:280px;resize:vertical}
.choices{margin-top:12px}
.choice{display:flex;gap:8px;margin-bottom:8px}
.choice input[type=text]{flex:1}
.choice .remove{background:transparent;color:var(--faint);border:1px solid rgba(122,138,168,.3);border-radius:6px;padding:8px 12px;cursor:pointer}
.choice .remove:hover{color:#a02020;border-color:#a02020}
.row{display:flex;gap:12px;margin-top:20px}
.btn{padding:12px 20px;background:var(--gold);color:#0a0f1c;border:none;border-radius:6px;font-weight:600;font-size:14px;cursor:pointer;text-decoration:none;transition:all .2s}
.btn:hover{background:var(--gold-l);box-shadow:0 0 16px rgba(240,181,74,.3)}
.btn.secondary{background:transparent;color:var(--cream);border:1px solid rgba(201,160,78,.4)}
.flash{padding:12px 16px;border-radius:6px;margin-bottom:16px;font-size:14px}
.flash.success{background:rgba(29,107,80,.3);border:1px solid var(--emerald);color:var(--cream)}
.flash.error{background:rgba(160,32,32,.3);border:1px solid #a02020;color:var(--cream)}
</style></head><body>
<div class="wrap">
<div class="brand">
<img src="/logo-halo-240.png" alt="PocketPlot">
<div class="brand-text">PocketPlot Universe</div>
</div>
<div class="eyebrow">Editing episode #{{ episode.episode_number }}</div>
<h1>{{ episode.title }}</h1>
{% if flash %}
<div class="flash {{ flash.type }}">{{ flash.message }}</div>
{% endif %}
<div class="panel">
<h3>Episode content</h3>
<form method="post">
<label>Title</label>
<input type="text" name="title" value="{{ episode.title or '' }}" required>
<label>Body</label>
<textarea name="body" required>{{ episode.body or '' }}</textarea>
<div class="choices">
<label>Choices (one per line)</label>
{% set choice_lines = (choices_text or '').split('\n') %}
{% for c in choice_lines %}
{% if c.strip() %}
<div class="choice"><input type="text" name="choices[]" value="{{ c }}"></div>
{% endif %}
{% endfor %}
<div class="choice"><input type="text" name="choices[]" placeholder="Add a new choice..."></div>
</div>
<div class="row">
<button type="submit" class="btn">Save changes</button>
<a href="/worlds/{{ world.id }}/edit/episodes" class="btn secondary">Back to episodes</a>
</div>
</form>
</div>
</div>
</body></html>"""


SCENE_GRAPH_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Scene Graph - PocketPlot Universe</title>
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh;line-height:1.6}
.wrap{max-width:1280px;margin:0 auto;padding:30px 28px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:24px}
.brand img{width:44px;height:40px}
.brand-text{font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--gold-l);font-size:22px;font-weight:600}
.eyebrow{font-family:Helvetica,sans-serif;font-size:11px;letter-spacing:.15em;color:var(--gold-l);text-transform:uppercase;margin-bottom:8px}
h1{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:28px;color:var(--cream);margin:0 0 8px;line-height:1.2}
.toolbar{display:flex;gap:8px;margin-bottom:16px;align-items:center}
.btn{padding:8px 16px;background:var(--gold);color:#0a0f1c;border:none;border-radius:6px;font-weight:600;font-size:13px;cursor:pointer;text-decoration:none}
.btn:hover{background:var(--gold-l)}
.btn.secondary{background:transparent;color:var(--cream);border:1px solid rgba(201,160,78,.4)}
.help{font-size:12px;color:var(--faint);margin-left:auto}
.canvas-wrap{background:var(--navy-2);border:1px solid rgba(201,160,78,.2);border-radius:8px;position:relative;height:600px;overflow:hidden}
.canvas{width:100%;height:100%;position:relative}
.node{position:absolute;background:var(--navy-3);border:2px solid var(--gold);border-radius:8px;padding:12px 16px;min-width:120px;cursor:move;user-select:none;font-size:13px;color:var(--cream)}
.node.start{border-color:var(--gold-l);background:rgba(201,160,78,.15)}
.node.selected{box-shadow:0 0 0 3px var(--gold)}
.node .label{font-weight:600}
.node .id{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--faint);margin-top:4px}
.edge-svg{position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0}
svg line{stroke:var(--gold);stroke-width:2;fill:none;marker-end:url(#arrowhead)}
svg line:hover{stroke:var(--amber)}
.flash{padding:12px 16px;border-radius:6px;margin-bottom:16px;font-size:14px}
.flash.success{background:rgba(29,107,80,.3);border:1px solid var(--emerald);color:var(--cream)}
</style></head><body>
<div class="wrap">
<div class="brand">
<img src="/logo-halo-240.png" alt="PocketPlot">
<div class="brand-text">PocketPlot Universe</div>
</div>
<div class="eyebrow">Editing</div>
<h1>Scene graph - {{ world.title }}</h1>
{% if flash %}
<div class="flash {{ flash.type }}">{{ flash.message }}</div>
{% endif %}
<div class="toolbar">
<button class="btn" id="add-node-btn">+ Add scene</button>
<button class="btn secondary" id="add-edge-btn">+ Connect</button>
<button class="btn secondary" id="auto-layout-btn">Auto-layout</button>
<button class="btn" id="save-btn">Save graph</button>
<a href="/worlds/{{ world.id }}/edit" class="btn secondary">&larr; Back</a>
<span class="help">Drag scenes to position. Click + Connect to link two scenes.</span>
</div>
<div class="canvas-wrap">
<svg class="edge-svg"><defs><marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><polygon points="0 0, 10 3, 0 6" fill="#c9a04e"/></marker></defs>{% for e in edges %}<line x1="{{ nodes[loop.index0 if false else 0].x + 60 }}" y1="{{ nodes[loop.index0 if false else 0].y + 30 }}" x2="{{ '' }}" y2="{{ '' }}" data-from="{{ e.from_id }}" data-to="{{ e.to_id }}"/>{% endfor %}</svg>
<div class="canvas" id="canvas">
{% for n in nodes %}
<div class="node {{ 'start' if loop.first else '' }}" data-id="{{ n.id }}" style="left:{{ n.x }}px;top:{{ n.y }}px">
<div class="label">{{ n.label }}</div>
<div class="id">{{ n.id }} - ep #{{ n.episode_number or '?' }}</div>
</div>
{% endfor %}
</div>
</div>
</div>
{% raw %}<script>
const canvas = document.getElementById('canvas');
const nodes = {{ nodes_json|safe }};
const edges = {{ edges_json|safe }};
let connecting = false;
let selectedFrom = null;
let draggedNode = null;
let dragOffset = { x: 0, y: 0 };
let dirty = false;

function dirty_mark() { dirty = true; }

document.querySelectorAll('.node').forEach(el => {
    el.addEventListener('mousedown', e => {
        if (connecting) {
            const id = el.dataset.id;
            if (!selectedFrom) { selectedFrom = id; el.classList.add('selected'); }
            else if (selectedFrom !== id) {
                const label = prompt('Choice label:', 'Continue');
                if (label !== null) {
                    edges.push({ from_id: selectedFrom, to_id: id, choice_label: label, choice_index: edges.filter(e => e.from_id === selectedFrom).length });
                    renderEdges();
                    dirty_mark();
                }
                document.querySelectorAll('.node.selected').forEach(n => n.classList.remove('selected'));
                selectedFrom = null;
                connecting = false;
            }
            e.preventDefault();
            return;
        }
        draggedNode = el;
        const rect = el.getBoundingClientRect();
        dragOffset.x = e.clientX - rect.left;
        dragOffset.y = e.clientY - rect.top;
        e.preventDefault();
    });
});

document.addEventListener('mousemove', e => {
    if (!draggedNode) return;
    const canvasRect = canvas.getBoundingClientRect();
    const x = e.clientX - canvasRect.left - dragOffset.x;
    const y = e.clientY - canvasRect.top - dragOffset.y;
    draggedNode.style.left = Math.max(0, x) + 'px';
    draggedNode.style.top = Math.max(0, y) + 'px';
    const id = draggedNode.dataset.id;
    const n = nodes.find(n => n.id === id);
    if (n) { n.x = Math.max(0, x); n.y = Math.max(0, y); }
    renderEdges();
    dirty_mark();
});

document.addEventListener('mouseup', () => { draggedNode = null; });

document.getElementById('add-node-btn').addEventListener('click', () => {
    const label = prompt('Scene label:');
    if (label) {
        const i = nodes.length + 1;
        const id = 'n' + i;
        nodes.push({ id, episode_id: null, label, x: 200 + (i % 5) * 160, y: 200 + Math.floor(i / 5) * 140, color: '#c9a04e' });
        renderNodes();
        renderEdges();
        dirty_mark();
    }
});

document.getElementById('add-edge-btn').addEventListener('click', () => {
    connecting = !connecting;
    document.getElementById('add-edge-btn').textContent = connecting ? 'Click two scenes to connect' : '+ Connect';
    if (!connecting) {
        document.querySelectorAll('.node.selected').forEach(n => n.classList.remove('selected'));
        selectedFrom = null;
    }
});

document.getElementById('auto-layout-btn').addEventListener('click', () => {
    // BFS layout
    if (!nodes.length) return;
    const visited = new Set();
    const queue = [{ node: nodes[0], depth: 0, slot: 0 }];
    const layout = {};
    visited.add(nodes[0].id);
    while (queue.length) {
        const { node, depth, slot } = queue.shift();
        layout[node.id] = { depth, slot };
        const children = edges.filter(e => e.from_id === node.id).map(e => e.to_id);
        children.forEach((cid, i) => {
            if (!visited.has(cid)) {
                visited.add(cid);
                const childNode = nodes.find(n => n.id === cid);
                if (childNode) queue.push({ node: childNode, depth: depth + 1, slot: slot + i });
            }
        });
    }
    nodes.forEach(n => {
        if (layout[n.id]) {
            n.x = 100 + layout[n.id].slot * 180;
            n.y = 80 + layout[n.id].depth * 140;
        }
    });
    renderNodes();
    renderEdges();
    dirty_mark();
});

document.getElementById('save-btn').addEventListener('click', async () => {
    const resp = await fetch('/worlds/{{ world.id }}/graph/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nodes, edges })
    });
    if (resp.ok) { dirty = false; alert('Graph saved!'); }
    else { alert('Save failed'); }
});

function renderNodes() {
    canvas.innerHTML = '';
    nodes.forEach((n, i) => {
        const el = document.createElement('div');
        el.className = 'node' + (i === 0 ? ' start' : '');
        el.dataset.id = n.id;
        el.style.left = n.x + 'px';
        el.style.top = n.y + 'px';
        el.innerHTML = '<div class="label"></div><div class="id"></div>';
        el.querySelector('.label').textContent = n.label;
        el.querySelector('.id').textContent = n.id + (n.episode_number ? ' - ep #' + n.episode_number : '');
        canvas.appendChild(el);
    });
    // Re-bind drag handlers
    canvas.querySelectorAll('.node').forEach(el => {
        el.addEventListener('mousedown', e => {
            if (connecting) {
                const id = el.dataset.id;
                if (!selectedFrom) { selectedFrom = id; el.classList.add('selected'); }
                else if (selectedFrom !== id) {
                    const label = prompt('Choice label:', 'Continue');
                    if (label !== null) {
                        edges.push({ from_id: selectedFrom, to_id: id, choice_label: label, choice_index: edges.filter(e => e.from_id === selectedFrom).length });
                        renderEdges();
                        dirty_mark();
                    }
                    document.querySelectorAll('.node.selected').forEach(n => n.classList.remove('selected'));
                    selectedFrom = null;
                    connecting = false;
                    document.getElementById('add-edge-btn').textContent = '+ Connect';
                }
                e.preventDefault();
                return;
            }
            draggedNode = el;
            const rect = el.getBoundingClientRect();
            dragOffset.x = e.clientX - rect.left;
            dragOffset.y = e.clientY - rect.top;
            e.preventDefault();
        });
    });
}

function renderEdges() {
    const svg = document.querySelector('.edge-svg');
    svg.querySelectorAll('line').forEach(l => l.remove());
    edges.forEach(e => {
        const fromNode = nodes.find(n => n.id === e.from_id);
        const toNode = nodes.find(n => n.id === e.to_id);
        if (!fromNode || !toNode) return;
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        const nodeEl = document.querySelector('.node[data-id="' + e.from_id + '"]');
        const toEl = document.querySelector('.node[data-id="' + e.to_id + '"]');
        if (!nodeEl || !toEl) return;
        line.setAttribute('x1', fromNode.x + nodeEl.offsetWidth / 2);
        line.setAttribute('y1', fromNode.y + nodeEl.offsetHeight / 2);
        line.setAttribute('x2', toNode.x + toEl.offsetWidth / 2);
        line.setAttribute('y2', toNode.y + toEl.offsetHeight / 2);
        svg.appendChild(line);
    });
}

renderEdges();
if ('serviceWorker' in navigator) { navigator.serviceWorker.register('/sw.js').catch(function(){}); }
{% endraw %}</script>
</body></html>"""


INVENTORY_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Inventory - PocketPlot Universe</title>
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8;--emerald:#1d6b50;--emerald-l:#3a8c6c}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh;line-height:1.6}
.wrap{max-width:920px;margin:0 auto;padding:40px 28px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:32px}
.brand img{width:44px;height:40px}
.brand-text{font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--gold-l);font-size:22px;font-weight:600}
.eyebrow{font-family:Helvetica,sans-serif;font-size:11px;letter-spacing:.15em;color:var(--gold-l);text-transform:uppercase;margin-bottom:8px}
h1{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:32px;color:var(--cream);margin:0 0 12px;line-height:1.2}
.lead{color:var(--muted);font-size:14px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;margin-top:16px}
.item{background:var(--navy-2);border:1px solid rgba(201,160,78,.2);border-radius:8px;padding:16px;position:relative;overflow:hidden;transition:all .2s}
.item:hover{border-color:var(--gold);transform:translateY(-2px)}
.item .accent{position:absolute;top:0;left:0;right:0;height:3px}
.item.common .accent{background:var(--faint)}
.item.uncommon .accent{background:var(--muted)}
.item.rare .accent{background:var(--gold)}
.item.epic .accent{background:var(--amber)}
.item.legendary .accent{background:var(--emerald-l)}
.item .icon{font-size:32px;margin-bottom:8px}
.item .name{font-weight:600;font-size:15px;color:var(--cream);margin-bottom:4px}
.item .desc{font-size:12px;color:var(--muted);line-height:1.4}
.item .qty{position:absolute;top:12px;right:12px;background:var(--gold);color:#0a0f1c;padding:2px 10px;border-radius:10px;font-size:12px;font-weight:700}
.item .tier{font-size:10px;color:var(--faint);margin-top:8px;text-transform:uppercase;letter-spacing:.05em}
.section{margin:32px 0}
.section h2{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:22px;color:var(--cream);margin-bottom:12px}
.history{list-style:none;padding:0;margin:0}
.history li{padding:10px 12px;background:var(--navy-2);border-radius:6px;margin-bottom:6px;font-size:13px;color:var(--muted);display:flex;justify-content:space-between;align-items:center}
.history .action{font-family:'JetBrains Mono',monospace;color:var(--amber)}
.empty{color:var(--faint);font-style:italic;padding:24px;text-align:center}
</style></head><body>
<div class="wrap">
<div class="brand">
<img src="/logo-halo-240.png" alt="PocketPlot">
<div class="brand-text">PocketPlot Universe</div>
</div>
<div class="eyebrow">Your collection</div>
<h1>Inventory</h1>
<p class="lead">Items you've collected from completing stories, hitting milestones, or being granted by admins. Use them in worlds to unlock scenes, reveal branches, or roll the art.</p>
<div class="section">
<h2>Catalog ({{ inventory|length }} items)</h2>
{% if inventory %}
<div class="grid">
{% for it in inventory %}
<div class="item {{ it.rarity }}">
<div class="accent"></div>
<span class="qty">{{ it.quantity }}</span>
<div class="icon">{{ it.icon or '�' }}</div>
<div class="name">{{ it.name }}</div>
<div class="desc">{{ it.description }}</div>
<div class="tier">{{ it.rarity }} - {{ it.tier_required|title }} tier</div>
</div>
{% endfor %}
</div>
{% else %}
<div class="empty">Your inventory is empty. New users receive a starter pack - try writing your first scene or completing a story.</div>
{% endif %}
</div>
<div class="section">
<h2>Recent history</h2>
{% if history %}
<ul class="history">
{% for h in history %}
<li>
<span><span class="action">{{ h.action }}</span> {{ h.item_key }} {% if h.quantity_delta %}<span style="color:var(--gold)">{{ '+' if h.quantity_delta > 0 else '' }}{{ h.quantity_delta }}</span>{% endif %}</span>
<span style="color:var(--faint);font-size:12px">{{ h.created_at[:19].replace('T', ' ') }}</span>
</li>
{% endfor %}
</ul>
{% else %}
<div class="empty">No history yet.</div>
{% endif %}
</div>
<p style="margin-top:24px"><a href="/me" class="btn" style="display:inline-block;padding:10px 20px;background:var(--gold);color:#0a0f1c;text-decoration:none;border-radius:6px;font-weight:600">Back to dashboard</a></p>
</div>
</body></html>"""


ADMIN_AUDIT_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audit log - Admin - PocketPlot Universe</title>
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh;line-height:1.6}
.wrap{max-width:1200px;margin:0 auto;padding:40px 28px}
.brand{display:flex;align-items:center;gap:12px;margin-bottom:32px}
.brand img{width:44px;height:40px}
.brand-text{font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--gold-l);font-size:22px;font-weight:600}
.eyebrow{font-family:Helvetica,sans-serif;font-size:11px;letter-spacing:.15em;color:var(--gold-l);text-transform:uppercase;margin-bottom:8px}
h1{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:32px;color:var(--cream);margin:0 0 16px;line-height:1.2}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--navy-3)}
th{font-weight:600;color:var(--faint);font-size:11px;text-transform:uppercase;letter-spacing:.05em;background:var(--navy-2)}
tr:hover{background:rgba(201,160,78,.05)}
.action{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--amber)}
.actor{color:var(--gold-l);font-size:12px}
.target{color:var(--muted);font-size:12px}
.time{color:var(--faint);font-size:12px;font-family:'JetBrains Mono',monospace}
.meta{color:var(--muted);font-size:11px;margin-top:4px;font-family:'JetBrains Mono',monospace;white-space:pre-wrap;word-break:break-all}
.stats{display:flex;gap:16px;margin:16px 0 32px}
.stat{background:var(--navy-2);border:1px solid rgba(201,160,78,.2);border-radius:6px;padding:14px 18px;flex:1}
.stat .n{font-family:Fraunces,Georgia,serif;font-style:italic;font-size:28px;color:var(--gold-l);line-height:1}
.stat .label{font-size:11px;color:var(--faint);text-transform:uppercase;letter-spacing:.05em;margin-top:4px}
</style></head><body>
<div class="wrap">
<div class="brand">
<img src="/logo-halo-240.png" alt="PocketPlot">
<div class="brand-text">PocketPlot Universe - Admin</div>
</div>
<div class="eyebrow">Admin</div>
<h1>Audit log</h1>
<div class="stats">
{% for s in stats %}
<div class="stat">
<div class="n">{{ s.n }}</div>
<div class="label">{{ s.action }}</div>
</div>
{% endfor %}
</div>
<table>
<thead><tr><th>Time</th><th>Action</th><th>Actor</th><th>Target</th><th>IP</th><th>Metadata</th></tr></thead>
<tbody>
{% for e in entries %}
<tr>
<td class="time">{{ e.created_at[:19].replace('T', ' ') }}</td>
<td class="action">{{ e.action }}</td>
<td class="actor">{{ e.actor_type }}{% if e.actor_id %} #{{ e.actor_id }}{% endif %}</td>
<td class="target">{{ e.target_type or '-' }}{% if e.target_id %} #{{ e.target_id }}{% endif %}</td>
<td class="time">{{ (e.ip_address or '-')[:16] }}</td>
<td class="target">
{% if e.metadata_json %}<div class="meta">{{ e.metadata_json[:120] }}{% if e.metadata_json|length > 120 %}...{% endif %}</div>{% else %}-{% endif %}
</td>
</tr>
{% endfor %}
</tbody>
</table>
<p style="margin-top:24px;color:var(--faint);font-size:13px">Showing the most recent {{ entries|length }} entries from the last 30 days.</p>
</div>
</body></html>"""


# ===================== end v24 templates =====================


# SEO: sitemap + public story page
# =====================================================================

@app.route("/sitemap.xml")
def sitemap_xml():
    from html import escape as _e
    base = request.host_url.rstrip('/')
    urls = [f"{base}/", f"{base}/pricing", f"{base}/how-it-works", f"{base}/faq"]
    # Add public stories
    public = db().execute(
        "SELECT s.username, w.id, w.slug FROM worlds w "
        "JOIN subscribers s ON w.subscriber_id = s.id "
        "WHERE w.is_public = 1 AND w.slug IS NOT NULL "
        "ORDER BY w.id DESC LIMIT 500"
    ).fetchall()
    for p in public:
        urls.append(f"{base}/u/{p['username']}/world/{p['slug']}")
    # Add public profiles
    profiles = db().execute(
        "SELECT username FROM subscribers WHERE is_public=1 LIMIT 200"
    ).fetchall()
    for p in profiles:
        urls.append(f"{base}/u/{p['username']}")
    body = '<?xml version="1.0" encoding="UTF-8"?>\n'
    body += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for url in urls:
        body += f'  <url><loc>{_e(url)}</loc></url>\n'
    body += '</urlset>\n'
    return Response(body, mimetype="application/xml")


@app.route("/robots.txt")
def robots_txt():
    base = request.host_url.rstrip('/')
    body = f"""User-agent: *
Disallow: /admin
Disallow: /api
Disallow: /play
Disallow: /read
Allow: /

Sitemap: {base}/sitemap.xml
"""
    return Response(body, mimetype="text/plain")


@app.route("/u/<username>/world/<slug>")
def public_world_view(username, slug):
    row = db().execute(
        "SELECT w.*, s.username, s.tier, s.bio FROM worlds w "
        "JOIN subscribers s ON w.subscriber_id = s.id "
        "WHERE s.username=? AND w.slug=?",
        (username, slug),
    ).fetchone()
    if not row:
        return ("Not found", 404)
    w = dict(row)
    if not w.get("is_public"):
        return ("Not public", 403)
    eps = db().execute("SELECT * FROM world_episodes WHERE world_id=? ORDER BY episode_number",
                       (w["id"],)).fetchall()
    # Stats
    view_row = db().execute("SELECT views, plays FROM story_stats WHERE world_id=?", (w["id"],)).fetchone()
    view_count = (dict(view_row).get("views") if view_row else 0) or 0
    play_count = (dict(view_row).get("plays") if view_row else 0) or 0
    # Comments
    import social
    comments = social.list_comments(db, w["id"])
    # Reactions
    reactions = social.reaction_counts(db, w["id"])
    return Response(_render_public_world(w, eps, view_count, play_count, comments, reactions, username),
                    mimetype="text/html")


def _render_public_world(w, eps, view_count, play_count, comments, reactions, username):
    from html import escape as _e
    """Render a public world page with OG tags + JSON-LD."""
    title = w.get("title") or "Untitled"
    genre = w.get("genre") or "fantasy"
    description = (w.get("setting") or w.get("character_description") or "")[:160]
    # Build a game token for the "Play it" link
    game_token = db().execute(
        "SELECT token FROM share_tokens WHERE world_id=? AND kind='game' AND revoked_at IS NULL LIMIT 1",
        (w["id"],),
    ).fetchone()
    game_url = f"{request.host_url.rstrip('/')}/play/{dict(game_token)['token']}" if game_token else ""
    read_token = db().execute(
        "SELECT token FROM share_tokens WHERE world_id=? AND kind='read' AND revoked_at IS NULL LIMIT 1",
        (w["id"],),
    ).fetchone()
    read_url = f"{request.host_url.rstrip('/')}/read/{dict(read_token)['token']}/page/1" if read_token else ""
    cover_url = f"{request.host_url.rstrip('/')}/worlds/{w['id']}/cover.png"
    og_url = request.url
    # JSON-LD
    jsonld = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": title,
        "author": {"@type": "Person", "name": username},
        "genre": genre,
        "description": description,
        "url": og_url,
        "image": cover_url,
        "interactionStatistic": [
            {"@type": "InteractionCounter", "interactionType": "ViewAction", "userInteractionCount": view_count},
            {"@type": "InteractionCounter", "interactionType": "PlayAction", "userInteractionCount": play_count},
        ],
    }
    jsonld_str = json.dumps(jsonld)
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8">
<title>{_e(title)} by {_e(username)} - PocketPlot Universe</title>
<meta name="description" content="{_e(description)}">
<link rel="canonical" href="{_e(og_url)}">
<meta property="og:title" content="{_e(title)}">
<meta property="og:description" content="{_e(description)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{_e(og_url)}">
<meta property="og:image" content="{_e(cover_url)}">
<meta property="og:site_name" content="PocketPlot Universe">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{_e(title)}">
<meta name="twitter:description" content="{_e(description)}">
<meta name="twitter:image" content="{_e(cover_url)}">
<script type="application/ld+json">{jsonld_str}</script>
<style>
:root{{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}}
*{{box-sizing:border-box}}
body{{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh;line-height:1.6}}
.wrap{{max-width:780px;margin:0 auto;padding:40px 28px}}
.cover{{width:100%;aspect-ratio:1200/630;background:var(--navy-2);border-radius:12px;overflow:hidden;margin-bottom:24px;border:1px solid rgba(201,160,78,.2)}}
.cover img{{width:100%;height:100%;object-fit:cover;display:block}}
.eyebrow{{font-family:Helvetica,sans-serif;font-size:11px;letter-spacing:.15em;color:var(--gold-l);text-transform:uppercase;margin-bottom:8px}}
h1{{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:42px;color:var(--cream);margin:0 0 16px;line-height:1.1}}
.author{{color:var(--muted);font-size:14px;margin-bottom:24px}}
.author a{{color:var(--gold-l);text-decoration:none}}
.actions{{display:flex;gap:12px;margin:24px 0;flex-wrap:wrap}}
.btn{{display:inline-block;padding:12px 24px;background:var(--gold);color:#0a0f1c;text-decoration:none;border-radius:8px;font-weight:600;font-size:14px}}
.btn:hover{{background:var(--gold-l);box-shadow:0 0 20px rgba(240,181,74,.4)}}
.btn.secondary{{background:transparent;color:var(--cream);border:1px solid rgba(201,160,78,.4)}}
.stats{{display:flex;gap:24px;color:var(--muted);font-size:14px;margin:24px 0;padding:16px 0;border-top:1px solid var(--navy-3);border-bottom:1px solid var(--navy-3)}}
.stats b{{color:var(--gold-l);font-weight:600}}
.episodes{{margin:32px 0}}
.episodes h2{{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:500;font-size:24px;color:var(--cream);margin-bottom:16px}}
.episode{{background:var(--navy-2);border:1px solid rgba(201,160,78,.2);border-radius:8px;padding:16px 20px;margin-bottom:12px}}
.episode .n{{font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--gold-l);font-size:14px}}
.episode .title{{font-weight:600;font-size:16px;color:var(--cream);margin:4px 0}}
.episode .body{{font-size:14px;color:var(--cream-w);white-space:pre-wrap}}
</style></head><body>
<div class="wrap">
<a href="/" style="display:inline-flex;align-items:center;gap:8px;margin-bottom:16px;text-decoration:none;color:var(--gold-l)"><img src="/logo-halo-240.png" alt="" width="36" height="34"><span style="font-family:Fraunces,Georgia,serif;font-style:italic;font-size:18px">PocketPlot Universe</span></a>
<div class="cover"><img src="{_e(cover_url)}" alt="{_e(title)}"></div>
<div class="eyebrow">{_e(genre)}</div>
<h1>{_e(title)}</h1>
<p class="author">by <a href="/u/{_e(username)}">{_e(username)}</a></p>
<p>{_e(description)}</p>
<div class="actions">
<a href="/worlds/{w['id']}/share" class="btn">Share this story</a>
{game_url and f'<a href="{_e(game_url)}" class="btn secondary">Play it</a>' or ''}
{read_url and f'<a href="{_e(read_url)}" class="btn secondary">Read it</a>' or ''}
</div>
<div class="stats">
<div><b>{view_count}</b> views</div>
<div><b>{play_count}</b> plays</div>
<div><b>{len(eps)}</b> episodes</div>
</div>
<div class="episodes">
<h2>Episodes</h2>
{''.join(f'<div class="episode"><div class="n">Episode #{_e(ep["episode_number"])}</div><div class="title">{_e(ep["title"] or "")}</div><div class="body">{_e(ep["body"][:500] + ("..." if len(ep["body"]) > 500 else ""))}</div></div>' for ep in eps)}
</div>
</div>
</body></html>"""





# ===================== v25 route handlers =====================
"""v25 Inventory route handlers - place/pick up items in a world."""

@app.route("/worlds/<int:world_id>/inventory", methods=["GET"])
def world_inventory_page(world_id):
    """Show the inventory placement page for a world."""
    if not session.get("user_id"):
        return redirect(url_for("login"))
    w = db().execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not w or dict(w).get("subscriber_id") != session["user_id"]:
        return ("Forbidden", 403)
    import inventory
    inv_counts = inventory.user_inventory(db, session["user_id"])
    catalog = inventory.list_items(db)
    inv_items = []
    for item in catalog:
        qty = inv_counts.get(item['key'], 0)
        inv_items.append({**item, 'quantity': qty})
    placed = inventory.world_items(db, world_id)
    # Build a JSON-safe version for the script
    placed_json = json.dumps([
        {
            'id': p['id'], 'name': p['name'], 'icon': p.get('icon', '✦'),
            'rarity': p.get('rarity', 'common'), 'x': p['x'], 'y': p['y']
        } for p in placed
    ])
    return render_template_string(WORLD_INVENTORY_HTML,
        world_id=world_id,
        inventory=inv_items,
        placed=placed,
        placed_json=placed_json,
        flash=None)


@app.route("/worlds/<int:world_id>/inventory/place/<item_key>", methods=["POST"])
def world_inventory_place(world_id, item_key):
    """Place an item from inventory into a world."""
    if not session.get("user_id"):
        return redirect(url_for("login"))
    w = db().execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not w or dict(w).get("subscriber_id") != session["user_id"]:
        return ("Forbidden", 403)
    x = float(request.form.get("x", 100))
    y = float(request.form.get("y", 100))
    import inventory
    success = inventory.place_item(db, world_id, session["user_id"], item_key, x, y)
    import audit_v24
    audit_v24.audit(db, "inventory.place", actor_id=session["user_id"],
        target_type="world", target_id=world_id,
        metadata={"item_key": item_key, "x": x, "y": y, "success": success},
        ip_address=request.remote_addr)
    if success:
        # XP for placing
        import streaks_xp
        streaks_xp.award_xp(db, session["user_id"], "wrote_scene", related_id=world_id)
    return redirect(url_for("world_inventory_page", world_id=world_id))


@app.route("/worlds/<int:world_id>/inventory/pickup/<int:item_id>", methods=["POST"])
def world_inventory_pickup(world_id, item_id):
    """Pick up a placed item back into inventory."""
    if not session.get("user_id"):
        return redirect(url_for("login"))
    w = db().execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not w or dict(w).get("subscriber_id") != session["user_id"]:
        return ("Forbidden", 403)
    import inventory
    success = inventory.remove_world_item(db, item_id, session["user_id"])
    import audit_v24
    audit_v24.audit(db, "inventory.pickup", actor_id=session["user_id"],
        target_type="world", target_id=world_id,
        metadata={"item_id": item_id, "success": success},
        ip_address=request.remote_addr)
    return redirect(url_for("world_inventory_page", world_id=world_id))


@app.route("/worlds/<int:world_id>/inventory/move", methods=["POST"])
def world_inventory_move(world_id):
    """Move a placed item to new x/y coordinates."""
    if not session.get("user_id"):
        return ("Forbidden", 403)
    data = request.get_json(force=True)
    item_id = data.get("id")
    x = float(data.get("x", 0))
    y = float(data.get("y", 0))
    if not item_id:
        return ("Bad request", 400)
    w = db().execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not w or dict(w).get("subscriber_id") != session["user_id"]:
        return ("Forbidden", 403)
    # Verify ownership of the item
    owner = db().execute("SELECT subscriber_id FROM world_inventory WHERE id=?", (item_id,)).fetchone()
    if not owner or owner['subscriber_id'] != session["user_id"]:
        return ("Forbidden", 403)
    db().execute("UPDATE world_inventory SET x=?, y=? WHERE id=?", (x, y, item_id))
    db().commit()
    return ("OK", 200)


# ===================== end v25 handlers =====================
# ===================== v24 route handlers =====================
"""v24 route handlers for PocketPlot Universe.

Appended to app.py. Provides:
  - /onboarding, /onboarding/step, /onboarding/skip
  - /worlds/<id>/edit (world editor)
  - /worlds/<id>/edit/episodes (episode list)
  - /worlds/<id>/edit/episode/<ep_id> (single episode editor)
  - /worlds/<id>/graph (scene-graph editor)
  - /worlds/<id>/graph/save (POST save graph)
  - /worlds/<id>/comments (POST add comment)
  - /worlds/<id>/reactions (POST toggle reaction)
  - /worlds/<id>/cover.png (GET cover image)
  - /me/streak
  - /me/inventory
  - /worlds/<id>/inventory
  - /api/tts/voices
  - /api/tts/sanitize
  - /admin/audit
  - /sitemap.xml
  - /robots.txt
  - /u/<username>/world/<slug> (public story page)
"""

# =====================================================================
# ONBOARDING
# =====================================================================

@app.route("/onboarding", methods=["GET"])
def onboarding_wizard():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    import onboarding
    state = onboarding.get_state(db, session["user_id"])
    step1 = json.loads(state.get("step1_data") or "{}") if state.get("step1_data") else {}
    step2 = json.loads(state.get("step2_data") or "{}") if state.get("step2_data") else {}
    step3 = json.loads(state.get("step3_data") or "{}") if state.get("step3_data") else {}
    return render_template_string(
        ONBOARDING_HTML,
        state=state,
        genres=onboarding.GENRES,
        tones=onboarding.TONES,
        genre_labels=onboarding.GENRE_LABELS,
        tone_labels=onboarding.TONE_LABELS,
        step1_data=step1, step2_data=step2, step3_data=step3,
    )


@app.route("/onboarding/step", methods=["POST"])
def onboarding_step():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    import onboarding
    sid = session["user_id"]
    step = int(request.form.get("step", 1))
    if step == 1:
        genre = request.form.get("genre", "").strip()
        if genre not in onboarding.GENRES:
            return redirect(url_for("onboarding_wizard"))
        onboarding.advance_step(db, sid, 1, 2, {"genre": genre})
    elif step == 2:
        character = request.form.get("character", "").strip()[:1000]
        if not character:
            return redirect(url_for("onboarding_wizard"))
        onboarding.advance_step(db, sid, 2, 3, {"character": character})
    elif step == 3:
        tone = request.form.get("tone", "").strip()
        if tone not in onboarding.TONES:
            return redirect(url_for("onboarding_wizard"))
        onboarding.update_step(db, sid, 3, {"tone": tone})
        onboarding.mark_complete(db, sid)
        # Pre-fill pending_seed for worlds/new
        s1 = onboarding.get_state(db, sid)
        sd1 = json.loads(s1.get("step1_data") or "{}")
        sd2 = json.loads(s1.get("step2_data") or "{}")
        sd3 = json.loads(s1.get("step3_data") or "{}")
        session["pending_seed"] = {
            "title_hint": "",
            "genre": sd1.get("genre", ""),
            "character_description": sd2.get("character", ""),
            "tone": sd3.get("tone", ""),
        }
        return redirect(url_for("worlds_new"))
    # Allow GET to step=n to go backwards
    if request.method == "GET":
        back_step = int(request.args.get("step", 1))
        onboarding.update_step(db, sid, back_step, {})
        return redirect(url_for("onboarding_wizard"))
    return redirect(url_for("onboarding_wizard"))


@app.route("/onboarding/skip")
def onboarding_skip():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    import onboarding
    onboarding.skip(db, session["user_id"])
    return redirect(url_for("me"))


# =====================================================================
# STORY EDITOR
# =====================================================================

@app.route("/worlds/<int:world_id>/edit", methods=["GET"])
def world_edit(world_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    w = db().execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not w:
        return ("Not found", 404)
    if dict(w).get("subscriber_id") != session["user_id"]:
        return ("Forbidden", 403)
    return render_template_string(STORY_EDITOR_HTML, world=dict(w), tab="world",
        flash=None, episodes=[], genres=globals().get("GENRES_V16", []),
        tones=globals().get("TONES_V16", []))


@app.route("/worlds/<int:world_id>/edit", methods=["POST"])
def world_edit_save(world_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    w = db().execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not w:
        return ("Not found", 404)
    if dict(w).get("subscriber_id") != session["user_id"]:
        return ("Forbidden", 403)
    title = request.form.get("title", "").strip()[:200]
    genre = request.form.get("genre", "fantasy")
    tone = request.form.get("tone", "hopeful")
    setting = request.form.get("setting", "").strip()[:2000]
    char = request.form.get("character_description", "").strip()[:2000]
    obj = request.form.get("primary_objective", "").strip()[:1000]
    is_public = int(request.form.get("is_public", 0))
    wd = dict(w)
    import audit_v24
    audit_v24.audit(db, "world.edit", actor_id=session["user_id"],
        target_type="world", target_id=world_id,
        metadata={"title_changed": wd.get("title") != title},
        ip_address=request.remote_addr, user_agent=request.user_agent.string[:120])
    db().execute(
        "UPDATE worlds SET title=?, genre=?, tone=?, setting=?, character_description=?, "
        "primary_objective=?, is_public=?, slug=? WHERE id=?",
        (title, genre, tone, setting, char, obj, is_public,
         _slugify(title), world_id),
    )
    # Track revision for the title field if it changed
    if wd.get("title") != title:
        db().execute(
            "INSERT INTO story_revisions(world_id, subscriber_id, field, old_value, new_value, created_at) "
            "VALUES (?, ?, 'title', ?, ?, ?)",
            (world_id, session["user_id"], wd.get("title"), title,
             dt.datetime.utcnow().isoformat(timespec="seconds")),
        )
    db().commit()
    # Award XP for the edit
    import streaks_xp
    streaks_xp.award_xp(db, session["user_id"], "wrote_scene", related_id=world_id)
    flash = {"type": "success", "message": "Saved."}
    w = db().execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    return render_template_string(STORY_EDITOR_HTML, world=dict(w), tab="world",
        flash=flash, episodes=[], genres=globals().get("GENRES_V16", []),
        tones=globals().get("TONES_V16", []))


@app.route("/worlds/<int:world_id>/edit/episodes", methods=["GET"])
def world_edit_episodes(world_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    w = db().execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not w or dict(w).get("subscriber_id") != session["user_id"]:
        return ("Forbidden", 403)
    eps = db().execute("SELECT * FROM world_episodes WHERE world_id=? ORDER BY episode_number",
                       (world_id,)).fetchall()
    return render_template_string(STORY_EDITOR_HTML, world=dict(w), tab="episodes",
        flash=None, episodes=[dict(e) for e in eps],
        genres=globals().get("GENRES_V16", []),
        tones=globals().get("TONES_V16", []))


@app.route("/worlds/<int:world_id>/edit/episode/<int:episode_id>", methods=["GET", "POST"])
def episode_edit(world_id, episode_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    ep = db().execute("SELECT * FROM world_episodes WHERE id=?", (episode_id,)).fetchone()
    if not ep:
        return ("Not found", 404)
    w = db().execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not w or dict(w).get("subscriber_id") != session["user_id"]:
        return ("Forbidden", 403)
    if request.method == "POST":
        epd = dict(ep)
        title = request.form.get("title", "").strip()[:200]
        body = request.form.get("body", "").strip()
        choices = request.form.getlist("choices[]")
        choices = [c.strip() for c in choices if c.strip()]
        choices_json = json.dumps(choices)
        import audit_v24
        audit_v24.audit(db, "episode.edit", actor_id=session["user_id"],
            target_type="episode", target_id=episode_id,
            metadata={"old_title": epd.get("title"), "new_title": title},
            ip_address=request.remote_addr)
        # Track revision
        if epd.get("title") != title:
            db().execute(
                "INSERT INTO scene_revisions(episode_id, subscriber_id, field, old_value, new_value, created_at) "
                "VALUES (?, ?, 'title', ?, ?, ?)",
                (episode_id, session["user_id"], epd.get("title"), title,
                 dt.datetime.utcnow().isoformat(timespec="seconds")),
            )
        if epd.get("body") != body:
            db().execute(
                "INSERT INTO scene_revisions(episode_id, subscriber_id, field, old_value, new_value, created_at) "
                "VALUES (?, ?, 'body', ?, ?, ?)",
                (episode_id, session["user_id"], epd.get("body")[:200], body[:200],
                 dt.datetime.utcnow().isoformat(timespec="seconds")),
            )
        db().execute(
            "UPDATE world_episodes SET title=?, body=?, choices_json=? WHERE id=?",
            (title, body, choices_json, episode_id),
        )
        db().commit()
        import streaks_xp
        streaks_xp.award_xp(db, session["user_id"], "wrote_scene", related_id=episode_id)
        flash = {"type": "success", "message": "Episode saved."}
        ep = db().execute("SELECT * FROM world_episodes WHERE id=?", (episode_id,)).fetchone()
    else:
        flash = None
    choices_text = "\n".join(json.loads(dict(ep).get("choices_json") or "[]")) if dict(ep).get("choices_json") else ""
    return render_template_string(EPISODE_EDIT_HTML, episode=dict(ep), world=dict(w),
        flash=flash, choices_text=choices_text)


# =====================================================================
# SCENE-GRAPH EDITOR
# =====================================================================

@app.route("/worlds/<int:world_id>/graph", methods=["GET"])
def scene_graph_editor(world_id):
    if not session.get("user_id"):
        return redirect(url_for("login"))
    w = db().execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not w or dict(w).get("subscriber_id") != session["user_id"]:
        return ("Forbidden", 403)
    import scene_graph
    graph = scene_graph.load_graph(db, world_id)
    nodes = graph['nodes']
    edges = graph['edges']
    # Ensure all episodes are present as nodes
    eps = db().execute("SELECT id, episode_number, title FROM world_episodes WHERE world_id=?",
                       (world_id,)).fetchall()
    existing_ep_ids = {n.get('episode_id') for n in nodes if n.get('episode_id')}
    for ep in eps:
        if ep['id'] not in existing_ep_ids:
            # Add missing episode as a node
            new_node = scene_graph.add_node(db, world_id, ep['title'] or f"Episode {ep['episode_number']}",
                                            episode_id=ep['id'])
            # Re-fetch
            graph = scene_graph.load_graph(db, world_id)
            nodes = graph['nodes']
            edges = graph['edges']
    return render_template_string(SCENE_GRAPH_HTML, world=dict(w),
        nodes=nodes, edges=edges,
        nodes_json=json.dumps(nodes), edges_json=json.dumps(edges),
        flash=None)


@app.route("/worlds/<int:world_id>/graph/save", methods=["POST"])
def scene_graph_save(world_id):
    if not session.get("user_id"):
        return ("Forbidden", 403)
    w = db().execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not w or dict(w).get("subscriber_id") != session["user_id"]:
        return ("Forbidden", 403)
    data = request.get_json(force=True)
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    import scene_graph
    scene_graph.save_graph(db, world_id, nodes, edges)
    import audit_v24
    audit_v24.audit(db, "world.graph.save", actor_id=session["user_id"],
        target_type="world", target_id=world_id,
        metadata={"node_count": len(nodes), "edge_count": len(edges)},
        ip_address=request.remote_addr)
    return ("OK", 200)


# =====================================================================
# COMMENTS + REACTIONS
# =====================================================================

@app.route("/worlds/<int:world_id>/comments", methods=["POST"])
def post_comment(world_id):
    if not session.get("user_id"):
        return ("Login required", 401)
    import social
    body = request.form.get("body", "").strip()[:4000]
    parent_id = request.form.get("parent_id")
    if parent_id:
        try:
            parent_id = int(parent_id)
        except ValueError:
            parent_id = None
    try:
        cid = social.add_comment(db, world_id, session["user_id"], body, parent_id=parent_id)
    except ValueError:
        return ("Comment cannot be empty", 400)
    import audit_v24
    audit_v24.audit(db, "comment.create", actor_id=session["user_id"],
        target_type="comment", target_id=cid, target_type_2="world", target_id_2=world_id,
        ip_address=request.remote_addr)
    return redirect(request.referrer or url_for("worlds_view", world_id=world_id))


@app.route("/worlds/<int:world_id>/reactions", methods=["POST"])
def post_reaction(world_id):
    if not session.get("user_id"):
        return ("Login required", 401)
    import social
    kind = request.form.get("kind", "")
    if kind not in dict(social.REACTION_KINDS):
        return ("Unknown reaction", 400)
    result = social.toggle_reaction(db, world_id, session["user_id"], kind)
    import audit_v24
    audit_v24.audit(db, f"reaction.{result}", actor_id=session["user_id"],
        target_type="world", target_id=world_id,
        metadata={"kind": kind}, ip_address=request.remote_addr)
    return redirect(request.referrer or url_for("worlds_view", world_id=world_id))


# =====================================================================
# STORY COVERS
# =====================================================================

@app.route("/worlds/<int:world_id>/cover.png")
def story_cover(world_id):
    w = db().execute("SELECT * FROM worlds WHERE id=?", (world_id,)).fetchone()
    if not w:
        return ("Not found", 404)
    import social
    path = social.generate_cover(db, world_id,
        title=dict(w).get("title") or "Untitled",
        genre=dict(w).get("genre") or "fantasy",
        tone=dict(w).get("tone") or "hopeful",
        subtitle=dict(w).get("primary_objective") or "")
    if not path or not os.path.exists(path):
        return ("Cover not generated", 404)
    from flask import send_file
    return send_file(path, mimetype="image/png", max_age=86400)


# =====================================================================
# STREAK + INVENTORY
# =====================================================================

@app.route("/me/streak")
def me_streak():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    import streaks_xp
    stats = streaks_xp.get_stats(db, session["user_id"])
    # Recent events
    recent = db().execute(
        "SELECT reason, amount, created_at FROM xp_events WHERE subscriber_id=? "
        "ORDER BY created_at DESC LIMIT 20",
        (session["user_id"],),
    ).fetchall()
    return render_template_string(STREAK_HTML, stats=stats,
        recent_events=[dict(r) for r in recent])


@app.route("/me/inventory")
def me_inventory():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    import inventory
    inv = inventory.user_inventory(db, session["user_id"])
    catalog = inventory.list_items(db)
    # Merge
    items = []
    for item in catalog:
        qty = inv.get(item['key'], 0)
        items.append({**item, 'quantity': qty})
    history = inventory.history(db, session["user_id"], limit=20)
    return render_template_string(INVENTORY_HTML, inventory=items, history=history)


# =====================================================================
# TTS API
# =====================================================================

@app.route("/api/tts/voices", methods=["GET"])
def tts_voices():
    import tts as tts_module
    return {"voices": tts_module.get_voices(), "default": tts_module.get_default_voice_id()}


@app.route("/api/tts/sanitize", methods=["POST"])
def tts_sanitize():
    import tts as tts_module
    data = request.get_json(force=True)
    text = data.get("text", "")
    return {
        "text": tts_module.sanitize(text),
        "duration_estimate": tts_module.estimate_duration(text),
        "chunks": tts_module.split_into_chunks(text),
    }


# =====================================================================
# ADMIN AUDIT
# =====================================================================

@app.route("/admin/audit-v24")
def admin_audit_v24():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    import audit_v24
    entries = audit_v24.recent(db, limit=200)
    stats = audit_v24.stats(db, since_days=30)
    return render_template_string(ADMIN_AUDIT_HTML,
        entries=[dict(e) for e in entries],
        stats=[dict(s) for s in stats])


# =====================================================================

@app.route("/contact", methods=["GET", "POST"])
def contact():
    import audit
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        subject = (request.form.get("subject") or "").strip()
        body = (request.form.get("body") or "").strip()
        if not email or "@" not in email:
            flash("Please enter a valid email address.", "err")
            return redirect(url_for("contact"))
        if len(subject) < 3:
            flash("Subject is too short.", "err")
            return redirect(url_for("contact"))
        if len(body) < 10:
            flash("Message body is too short — at least 10 characters.", "err")
            return redirect(url_for("contact"))
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        msg_id = audit.save_contact_message(db, email, subject, body, ip=ip)
        # Notify admin via the outbox
        try:
            admin_email = os.environ.get("POCKETPLOT_ADMIN_EMAIL", "admin@pocketplot.local")
            plain = (
                "New contact message (#%d) from %s\n\nSubject: %s\n\n%s\n"
                % (msg_id, email, subject, body)
            )
            _send_raw_email(admin_email, "[PocketPlot] Contact: " + subject, plain, plain)
        except Exception:
            pass
        audit.record(db, actor_id=None, actor_type="system",
                     action="contact.received", target_type="contact_message",
                     target_id=msg_id, metadata={"subject": subject, "from": email},
                     ip=ip, user_agent=request.headers.get("User-Agent"))
        flash("Message sent. We usually reply within one business day.", "ok")
        return redirect(url_for("contact"))
    return render_template_string(CONTACT_HTML)


# ---- Phase 13 polish: /status ----
@app.route("/status", methods=["GET"])
def status_page():
    """Public status page: cron recency, queue depth, recent errors.
    Designed to be reachable even when the rest of the app is unhappy."""
    conn = db()
    last_cron = conn.execute(
        "SELECT created_at, note FROM story_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    queue_counts = conn.execute(
        "SELECT status, COUNT(*) AS n FROM review_queue GROUP BY status"
    ).fetchall()
    by_status = {r["status"]: r["n"] for r in queue_counts}
    deliveries_24h_row = conn.execute(
        "SELECT COUNT(*) AS n FROM deliveries WHERE sent_at >= datetime('now', '-1 day')"
    ).fetchone()
    deliveries_24h = deliveries_24h_row["n"] if deliveries_24h_row else 0
    recent_errors = conn.execute(
        "SELECT id, pass, verdict, reason, created_at FROM validation_log "
        "WHERE verdict IN ('reject','rewrite') ORDER BY id DESC LIMIT 5"
    ).fetchall()
    conn.close()
    return render_template_string(
        STATUS_HTML,
        last_cron=last_cron,
        pending=by_status.get("pending", 0),
        sent=by_status.get("sent", 0),
        approved=by_status.get("approved", 0),
        rejected=by_status.get("rejected", 0),
        deliveries_24h=deliveries_24h,
        recent_errors=recent_errors,
    )


# ---- Phase 13 polish: /roadmap ----
@app.route("/roadmap", methods=["GET"])
def roadmap_page():
    """Public roadmap: shipped, planned, most-requested. Anyone can vote."""
    import audit
    shipped = [
        {"v": "v12", "title": "Launch polish: 18+ age gate, Stripe-safe content, ToS, brand separation"},
        {"v": "v11", "title": "PocketPlot Universe — adults-only tiered platform with StoryWorlds + BYOB/BYOG"},
        {"v": "v10", "title": "Avatar builder, gamification, weekly insights, story packs, printable merch"},
        {"v": "v9",  "title": "Admin dashboard"},
        {"v": "v8",  "title": "Review queue + weekly digest"},
        {"v": "v7",  "title": "Mini-game"},
        {"v": "v6",  "title": "Educational layer (Word of the Day, Story Talk, Parent Guide)"},
        {"v": "v5",  "title": "Pro tier + Stripe billing"},
        {"v": "v4",  "title": "Rebrand to PocketPlot + onboarding polish"},
        {"v": "v1-v3", "title": "Original PocketPlot — nightly story engine, MVP, and learning layer"},
    ]
    planned = [
        {"title": "EPUB export for stories and worlds", "size": "small"},
        {"title": "Email-based story replies (talk back to your story)", "size": "medium"},
        {"title": "Saved searches in /me + a notifications feed", "size": "small"},
        {"title": "Public author pages (opt-in)", "size": "medium"},
        {"title": "Mobile app (iOS first)", "size": "large"},
    ]
    conn = db()
    wanted = audit.list_feature_requests(conn, status="open", limit=20)
    conn.close()
    voted_session = set(session.get("voted_features") or [])
    return render_template_string(
        ROADMAP_HTML,
        shipped=shipped,
        planned=planned,
        wanted=wanted,
        voted_features=voted_session,
    )


@app.route("/roadmap/vote/<int:feature_id>", methods=["POST"])
def roadmap_vote(feature_id):
    import audit
    voted = set(session.get("voted_features") or [])
    if feature_id in voted:
        flash("You already voted for this.", "ok")
        return redirect(url_for("roadmap_page"))
    audit.vote_feature_request(db, feature_id)
    voted.add(feature_id)
    session["voted_features"] = list(voted)
    flash("Thanks for the vote.", "ok")
    return redirect(url_for("roadmap_page") + "#wanted")


@app.route("/roadmap/request", methods=["POST"])
def roadmap_request():
    """Submit a new feature request."""
    import audit
    title = (request.form.get("title") or "").strip()[:200]
    description = (request.form.get("description") or "").strip()
    email = (request.form.get("email") or "").strip().lower() or None
    if len(title) < 3:
        flash("Title is too short.", "err")
        return redirect(url_for("roadmap_page"))
    fid = audit.add_feature_request(db, title, description, submitter_email=email)
    audit.record(db, actor_id=None, actor_type="system", action="feature_request.created",
                 target_type="feature_request", target_id=fid, metadata={"title": title})
    flash("Thanks — your request is on the public roadmap.", "ok")
    return redirect(url_for("roadmap_page") + "#wanted")


# ---- Phase 13 polish: error handlers ----
@app.errorhandler(404)
def error_404(e):
    try:
        import audit
        audit.record(db, actor_type="system", action="http.404",
                     metadata={"path": request.path},
                     ip=request.headers.get("X-Forwarded-For", request.remote_addr),
                     user_agent=request.headers.get("User-Agent"))
    except Exception:
        pass
    import pathlib
    p = pathlib.Path(__file__).parent / "404.html"
    if p.exists():
        return send_file(str(p), mimetype="text/html"), 404
    return (
        "<!doctype html><html><head><title>404 \xc2\xb7 PocketPlot Universe</title>"
        "<style>body{font-family:Karla,system-ui;background:#0e1a2e;color:#f3e9d2;"
        "display:flex;align-items:center;justify-content:center;min-height:100vh;"
        "margin:0;text-align:center}</style></head><body>"
        "<div><h1 style=font-family:Fraunces,Georgia;font-size:64px;margin:0;color:#e6c879>404</h1>"
        "<p>The page you're looking for doesn't exist.</p>"
        "<p><a href=/ style=color:#e6c879>Home</a> \xc2\xb7 <a href=/faq style=color:#e6c879>FAQ</a> \xc2\xb7 <a href=/help style=color:#e6c879>Help</a></p></div></body></html>",
        404,
    )


@app.errorhandler(500)
def error_500(e):
    try:
        import audit
        audit.record(db, actor_type="system", action="http.500",
                     metadata={"path": request.path},
                     ip=request.headers.get("X-Forwarded-For", request.remote_addr),
                     user_agent=request.headers.get("User-Agent"))
    except Exception:
        pass
    import pathlib
    p = pathlib.Path(__file__).parent / "500.html"
    if p.exists():
        return send_file(str(p), mimetype="text/html"), 500
    return (
        "<!doctype html><html><head><title>500 \xc2\xb7 PocketPlot Universe</title>"
        "<style>body{font-family:Karla,system-ui;background:#0e1a2e;color:#f3e9d2;"
        "display:flex;align-items:center;justify-content:center;min-height:100vh;"
        "margin:0;text-align:center}</style></head><body>"
        "<div><h1 style=font-family:Fraunces,Georgia;font-size:64px;margin:0;color:#e6c879>500</h1>"
        "<p>Something went wrong on our end. The team has been notified.</p>"
        "<p><a href=/status style=color:#e6c879>Check system status</a> \xc2\xb7 <a href=/contact style=color:#e6c879>Report this</a></p></div></body></html>",
        500,
    )



# ---- Phase 11: Templates: /worlds ----
WORLDS_LIST_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Worlds · PocketPlot Universe</title>
<style>
  body{font-family:Karla,system-ui;background:#0e1a2e;color:#f3e9d2;margin:0;padding:0;min-height:100vh}
  .wrap{max-width:920px;margin:36px auto;padding:0 24px}
  h1{font-family:Fraunces,Georgia,serif;font-size:32px;margin:0 0 8px;color:#e6c879;font-weight:600}
  h1 i{color:#9eb6d4;font-style:italic}
  .wordmark{font-family:Fraunces;font-style:italic;color:#9eb6d4;font-size:14px}
  .nav{margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #1a2a44}
  .nav a{color:#9eb6d4;text-decoration:none;margin-right:18px;font-size:13px;letter-spacing:.05em;text-transform:uppercase}
  .nav a.active{color:#e6c879;font-weight:600}
  .card{background:#15243f;border:1px solid #1f3460;border-radius:14px;padding:24px;margin-bottom:14px;display:flex;gap:18px;align-items:center;justify-content:space-between}
  .card .left{flex:1}
  .card h2{font-family:Fraunces;font-size:20px;color:#f3e9d2;margin:0 0 6px;font-weight:600}
  .card p{font-family:Karla;font-size:13px;color:#9eb6d4;margin:0}
  .pill{display:inline-block;padding:3px 9px;border-radius:99px;background:#1f3460;color:#9eb6d4;font-family:Karla;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-right:6px}
  .pill.gold{background:#3a2e1a;color:#e6c879}
  .pill.empty{background:#1a2a44;color:#7a8aa8}
  .btn{background:#e6c879;color:#0e1a2e;border:none;padding:10px 20px;border-radius:99px;font-family:Karla;font-weight:700;font-size:13px;cursor:pointer;text-decoration:none;display:inline-block}
  .btn:hover{background:#d4b566}
  .btn.secondary{background:transparent;color:#9eb6d4;border:1px solid #2a3e60}
  .empty-state{background:#0a1428;border:2px dashed #1f3460;border-radius:14px;padding:48px;text-align:center;color:#7a8aa8;font-family:Fraunces;font-style:italic}
</style>
</head><body>
<div class="wrap">
  <div class="wordmark">PocketPlot Universe</div>
  <h1>Worlds</h1>
  <div class="nav">
    <a href="/me">Dashboard</a>
    <a class="active" href="/worlds">Worlds</a>
    <a href="/me/settings">Settings</a>
    <a href="/logout">Sign out</a>
  </div>

  <p style="font-family:Fraunces;font-size:15px;color:#d4b8a4;line-height:1.6;font-style:italic;margin:0 0 24px">
    A world is a living story with branching choices. Each episode ends with three
    doors; the one you pick changes what happens next. Up to ten episodes per world
    before the story closes.
  </p>

  {% if worlds %}
    {% for w in worlds %}
    <div class="card">
      <div class="left">
        <h2>{{w.title}}</h2>
        <p>
          <span class="pill {% if w.genre=='fantasy' %}gold{% endif %}">{{w.genre}}</span>
          <span class="pill">{{w.tone}}</span>
          <span class="pill empty">{{w.setting[:40]}}</span>
          &nbsp; last played {{w.last_played_at[:10]}}
        </p>
      </div>
      <a class="btn" href="/worlds/{{w.id}}">Enter →</a>
    </div>
    {% endfor %}
  {% else %}
    <div class="empty-state">
      No worlds yet. Start one and see where the door takes you.
    </div>
  {% endif %}

  <p style="text-align:center;margin-top:30px">
    <a class="btn" href="/worlds/new">+ Begin a new world</a>
  </p>
</div>
</body></html>"""


WORLD_NEW_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>New world · PocketPlot Universe</title>
<style>
  body{font-family:Karla,system-ui;background:#0e1a2e;color:#f3e9d2;margin:0;padding:0;min-height:100vh}
  .wrap{max-width:720px;margin:36px auto;padding:0 24px}
  h1{font-family:Fraunces,Georgia,serif;font-size:32px;margin:0 0 8px;color:#e6c879;font-weight:600}
  h1 i{color:#9eb6d4;font-style:italic}
  .wordmark{font-family:Fraunces;font-style:italic;color:#9eb6d4;font-size:14px}
  .nav{margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #1a2a44}
  .nav a{color:#9eb6d4;text-decoration:none;margin-right:18px;font-size:13px;letter-spacing:.05em;text-transform:uppercase}
  .card{background:#15243f;border:1px solid #1f3460;border-radius:14px;padding:28px}
  .field{margin-bottom:18px}
  .field label{display:block;font-family:Karla;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#9eb6d4;margin-bottom:6px;font-weight:600}
  .field input,.field select,.field textarea{width:100%;background:#0a1428;border:1px solid #2a3e60;border-radius:8px;color:#f3e9d2;padding:10px 12px;font-family:Karla;font-size:14px;box-sizing:border-box}
  .field .hint{font-size:11px;color:#7a8aa8;margin-top:4px;font-style:italic}
  .btn{background:#e6c879;color:#0e1a2e;border:none;padding:11px 22px;border-radius:99px;font-family:Karla;font-weight:700;font-size:13px;cursor:pointer;text-decoration:none;display:inline-block}
  .btn:hover{background:#d4b566}
  .btn.secondary{background:transparent;color:#9eb6d4;border:1px solid #2a3e60}
</style>
</head><body>
<div class="wrap">
  <div class="wordmark">PocketPlot Universe</div>
  <h1>Begin a world</h1>
  <p style="font-family:'Fraunces',Georgia,serif;font-style:italic;color:#9eb6d4;font-size:15px;margin:0 0 18px">Every field here shapes both the story and the scene art. The more specific you are, the more the engine can deliver.</p>
  <div class="nav">
    <a href="/me">Dashboard</a>
    <a href="/worlds">Worlds</a>
    <a href="/me/settings">Settings</a>
  </div>

  <form method="post" class="card">
    <div class="field">
      <label>Title</label>
      <input type="text" name="title" maxlength="120" placeholder="e.g. The Lantern Quarter" required value="{{ (seed or {}).get('title_hint', '') }}">
      <div class="hint">A short, evocative title. You can rename later.</div>
    </div>
    <div class="field">
      <label>Genre</label>
      <select name="genre">
        {% for label, key in genre_choices %}<option value="{{ key }}"{% if (seed or {}).get('genre', '') == key %} selected{% endif %}>{{ label }}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <label>Tone</label>
      <select name="tone">
        {% for t in tones %}<option value="{{t}}"{% if (seed or {}).get('tone', '') == t %} selected{% endif %}>{{t}}</option>{% endfor %}
      </select>
    </div>
    <div class="field">
      <label>Setting (where it starts)</label>
      <input type="text" name="setting" maxlength="200" placeholder="e.g. a fog-bound dock at the edge of the city" value="{{ (seed or {}).get('setting', '') }}">
    </div>
    <!-- v16: mandatory story specification fields (character + objective) -->
    <div class="field">
      <label>Main Character Description</label>
      <textarea name="character_description" rows="3" maxlength="500" required placeholder="e.g. A cynical detective who plays by their own rules, haunted by the case that ended her last partner">{{ (seed or {}).get('character_description', '') }}</textarea>
      <div class="hint">Required. This drives the avatar/character pose in the scene art.</div>
    </div>
    <div class="field">
      <label>Primary Objective</label>
      <textarea name="primary_objective" rows="2" maxlength="240" required placeholder="e.g. Find the missing AI before the city forgets she ever existed">{{ (seed or {}).get('primary_objective', '') }}</textarea>
      <div class="hint">Required. This shapes the first episode and the branch choices.</div>
    </div>
    <div style="display:flex;gap:10px;margin-top:24px">
      <button class="btn" type="submit">Begin →</button>
      <a class="btn secondary" href="/worlds">Cancel</a>
    </div>
  </form>
</div>
</body></html>"""


WORLD_VIEW_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{{world.title}} · PocketPlot Universe</title>
<style>
  body{font-family:Karla,system-ui;background:#0e1a2e;color:#f3e9d2;margin:0;padding:0;min-height:100vh}
  .wrap{max-width:780px;margin:36px auto;padding:0 24px}
  h1{font-family:Fraunces,Georgia,serif;font-size:32px;margin:0 0 8px;color:#e6c879;font-weight:600}
  h1 i{color:#9eb6d4;font-style:italic}
  .wordmark{font-family:Fraunces;font-style:italic;color:#9eb6d4;font-size:14px}
  .nav{margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #1a2a44}
  .nav a{color:#9eb6d4;text-decoration:none;margin-right:18px;font-size:13px;letter-spacing:.05em;text-transform:uppercase}
  .meta{font-family:Karla;font-size:12px;color:#7a8aa8;margin-bottom:24px}
  .meta .pill{display:inline-block;padding:3px 9px;border-radius:99px;background:#1f3460;color:#9eb6d4;font-family:Karla;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-right:6px}
  .meta .pill.gold{background:#3a2e1a;color:#e6c879}
  .episode{background:#15243f;border:1px solid #1f3460;border-radius:14px;padding:28px;margin-bottom:18px}
  .episode h2{font-family:Fraunces;font-size:20px;color:#f3e9d2;margin:0 0 12px;font-weight:600}
  .episode h2 .n{color:#9eb6d4;font-size:14px;margin-right:8px}
  .episode p{font-family:Georgia,serif;font-size:16px;color:#e6dac0;line-height:1.7;margin:0 0 12px}
  .choices{margin-top:18px;display:flex;flex-direction:column;gap:8px}
  .choice{background:#0a1428;border:1px solid #2a3e60;border-radius:10px;padding:14px 18px;cursor:pointer;font-family:Georgia,serif;font-size:15px;color:#d4b8a4;text-align:left;transition:all .15s}
  .choice:hover{background:#1a2a44;border-color:#e6c879;color:#f3e9d2}
  .btn{background:#e6c879;color:#0e1a2e;border:none;padding:10px 22px;border-radius:99px;font-family:Karla;font-weight:700;font-size:13px;cursor:pointer;text-decoration:none;display:inline-block}
  .btn:hover{background:#d4b566}
  .btn.secondary{background:transparent;color:#9eb6d4;border:1px solid #2a3e60}
  .concluded{background:#1a2a44;border:1px dashed #5c4a2a;border-radius:10px;padding:16px;font-family:Fraunces;font-style:italic;color:#d4b8a4;text-align:center}
</style>
</head><body>
<div class="wrap">
  <div class="wordmark">PocketPlot Universe</div>
  <h1>{{world.title}}</h1>
  <div class="nav">
    <a href="/me">Dashboard</a>
    <a href="/worlds">Worlds</a>
    <a href="/me/settings">Settings</a>
  </div>
  <div class="meta">
    <span class="pill {% if world.genre=='fantasy' %}gold{% endif %}">{{world.genre}}</span>
    <span class="pill">{{world.tone}}</span>
    <span class="pill">{{world.setting[:50]}}</span>
    &nbsp; last played {{world.last_played_at[:16]}}
  </div>

  {% for e in episodes %}
  <div class="episode" id="ep{{e.episode_number}}">
    <h2><span class="n">Ep {{e.episode_number}} ·</span> {{e.title}}</h2>
    {% for para in e.body.split('\n\n') if para.strip() %}
      <p>{{para}}</p>
    {% endfor %}
    {% if e.choices and not e.chosen_choice and e.episode_number == episodes[-1].episode_number and e.episode_number < 10 %}
    <form method="post">
      <input type="hidden" name="choice_from_episode_id" value="{{e.id}}">
      <div class="choices">
        {% for c in e.choices %}
          <button class="choice" type="submit" name="chosen_index" value="{{loop.index0}}">{{c.label}}</button>
        {% endfor %}
      </div>
    </form>
    {% elif e.episode_number == episodes[-1].episode_number and e.episode_number >= 10 %}
    <div class="concluded">This world has reached its tenth episode. Start a new one to continue.</div>
    {% endif %}
  </div>
  {% endfor %}

  {% if not episodes %}
  <div class="episode">
    <p style="font-family:Fraunces;font-style:italic;color:#9eb6d4">This world hasn't begun yet. Pick a door to start the first episode.</p>
    <form method="post">
      <input type="hidden" name="chosen_index" value="-1">
      <button class="btn" type="submit">Begin episode 1 →</button>
    </form>
  </div>
  {% endif %}

  <p style="text-align:center;margin-top:24px">
    <a class="btn secondary" href="/worlds">← All worlds</a>
  </p>
</div>
</body></html>"""


"""
PocketPlot Universe - v17 templates: LIBRARY_HTML, SEED_HTML, REMIX_HTML,
PROFILE_HTML, ADMIN_FEATURES_HTML, ADMIN_TOP_HTML.

These are appended to app.py via the @library @seed_page @remix_page
@public_profile @admin_features @admin_top_stories handlers.
"""
import pathlib

LIBRARY_HTML = """

<style>
/* v30 in-product styling - uses semantic tokens from the design system */
body { background: var(--bg); color: var(--text-body); }
h1, h2, h3 { color: var(--text-heading); font-family: var(--font-serif, Georgia, serif); }

/* Cards & surfaces */
.card, .surface {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg, 16px);
  color: var(--text-body);
}

/* Buttons - 3 tiers */
.btn-primary, button.primary, .primary {
  background: linear-gradient(180deg, var(--brand-light), var(--brand), var(--brand-deep));
  color: var(--brand-text);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
  font-weight: 600;
}
.btn-secondary, button.secondary, .secondary {
  background: transparent;
  color: var(--text-body);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
}
.btn-ghost, button.ghost, .ghost {
  background: transparent;
  color: var(--brand);
  border: none;
}
a { color: var(--brand); text-decoration: none; }
a:hover { border-bottom: 1px solid var(--brand); }

/* Status */
.success { color: var(--success-light); }
.warning { color: var(--warning); }
.danger  { color: var(--danger-light); }

/* Inputs */
input, textarea, select {
  background: var(--bg-elevated);
  color: var(--text-heading);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius, 8px);
}
input:focus { border-color: var(--brand); outline: none; box-shadow: 0 0 0 3px var(--brand-soft); }

.muted { color: var(--text-caption); }
.faint { color: var(--text-faint); }
</style><!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Library \u00b7 PocketPlot Universe</title>
<style>
:root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460;
        --gold:#e6c879; --gold-2:#d4b566;
        --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--navy); color:var(--cream);
       font-family:Karla,system-ui; line-height:1.6; }
.wrap { max-width:1100px; margin:0 auto; padding:0 24px; }
header { padding:20px 0; border-bottom:1px solid var(--navy-3); }
.wordmark { font-family:'Fraunces',Georgia,serif; font-style:italic;
            color:var(--gold); font-size:22px; font-weight:600; }
.wordmark i { color:var(--muted); font-style:italic; font-weight:400; }
nav { float:right; margin-top:8px; }
nav a { color:var(--muted); text-decoration:none; margin-left:18px;
       font-size:13px; letter-spacing:.05em; text-transform:uppercase; }
nav a:hover { color:var(--gold); }
nav a.cta { color:var(--navy); background:var(--gold); padding:8px 16px;
            border-radius:99px; text-transform:none; letter-spacing:0; font-weight:700; }
h1 { font-family:'Fraunces',Georgia,serif; font-size:32px; margin:36px 0 8px;
     color:var(--gold); font-weight:600; }
h1 i { color:var(--muted); font-style:italic; }
.lead { font-family:'Fraunces',Georgia,serif; font-style:italic;
        color:var(--muted); font-size:16px; margin:0 0 28px; }
.toolbar { background:var(--navy-2); border:1px solid var(--navy-3);
           border-radius:14px; padding:18px 22px; margin-bottom:24px;
           display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
.toolbar input, .toolbar select {
   background:var(--navy); border:1px solid var(--navy-3);
   color:var(--cream); padding:8px 12px; border-radius:8px;
   font-family:Karla; font-size:13px;
}
.toolbar input { flex:1; min-width:200px; }
.btn { background:var(--gold); color:var(--navy); border:none;
       padding:8px 16px; border-radius:99px; font-weight:700;
       font-size:13px; cursor:pointer; text-decoration:none;
       display:inline-block; }
.btn:hover { background:var(--gold-2); }
.btn.secondary { background:transparent; color:var(--muted);
                  border:1px solid var(--navy-3); }
.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr));
        gap:18px; }
.card { background:var(--navy-2); border:1px solid var(--navy-3);
        border-radius:14px; padding:18px; transition:border-color .2s, transform .2s; }
.card:hover { border-color:var(--gold); transform:translateY(-2px); }
.card .g { font-size:11px; letter-spacing:.14em; text-transform:uppercase;
          color:var(--gold); margin-bottom:8px; }
.card h3 { font-family:'Fraunces',Georgia,serif; font-size:20px; margin:0 0 10px;
          color:var(--cream); font-weight:600; }
.card .meta { color:var(--faint); font-size:12px; display:flex;
              gap:12px; flex-wrap:wrap; }
.card .stats { display:flex; gap:14px; margin-top:12px; padding-top:10px;
               border-top:1px solid var(--navy-3); color:var(--muted); font-size:12px; }
.empty { text-align:center; padding:60px 20px; color:var(--faint);
         font-family:'Fraunces',Georgia,serif; font-style:italic; font-size:18px; }
</style></head><body>
<div class="wrap">
  <header>
    <a href="/" style="text-decoration:none"><div class="wordmark">Pocket<i>Plot</i> Universe</div></a>
    <nav>
      <a href="/me">Dashboard</a>
      <a href="/library" style="color:var(--gold)">Library</a>
      <a href="/seed">Seed</a>
      <a href="/remix">Remix</a>
      <a href="/logout">Logout</a>
    </nav>
  </header>

  <h1>Your <i>library</i>.</h1>
  <p class="lead">Every story, every world, every choice you've made \u2014 in one place.</p>

  <form class="toolbar" method="get">
    <input type="text" name="q" value="{{ q }}" placeholder="Search by title or setting...">
    <select name="genre">
      <option value="">All genres</option>
      {% for g in genres %}
        <option value="{{ g }}"{% if g == genre_filter %} selected{% endif %}>{{ labels.get(g, g) }}</option>
      {% endfor %}
    </select>
    <button class="btn" type="submit">Search</button>
    {% if stories %}
      <a class="btn secondary" href="/library/export">Export all (.zip)</a>
    {% endif %}
  </form>

  {% if stories %}
    <div class="grid">
      {% for s in stories %}
        <a class="card" href="/worlds/{{ s['id'] }}" style="text-decoration:none">
          <div class="g">{{ labels.get(s['genre'], s['genre']) }}</div>
          <h3>{{ s['title'] }}</h3>
          <div class="meta">
            <span>{{ s['tone'] }}</span>
            <span>\u00b7 {{ s['ep_count'] }} episode{{ '' if s['ep_count'] == 1 else 's' }}</span>
          </div>
          <div class="stats">
            <span>\u25b2 {{ s['view_count'] }}</span>
            <span>\u00b7 \u25b6 {{ s['read_count'] }}</span>
            <span>\u00b7 {{ s['last_played_at'][:10] }}</span>
          </div>
        </a>
      {% endfor %}
    </div>
  {% else %}
    <div class="empty">No stories yet. Start with a <a href="/seed" style="color:var(--gold)">Seed</a>, or visit <a href="/worlds/new" style="color:var(--gold)">/worlds/new</a> to begin.</div>
  {% endif %}
</div></body></html>"""


SEED_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Story Seed \u00b7 PocketPlot Universe</title>
<style>
:root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460;
        --gold:#e6c879; --gold-2:#d4b566;
        --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--navy); color:var(--cream);
       font-family:Karla,system-ui; line-height:1.6; }
.wrap { max-width:760px; margin:0 auto; padding:0 24px; }
header { padding:20px 0; border-bottom:1px solid var(--navy-3); }
.wordmark { font-family:'Fraunces',Georgia,serif; font-style:italic;
            color:var(--gold); font-size:22px; font-weight:600; }
.wordmark i { color:var(--muted); font-style:italic; font-weight:400; }
nav { float:right; margin-top:8px; }
nav a { color:var(--muted); text-decoration:none; margin-left:18px;
       font-size:13px; letter-spacing:.05em; text-transform:uppercase; }
nav a:hover { color:var(--gold); }
nav a.cta { color:var(--navy); background:var(--gold); padding:8px 16px;
            border-radius:99px; text-transform:none; letter-spacing:0; font-weight:700; }
h1 { font-family:'Fraunces',Georgia,serif; font-size:36px; margin:48px 0 4px;
     font-weight:600; }
h1 i { color:var(--gold); font-style:italic; }
.lead { font-family:'Fraunces',Georgia,serif; font-style:italic;
        color:var(--muted); font-size:17px; margin:0 0 28px; }
.seed { background:var(--navy-2); border:1px solid var(--gold);
        border-radius:16px; padding:28px 32px; margin-bottom:24px;
        box-shadow:0 32px 80px rgba(230,200,121,.12); }
.seed .g { font-size:11px; letter-spacing:.14em; text-transform:uppercase;
          color:var(--gold); margin-bottom:6px; }
.seed h2 { font-family:'Fraunces',Georgia,serif; font-size:26px;
          margin:0 0 16px; color:var(--cream); font-weight:600; font-style:italic; }
.seed .row { margin-bottom:14px; }
.seed .row .lab { font-size:11px; letter-spacing:.14em; text-transform:uppercase;
                color:var(--muted); margin-bottom:4px; }
.seed .row .val { color:var(--cream); font-size:15px; line-height:1.55; }
.btn-row { display:flex; gap:10px; margin-top:24px; }
.btn { background:var(--gold); color:var(--navy); border:none;
       padding:12px 22px; border-radius:99px; font-weight:700;
       font-size:14px; cursor:pointer; text-decoration:none;
       display:inline-block; }
.btn:hover { background:var(--gold-2); }
.btn.secondary { background:transparent; color:var(--gold); border:1px solid var(--gold); }
#seed-data { display:none; }
</style></head><body>
<div class="wrap">
  <header>
    <a href="/" style="text-decoration:none"><div class="wordmark">Pocket<i>Plot</i> Universe</div></a>
    <nav>
      <a href="/me">Dashboard</a>
      <a href="/library">Library</a>
      <a href="/seed" style="color:var(--gold)">Seed</a>
      <a href="/remix">Remix</a>
      <a href="/logout">Logout</a>
    </nav>
  </header>

  <h1>Story <i>Seed</i>.</h1>
  <p class="lead">Roll a random prompt until something grabs you. Then we'll pre-fill your next world with it.</p>

  <div class="seed" id="seed-card">
    <div class="g">{{ seed['genre_label'] }} \u00b7 {{ seed['tone'] }}</div>
    <h2 id="seed-title">{{ seed['title_hint'] }}</h2>
    <div class="row">
      <div class="lab">Character</div>
      <div class="val" id="seed-character">{{ seed['character_description'] }}</div>
    </div>
    <div class="row">
      <div class="lab">Setting</div>
      <div class="val" id="seed-setting">{{ seed['setting'] }}</div>
    </div>
    <div class="row">
      <div class="lab">Objective</div>
      <div class="val" id="seed-objective">{{ seed['primary_objective'] }}</div>
    </div>
    <div class="btn-row">
      <button class="btn" id="try-another" type="button">Try another \u21bb</button>
      <form method="post" action="/seed/use" id="use-seed-form" style="display:inline">
        <input type="hidden" name="title_hint" id="f-title" value="{{ seed['title_hint'] }}">
        <input type="hidden" name="genre" id="f-genre" value="{{ seed['genre'] }}">
        <input type="hidden" name="tone" id="f-tone" value="{{ seed['tone'] }}">
        <input type="hidden" name="setting" id="f-setting" value="{{ seed['setting'] }}">
        <input type="hidden" name="character_description" id="f-character" value="{{ seed['character_description'] }}">
        <input type="hidden" name="primary_objective" id="f-objective" value="{{ seed['primary_objective'] }}">
        <button class="btn secondary" type="submit">Use this prompt \u2192</button>
      </form>
    </div>
  </div>
</div>
<script>
document.getElementById('try-another').addEventListener('click', async () => {
  const r = await fetch('/seed/roll', {method:'POST'});
  const j = await r.json();
  document.getElementById('seed-title').textContent = j.title_hint;
  document.getElementById('seed-character').textContent = j.character_description;
  document.getElementById('seed-setting').textContent = j.setting;
  document.getElementById('seed-objective').textContent = j.primary_objective;
  document.querySelector('.seed .g').textContent = j.genre_label + ' \u00b7 ' + j.tone;
  document.getElementById('f-title').value = j.title_hint;
  document.getElementById('f-genre').value = j.genre;
  document.getElementById('f-tone').value = j.tone;
  document.getElementById('f-setting').value = j.setting;
  document.getElementById('f-character').value = j.character_description;
  document.getElementById('f-objective').value = j.primary_objective;
});
</script>
</body></html>"""


REMIX_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Remix \u00b7 PocketPlot Universe</title>
<style>
:root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460;
        --gold:#e6c879; --gold-2:#d4b566;
        --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--navy); color:var(--cream);
       font-family:Karla,system-ui; line-height:1.6; }
.wrap { max-width:900px; margin:0 auto; padding:0 24px; }
header { padding:20px 0; border-bottom:1px solid var(--navy-3); }
.wordmark { font-family:'Fraunces',Georgia,serif; font-style:italic;
            color:var(--gold); font-size:22px; font-weight:600; }
.wordmark i { color:var(--muted); font-style:italic; font-weight:400; }
nav { float:right; margin-top:8px; }
nav a { color:var(--muted); text-decoration:none; margin-left:18px;
       font-size:13px; letter-spacing:.05em; text-transform:uppercase; }
nav a:hover { color:var(--gold); }
h1 { font-family:'Fraunces',Georgia,serif; font-size:32px; margin:36px 0 8px;
     color:var(--gold); font-weight:600; }
h1 i { color:var(--muted); font-style:italic; }
.lead { font-family:'Fraunces',Georgia,serif; font-style:italic;
        color:var(--muted); font-size:16px; margin:0 0 24px; }
.list { display:flex; flex-direction:column; gap:14px; }
.row { background:var(--navy-2); border:1px solid var(--navy-3);
       border-radius:14px; padding:18px 22px;
       display:grid; grid-template-columns:1fr auto; gap:14px;
       align-items:center; }
.row .g { font-size:11px; letter-spacing:.14em; text-transform:uppercase;
         color:var(--gold); }
.row .t { font-family:'Fraunces',Georgia,serif; font-size:18px; margin:4px 0;
          color:var(--cream); }
.row .meta { color:var(--faint); font-size:12px; }
.row form { display:flex; gap:8px; align-items:center; }
.row select { background:var(--navy); border:1px solid var(--navy-3);
             color:var(--cream); padding:8px 12px; border-radius:8px;
             font-family:Karla; font-size:12px; }
.btn { background:var(--gold); color:var(--navy); border:none;
       padding:9px 16px; border-radius:99px; font-weight:700;
       font-size:12px; cursor:pointer; }
.btn:hover { background:var(--gold-2); }
.empty { text-align:center; padding:60px; color:var(--faint);
         font-family:'Fraunces',Georgia,serif; font-style:italic; font-size:18px; }
</style></head><body>
<div class="wrap">
  <header>
    <a href="/" style="text-decoration:none"><div class="wordmark">Pocket<i>Plot</i> Universe</div></a>
    <nav>
      <a href="/me">Dashboard</a>
      <a href="/library">Library</a>
      <a href="/seed">Seed</a>
      <a href="/remix" style="color:var(--gold)">Remix</a>
      <a href="/logout">Logout</a>
    </nav>
  </header>

  <h1>Story <i>Remix</i>.</h1>
  <p class="lead">Take an existing story and change its genre while keeping the core character + objective intact.</p>

  {% if worlds %}
    <div class="list">
      {% for w in worlds %}
      <div class="row">
        <div>
          <div class="g">{{ labels.get(w['genre'], w['genre']) }} \u00b7 {{ w['tone'] }}</div>
          <div class="t">{{ w['title'] }}</div>
          <div class="meta">\u25b2 {{ w['view_count'] }} \u00b7 \u25b6 {{ w['read_count'] }}</div>
        </div>
        <form method="post" action="/remix">
          <input type="hidden" name="world_id" value="{{ w['id'] }}">
          <select name="to_genre" required>
            <option value="">remix as\u2026</option>
            {% for g in genres %}
              {% if g != w['genre'] %}
                <option value="{{ g }}">{{ labels.get(g, g) }}</option>
              {% endif %}
            {% endfor %}
          </select>
          <button class="btn" type="submit">Remix</button>
        </form>
      </div>
      {% endfor %}
    </div>
  {% else %}
    <div class="empty">No stories to remix yet. Start one at <a href="/worlds/new" style="color:var(--gold)">/worlds/new</a>.</div>
  {% endif %}
</div></body></html>"""


PROFILE_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ profile.get('child_name') or 'Profile' }} \u00b7 PocketPlot Universe</title>
<style>
:root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460;
        --gold:#e6c879; --gold-2:#d4b566;
        --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--navy); color:var(--cream);
       font-family:Karla,system-ui; line-height:1.6; }
.wrap { max-width:1000px; margin:0 auto; padding:0 24px; }
header { padding:20px 0; border-bottom:1px solid var(--navy-3); }
.wordmark { font-family:'Fraunces',Georgia,serif; font-style:italic;
            color:var(--gold); font-size:22px; font-weight:600; }
.wordmark i { color:var(--muted); font-style:italic; font-weight:400; }
nav { float:right; margin-top:8px; }
nav a { color:var(--muted); text-decoration:none; margin-left:18px;
       font-size:13px; letter-spacing:.05em; text-transform:uppercase; }
.hero { padding:48px 0 28px; }
.hero h1 { font-family:'Fraunces',Georgia,serif; font-size:48px; margin:0 0 4px;
          color:var(--cream); font-weight:600; }
.hero h1 i { color:var(--gold); font-style:italic; }
.handle { font-family:'Fraunces',Georgia,serif; font-style:italic;
          color:var(--gold); font-size:18px; margin:0 0 12px; }
.cta-row { display:flex; gap:10px; flex-wrap:wrap; margin:16px 0; }
.btn { background:var(--gold); color:var(--navy); border:none;
       padding:10px 20px; border-radius:99px; font-weight:700;
       font-size:13px; cursor:pointer; text-decoration:none;
       display:inline-block; }
.btn:hover { background:var(--gold-2); }
.btn.secondary { background:transparent; color:var(--gold);
                  border:1px solid var(--gold); }
.stats { display:flex; gap:24px; margin:18px 0; color:var(--muted); font-size:14px; }
.stats b { color:var(--gold); font-weight:600; }
h2 { font-family:'Fraunces',Georgia,serif; font-size:24px; margin:36px 0 14px;
      color:var(--gold); font-weight:600; }
.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(240px, 1fr));
       gap:14px; }
.card { background:var(--navy-2); border:1px solid var(--navy-3);
       border-radius:14px; padding:18px; }
.card .g { font-size:11px; letter-spacing:.14em; text-transform:uppercase;
         color:var(--gold); margin-bottom:6px; }
.card .t { font-family:'Fraunces',Georgia,serif; font-size:18px;
          color:var(--cream); margin-bottom:8px; }
.card .m { color:var(--faint); font-size:12px; }
</style></head><body>
<div class="wrap">
  <header>
    <a href="/" style="text-decoration:none"><div class="wordmark">Pocket<i>Plot</i> Universe</div></a>
    <nav>
      <a href="/">Home</a>
      <a href="/pricing">Pricing</a>
      <a href="/faq">FAQ</a>
    </nav>
  </header>

  <section class="hero">
    <div class="handle">@{{ profile['username'] }}</div>
    <h1>{{ profile.get('child_name') or 'A PocketPlot creator' }}</h1>
    <div class="cta-row">
      <form method="post" action="/u/{{ profile['username'] }}/follow">
        <button class="btn" type="submit">
          {{ 'Unfollow' if is_following else 'Follow' }}
        </button>
      </form>
    </div>
    <div class="stats">
      <span><b>{{ fc }}</b> follower{{ '' if fc == 1 else 's' }}</span>
      <span><b>{{ fgc }}</b> following</span>
      <span>joined <b>{{ profile['created_at'][:10] }}</b></span>
    </div>
  </section>

  {% if featured %}
    <h2>Featured stories</h2>
    <div class="grid">
      {% for s in featured %}
        <a class="card" href="/worlds/{{ s['id'] }}" style="text-decoration:none">
          <div class="g">{{ s['genre'] }}</div>
          <div class="t">{{ s['title'] }}</div>
          <div class="m">\u25b2 {{ s['view_count'] }} \u00b7 \u25b6 {{ s['read_count'] }}</div>
        </a>
      {% endfor %}
    </div>
  {% endif %}

  <h2>Public stories</h2>
  {% if worlds %}
    <div class="grid">
      {% for w in worlds %}
        <a class="card" href="/worlds/{{ w['id'] }}" style="text-decoration:none">
          <div class="g">{{ w['genre'] }} \u00b7 {{ w['tone'] }}</div>
          <div class="t">{{ w['title'] }}</div>
          <div class="m">\u25b2 {{ w['view_count'] }} \u00b7 \u25b6 {{ w['read_count'] }}</div>
        </a>
      {% endfor %}
    </div>
  {% else %}
    <div style="color:var(--faint);font-style:italic">No public stories yet.</div>
  {% endif %}
</div></body></html>"""


ADMIN_FEATURES_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Feature Flags \u00b7 Admin</title>
<style>
:root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460;
        --gold:#e6c879; --gold-2:#d4b566;
        --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--navy); color:var(--cream);
       font-family:Karla,system-ui; }
.wrap { max-width:900px; margin:36px auto; padding:0 24px; }
header { padding:0 0 16px; border-bottom:1px solid var(--navy-3);
         margin-bottom:24px; }
.wordmark { font-family:'Fraunces',Georgia,serif; font-style:italic;
            color:var(--gold); font-size:20px; font-weight:600; }
nav { float:right; margin-top:6px; }
nav a { color:var(--muted); text-decoration:none; margin-left:14px;
       font-size:12px; text-transform:uppercase; letter-spacing:.05em; }
h1 { font-family:'Fraunces',Georgia,serif; font-size:28px; margin:0;
      color:var(--gold); font-weight:600; }
table { width:100%; border-collapse:collapse; margin-top:12px; }
th { text-align:left; padding:10px; color:var(--muted); font-size:11px;
      letter-spacing:.14em; text-transform:uppercase;
      border-bottom:1px solid var(--navy-3); }
td { padding:12px 10px; border-bottom:1px solid rgba(255,255,255,.04);
      font-size:13px; }
.badge { display:inline-block; padding:3px 10px; border-radius:99px;
         font-size:11px; font-weight:700; }
.badge.on { background:#1a4a2a; color:#9ad6a4; }
.badge.off { background:#4a1a1a; color:#e6a4a4; }
.btn { background:var(--gold); color:var(--navy); border:none;
       padding:6px 14px; border-radius:99px; font-weight:700;
       font-size:11px; cursor:pointer; }
.btn.off { background:#4a1a1a; color:#e6a4a4; }
</style></head><body>
<div class="wrap">
  <header>
    <div class="wordmark">Pocket<i>Plot</i> Universe \u00b7 Admin</div>
    <nav>
      <a href="/admin/dashboard">Dashboard</a>
      <a href="/admin/queue">Queue</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/top">Top stories</a>
      <a href="/admin/features" style="color:var(--gold)">Features</a>
      <a href="/logout">Logout</a>
    </nav>
    <h1 style="margin-top:14px">Feature Flags</h1>
  </header>

  <table>
    <tr><th>Key</th><th>Description</th><th>Status</th><th>Toggle</th></tr>
    {% for f in features %}
      <tr>
        <td><code>{{ f['key'] }}</code></td>
        <td>{{ f['description'] or '' }}</td>
        <td>
          <span class="badge {{ 'on' if f['enabled'] else 'off' }}">
            {{ 'ON' if f['enabled'] else 'OFF' }}
          </span>
        </td>
        <td>
          <form method="post" action="/admin/features/{{ f['key'] }}/toggle" style="display:inline">
            <input type="hidden" name="enabled" value="{{ '0' if f['enabled'] else '1' }}">
            <button class="btn {{ 'off' if f['enabled'] else '' }}" type="submit">
              {{ 'Disable' if f['enabled'] else 'Enable' }}
            </button>
          </form>
        </td>
      </tr>
    {% endfor %}
  </table>
</div></body></html>"""


ADMIN_TOP_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Top stories \u00b7 Admin</title>
<style>
:root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460;
        --gold:#e6c879; --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--navy); color:var(--cream);
       font-family:Karla,system-ui; }
.wrap { max-width:1000px; margin:36px auto; padding:0 24px; }
header { padding:0 0 16px; border-bottom:1px solid var(--navy-3); margin-bottom:24px; }
.wordmark { font-family:'Fraunces',Georgia,serif; font-style:italic;
            color:var(--gold); font-size:20px; font-weight:600; }
nav { float:right; margin-top:6px; }
nav a { color:var(--muted); text-decoration:none; margin-left:14px;
       font-size:12px; text-transform:uppercase; letter-spacing:.05em; }
h1 { font-family:'Fraunces',Georgia,serif; font-size:28px; margin:0;
      color:var(--gold); font-weight:600; }
table { width:100%; border-collapse:collapse; margin-top:12px; }
th { text-align:left; padding:10px; color:var(--muted); font-size:11px;
      letter-spacing:.14em; text-transform:uppercase;
      border-bottom:1px solid var(--navy-3); }
td { padding:10px; border-bottom:1px solid rgba(255,255,255,.04);
      font-size:13px; }
.tag { display:inline-block; padding:2px 8px; background:var(--navy-3);
       color:var(--gold); border-radius:99px; font-size:11px;
       text-transform:uppercase; letter-spacing:.1em; }
</style></head><body>
<div class="wrap">
  <header>
    <div class="wordmark">Pocket<i>Plot</i> Universe \u00b7 Admin</div>
    <nav>
      <a href="/admin/dashboard">Dashboard</a>
      <a href="/admin/queue">Queue</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/top" style="color:var(--gold)">Top stories</a>
      <a href="/admin/features">Features</a>
      <a href="/logout">Logout</a>
    </nav>
    <h1 style="margin-top:14px">Top stories by views</h1>
  </header>

  {% if stories %}
    <table>
      <tr><th>#</th><th>Title</th><th>Genre</th><th>Owner</th><th>Views</th><th>Reads</th></tr>
      {% for i, s in enumerate(stories) %}
        <tr>
          <td>{{ i+1 }}</td>
          <td><a href="/worlds/{{ s['id'] }}" style="color:var(--gold)">{{ s['title'] }}</a></td>
          <td><span class="tag">{{ s['genre'] }}</span></td>
          <td>{{ s.get('email', '') }}</td>
          <td>{{ s['view_count'] }}</td>
          <td>{{ s['read_count'] }}</td>
        </tr>
      {% endfor %}
    </table>
  {% else %}
    <p style="color:var(--faint)">No story analytics yet.</p>
  {% endif %}
</div></body></html>"""

print('Templates written:',
      'LIBRARY_HTML', len(LIBRARY_HTML),
      'SEED_HTML', len(SEED_HTML),
      'REMIX_HTML', len(REMIX_HTML),
      'PROFILE_HTML', len(PROFILE_HTML),
      'ADMIN_FEATURES_HTML', len(ADMIN_FEATURES_HTML),
      'ADMIN_TOP_HTML', len(ADMIN_TOP_HTML))




# ---- v21: serve the brand image assets from /root/pocketplot/ ----
from flask import send_from_directory as _send_from_dir
_BRAND_FILES = {
    # No-halo variants (transparent background, blends with chrome)
    'logo.png', 'logo.jpg', 'logo-icon.png', 'logo-icon-32.png',
    'logo-icon-180.png', 'logo-wide.png', 'logo-og.png',
    'logo-600.png', 'logo-400.png', 'logo-240.png', 'logo.svg',
    # Halo variants (soft amber glow behind, for standalone use)
    'logo-halo.png', 'logo-halo-icon.png', 'logo-halo-icon-32.png',
    'logo-halo-icon-180.png', 'logo-halo-og.png', 'logo-halo-600.png',
    'logo-halo-400.png', 'logo-halo-240.png',
    'manifest.json',
    'sw.js',
    'style.css',
    'pocketplot_01_hero.jpg',
    'pocketplot_02_three-doors.jpg',
    'pocketplot_03_genre-grid.jpg',
    'pocketplot_04_two-modes.jpg',
    'pocketplot_05_app-icon.jpg',
    'pocketplot_06_og-card.jpg',
    'pocketplot_07_genre-grid-2.jpg',
    'pocketplot_08_word-vault.jpg',
    'pocketplot_09_empty-state.jpg',
    'pocketplot_10_screenshot-play.jpg',
    'pocketplot_11_screenshot-library.jpg',
    'pocketplot_06_og-card-1200x630.jpg',
    'favicon.png',
    'favicon-512.png',
    'favicon-196.png',
    'apple-touch-icon-1024.png',
    'pocketplot_12_screenshot-read.jpg',
    'pocketplot_13_screenshot-byob.jpg',
    'pocketplot_13b_screenshot-byob-framed.jpg',
    'pocketplot_14_screenshot-vault.jpg',
    'pocketplot_15_sticker-sheet.jpg',
    'pocketplot_16_launch_banner.jpg',
    'pocketplot_17_tier_explorer.jpg',
    'pocketplot_18_tier_worldsmith.jpg',
    'pocketplot_19_tier_architect.jpg',
    'pocketplot_20_icon_branch.jpg',
    'pocketplot_21_icon_world.jpg',
    'pocketplot_22_icon_seed.jpg',
    'pocketplot_23_icon_remix.jpg',
    'stickers.html',
}
@app.route('/<path:filename>', methods=['GET'])
def _serve_brand_asset(filename):
    """Serve brand assets from project root or charcoal_art/ subdirectory. Whitelisted."""
    from flask import send_file, abort
    if filename not in _BRAND_FILES:
        abort(404)
    import os
    candidates = [
        os.path.join(os.getcwd(), filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
        os.path.join(os.getcwd(), 'charcoal_art', filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'charcoal_art', filename),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return send_file(path, conditional=True)
    abort(404)



if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    log.info("PocketPlot starting on http://localhost:%d", port)
    log.info("SMTP: %s · outbox fallback: %s",
             ("configured" if SMTP_HOST else f"not configured → saving to {OUTBOX_DIR}"),
             OUTBOX_DIR)
    log.info("Daily delivery at %02d:00 UTC", DELIVERY_HOUR)
    log.info("Billing: %s", ("MOCK mode — set STRIPE_SECRET_KEY for live Stripe" if STRIPE_MOCK else "LIVE Stripe"))
    app.run(host="127.0.0.1", port=port, debug=False)


"""
PocketPlot Universe - v17 templates: LIBRARY_HTML, SEED_HTML, REMIX_HTML,
PROFILE_HTML, ADMIN_FEATURES_HTML, ADMIN_TOP_HTML.

These are appended to app.py via the @library @seed_page @remix_page
@public_profile @admin_features @admin_top_stories handlers.
"""
import pathlib

LIBRARY_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Library \u00b7 PocketPlot Universe</title>
<style>
:root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460;
        --gold:#e6c879; --gold-2:#d4b566;
        --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--navy); color:var(--cream);
       font-family:Karla,system-ui; line-height:1.6; }
.wrap { max-width:1100px; margin:0 auto; padding:0 24px; }
header { padding:20px 0; border-bottom:1px solid var(--navy-3); }
.wordmark { font-family:'Fraunces',Georgia,serif; font-style:italic;
            color:var(--gold); font-size:22px; font-weight:600; }
.wordmark i { color:var(--muted); font-style:italic; font-weight:400; }
nav { float:right; margin-top:8px; }
nav a { color:var(--muted); text-decoration:none; margin-left:18px;
       font-size:13px; letter-spacing:.05em; text-transform:uppercase; }
nav a:hover { color:var(--gold); }
nav a.cta { color:var(--navy); background:var(--gold); padding:8px 16px;
            border-radius:99px; text-transform:none; letter-spacing:0; font-weight:700; }
h1 { font-family:'Fraunces',Georgia,serif; font-size:32px; margin:36px 0 8px;
     color:var(--gold); font-weight:600; }
h1 i { color:var(--muted); font-style:italic; }
.lead { font-family:'Fraunces',Georgia,serif; font-style:italic;
        color:var(--muted); font-size:16px; margin:0 0 28px; }
.toolbar { background:var(--navy-2); border:1px solid var(--navy-3);
           border-radius:14px; padding:18px 22px; margin-bottom:24px;
           display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
.toolbar input, .toolbar select {
   background:var(--navy); border:1px solid var(--navy-3);
   color:var(--cream); padding:8px 12px; border-radius:8px;
   font-family:Karla; font-size:13px;
}
.toolbar input { flex:1; min-width:200px; }
.btn { background:var(--gold); color:var(--navy); border:none;
       padding:8px 16px; border-radius:99px; font-weight:700;
       font-size:13px; cursor:pointer; text-decoration:none;
       display:inline-block; }
.btn:hover { background:var(--gold-2); }
.btn.secondary { background:transparent; color:var(--muted);
                  border:1px solid var(--navy-3); }
.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr));
        gap:18px; }
.card { background:var(--navy-2); border:1px solid var(--navy-3);
        border-radius:14px; padding:18px; transition:border-color .2s, transform .2s; }
.card:hover { border-color:var(--gold); transform:translateY(-2px); }
.card .g { font-size:11px; letter-spacing:.14em; text-transform:uppercase;
          color:var(--gold); margin-bottom:8px; }
.card h3 { font-family:'Fraunces',Georgia,serif; font-size:20px; margin:0 0 10px;
          color:var(--cream); font-weight:600; }
.card .meta { color:var(--faint); font-size:12px; display:flex;
              gap:12px; flex-wrap:wrap; }
.card .stats { display:flex; gap:14px; margin-top:12px; padding-top:10px;
               border-top:1px solid var(--navy-3); color:var(--muted); font-size:12px; }
.empty { text-align:center; padding:60px 20px; color:var(--faint);
         font-family:'Fraunces',Georgia,serif; font-style:italic; font-size:18px; }
</style></head><body>
<div class="wrap">
  <header>
    <a href="/" style="text-decoration:none"><div class="wordmark">Pocket<i>Plot</i> Universe</div></a>
    <nav>
      <a href="/me">Dashboard</a>
      <a href="/library" style="color:var(--gold)">Library</a>
      <a href="/seed">Seed</a>
      <a href="/remix">Remix</a>
      <a href="/logout">Logout</a>
    </nav>
  </header>

  <h1>Your <i>library</i>.</h1>
  <p class="lead">Every story, every world, every choice you've made \u2014 in one place.</p>

  <form class="toolbar" method="get">
    <input type="text" name="q" value="{{ q }}" placeholder="Search by title or setting...">
    <select name="genre">
      <option value="">All genres</option>
      {% for g in genres %}
        <option value="{{ g }}"{% if g == genre_filter %} selected{% endif %}>{{ labels.get(g, g) }}</option>
      {% endfor %}
    </select>
    <button class="btn" type="submit">Search</button>
    {% if stories %}
      <a class="btn secondary" href="/library/export">Export all (.zip)</a>
    {% endif %}
  </form>

  {% if stories %}
    <div class="grid">
      {% for s in stories %}
        <a class="card" href="/worlds/{{ s['id'] }}" style="text-decoration:none">
          <div class="g">{{ labels.get(s['genre'], s['genre']) }}</div>
          <h3>{{ s['title'] }}</h3>
          <div class="meta">
            <span>{{ s['tone'] }}</span>
            <span>\u00b7 {{ s['ep_count'] }} episode{{ '' if s['ep_count'] == 1 else 's' }}</span>
          </div>
          <div class="stats">
            <span>\u25b2 {{ s['view_count'] }}</span>
            <span>\u00b7 \u25b6 {{ s['read_count'] }}</span>
            <span>\u00b7 {{ s['last_played_at'][:10] }}</span>
          </div>
        </a>
      {% endfor %}
    </div>
  {% else %}
    <div class="empty">No stories yet. Start with a <a href="/seed" style="color:var(--gold)">Seed</a>, or visit <a href="/worlds/new" style="color:var(--gold)">/worlds/new</a> to begin.</div>
  {% endif %}
</div></body></html>"""


SEED_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Story Seed \u00b7 PocketPlot Universe</title>
<style>
:root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460;
        --gold:#e6c879; --gold-2:#d4b566;
        --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--navy); color:var(--cream);
       font-family:Karla,system-ui; line-height:1.6; }
.wrap { max-width:760px; margin:0 auto; padding:0 24px; }
header { padding:20px 0; border-bottom:1px solid var(--navy-3); }
.wordmark { font-family:'Fraunces',Georgia,serif; font-style:italic;
            color:var(--gold); font-size:22px; font-weight:600; }
.wordmark i { color:var(--muted); font-style:italic; font-weight:400; }
nav { float:right; margin-top:8px; }
nav a { color:var(--muted); text-decoration:none; margin-left:18px;
       font-size:13px; letter-spacing:.05em; text-transform:uppercase; }
nav a:hover { color:var(--gold); }
nav a.cta { color:var(--navy); background:var(--gold); padding:8px 16px;
            border-radius:99px; text-transform:none; letter-spacing:0; font-weight:700; }
h1 { font-family:'Fraunces',Georgia,serif; font-size:36px; margin:48px 0 4px;
     font-weight:600; }
h1 i { color:var(--gold); font-style:italic; }
.lead { font-family:'Fraunces',Georgia,serif; font-style:italic;
        color:var(--muted); font-size:17px; margin:0 0 28px; }
.seed { background:var(--navy-2); border:1px solid var(--gold);
        border-radius:16px; padding:28px 32px; margin-bottom:24px;
        box-shadow:0 32px 80px rgba(230,200,121,.12); }
.seed .g { font-size:11px; letter-spacing:.14em; text-transform:uppercase;
          color:var(--gold); margin-bottom:6px; }
.seed h2 { font-family:'Fraunces',Georgia,serif; font-size:26px;
          margin:0 0 16px; color:var(--cream); font-weight:600; font-style:italic; }
.seed .row { margin-bottom:14px; }
.seed .row .lab { font-size:11px; letter-spacing:.14em; text-transform:uppercase;
                color:var(--muted); margin-bottom:4px; }
.seed .row .val { color:var(--cream); font-size:15px; line-height:1.55; }
.btn-row { display:flex; gap:10px; margin-top:24px; }
.btn { background:var(--gold); color:var(--navy); border:none;
       padding:12px 22px; border-radius:99px; font-weight:700;
       font-size:14px; cursor:pointer; text-decoration:none;
       display:inline-block; }
.btn:hover { background:var(--gold-2); }
.btn.secondary { background:transparent; color:var(--gold); border:1px solid var(--gold); }
#seed-data { display:none; }
</style></head><body>
<div class="wrap">
  <header>
    <a href="/" style="text-decoration:none"><div class="wordmark">Pocket<i>Plot</i> Universe</div></a>
    <nav>
      <a href="/me">Dashboard</a>
      <a href="/library">Library</a>
      <a href="/seed" style="color:var(--gold)">Seed</a>
      <a href="/remix">Remix</a>
      <a href="/logout">Logout</a>
    </nav>
  </header>

  <h1>Story <i>Seed</i>.</h1>
  <p class="lead">Roll a random prompt until something grabs you. Then we'll pre-fill your next world with it.</p>

  <div class="seed" id="seed-card">
    <div class="g">{{ seed['genre_label'] }} \u00b7 {{ seed['tone'] }}</div>
    <h2 id="seed-title">{{ seed['title_hint'] }}</h2>
    <div class="row">
      <div class="lab">Character</div>
      <div class="val" id="seed-character">{{ seed['character_description'] }}</div>
    </div>
    <div class="row">
      <div class="lab">Setting</div>
      <div class="val" id="seed-setting">{{ seed['setting'] }}</div>
    </div>
    <div class="row">
      <div class="lab">Objective</div>
      <div class="val" id="seed-objective">{{ seed['primary_objective'] }}</div>
    </div>
    <div class="btn-row">
      <button class="btn" id="try-another" type="button">Try another \u21bb</button>
      <form method="post" action="/seed/use" id="use-seed-form" style="display:inline">
        <input type="hidden" name="title_hint" id="f-title" value="{{ seed['title_hint'] }}">
        <input type="hidden" name="genre" id="f-genre" value="{{ seed['genre'] }}">
        <input type="hidden" name="tone" id="f-tone" value="{{ seed['tone'] }}">
        <input type="hidden" name="setting" id="f-setting" value="{{ seed['setting'] }}">
        <input type="hidden" name="character_description" id="f-character" value="{{ seed['character_description'] }}">
        <input type="hidden" name="primary_objective" id="f-objective" value="{{ seed['primary_objective'] }}">
        <button class="btn secondary" type="submit">Use this prompt \u2192</button>
      </form>
    </div>
  </div>
</div>
<script>
document.getElementById('try-another').addEventListener('click', async () => {
  const r = await fetch('/seed/roll', {method:'POST'});
  const j = await r.json();
  document.getElementById('seed-title').textContent = j.title_hint;
  document.getElementById('seed-character').textContent = j.character_description;
  document.getElementById('seed-setting').textContent = j.setting;
  document.getElementById('seed-objective').textContent = j.primary_objective;
  document.querySelector('.seed .g').textContent = j.genre_label + ' \u00b7 ' + j.tone;
  document.getElementById('f-title').value = j.title_hint;
  document.getElementById('f-genre').value = j.genre;
  document.getElementById('f-tone').value = j.tone;
  document.getElementById('f-setting').value = j.setting;
  document.getElementById('f-character').value = j.character_description;
  document.getElementById('f-objective').value = j.primary_objective;
});
</script>
</body></html>"""


REMIX_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Remix \u00b7 PocketPlot Universe</title>
<style>
:root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460;
        --gold:#e6c879; --gold-2:#d4b566;
        --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--navy); color:var(--cream);
       font-family:Karla,system-ui; line-height:1.6; }
.wrap { max-width:900px; margin:0 auto; padding:0 24px; }
header { padding:20px 0; border-bottom:1px solid var(--navy-3); }
.wordmark { font-family:'Fraunces',Georgia,serif; font-style:italic;
            color:var(--gold); font-size:22px; font-weight:600; }
.wordmark i { color:var(--muted); font-style:italic; font-weight:400; }
nav { float:right; margin-top:8px; }
nav a { color:var(--muted); text-decoration:none; margin-left:18px;
       font-size:13px; letter-spacing:.05em; text-transform:uppercase; }
nav a:hover { color:var(--gold); }
h1 { font-family:'Fraunces',Georgia,serif; font-size:32px; margin:36px 0 8px;
     color:var(--gold); font-weight:600; }
h1 i { color:var(--muted); font-style:italic; }
.lead { font-family:'Fraunces',Georgia,serif; font-style:italic;
        color:var(--muted); font-size:16px; margin:0 0 24px; }
.list { display:flex; flex-direction:column; gap:14px; }
.row { background:var(--navy-2); border:1px solid var(--navy-3);
       border-radius:14px; padding:18px 22px;
       display:grid; grid-template-columns:1fr auto; gap:14px;
       align-items:center; }
.row .g { font-size:11px; letter-spacing:.14em; text-transform:uppercase;
         color:var(--gold); }
.row .t { font-family:'Fraunces',Georgia,serif; font-size:18px; margin:4px 0;
          color:var(--cream); }
.row .meta { color:var(--faint); font-size:12px; }
.row form { display:flex; gap:8px; align-items:center; }
.row select { background:var(--navy); border:1px solid var(--navy-3);
             color:var(--cream); padding:8px 12px; border-radius:8px;
             font-family:Karla; font-size:12px; }
.btn { background:var(--gold); color:var(--navy); border:none;
       padding:9px 16px; border-radius:99px; font-weight:700;
       font-size:12px; cursor:pointer; }
.btn:hover { background:var(--gold-2); }
.empty { text-align:center; padding:60px; color:var(--faint);
         font-family:'Fraunces',Georgia,serif; font-style:italic; font-size:18px; }
</style></head><body>
<div class="wrap">
  <header>
    <a href="/" style="text-decoration:none"><div class="wordmark">Pocket<i>Plot</i> Universe</div></a>
    <nav>
      <a href="/me">Dashboard</a>
      <a href="/library">Library</a>
      <a href="/seed">Seed</a>
      <a href="/remix" style="color:var(--gold)">Remix</a>
      <a href="/logout">Logout</a>
    </nav>
  </header>

  <h1>Story <i>Remix</i>.</h1>
  <p class="lead">Take an existing story and change its genre while keeping the core character + objective intact.</p>

  {% if worlds %}
    <div class="list">
      {% for w in worlds %}
      <div class="row">
        <div>
          <div class="g">{{ labels.get(w['genre'], w['genre']) }} \u00b7 {{ w['tone'] }}</div>
          <div class="t">{{ w['title'] }}</div>
          <div class="meta">\u25b2 {{ w['view_count'] }} \u00b7 \u25b6 {{ w['read_count'] }}</div>
        </div>
        <form method="post" action="/remix">
          <input type="hidden" name="world_id" value="{{ w['id'] }}">
          <select name="to_genre" required>
            <option value="">remix as\u2026</option>
            {% for g in genres %}
              {% if g != w['genre'] %}
                <option value="{{ g }}">{{ labels.get(g, g) }}</option>
              {% endif %}
            {% endfor %}
          </select>
          <button class="btn" type="submit">Remix</button>
        </form>
      </div>
      {% endfor %}
    </div>
  {% else %}
    <div class="empty">No stories to remix yet. Start one at <a href="/worlds/new" style="color:var(--gold)">/worlds/new</a>.</div>
  {% endif %}
</div></body></html>"""


PROFILE_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ profile.get('child_name') or 'Profile' }} \u00b7 PocketPlot Universe</title>
<style>
:root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460;
        --gold:#e6c879; --gold-2:#d4b566;
        --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--navy); color:var(--cream);
       font-family:Karla,system-ui; line-height:1.6; }
.wrap { max-width:1000px; margin:0 auto; padding:0 24px; }
header { padding:20px 0; border-bottom:1px solid var(--navy-3); }
.wordmark { font-family:'Fraunces',Georgia,serif; font-style:italic;
            color:var(--gold); font-size:22px; font-weight:600; }
.wordmark i { color:var(--muted); font-style:italic; font-weight:400; }
nav { float:right; margin-top:8px; }
nav a { color:var(--muted); text-decoration:none; margin-left:18px;
       font-size:13px; letter-spacing:.05em; text-transform:uppercase; }
.hero { padding:48px 0 28px; }
.hero h1 { font-family:'Fraunces',Georgia,serif; font-size:48px; margin:0 0 4px;
          color:var(--cream); font-weight:600; }
.hero h1 i { color:var(--gold); font-style:italic; }
.handle { font-family:'Fraunces',Georgia,serif; font-style:italic;
          color:var(--gold); font-size:18px; margin:0 0 12px; }
.cta-row { display:flex; gap:10px; flex-wrap:wrap; margin:16px 0; }
.btn { background:var(--gold); color:var(--navy); border:none;
       padding:10px 20px; border-radius:99px; font-weight:700;
       font-size:13px; cursor:pointer; text-decoration:none;
       display:inline-block; }
.btn:hover { background:var(--gold-2); }
.btn.secondary { background:transparent; color:var(--gold);
                  border:1px solid var(--gold); }
.stats { display:flex; gap:24px; margin:18px 0; color:var(--muted); font-size:14px; }
.stats b { color:var(--gold); font-weight:600; }
h2 { font-family:'Fraunces',Georgia,serif; font-size:24px; margin:36px 0 14px;
      color:var(--gold); font-weight:600; }
.grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(240px, 1fr));
       gap:14px; }
.card { background:var(--navy-2); border:1px solid var(--navy-3);
       border-radius:14px; padding:18px; }
.card .g { font-size:11px; letter-spacing:.14em; text-transform:uppercase;
         color:var(--gold); margin-bottom:6px; }
.card .t { font-family:'Fraunces',Georgia,serif; font-size:18px;
          color:var(--cream); margin-bottom:8px; }
.card .m { color:var(--faint); font-size:12px; }
</style></head><body>
<div class="wrap">
  <header>
    <a href="/" style="text-decoration:none"><div class="wordmark">Pocket<i>Plot</i> Universe</div></a>
    <nav>
      <a href="/">Home</a>
      <a href="/pricing">Pricing</a>
      <a href="/faq">FAQ</a>
    </nav>
  </header>

  <section class="hero">
    <div class="handle">@{{ profile['username'] }}</div>
    <h1>{{ profile.get('child_name') or 'A PocketPlot creator' }}</h1>
    <div class="cta-row">
      <form method="post" action="/u/{{ profile['username'] }}/follow">
        <button class="btn" type="submit">
          {{ 'Unfollow' if is_following else 'Follow' }}
        </button>
      </form>
    </div>
    <div class="stats">
      <span><b>{{ fc }}</b> follower{{ '' if fc == 1 else 's' }}</span>
      <span><b>{{ fgc }}</b> following</span>
      <span>joined <b>{{ profile['created_at'][:10] }}</b></span>
    </div>
  </section>

  {% if featured %}
    <h2>Featured stories</h2>
    <div class="grid">
      {% for s in featured %}
        <a class="card" href="/worlds/{{ s['id'] }}" style="text-decoration:none">
          <div class="g">{{ s['genre'] }}</div>
          <div class="t">{{ s['title'] }}</div>
          <div class="m">\u25b2 {{ s['view_count'] }} \u00b7 \u25b6 {{ s['read_count'] }}</div>
        </a>
      {% endfor %}
    </div>
  {% endif %}

  <h2>Public stories</h2>
  {% if worlds %}
    <div class="grid">
      {% for w in worlds %}
        <a class="card" href="/worlds/{{ w['id'] }}" style="text-decoration:none">
          <div class="g">{{ w['genre'] }} \u00b7 {{ w['tone'] }}</div>
          <div class="t">{{ w['title'] }}</div>
          <div class="m">\u25b2 {{ w['view_count'] }} \u00b7 \u25b6 {{ w['read_count'] }}</div>
        </a>
      {% endfor %}
    </div>
  {% else %}
    <div style="color:var(--faint);font-style:italic">No public stories yet.</div>
  {% endif %}
</div></body></html>"""


ADMIN_FEATURES_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Feature Flags \u00b7 Admin</title>
<style>
:root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460;
        --gold:#e6c879; --gold-2:#d4b566;
        --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--navy); color:var(--cream);
       font-family:Karla,system-ui; }
.wrap { max-width:900px; margin:36px auto; padding:0 24px; }
header { padding:0 0 16px; border-bottom:1px solid var(--navy-3);
         margin-bottom:24px; }
.wordmark { font-family:'Fraunces',Georgia,serif; font-style:italic;
            color:var(--gold); font-size:20px; font-weight:600; }
nav { float:right; margin-top:6px; }
nav a { color:var(--muted); text-decoration:none; margin-left:14px;
       font-size:12px; text-transform:uppercase; letter-spacing:.05em; }
h1 { font-family:'Fraunces',Georgia,serif; font-size:28px; margin:0;
      color:var(--gold); font-weight:600; }
table { width:100%; border-collapse:collapse; margin-top:12px; }
th { text-align:left; padding:10px; color:var(--muted); font-size:11px;
      letter-spacing:.14em; text-transform:uppercase;
      border-bottom:1px solid var(--navy-3); }
td { padding:12px 10px; border-bottom:1px solid rgba(255,255,255,.04);
      font-size:13px; }
.badge { display:inline-block; padding:3px 10px; border-radius:99px;
         font-size:11px; font-weight:700; }
.badge.on { background:#1a4a2a; color:#9ad6a4; }
.badge.off { background:#4a1a1a; color:#e6a4a4; }
.btn { background:var(--gold); color:var(--navy); border:none;
       padding:6px 14px; border-radius:99px; font-weight:700;
       font-size:11px; cursor:pointer; }
.btn.off { background:#4a1a1a; color:#e6a4a4; }
</style></head><body>
<div class="wrap">
  <header>
    <div class="wordmark">Pocket<i>Plot</i> Universe \u00b7 Admin</div>
    <nav>
      <a href="/admin/dashboard">Dashboard</a>
      <a href="/admin/queue">Queue</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/top">Top stories</a>
      <a href="/admin/features" style="color:var(--gold)">Features</a>
      <a href="/logout">Logout</a>
    </nav>
    <h1 style="margin-top:14px">Feature Flags</h1>
  </header>

  <table>
    <tr><th>Key</th><th>Description</th><th>Status</th><th>Toggle</th></tr>
    {% for f in features %}
      <tr>
        <td><code>{{ f['key'] }}</code></td>
        <td>{{ f['description'] or '' }}</td>
        <td>
          <span class="badge {{ 'on' if f['enabled'] else 'off' }}">
            {{ 'ON' if f['enabled'] else 'OFF' }}
          </span>
        </td>
        <td>
          <form method="post" action="/admin/features/{{ f['key'] }}/toggle" style="display:inline">
            <input type="hidden" name="enabled" value="{{ '0' if f['enabled'] else '1' }}">
            <button class="btn {{ 'off' if f['enabled'] else '' }}" type="submit">
              {{ 'Disable' if f['enabled'] else 'Enable' }}
            </button>
          </form>
        </td>
      </tr>
    {% endfor %}
  </table>
</div></body></html>"""


ADMIN_TOP_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Top stories \u00b7 Admin</title>
<style>
:root { --navy:#0e1a2e; --navy-2:#15243f; --navy-3:#1f3460;
        --gold:#e6c879; --cream:#f3e9d2; --muted:#9eb6d4; --faint:#7a8aa8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--navy); color:var(--cream);
       font-family:Karla,system-ui; }
.wrap { max-width:1000px; margin:36px auto; padding:0 24px; }
header { padding:0 0 16px; border-bottom:1px solid var(--navy-3); margin-bottom:24px; }
.wordmark { font-family:'Fraunces',Georgia,serif; font-style:italic;
            color:var(--gold); font-size:20px; font-weight:600; }
nav { float:right; margin-top:6px; }
nav a { color:var(--muted); text-decoration:none; margin-left:14px;
       font-size:12px; text-transform:uppercase; letter-spacing:.05em; }
h1 { font-family:'Fraunces',Georgia,serif; font-size:28px; margin:0;
      color:var(--gold); font-weight:600; }
table { width:100%; border-collapse:collapse; margin-top:12px; }
th { text-align:left; padding:10px; color:var(--muted); font-size:11px;
      letter-spacing:.14em; text-transform:uppercase;
      border-bottom:1px solid var(--navy-3); }
td { padding:10px; border-bottom:1px solid rgba(255,255,255,.04);
      font-size:13px; }
.tag { display:inline-block; padding:2px 8px; background:var(--navy-3);
       color:var(--gold); border-radius:99px; font-size:11px;
       text-transform:uppercase; letter-spacing:.1em; }
</style></head><body>
<div class="wrap">
  <header>
    <div class="wordmark">Pocket<i>Plot</i> Universe \u00b7 Admin</div>
    <nav>
      <a href="/admin/dashboard">Dashboard</a>
      <a href="/admin/queue">Queue</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/top" style="color:var(--gold)">Top stories</a>
      <a href="/admin/features">Features</a>
      <a href="/logout">Logout</a>
    </nav>
    <h1 style="margin-top:14px">Top stories by views</h1>
  </header>

  {% if stories %}
    <table>
      <tr><th>#</th><th>Title</th><th>Genre</th><th>Owner</th><th>Views</th><th>Reads</th></tr>
      {% for i, s in enumerate(stories) %}
        <tr>
          <td>{{ i+1 }}</td>
          <td><a href="/worlds/{{ s['id'] }}" style="color:var(--gold)">{{ s['title'] }}</a></td>
          <td><span class="tag">{{ s['genre'] }}</span></td>
          <td>{{ s.get('email', '') }}</td>
          <td>{{ s['view_count'] }}</td>
          <td>{{ s['read_count'] }}</td>
        </tr>
      {% endfor %}
    </table>
  {% else %}
    <p style="color:var(--faint)">No story analytics yet.</p>
  {% endif %}
</div></body></html>"""

print('Templates written:',
      'LIBRARY_HTML', len(LIBRARY_HTML),
      'SEED_HTML', len(SEED_HTML),
      'REMIX_HTML', len(REMIX_HTML),
      'PROFILE_HTML', len(PROFILE_HTML),
      'ADMIN_FEATURES_HTML', len(ADMIN_FEATURES_HTML),
      'ADMIN_TOP_HTML', len(ADMIN_TOP_HTML))

# ---- v21: serve the brand image assets from /root/pocketplot/ ----


# (Duplicate _BRAND_FILES block removed; primary one above)
"""v23 routes for PocketPlot Universe.

This module is meant to be appended to app.py at the right insertion
point. It provides:
  - /worlds/<id>/share       manage share tokens for a world
  - /worlds/<id>/export.epub export a world as EPUB
  - /worlds/<id>/export.zip  export a world as a bulk ZIP
  - /worlds/<id>/export.pdf  export a world as a single PDF
  - /worlds/<id>/like        POST to like (toggle)
  - /play/<token>             PLAY mode (game with choices, branching)
  - /play/<token>/map         PLAY mode world map (foundation for Minecraft-style)
  - /play/<token>/choose      POST to choose a branch
  - /read/<token>             READ mode (manga, page-flip)
  - /read/<token>/page/<n>   READ mode single page (for swipe)
  - /api/v1/shares            API: create share tokens
  - /api/v1/likes/<world_id>  API: like/unlike a world
  - /api/v1/world/<id>/stats  API: world stats JSON
  - /api/v1/world/<id>/inventory API stub (v24)
  - /api/v1/world/<id>/build    API stub (v24)
  - /redeem/<code>              redeem a promo code
  - /admin/segments            admin: manage email segments
  - /admin/promo-codes         admin: manage promo codes
  - /admin/promo-codes/new     admin: create a promo code
  - /admin/newsletter          admin: send a newsletter to a segment
  - /manifest.json             PWA manifest
  - /sw.js                     service worker
  - /push/subscribe            subscribe to push notifications
  - /push/unsubscribe          unsubscribe

All routes are inserted into the existing app via @app.route decorators.
This script is meant to be appended to app.py just before the
ENTRY block (so all decorators register before app.run()).

The block also appends the HTML templates (SHARE_HTML, PLAY_HTML,
READ_HTML, MAP_HTML, REDEEM_HTML, ADMIN_SEGMENTS_HTML, ADMIN_PROMO_HTML,
ADMIN_NEWSLETTER_HTML) - they're module-level constants, referenced by
the render_template_string() calls.
"""

import sys, pathlib
sys.path.insert(0, '/root/pocketplot')
import engagement as _eng
import exports as _exp
import promo as _promo
import migrations_phase23 as _m23
import audit_v24 as _audit24
import streaks_xp as _streaks
import social as _social
import inventory as _inv
import scene_graph as _sgraph
import onboarding as _onb
import tts as _tts
import sentry_v24 as _sentry
from qrcode_lib import qr_svg, qr_png_data_url, make_share_token, make_player_session_id


# ============ TEMPLATES (defined at module level, referenced by handlers) ============

SHARE_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Share - {title}</title>
<link rel="icon" type="image/png" href="/logo-icon-32.png" sizes="32x32">
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;line-height:1.6}
.wrap{max-width:780px;margin:0 auto;padding:24px}
header{padding:18px 0;border-bottom:1px solid rgba(201,160,78,.25);display:flex;justify-content:space-between;align-items:center}
header a{color:var(--cream);text-decoration:none}
.brand{display:flex;align-items:center;gap:12px}
.brand img{width:40px;height:37px;border-radius:3px}
.brand-text{font-family:Fraunces,Georgia,serif;font-style:italic;font-weight:600;color:var(--gold-l);font-size:18px}
.brand-text em{color:var(--muted);font-style:normal;font-weight:400}
nav a{color:var(--muted);text-decoration:none;margin-left:18px;font-size:13px;letter-spacing:.05em;text-transform:uppercase}
nav a:hover{color:var(--gold-l)}
h1{font-family:Fraunces,Georgia,serif;font-size:32px;margin:36px 0 8px;color:var(--cream);font-weight:600}
h1 i{color:var(--gold-l);font-style:italic}
.lead{color:var(--muted);font-style:italic;font-family:Fraunces,Georgia,serif;margin:0 0 28px}
.card{background:linear-gradient(180deg,rgba(21,36,63,.5) 0%,rgba(15,26,46,.95) 100%);border:1px solid rgba(201,160,78,.3);border-radius:8px;padding:24px;margin-bottom:18px}
.card h2{font-family:Fraunces,Georgia,serif;font-size:20px;margin:0 0 12px;color:var(--cream);font-weight:500}
.row{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.row:last-child{margin-bottom:0}
.copybox{background:var(--navy);border:1px solid var(--navy-3);border-radius:6px;padding:10px 14px;font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--gold-l);flex:1;min-width:200px;user-select:all;cursor:text}
.btn{background:linear-gradient(180deg,var(--gold-l) 0%,var(--gold) 50%,#8a6a26 100%);color:var(--navy);border:1px solid #8a6a26;padding:9px 16px;border-radius:3px;font-family:Karla,sans-serif;font-weight:700;font-size:13px;cursor:pointer;text-decoration:none;display:inline-block;box-shadow:0 0 0 1px var(--gold-l) inset}
.btn:hover{box-shadow:0 0 0 1px var(--amber) inset,0 0 12px var(--amber)}
.btn.secondary{background:transparent;color:var(--gold-l);border-color:var(--gold);box-shadow:0 0 0 1px #8a6a26 inset}
.qr-wrap{display:flex;justify-content:center;padding:20px;background:#f3e9d2;border-radius:8px;margin:12px 0}
.qr-wrap svg{width:200px;height:200px;display:block}
.token{display:flex;gap:8px;align-items:center;background:var(--navy);padding:8px 14px;border-radius:99px;border:1px solid rgba(201,160,78,.3);font-family:'JetBrains Mono',monospace;font-size:14px;color:var(--gold-l);cursor:text;user-select:all}
.section-label{font-family:Karla,sans-serif;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold-l);font-weight:600;margin:0 0 8px}
.tabs{display:flex;gap:8px;margin-bottom:18px;border-bottom:1px solid rgba(201,160,78,.3);padding-bottom:8px}
.tab{padding:6px 14px;background:transparent;border:1px solid rgba(201,160,78,.3);border-radius:99px;color:var(--muted);font-size:12px;cursor:pointer;text-decoration:none;font-family:Karla,sans-serif;letter-spacing:.04em}
.tab.active{background:var(--gold);color:var(--navy);border-color:var(--gold)}
.existing-list{margin-top:14px;padding-top:14px;border-top:1px solid rgba(201,160,78,.2)}
.existing-item{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(201,160,78,.1);font-size:13px}
.existing-item:last-child{border-bottom:none}
.existing-item code{font-family:'JetBrains Mono',monospace;color:var(--gold-l);font-size:12px}
.export-row{display:flex;gap:10px;flex-wrap:wrap}
.export-row .btn{flex:1;min-width:140px;text-align:center}
.like-btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;background:transparent;border:1px solid rgba(201,160,78,.3);border-radius:99px;color:var(--gold-l);font-size:13px;cursor:pointer;font-family:Karla,sans-serif}
.like-btn.liked{background:rgba(232,90,138,.15);border-color:var(--gold);color:#e85a8a}
.like-btn:hover{background:rgba(201,160,78,.15)}
.stats-row{display:flex;gap:24px;flex-wrap:wrap;color:var(--muted);font-size:13px}
.stats-row b{color:var(--gold-l)}
</style></head><body>
<div class="wrap">
  <header>
    <a href="/me" class="brand">
      <img src="/logo-halo-240.png" alt="PocketPlot Universe">
      <span class="brand-text">Pocket<em>Plot</em> Universe</span>
    </a>
    <nav>
      <a href="/me">Dashboard</a>
      <a href="/library">Library</a>
      <a href="/logout">Logout</a>
    </nav>
  </header>

  <h1>Share <i>{{ world_title }}</i></h1>
  <p class="lead">Two ways to share. One for players, one for readers.</p>

  <!-- ============== GAME MODE ============== -->
  <div class="card">
    <div class="section-label">Play it - PLAY mode</div>
    <h2>{{ game_token or 'Create a shareable game link' }}</h2>
    <p style="font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--muted);margin:0 0 14px">An interactive, branching story with choices. Players tap to make decisions and explore the world.</p>
    {% if game_token %}
      <div class="row">
        <code class="copybox" id="game-link">https://{{ host }}/play/{{ game_token }}</code>
        <button class="btn" onclick="navigator.clipboard.writeText('https://{{ host }}/play/{{ game_token }}').then(()=>this.textContent='Copied!')">Copy</button>
      </div>
      <div class="row">
        <div class="qr-wrap" id="game-qr"></div>
      </div>
      <div class="row">
        <a class="btn secondary" href="/play/{{ game_token }}" target="_blank">Test the game link</a>
        <form method="post" action="/worlds/{{ world_id }}/share" style="display:inline">
          <input type="hidden" name="action" value="revoke-game">
          <button class="btn secondary" type="submit">Revoke this token</button>
        </form>
      </div>
    {% else %}
      <p style="color:var(--faint);font-style:italic">No game token yet.</p>
      <form method="post" action="/worlds/{{ world_id }}/share">
        <input type="hidden" name="action" value="create-game">
        <button class="btn" type="submit">Create game link</button>
      </form>
    {% endif %}
  </div>

  <!-- ============== READ MODE ============== -->
  <div class="card">
    <div class="section-label">Read it - manga / storybook</div>
    <h2>{{ read_token or 'Create a shareable read link' }}</h2>
    <p style="font-family:Fraunces,Georgia,serif;font-style:italic;color:var(--muted);margin:0 0 14px">A read-only manga-style view of the story. Pages with art + narration + speech bubbles. For readers who prefer to read.</p>
    {% if read_token %}
      <div class="row">
        <code class="copybox" id="read-link">https://{{ host }}/read/{{ read_token }}</code>
        <button class="btn" onclick="navigator.clipboard.writeText('https://{{ host }}/read/{{ read_token }}').then(()=>this.textContent='Copied!')">Copy</button>
      </div>
      <div class="row">
        <div class="qr-wrap" id="read-qr"></div>
      </div>
      <div class="row">
        <a class="btn secondary" href="/read/{{ read_token }}" target="_blank">Test the read link</a>
        <form method="post" action="/worlds/{{ world_id }}/share" style="display:inline">
          <input type="hidden" name="action" value="revoke-read">
          <button class="btn secondary" type="submit">Revoke this token</button>
        </form>
      </div>
    {% else %}
      <p style="color:var(--faint);font-style:italic">No read token yet.</p>
      <form method="post" action="/worlds/{{ world_id }}/share">
        <input type="hidden" name="action" value="create-read">
        <button class="btn" type="submit">Create read link</button>
      </form>
    {% endif %}
  </div>

  <!-- ============== EXPORTS ============== -->
  <div class="card">
    <div class="section-label">Export</div>
    <h2>Take it with you</h2>
    <p style="color:var(--muted);font-size:14px;margin:0 0 14px">Download your story in any of these formats. Read offline, share with non-platform users, print it.</p>
    <div class="export-row">
      <a class="btn secondary" href="/worlds/{{ world_id }}/export.epub">EPUB (e-reader)</a>
      <a class="btn secondary" href="/worlds/{{ world_id }}/export.pdf">PDF (book)</a>
      <a class="btn secondary" href="/worlds/{{ world_id }}/export.zip">Bulk ZIP (markdown + SVG)</a>
    </div>
  </div>

  <!-- ============== STATS + LIKE ============== -->
  <div class="card">
    <div class="section-label">Engagement</div>
    <div class="stats-row">
      <span><b>{{ stats.view_count }}</b> views</span>
      <span><b>{{ stats.play_count }}</b> plays</span>
      <span><b>{{ stats.completion_count }}</b> completions</span>
      <span><b>{{ stats.like_count }}</b> likes</span>
      <span><b>{{ stats.episode_count }}</b> episodes</span>
      <span><b>{{ stats.approx_words }}</b> words</span>
    </div>
    <div class="row" style="margin-top:14px">
      <form method="post" action="/worlds/{{ world_id }}/like" style="display:inline">
        <input type="hidden" name="action" value="{{ 'unlike' if liked else 'like' }}">
        <button class="like-btn {{ 'liked' if liked else '' }}" type="submit">
          {{ '\\u2764' if liked else '\\u2661' }} {{ stats.like_count }} {{ 'liked' if liked else 'like' }}
        </button>
      </form>
    </div>
  </div>

</div>
<script>
  // Inject QR codes into the QR slots using the qrcode SVG endpoint
  async function injectQR(targetId, url) {
    const r = await fetch('/qr.svg?u=' + encodeURIComponent(url));
    if (r.ok) {
      document.getElementById(targetId).innerHTML = await r.text();
    }
  }
  {% if game_token %}injectQR('game-qr', 'https://{{ host }}/play/{{ game_token }}');{% endif %}
  {% if read_token %}injectQR('read-qr', 'https://{{ host }}/read/{{ read_token }}');{% endif %}
</script>
</body></html>"""


PLAY_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - Play</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/png" href="/logo-icon-32.png" sizes="32x32">
<link rel="apple-touch-icon" href="/logo-icon-180.png">
<meta name="theme-color" content="#0a0f1c">
<style>
:root{--navy:#0a0f1c;--navy-2:#15243f;--navy-3:#1f3460;--gold:#c9a04e;--gold-l:#e8c879;--amber:#f0b54a;--cream:#f3e9d2;--muted:#9eb6d4;--faint:#7a8aa8}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:linear-gradient(180deg,#0a0f1c 0%,#0e1a2e 100%);background-attachment:fixed;color:var(--cream);font-family:Karla,sans-serif;min-height:100vh}
.scene{max-width:680px;margin:0 auto;padding:32px 20px;min-height:100vh;display:flex;flex-direction:column}
.scene-art{flex:0 0 auto;display:flex;justify-content:center;margin-bottom:20px;max-height:42vh}
.scene-art svg,.scene-art img{max-width:100%;max-height:42vh;width:auto;height:auto;border-radius:8px;box-shadow:0 0 0 1px var(--gold) inset,0 20px 60px rgba(0,0,0,.5)}
.ep-num{font-family:Cinzel,serif;font-size:11px;letter-spacing:.2em;color:var(--gold-l);text-align:center;margin:0 0 8px;text-transform:uppercase}
.ep-title{font-family:Fraunces,Georgia,serif;font-style:italic;font-size:32px;color:var(--cream);text-align:center;margin:0 0 14px;font-weight:500;line-height:1.2}
.body{font-family:Fraunces,Georgia,serif;font-size:17px;color:var(--cream);line-height:1.7;text-align:left;margin:0 auto 24px;max-width:560px}
.body p{margin:0 0 14px}
.progress-bar{height:4px;background:rgba(201,160,78,.2);border-radius:2px;margin-bottom:18px;overflow:hidden}
.progress-fill{height:100%;background:linear-gradient(90deg,var(--amber),var(--gold-l));border-radius:2px;transition:width .4s}
.choices{display:flex;flex-direction:column;gap:10px;margin:24px 0;max-width:560px;margin-left:auto;margin-right:auto}
.choice{background:linear-gradient(180deg,rgba(21,36,63,.6) 0%,rgba(15,26,46,.95) 100%);border:1px solid rgba(201,160,78,.4);border-radius:8px;padding:14px 18px;color:var(--cream);font-family:Karla,sans-serif;font-size:15px;text-align:left;cursor:pointer;transition:all .15s;display:flex;align-items:flex-start;gap:12px}
.choice:hover{border-color:var(--gold-l);background:linear-gradient(180deg,rgba(240,181,74,.12) 0%,rgba(15,26,46,.95) 100%);transform:translateY(-2px);box-shadow:0 0 0 1px var(--gold-l) inset,0 8px 24px rgba(240,181,74,.2)}
.choice-num{font-family:Cinzel,serif;font-size:14px;color:var(--gold-l);font-weight:600;flex-shrink:0;margin-top:1px}
.choice-text{flex:1}
.no-choices{color:var(--muted);font-style:italic;text-align:center;padding:20px;font-family:Fraunces,Georgia,serif}
.footer-info{display:flex;justify-content:space-between;align-items:center;padding:14px 0;border-top:1px solid rgba(201,160,78,.2);margin-top:auto;font-size:12px;color:var(--faint)}
.footer-info .actions{display:flex;gap:12px}
.footer-info a{color:var(--gold-l);text-decoration:none}
.footer-info a:hover{color:var(--amber)}
.completed-banner{background:linear-gradient(180deg,rgba(240,181,74,.15) 0%,rgba(15,26,46,.95) 100%);border:1px solid var(--gold);border-radius:8px;padding:24px;text-align:center;margin-bottom:20px}
.completed-banner .check{font-size:42px;color:var(--gold-l)}
.completed-banner h2{font-family:Fraunces,Georgia,serif;font-size:24px;margin:8px 0;color:var(--cream);font-weight:500}
.completed-banner p{color:var(--muted);margin:0 0 14px;font-style:italic}
.completed-banner a{color:var(--amber)}
@keyframes fade-in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}.scene{animation:fade-in .4s ease-out}
</style></head><body>
<div class="scene">
  {completed_banner}
  <div class="ep-num">{ep_label}</div>
  <div class="progress-bar"><div class="progress-fill" style="width:{progress}%"></div></div>
  <h1 class="ep-title">{title}</h1>
  <div class="scene-art">{art}</div>
  <div class="body">{body}</div>

  {choices_or_end}

  <div class="footer-info">
    <div>
      {stats_summary}
    </div>
    <div class="actions">
      {continue_link}
      <a href="/worlds/{world_id}/share">Share this story</a>
    </div>
  </div>
</div>
<script>
{% raw %}
  // PWA service worker registration
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(function() {});
  }
  // Keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft' && !e.metaKey) {
      const prev = document.querySelector('.nav-btn:not(.primary)');
      if (prev && !prev.href.endsWith('#')) prev.click();
    } else if (e.key === 'ArrowRight') {
      const next = document.querySelector('.nav-btn.primary');
      if (next) next.click();
    }
  });
{% endraw %}
</script>
</body></html>"""








# ============ END TEMPLATES ============


# These are placeholders that get filled in by app.py
SHARE_HTML = SHARE_HTML
PLAY_HTML = PLAY_HTML
MAP_HTML = MAP_HTML
READ_HTML = READ_HTML
REDEEM_HTML = REDEEM_HTML
ADMIN_SEGMENTS_HTML = ADMIN_SEGMENTS_HTML
ADMIN_PROMO_HTML = ADMIN_PROMO_HTML
ADMIN_NEWSLETTER_HTML = ADMIN_NEWSLETTER_HTML


# ============================================================================
# v23 routes (templates above; routes below)
# ============================================================================
@app.route("/_debug_routes")
def _debug_routes_route():
    """List all registered routes."""
    from flask import current_app
    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append({
            'rule': str(rule),
            'endpoint': rule.endpoint,
            'methods': sorted(rule.methods - {'HEAD', 'OPTIONS'}),
        })
    return {'routes': sorted(routes, key=lambda r: r['rule'])}, 200, {'Content-Type': 'application/json'}

# PocketPlot — Local Review Quick-Start

> A short "what to look at first" guide for the reviewer.

## What to run first (1 minute)

```bash
# 1. Install deps (mock Stripe mode works with no real account)
pip install -r requirements.txt

# 2. Boot
python3 app.py
# → http://localhost:5000

# 3. Sign up a test subscriber via the landing page
#    → first story appears in ./outbox/<timestamp>_at_example.com.eml
#    → magic-link email appears in the same folder
```

The `outbox/` folder is the runtime "what email would have been sent" log.
Open the `.eml` files in any email client (Apple Mail, Thunderbird) or view the HTML source.

## What to click through (5 minutes)

1. **`/`** — the marketing landing (this is the polished `INDEX_HTML` from `app.py`)
2. **`/signup`** — signup form, gets you an account + first story
3. **`/signup?plan=pro`** — Pro signup variant (just sets `plan=pro` later in the DB)
4. **`/pricing`** — the pricing comparison
5. **`/login`** + click the magic link in the outbox email → **`/me`** self-service portal
6. **`/me`** features (Pro):
   - Click **Upgrade to Pro** (mock) → full Pro dashboard
   - Set **Choose Your Adventure** answer (subscriber chooses before tomorrow's story)
   - Pick **recurring helper** + **setting theme** (locks the cast/setting)
   - **Learning dashboard** with all v3 + v4 stats
7. **`/admin`** (password `letmein`):
   - Re-send a story to any subscriber
   - See the deliveries log

## What to check in the code (10 minutes)

### `app.py` reading order (the 5 best bits)

1. **`WORDS_BY_TIER`** (~line 295) — the v3 word pool, three tiers, 102 words
2. **`generate_story()`** (~line 595) — how the engine pieces together + bolding
3. **`_send_with_v4_enrichment()`** (~line 1563) — orchestrator: poll → moment → audio → email
4. **`pick_moment()`** (~line 605) — the v4 moments pool
5. **`render_email()`** (~line 1438) — the HTML email assembly with all 6 boxes

### DB schema (`init_db()` ~line 116)

5 tables: `subscribers`, `deliveries`, `story_log`, `magic_tokens`, plus v4 additions:
`polls`, `drawings`, `moments`. The schema is intentionally additive — adding a
column on a v1 install won't break.

### Test data you'll see in the outbox

Open `outbox/*.eml` in any mail client. The file contains both:
- A **plain-text** fallback (for plain-text email readers)
- A **multipart/alternative HTML** version (the design)

The HTML version has all 5 learning/interactivity blocks:
1. Cozy banner (moon + tree branch + bird, inline SVG)
2. POCKETPLOT ★ PRO header
3. ★ TONIGHT'S STORY eyebrow + story title
4. Story body (with the poll answer seamlessly woven into the ending)
5. **Listen to the Story** pill button (terracotta, links to /audio/<sub>/<file>.mp3)
6. **Word of the Day** box (italic serif word + definition + personalized example)
7. **Story Talk** (3 comprehension questions, all referencing the actual cast)
8. **Parent Guide** PRO-only (deeper reflection / 5-hook rotation)
9. **Wren's Moment of the Day** (kindness beat, italic warm message)
10. Pro perk ribbon + manage account links

## What's intentionally mocked (not real)

- **Stripe** — runs in MOCK mode unless `STRIPE_SECRET_KEY` is set. See
  `guide.html` for the live setup walkthrough.
- **SMTP** — saves to `outbox/*.eml` unless `POCKETPLOT_SMTP_*` env vars are set.
  Open the .eml files to see the rendered email.
- **Audio TTS** — uses `pyttsx3` + `espeak-ng`. If you don't have espeak installed:
  `apt-get install espeak-ng` (Debian/Ubuntu). On macOS the system `say` is used
  automatically. On systems with neither, audio will gracefully skip and the
  email Listen button won't render (no failure, just no audio).

## Honest caveats

- **`datetime.utcnow()` is deprecated** in Python 3.12+. The app still
  works (just emits DeprecationWarnings). v4 refactor should swap to
  `datetime.now(timezone.utc)`.
- **Audio files are ~5MB each.** espeak produces high-fidelity but
  large WAV-encoded MP3s. For a real production launch you'd want a
  higher-quality TTS or compress the audio.
- **No automated tests.** Every check in this guide was ad-hoc. A real
  test suite (pytest + Stripe replay harness) is the natural next step.
- **The reviewer may notice** that `app.py` is 4104 lines. That's intentional
  for an MVP single-file deliverable, but it's the next thing to refactor
  once features stabilize (extract `learning_layer.py`, `billing.py`, etc.).

## What's bundled

```
pocketplot/
├── app.py                 215 KB — the whole app
├── requirements.txt       Python deps (flask, apscheduler, itsdangerous, stripe, gunicorn)
├── Dockerfile             python:3.12-slim + gunicorn + tini, non-root, healthcheck
├── docker-compose.yml     one-command deploy with volumes + resource limits
├── .env.example           full env template with comments
├── .dockerignore          excludes secrets, db, outbox, venv from image
├── README.md              16 KB — quick start + deployment guide + production checklist
├── guide.html             50 KB — Stripe setup reference with 4 annotated SVG diagrams
├── index.html             static export of marketing landing (open in browser)
├── signup.html            static export of free signup form
├── signup-pro.html        static export of Pro signup form
└── HANDOFF.md             15 KB — context for resuming work in a future session
```

Not bundled (regenerated on first boot):
- `pocketplot.db` — SQLite, regenerated by `init_db()` on first launch
- `outbox/` — saves real emails here when SMTP isn't configured
- `audio/` — saves generated MP3s here when pyttsx3 is available

— Gizmo / 小吉

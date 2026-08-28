# PocketPlot

> **Personalised bedtime stories, delivered every night — with a built-in Learning Layer that helps children develop real vocabulary, comprehension, and emotional literacy.**

PocketPlot is a single-file Flask app you can run on a Linux box with one command. Parents sign up, name their child + age, and receive a unique story every night by email. Free tier includes a Word of the Day, Story Talk questions, and a Learning Dashboard. Pro tier adds a Parent Guide, full learning history, and a creator feature where kids upload drawings that show up in their own stories.

Built for ages 2-8. Premium visual identity in the Khan Academy Kids style — warm, rounded, kid-safe. **No build step, no SPA, no Docker required.**

---

## Quick Start — Linux (no Docker, no build)

These commands work on a fresh Linux machine with Python 3.10+ and `apt`. They are the canonical path we test against, so if anything breaks, this is the place to look first.

```bash
# 1. System dependencies
#    - python3-pip / python3-venv (Debian/Ubuntu: separate from python3)
#    - espeak-ng (offline TTS for the Story Time "Listen to the Story" feature)
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv espeak-ng curl

# 2. Clone or unzip into a working directory
cd ~/
unzip pocketplot.zip
cd pocketplot

# 3. Install the Python deps
#    On Debian 12+ / Ubuntu 23.10+, the system Python is PEP 668-locked:
#        - Use a venv (recommended for clean Python)
#        - OR pass --break-system-packages (simpler, but pollutes site-packages)
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# On older Debian/Ubuntu without PEP 668, you can skip the venv:
#   sudo pip3 install -r requirements.txt --break-system-packages

# 4. (Optional) Configure SMTP + Stripe in your environment
#    If you skip this step, emails land as real .eml files in ./outbox/ and
#    the app runs in mock-billing mode (no real Stripe account needed).
cp .env.example .env
$EDITOR .env   # set billing keys here, OR leave blank for outbox-only

# 5. Run
python3 app.py

# 6. Open it
#    - Landing page:   http://localhost:5000/
#    - Sign up:        http://localhost:5000/  (free or Pro button)
#    - Admin:          http://localhost:5000/admin  (default password: letmein)
#    - Outbox:         files appear in ./outbox/ — open the .eml in any mail client
#    - Audio:          files appear in ./audio/<subscriber_id>/ — playable .mp3
```

### That's it. ~2 minutes if you have the apt deps already; ~5 minutes from cold.

If the server doesn't start:

- **`Address already in use`** → another process is on port 5000. Run `PORT=5001 python3 app.py` to use a different port.
- **`No module named flask`** → your venv isn't active. Run `source .venv/bin/activate` and retry.
- **`espeak-ng: command not found`** → Story Time audio is silently skipped, but everything else works. Install espeak-ng to enable it.
- **`pip` install fails on a PEP 668 system** → use the `--break-system-packages` flag, or stick with the venv approach above.

### A 30-second sanity check

Once `python3 app.py` is up, in another terminal:

```bash
# Sign up as a test parent
curl -s -X POST http://localhost:5000/subscribe \
     -d 'email=demo@example.com&child_name=Demo&child_age=5'

# List the stories that were generated
ls outbox/                  # → 14KB .eml file with your child's name
ls audio/                   # → subdirectory per subscriber, with .mp3 inside

# Verify in the browser
open http://localhost:5000/  # macOS
xdg-open http://localhost:5000/  # Linux
```

If those three commands produce the expected files and the page renders, the deployment is correct.

---



### v12 — Launch Polish Pass (2026-08-23)

Final launch-ready polish for PocketPlot Universe. Adults-only (18+), Stripe-safe content, new cinematic hero art, full Terms of Service + Content Policy, 18+ age gate on signup, BYOB setup guides in `/me/settings`, brand-separation docs.

**Content guidelines (v12):**
- **Allowed**: light violence, light romance, mature themes, strong language in moderation, drug/alcohol use in fiction.
- **Not allowed**: explicit sexual content (NSFW), graphic gore, anything depicting minors in sexual contexts (zero tolerance), hate speech.

### Two brands, one codebase

This codebase is **PocketPlot Universe**, the adults-only creative platform. The original **PocketPlot** (kids' bedtime stories) is a separate product; that codebase is unchanged and lives elsewhere. If you had an account on the original PocketPlot, it's still there. If you're reading this README, you're working on PocketPlot Universe.

### v11 — PocketPlot Universe (adults-only, tiered, BYOB/BYOG)
### v11 — PocketPlot Universe (adults-only, tiered, BYOB/BYOG)

A major platform evolution: **adults-only**, **single brand** "PocketPlot Universe," **three tiers** (Free / Pro $7.99 / Creator $19.99). Existing Pro subscribers grandfathered at $4.99 for life.

- **5 new modules**: `validation_system.py`, `external_api_manager.py`, `story_world.py`, `pocketplot_api.py`, `migrations_phase11.py` + `encryption.py` (stdlib-only authenticated encryption).
- **3 new backgrounds** + **3 new species** in the SVG composer v2.0 (castle, cyberpunk, magical library + robot, dragon, knight).
- **New routes**: `/me/settings` (Creator-tier BYOB key mgmt), `/worlds`, `/worlds/new`, `/worlds/<id>` (branching stories).
- **7 REST endpoints** at `/api/v1/*` — cookie or Bearer auth, ready for mobile clients.
- **New static pages**: `pricing.html` and `faq.html` with the new design palette (deep navy + warm gold + cream).
- **EVOLUTION_PLAN.md** — the architectural seams for future agents.

The full architecture + extension points are documented in `EVOLUTION_PLAN.md`.

## What's in here (by version)

PocketPlot's behavior is cumulative — every prior version's features are still in v10. The fastest way to read the codebase is bottom-up: `app.py` → 5 inlined SVG illustrations → `EMAIL_BANNER_SVG` / `MOMENT_ICON_SVG` / `PRO_BADGE_SVG` → `INDEX_HTML` (the marketing landing) → `ME_HTML` (the parent dashboard) → `HTML_TEMPLATE` (the email body) → `/game` route + `game.html` + `/admin/queue` routes + `review_queue.py` / `queue_templates.py` / `digest.py` + `/admin/dashboard` route + `admin_dashboard.py` → `avatar_builder.py` / `gamification.py` / `weekly_insight.py` / `story_packs.py` / `pdf_gen.py`. `HANDOFF.md` has the full v1→v10 evolution arc if you want context.

### v10 — Engagement & Revenue Layer (Phases 6-10)
- **Phase 6 — Avatar builder (Pro).** `/me` has a Privacy-first avatar builder — pick from 6 categories × 5 options each = 15,625 unique combinations. No photos, no PII, no DB schema for personal data. The avatar flows into the story's main character via `subscribers.avatar_json` + `story_image_composer.compose_story_image(avatar=...)`.
- **Phase 7 — Gamification.** Streaks (consecutive calendar days), Word Vault (cumulative unique words), 8 badges (first_story, week_1, ten_words, twentyfive_words, fifty_words, streak_3, streak_14, first_game). Hooks fire on every story-send and game-finish. `/me` shows the cards + badge grid + recent words. Game's win screen calls `/api/game/finish` to update stats.
- **Phase 8 — Weekly Insights email.** Pro subscribers get a warm digest every Sunday 09:00 UTC showing their week's words, streak, and badges. Inline-styled HTML template in `weekly_insight.py`. Manual trigger at `/admin/insights/trigger`.
- **Phase 9 — Story Packs.** Four default packs seeded on first boot (Dinosaurs, Space, Magic, Underwater). Pro subscribers get the active month's pack automatically via the `monthly_theme` rotation. Simpler than one-time Stripe purchases — Phase 2 enhancement if you want it.
- **Phase 10 — Printable Merch.** Two PDFs, generated on the fly with a hand-written zero-dependency PDF generator in `pdf_gen.py`. No `reportlab`, no `fpdf2`, no `weasyprint` — just pure Python that produces real PDF 1.4. Coloring Pack (4 silhouette pages for crayons) and Weekly Planner (personalized with the child's name). Pro-only via `/merch`.

### v9 — Admin Dashboard (Phase 5)
- New single-page dashboard at `/admin/dashboard` with everything in one scroll: live metrics (total/pro/pending/sent users), users table with pause/resume, content queue with bulk-approve + per-item approve/reject, story history with hero-SVG thumbnails + expandable full-story view, settings form (admin email + word count target + review queue toggle), system status (last cron run, 24h counts, recent errors).
- New `settings` table — runtime-configurable values that persist across restarts. New `hero_svg` column on `deliveries` so story history can show the illustration.
- Threaded `word_count_target` through to `story_gen.generate_new_story()` via `POCKETPLOT_WORD_COUNT_TARGET` env var. The default 250 produces 200-300 word stories; admin dashboard form lets you bump it for older readers.
- New `admin_dashboard.py` (25KB, single-file module — keeps `app.py` from bloating).

### v8 — Review queue + weekly digest (Phase 4)
- New `review_queue` table — every nightly-generated story now lands here first for admin approval instead of auto-sending. Holds the full story JSON, hero SVG, word, questions, moment, parent guide, and metadata.
- New `/admin/queue` UI: list view with tab filters (Pending/Approved/Rejected/Sent/All), bulk-approve, child name + PRO badge + queued timestamp. Detail view shows the hero illustration, story body, Word of the Day, Story Talk, Parent Guide, Moment of the Day — and inline approve/reject forms.
- New `/admin/digest/trigger` (manual) + APScheduler weekly digest job (Monday 09:00 UTC) — sends the admin a styled HTML digest email listing pending items (title + word + child + date) with a one-click link to the queue. Skips if queue is empty.
- 3 new standalone modules: `review_queue.py` (queue helpers), `queue_templates.py` (HTML templates), `digest.py` (digest email renderer).
- Default `POCKETPLOT_REVIEW_QUEUE=1` keeps the gating active; set to `0` to restore auto-send behavior.
- Game button in email now shows for any Pro subscriber (no longer requires TTS to have rendered).

### v7 — Mini-game (Phase 3)
- New `game.html` (27KB, single self-contained file, zero external dependencies) — a 2D Canvas top-down walker themed to the daily story. The child walks Wren from a cottage to a helper's hut, picks up a glowing orb (the Word of the Day), and answers Story Talk questions at checkpoint signs in dialogue with the helper.
- New `/game` route — Pro-only. Free users see a styled upsell with "Become Pro to play". Pro users see the game populated with today's actual story (title, body, word, all 3 questions pulled from the latest `deliveries` row).
- New moss-green `🎮 Play tonight's adventure` button in every Pro email — inline-styled so it survives Gmail/Outlook CSS stripping.
- Themed visuals: warm pastel palette matches the email aesthetic; all characters + trees + flowers + cottage + hut drawn with Canvas primitives (no images).

### v6 — Premium art + rebrand to PocketPlot
- 5 illustrations redesigned in the Khan Academy Kids style (rounded shapes, dot eyes with glints, blush cheeks, peach/cream/sky-blue palette). The hero is a bear parent + child silhouetted against a starry window with the book-light as the focal anchor; the email banner has a sleeping cloud as its hero element; the moment icon is a proper brand mark; the Pro badge has a laurel-leaf halo.
- Project renamed **StorySpark → PocketPlot** (original name had commercial collisions). Env vars are now `POCKETPLOT_*`. Database defaults to `pocketplot.db`.

### v5 — Learning Layer + interactive features
- **Word of the Day** — every story includes an age-matched vocabulary word (3 tiers: simple / intermediate / advanced, 100+ words), bolded inline in the story body, and surfaced in a dedicated info box in the email with a definition and a personalized example.
- **Story Talk** — 3 open-ended comprehension questions appended to every email, tailored to the actual cast and conflict in that night's story.
- **Learning Dashboard** at `/me` — this-month and total words learned, recent word history, tier breakdown bar chart for Pro users. Month counter auto-resets at the calendar boundary.
- **Parent Guide** (Pro only) — a deeper educational reflection appended to every Pro email.
- **Pricing tiers** — Free includes Word + Story Talk + 30-day dashboard. Pro adds Parent Guide, full learning history, and tier breakdown.

### v4 — Interactive Layer
- **"Choose Your Adventure" polls** — parent answers a daily question ("What should the main character's pet be?") on `/me`; the answer weaves into the next story.
- **Story Time audio** — every story gets a TTS MP3 (pyttsx3 + espeak-ng, offline, deterministic) and a "Listen to the Story" button in the email.
- **"Moments of the Day"** — a small positive life-lesson appended to every email, picked from a 15-pool rotation, themed around sharing / attention / kindness / gratitude / courage.
- **Pro tier field** (choice / adventure / creator) — nested under existing $4.99 Pro. *No new Stripe products.*

### v3 — Stripe + magic-link + self-service portal (still shipping)
- **PocketPlot Pro billing** — Free vs Pro ($4.99 / month). Pro unlocks a recurring helper of your choice + a setting theme, plus a Pro badge in the inbox.
- **Magic-link self-service portal** at `/me` — parents can view their plan/status, edit child name/age, pause/resume delivery, choose Pro preferences, and cancel.
- **Pricing page** at `/pricing`, **mock checkout** at `/mock/checkout` (works without a real Stripe account), **Stripe webhook** at `/webhook/stripe`.
- **Mock billing mode** — when `STRIPE_SECRET_KEY` is unset, every Stripe endpoint synthesizes the right webhook events in-process. Full upgrade → invoice.paid → cancel flow works locally.

### v1/v2 — Initial MVP + polish
- Single-file Flask app, SQLite, APScheduler nightly delivery.
- Server-rendered HTML (no SPA, no build).
- First story delivered immediately at signup (not "tonight at 8 pm").
- Outbox fallback for emails (real RFC-822 `.eml` files in `./outbox/` when no SMTP).
- 5 inlined SVGs (hero + 3 how-it-works icons + email banner).

---

## What "no SMTP configured" means

If you don't set `POCKETPLOT_SMTP_*` env vars, every email is written as a real RFC-822 `.eml` file in `./outbox/`. You can double-click any of those files to open them in your system mail client (Apple Mail, Thunderbird, etc.) and see exactly what your subscribers would receive. **This is the source of truth for QA.**

When SMTP *is* configured, the same `sendmail()` call goes to your real transactional email provider (SendGrid, Postmark, AWS SES, Mailgun — anything with SMTP).

---

## Going to production (live deployment)

The full production checklist is at the bottom of this README. The short version:

1. **Set `POCKETPLOT_SITE_URL`** to your real domain (used in Stripe redirects + magic-link URLs).
2. **Set `POCKETPLOT_ADMIN_PASSWORD`** to something stronger than `letmein`.
3. **Set the Stripe env vars** (`STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET`) for live billing.
4. **Set `POCKETPLOT_SMTP_*`** for real email delivery.
5. **Reverse proxy** (nginx/caddy) terminates TLS and forwards to port 5000.
6. **Backups**: copy `pocketplot.db` + `audio/` + `outbox/` to external storage on a schedule.
7. **Health check**: `GET /healthz` returns `200 OK` plain text.

---

## Full environment variables

| Variable | Default | Purpose |
|---|---|---|
| `POCKETPLOT_SECRET` | random at boot | Flask session signing key. **Set this in production** or you lose all sessions on restart. |
| `POCKETPLOT_SITE_URL` | `http://localhost:5000` | The public URL. Used in magic links, Stripe redirects, and email "Manage your account" footer. |
| `POCKETPLOT_ADMIN_PASSWORD` | `letmein` | Password for `/admin` and `/admin/login`. **Change in production.** |
| `POCKETPLOT_DB_PATH` | `./pocketplot.db` | SQLite database file location. |
| `POCKETPLOT_OUTBOX_DIR` | `./outbox/` | Where `.eml` files land when SMTP isn't configured. |
| `POCKETPLOT_AUDIO_DIR` | `./audio/` | Where TTS MP3 files are saved (per-subscriber subdirectories). |
| `POCKETPLOT_PUBLIC_AUDIO` | `false` | If `true`, audio files are accessible without authentication (useful for social sharing). |
| `POCKETPLOT_DELIVERY_HOUR` | `20` | UTC hour of nightly story delivery. 20 = 8 pm. |
| `POCKETPLOT_MAGIC_LINK_TTL` | `3600` | Magic-link expiry in seconds. 1 hour default. |
| `POCKETPLOT_SMTP_HOST` | (blank) | SMTP server hostname. If blank, the outbox fallback is used. |
| `POCKETPLOT_SMTP_PORT` | `587` | SMTP port (587 for STARTTLS, 465 for SMTPS). |
| `POCKETPLOT_SMTP_USER` | (blank) | SMTP username. |
| `POCKETPLOT_SMTP_PASS` | (blank) | SMTP password. |
| `POCKETPLOT_FROM_EMAIL` | `stories@pocketplot.local` | From-address for outbound email. |
| `STRIPE_SECRET_KEY` | (blank) | If blank, **mock billing mode** runs in-process. Set this for live Stripe. |
| `STRIPE_PUBLISHABLE_KEY` | (blank) | Not used by the server-side code, but documented for completeness. |
| `STRIPE_PRICE_ID` | (blank) | The `price_...` id of your Pro $4.99/month plan in Stripe. |
| `STRIPE_WEBHOOK_SECRET` | (blank) | The `whsec_...` signing secret Stripe gives you when you create the webhook endpoint. |

A complete template is in `.env.example`.

---

## Production checklist

- [ ] `POCKETPLOT_ADMIN_PASSWORD` is **not** `letmein`
- [ ] `POCKETPLOT_SITE_URL` matches your real domain (not `localhost`)
- [ ] `POCKETPLOT_SECRET` is set to a stable random value (otherwise sessions reset on every restart)
- [ ] Real Stripe keys set + a Stripe Product "PocketPlot Pro" + a $4.99/month Price created + a webhook endpoint pointed at `https://your-domain.com/webhook/stripe` listening for the 5 events (`customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`)
- [ ] SMTP credentials set + tested with a real send
- [ ] Reverse proxy terminating TLS in front of port 5000
- [ ] A backup of `pocketplot.db` is stored somewhere outside the server (cron: `cp pocketplot.db pocketplot-$(date +%F).db && rsync ...`)
- [ ] `GET /healthz` returns `200 OK`
- [ ] Log monitoring: stdout captures the `INFO 127.0.0.1 - -` access lines + your app's `log.info(...)` calls
- [ ] Tested: sign up → receive first story → upgrade to Pro → cancel → verify webhook events fire

---

## License & credits

Built by Gizmo (小吉) for 大哥 (YC). Single-file Flask, MIT-licensed. The illustrations are 100% original SVG, drawn in the Khan Academy Kids aesthetic warm-pastel palette. No external image assets — the entire visual identity is inline.

— *Ship it. ⚡*

## BYOB setup guide (Creator tier)

The Creator tier lets you connect your own OpenAI-compatible LLM and image API. Most support tickets are about this — here's the complete flow.

### Step 1: Pick a provider

Anything that speaks the OpenAI API format works. The most common:

| Provider | Where to get a key | Base URL | Example model |
|---|---|---|---|
| OpenAI | platform.openai.com/api-keys | `https://api.openai.com` | `gpt-4o-mini` |
| OpenRouter | openrouter.ai/keys | `https://openrouter.ai/api` | `anthropic/claude-3.5-sonnet` |
| Together | api.together.xyz | `https://api.together.xyz` | `meta-llama/Llama-3-70b-chat-hf` |
| Mistral | console.mistral.ai | `https://api.mistral.ai` | `mistral-large-latest` |
| Groq | console.groq.com | `https://api.groq.com/openai` | `llama-3.1-70b-versatile` |
| Ollama (local) | n/a (already running) | `http://localhost:11434/v1` | `llama3` |
| LiteLLM proxy | your own deployment | `https://your-litellm.example.com` | `gpt-4o-mini` |

### Step 2: Generate an API key from your provider

Don't share it. Don't commit it. Don't paste it in public channels.

### Step 3: Save it in PocketPlot Universe

1. Sign in at pocketplot.local
2. Go to **Settings** (link in the dashboard)
3. Scroll to **Bring Your Own Brain** (for LLM) or **Bring Your Own Graphics** (for image)
4. Paste key + base URL + model name into the form
5. Hit **Save**

Your key is encrypted at rest with PBKDF2 + HMAC. We use it only to route your requests. You can delete it anytime.

### Step 4: Verify

Hit **Save** — if the key is wrong, the next story you generate will fail with a clean 429-style refusal. If it succeeds, you'll see "this week's word: X" in the generated prose.

### Limits

- **100 external-API calls/day** per Creator subscriber (configurable via `POCKETPLOT_CREATOR_DAILY_LIMIT`)
- Every response passes through the content validator — paying for Creator does not unlock content that would violate platform policy.

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "Daily limit reached" | Hit the 100/day cap | Wait until midnight UTC, or raise the env var |
| "Upstream API returned HTTP 401" | Wrong API key | Re-paste your key; check it's not expired |
| "Upstream API returned HTTP 404" | Wrong base URL or model name | The model name must match what your provider exposes |
| Connection refused (Ollama) | Ollama isn't running or wrong port | Start Ollama with `OLLAMA_HOST=0.0.0.0:11434 ollama serve` |
| Content always rejected | Your prompt hits a validation rule | Read the FAQ's Content Policy section |


### v13 — Final polish pass (2026-08-23)

11 features added on top of the v12 launch polish: FAQ Assistant widget (deterministic, not an LLM), `/how-it-works` page, refund flow with audit logging, polished error pages, 5 new email templates with the v12 design palette, empty-state messages across every list view, audit log with admin page, public status page, contact form, public roadmap with voting, subscriber search on the admin dashboard, and `/robots.txt` + `/sitemap.xml`.

All written by us. No new external dependencies. All honors the "robustness over feature-complete UI" principle from the original brief.

### v14 — Cinematic polish pass (2026-08-23)

The visual upgrade. The hero illustration now reads as a premium movie poster: dense starfield + three layered nebulae + moon with three atmospheric halos + a vertical light beam from each of the three glowing doorways + a writer silhouette with notebook and pen. Tier icons now have glow rings, halos, sparkle dots, and star trails. Differentiator icons are scene-like (the SVG-Art icon is a tiny landscape inside a frame). Testimonial cards have SVG avatar circles.

A new `compose_layered_scene(genre)` function in `story_image_composer.py` generates six genre-specific layered scenes (fantasy, sci-fi, noir, romance, adventure, horror) with explicit BACKGROUND / MIDGROUND / FOREGROUND depth layers.

All artwork is original SVG authored in this codebase. No third-party assets.

### v15 — Cinematic enhancement pass (2026-08-23)

Crescent moon partially behind a taller mountain peak, faint galaxy swirl, grass + rocks + water in the foreground, radiant halos wrapping each doorway, richer tier icons with distinct gems and trails. New `compose_layered_scene_v15(genre)` adds the foreground depth on top of the v14 scene composers.

### v16 - Complete Universe build (2026-08-23)

The final architecture build. New `logo.svg` (standalone wordmark + branching icon). Homepage redesigned with a **16-genre showcase grid** (each card = unique SVG icon, links to /signup?genre=X). New mandatory Story Specification Form fields (Main Character Description + Primary Objective) on `/worlds/new` - threaded into the procedural engine + BYOB prompt via `state['spec']`. `validation_system.py` gains a multi-layer pipeline with pluggable Classifier backends (keyword default; operators wire up Llama Guard 3 / OpenAI moderation / GPT-4o-mini by extending `CLASSIFIER_BACKENDS`). Keyword patterns tightened to catch the cases v12 missed. 10 new layered scene composers (cyberpunk, action, drama, thriller, comedy, detective, fairytales, superhero, chicklit, roleplaying, historical fiction) bringing the total to 16. Network-level sandboxing documented as operator-side guidance, not code.

### v17 - Expansion & Polish (2026-08-23)

The full-feature expansion: new "Portal to Stories" hero (giant glowing book opening to a cosmic interior), 16 upgraded scene-like genre icons (each a 96x96 miniature), refined logo, Story Library (`/library` with search + genre filter + ZIP export), Story Seed (`/seed` random prompt generator + pre-fill `/worlds/new`), Story Remix (`/remix` procedural + BYOB), Public Profile + Follow/Unfollow + Notifications (social-graph stub), Story Analytics (views/reads/reading-time/milestones), Weekly Summary emails (Pro/Creator), Admin Feature Flags + Top Stories leaderboard, CSS animations (hero-fade, pulse-glow, float-up, twinkle).

### v18 - Tech-Victorian Aesthetic (2026-08-26)

A complete visual identity pivot. The platform now reads as a high-end creative studio from another era: 19th-century library (walnut floor, brass bookcase, amber banker's lamp, leather-bound folios) crossed with modern tech (cyan + magenta circuit lines, slow-rotating clockwork gears, holographic accents). All 16 genre icons are framed in brass with circuit detail. The hero is a cosmic book framed inside an open Victorian library with a brass border. New color tokens (warm wood, brass, amber, banker's emerald, cool neon) + new typography (Fraunces serif headlines + DM Sans body + Cinzel display). Every section divider is an ornate brass rule. Buttons are brass-bordered with amber glow on hover. Cards have a thin brass border that brightens on hover.

### v19 - The Story Engine (2026-08-26)

The book is the focal point. The v18 hero had a Victorian frame but the book itself was small + generic. v19 puts a real, open Victorian book at the center with visible printed text in Cinzel serif, gilt edges, brass-bordered spine, circuit lines threading the page margins (cyan left, magenta right), a holographic disc floating above (the "imagination field"), and 7 story-symbol glyphs floating up from the pages (crescent moon / lightning / heart / skull / crown / rocket / compass). Walnut desk surface, banker's lamp glow, 2 floating clockwork gears, POCKETPLOT UNIVERSE nameplate.

### v20 - The Split Book (2026-08-26)

The book is now a literal split artifact. Left page = 19th-century Victorian (cream parchment, Cinzel serif 'CHAPTER ONE', 7 paragraph lines of printed text, hand-drawn crescent-moon + stars illustration, ink splatter, Roman numeral 'I' page number, brass seam, gilt edge). Right page = futuristic high-tech (deep navy substrate, JetBrains Mono code comments `// CH.01 0x01` + `// story://init`, circuit-line 'text' in cyan + magenta with node dots, holographic orb, bracket symbols, data readout '78° / 14:02', neon underlight). The spine is split: left half dark walnut with brass binding posts, right half dark navy with glowing cyan terminal nodes. Above the book: left side has an amber field + a quill rising from the page + ink drops; right side has a cyan holographic field + data orb + brackets + sparkles. Brass gear top-left, cyan gear top-right. The frame border is split (brass corner gems left, cyan accent dots right).

### v21 - Adopted Brand Mark (2026-08-26)

Adopted the illustrated split-book character (Victorian book left, futuristic high-tech book right, sharing one binding, with two faces) as the official PocketPlot Universe brand mark. Replaces the v18/v19/v20 SVG-based hero as the focal art on the homepage AND as the logo in the navigation. Image appears in: homepage hero, homepage header, all secondary page headers (pricing / faq / how-it-works / terms / signup / signup-pro), email templates (welcome / magic link / refund / queue approved), favicon (`/logo-icon-32.png`), Apple touch icon (`/logo-icon-180.png`), OG / Twitter card (`/logo-og.png`, 1200x630). New Flask route `/_serve_brand_asset` serves the brand image files from the project root with a whitelist.

### v22 - Transparent Brand + Amber Halo (2026-08-26)

The brand image's cream background is now fully transparent (computed per-pixel Euclidean distance from cream, mapped to alpha with a soft gamma=0.85 curve). A second set of variants adds a soft amber radial glow behind the book so the logo pops on the deep navy without a white box around it. The header brand mark, secondary page headers, and email templates now use the halo variants. The homepage hero also uses the halo variant.

### v23 - Engagement, Community, Mobile Prep (2026-08-27)

The biggest feature expansion: sharing + community + exports + marketing + PWA. Adds 5 new modules (engagement, exports, promo, qrcode_lib, migrations_phase23), 8 new database tables, ~25 new routes including the long-awaited /play/[token] game mode (visual novel with choices + branching), /read/[token] manga/storybook mode (panels + narration + speech bubbles), and /play/[token]/map (world map with scenes as connected nodes - the foundation for full Minecraft-style navigation in v24). Plus EPUB export (hand-rolled, no library dep), bulk ZIP export, single-world PDF, promo codes, admin email segments, newsletter blasts, PWA manifest + service worker, push notification data model. Public API endpoints exposed at /api/v1/* (shares, likes, world stats, with 501 stubs for the v24 inventory + build systems).

### v24 - Engagement, Editor, Inventory, TTS, SEO (2026-08-27)

Adds 8 new modules (audit_v24, streaks_xp, social, inventory, scene_graph, onboarding, tts, sentry_v24 + migrations_phase24), 13 new database tables, 3 new world columns, ~25 new routes including: a 3-step onboarding wizard, a per-world + per-episode story editor with revision history, a visual scene-graph editor with drag-to-place nodes + click-to-connect edges, threaded comments + 6 emoji reactions on worlds, an XP + daily-streak system with milestone auto-awards, an inventory system with 8 starter items + Minecraft-style world placement, a TTS system with Web Speech API + pyttsx3 server fallback, a generated 1200x630 story cover image, Sentry opt-in error tracking, an extended audit log + admin dashboard, and SEO-friendly public story pages with OG tags + JSON-LD structured data + sitemap.xml.

### v25 - Automated tests + native shells (2026-08-27)

Adds the test foundation: 64 pytest tests covering auth, share tokens, engagement, exports, story generation, and all v24 modules. Fixed bugs caught by tests (duplicate route registration, missing HTML escape import, dict(REACTION_KINDS) bug, sqlite3.Row.get() bug). Added the v25 Inventory placement UI: /worlds/<id>/inventory page with drag-and-drop, place/pickup/move routes, sidebar with inventory + placed items + rarity legend. Native shell preparation via Capacitor.js: capacitor.config.json + enhanced manifest.json (shortcuts + share_target) + enhanced sw.js (tiered caching + push handler) + NATIVE_BUILD.md instructions + build_native.py generator. Run tests with `python3 -m pytest tests/ -v`. Build native shells with `npx cap add ios && npx cap add android` on a Mac.

### v26 - Apple-style refinement (2026-08-27)

A CSS-only revamp that keeps the v18 Tech-Victorian palette + brand mark while refining typography, cards, buttons, nav, and mobile layout toward Apple-style polish. New v26 token system (type scale, spacing, radii, shadows, motion). Hero composition with gradient mesh + floating brand mark. Sticky nav with frosted-glass backdrop. Mobile bottom tab bar. All 64 automated tests still pass.

### v27 - Apple-style restructure (2026-08-27)

Full HTML restructure (not just CSS) for the homepage + pricing page. Hero: single-column text-only focal point with massive display serif (60-128pt) + single CTA. Sections: 3-up card grids replaced with single-focal-point text entries. Pricing: 3 clean tier blocks with hairline borders + a "Most popular" pill. Footer: minimal. Mobile: bottom tab bar visible. All 64 tests still pass.

### v28 - Render deployment (2026-08-27)

v27 codebase is live at https://pocketplot.onrender.com (and pending DNS, soon at https://pocketplot.app). 64 automated tests pass. Source: github.com/pocketplot12/pocketplot-universe. Auto-deploy on every push. Bug fixed: removed duplicate _BRAND_FILES set that was shadowing the correct whitelist, causing 404 on PWA manifest + service worker.

### v29 - Kindle-e-ink theme toggle (2026-08-27)

Two reading-friendly themes added to https://pocketplot.app:
- **warm-dark** (default): deep navy + warm cream text (current visual style)
- **warm-light**: Kindle paper feel — warm cream background + warm dark brown text, NO pure white

Sun/moon toggle in nav. Choice persists via localStorage. First-visit uses system preference. Both themes preserve the brass/Tech-Victorian palette + Fraunces serif typography. 64 tests still passing.

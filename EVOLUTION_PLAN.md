# PocketPlot Universe — Evolution Plan

This document explains the architectural seams in PocketPlot Universe
that future agents (and you, when you wake up) can extend without
needing to redesign anything. Read this before adding features.

## The layering

```
┌─────────────────────────────────────────────────────────────┐
│  Templates (HTML)         index.html, me.html, pricing.html, │
│                           faq.html, settings.html, worlds/*. │
│  No business logic — just rendering. Safe to rewrite freely.│
└─────────────────────────────────────────────────────────────┘
                          ↑ renders into
┌─────────────────────────────────────────────────────────────┐
│  Routes (app.py)          GET/POST handlers in app.py.      │
│                           Each route is ~30 lines: fetch    │
│                           state, call one module function,  │
│                           render one template.              │
└─────────────────────────────────────────────────────────────┘
                          ↑ uses
┌─────────────────────────────────────────────────────────────┐
│  Modules (story_gen, story_world, gamification,            │
│  weekly_insight, story_packs, pdf_gen, validation_system,  │
│  external_api_manager, avatar_builder, encryption,         │
│  review_queue, digest, admin_dashboard, queue_templates)   │
│  Pure-ish: each takes (db, subscriber_id, ...) and returns  │
│  a dict or None. No Flask imports inside.                   │
└─────────────────────────────────────────────────────────────┘
                          ↑ uses
┌─────────────────────────────────────────────────────────────┐
│  Data layer (SQLite via migrations_phase6.py +              │
│  migrations_phase11.py). Schema is additive. Never drop a  │
│  column in production — only ADD.                           │
└─────────────────────────────────────────────────────────────┘
                          ↑ runs on
┌─────────────────────────────────────────────────────────────┐
│  Runtime (Flask + APScheduler + stdlib only).               │
└─────────────────────────────────────────────────────────────┘
```

The rule for future work: **add modules, don't edit them**. The
modules expose plain functions that take `db` and a subscriber id;
they don't import Flask. That makes them testable in isolation.

## Concrete extension points

### "I want to add a new story genre"

Edit `story_world.GENRES` in `story_world.py` — add a key with
`magic_words`, `antagonist`, `motif_verbs`, `settings` lists. The
generator + validator pick it up automatically. The HTML form at
`/worlds/new` enumerates the dict's keys.

### "I want to add a new BYOB provider"

`external_api_manager.call_llm()` and `call_image()` already speak
the OpenAI-compatible wire format. To add Anthropic (non-OpenAI),
add a new adapter function `call_llm_anthropic()` and dispatch on
`base_url` substring or a `provider` field on the row. The auth +
rate-limit plumbing is reusable as-is.

### "I want to expand the validation policy"

Edit `validation_system.DISALLOWED_PATTERNS` and
`validation_system.BANNED_PHRASES`. Tests should run new prompts
through `check_prompt()` and `sanitize_output()` to confirm. The
validation_log table records every pass for review.

### "I want to add a new tier feature"

1. Add the gated logic to the relevant module (e.g. longer word
   ceilings to `validation_system.TIER_WORD_CEILINGS`).
2. Add the UI affordance to the relevant template
   (e.g. `SETTINGS_HTML` for /me/settings).
3. Update `app.py` route handlers to read the new tier check.

### "I want to swap procedural for LLM-default"

`story_gen.generate_new_story()` is the entry point. Wrap it in
`external_api_manager.call_llm()` and use its returned text in
place of the procedural body. The validation pass is already
applied at the seam — no safety regression.

### "I want a mobile app"

The `/api/v1/*` routes are the surface. Authenticate via Bearer
token (the magic-link serializer is exposed via
`tokens_unsigner_for_api` in app.py). Mobile clients should
follow this contract:

  - GET  /api/v1/me       → profile + tier + remaining API quota
  - GET  /api/v1/worlds   → list user's worlds
  - POST /api/v1/worlds   → create world (title, genre, tone, setting)
  - POST /api/v1/worlds/<id>/episodes → generate episode, optionally
                                          with choice_from_episode_id
                                          + chosen_index
  - GET/POST/DELETE /api/v1/api-keys → list / save / deactivate keys
  - POST /api/v1/byob/llm  → Creator-only: route an LLM call
  - POST /api/v1/byob/image → Creator-only: generate an image

All endpoints return `{"ok": bool, "data": ..., "error": "..."}`.
Error codes: 401 / 403 / 404 / 409 / 429 / 500.

### "I want to add a new page"

1. Add a route handler in `app.py` (use `@login_required` or
   `@admin_required` decorators).
2. Add the template as a module-level constant (`FOO_HTML = """..."""`)
   near the other templates in `app.py`.
3. Render via `render_template_string(FOO_HTML, ...)`.

The single-file pattern is intentional — keeping the templates
next to their routes means a grep for the route finds the
template, and vice versa. Don't move them out unless there's a
strong reason.

## Hard constraints

These are NOT optional. Future agents must respect them.

1. **Encryption keys must remain encrypted at rest.** Don't log
   decrypted keys. Don't display them in admin UIs.
2. **Validation is non-bypassable.** Every external-API response
   passes through `validation_system.validate_for_tier` before
   reaching the user. Even at the Creator tier.
3. **Rate limits are enforced.** The default is 100 external-API
   calls/day per Creator subscriber. Don't raise it without
   understanding the cost.
4. **Adults only.** There's no profile_type=kid path. Don't add
   one. The brand split is deliberate.
5. **No new dependencies** without a written exception. The brief
   is explicit; "no external deps" is the constraint.

## What NOT to add

- A mobile app framework (the API is the surface; clients are
  someone else's problem).
- A reasoning model for coherence checking. The validation system
  is a safety net, not a judge. Adding a real coherence checker
  requires either a fine-tuned model or a much larger reasoning
  budget than the platform can absorb.
- A "make the platform safer by limiting creativity" toggle. The
  guardrail already says no to the truly-bad inputs; for everything
  else, we let the writer write.

## Where to read more

- `HANDOFF.md` — the v1 → v11 evolution arc with decisions, bugs,
  pushback, and verified results.
- `README.md` — current public overview + how to run.
- The module docstrings — each module starts with "WHY" and "SCOPE"
  sections that document what the module does and (importantly)
  what it deliberately doesn't do.

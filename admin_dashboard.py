"""Phase 5 — Admin Dashboard.

A single-page dashboard for the admin to manage everything from one place:
  - Overview metrics
  - User table with pause/resume
  - Pending story queue with approve/reject
  - Story history (last 30 deliveries) with hero illustrations
  - Settings (admin email, queue toggle, word-count target)
  - System status (last cron run, 24h story count, recent errors)

All HTML lives in this file as inline templates (DASHBOARD_HTML).
Keep it self-contained — no external dependencies.
"""
import datetime as dt
import json
import logging

log = logging.getLogger("pocketplot.dashboard")


# ---- Settings helpers ----
DEFAULT_SETTINGS = {
    # k -> default value (str)
    "admin_email":         "admin@pocketplot.local",
    "review_queue_enabled": "1",       # 1 = gated (queue mode), 0 = auto-send
    "word_count_target":   "250",      # target band midpoint; generator aims at +/- 50
    "delivery_hour_utc":   "20",       # cron hour for nightly run (server restart to apply)
}


def get_setting(db, key, default=None):
    """Read a single setting; fall back to DEFAULT_SETTINGS then to the supplied default."""
    conn = db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    if row and row[0] is not None:
        return row[0]
    return DEFAULT_SETTINGS.get(key, default)


def get_all_settings(db):
    """Return a dict of {key: value} merging DB rows with DEFAULT_SETTINGS."""
    out = dict(DEFAULT_SETTINGS)
    conn = db()
    for r in conn.execute("SELECT key, value FROM settings").fetchall():
        out[r[0]] = r[1] or DEFAULT_SETTINGS.get(r[0], "")
    conn.close()
    return out


def set_setting(db, key, value):
    conn = db()
    conn.execute(
        "INSERT INTO settings(key, value, updated_at) VALUES(?, ?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, value, dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"),
    )
    conn.commit()
    conn.close()


# ---- Metrics ----
def overview_metrics(db):
    conn = db()
    metrics = {}
    metrics["total_users"] = conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
    metrics["pro_users"]   = conn.execute("SELECT COUNT(*) FROM subscribers WHERE plan='pro'").fetchone()[0]
    metrics["free_users"]  = conn.execute("SELECT COUNT(*) FROM subscribers WHERE plan!='pro'").fetchone()[0]
    metrics["active_users"] = conn.execute("SELECT COUNT(*) FROM subscribers WHERE active=1").fetchone()[0]
    metrics["paused_users"] = conn.execute("SELECT COUNT(*) FROM subscribers WHERE active=0").fetchone()[0]
    metrics["pending_stories"] = conn.execute("SELECT COUNT(*) FROM review_queue WHERE status='pending'").fetchone()[0]
    metrics["approved_stories"] = conn.execute("SELECT COUNT(*) FROM review_queue WHERE status='approved'").fetchone()[0]
    metrics["sent_stories"]  = conn.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0]
    # Stories generated in the last 24h (from review_queue.created_at — this
    # captures all generations, whether approved or not).
    cutoff = (dt.datetime.utcnow() - dt.timedelta(hours=24)).isoformat(timespec="seconds") + "Z"
    metrics["queued_24h"] = conn.execute(
        "SELECT COUNT(*) FROM review_queue WHERE created_at >= ?", (cutoff,)
    ).fetchone()[0]
    metrics["delivered_24h"] = conn.execute(
        "SELECT COUNT(*) FROM deliveries WHERE sent_at >= ?", (cutoff,)
    ).fetchone()[0]
    # Last cron / nightly run timestamp (from story_log "Nightly run · ...").
    last = conn.execute(
        "SELECT ts, note FROM story_log WHERE note LIKE 'Nightly run%' "
        "ORDER BY id DESC LIMIT 1"
    ).fetchone()
    metrics["last_run_ts"]   = last["ts"] if last else "—"
    metrics["last_run_note"] = last["note"] if last else "no runs yet"
    conn.close()
    return metrics


def recent_errors(db, limit=10):
    """Recent story_log rows that look like errors (FAIL/ERROR/Exception)."""
    conn = db()
    rows = conn.execute(
        "SELECT ts, note FROM story_log "
        "WHERE lower(note) LIKE '%fail%' OR lower(note) LIKE '%error%' OR lower(note) LIKE '%exception%' "
        "ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def list_subscribers_full(db, limit=100):
    conn = db()
    rows = conn.execute(
        "SELECT id, email, child_name, child_age, plan, pro_tier, active, "
        "created_at, last_sent_at FROM subscribers ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def list_recent_deliveries(db, limit=30):
    conn = db()
    rows = conn.execute(
        """SELECT d.id, d.subscriber_id, d.sent_at, d.word_count, d.story,
                  d.hero_svg, d.word, d.audio_filename,
                  s.email, s.child_name, s.plan
           FROM deliveries d
           JOIN subscribers s ON s.id = d.subscriber_id
           ORDER BY d.id DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return rows


# ---- The HTML template ----
# Note: Jinja2 doesn't support chr() — we pre-split paragraphs in the route
# (or in the Python helper) before passing them to the template.
DASHBOARD_HTML = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Admin Dashboard · PocketPlot</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:wght@500;600&family=Karla:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --cream: #f6f0e1; --paper: #fff8e7; --ink: #1a241d;
    --moss: #5c7c5a; --mossD: #3e5a3c; --rust: #c46a3f; --rustD: #a8572f;
    --gold: #c9a96e; --paper2: #ecdfc3; --paper3: #d8cfb3; --faint: #7a8a6a;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    font-family: Karla, -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--cream); color: var(--ink); line-height: 1.5;
    padding-bottom: 80px;
  }
  .header {
    background: var(--paper);
    border-bottom: 1px solid var(--paper3);
    padding: 16px 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky; top: 0; z-index: 100;
  }
  .wordmark { font-family: Fraunces; font-size: 20px; color: var(--ink); }
  .wordmark i { color: var(--moss); font-style: italic; }
  .nav { display: flex; gap: 6px; }
  .nav a {
    font-size: 13px; font-weight: 600; color: var(--moss);
    text-decoration: none; padding: 6px 12px; border-radius: 99px;
  }
  .nav a:hover { background: var(--paper2); }
  .nav a.active { background: var(--moss); color: white; }
  .nav .site { color: var(--faint); margin-left: 6px; }
  .wrap { max-width: 1200px; margin: 28px auto 0; padding: 0 24px; }
  h2 {
    font-family: Fraunces; font-weight: 600; font-size: 22px;
    color: var(--ink); margin: 32px 0 12px;
    display: flex; align-items: baseline; gap: 12px;
  }
  h2 .badge { font-family: Karla; font-size: 11px; font-weight: 700; color: var(--faint); }
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 14px;
    margin-bottom: 8px;
  }
  .metric {
    background: var(--paper); border: 1px solid var(--paper3);
    border-radius: 14px; padding: 18px;
  }
  .metric .label {
    font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
    color: var(--faint); font-weight: 700; margin-bottom: 6px;
  }
  .metric .value {
    font-family: Fraunces; font-weight: 600; font-size: 32px; color: var(--ink);
    line-height: 1;
  }
  .metric .hint { font-size: 11px; color: var(--faint); margin-top: 6px; font-style: italic; }
  .metric.accent-moss .value { color: var(--moss); }
  .metric.accent-rust .value { color: var(--rust); }
  .metric.accent-gold .value { color: var(--gold); }
  table { width: 100%; border-collapse: collapse; background: var(--paper); border-radius: 14px; overflow: hidden; border: 1px solid var(--paper3); }
  th { padding: 10px 14px; text-align: left; font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: var(--moss); background: var(--paper2); font-family: Karla; font-weight: 700; }
  td { padding: 12px 14px; border-top: 1px solid var(--paper2); font-family: Georgia, serif; color: var(--ink); vertical-align: top; font-size: 14px; }
  td.email { font-family: Karla; font-size: 13px; }
  td.muted { color: var(--faint); font-size: 12px; }
  .badge { display: inline-block; font-size: 10px; letter-spacing: .1em; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; background: var(--paper2); color: var(--moss); font-family: Karla; font-weight: 700; vertical-align: middle; }
  .badge.pro { background: var(--gold); color: white; }
  .badge.active { background: #d8e4d4; color: var(--mossD); }
  .badge.paused { background: #f0d3c4; color: #a8572f; }
  .btn {
    background: var(--moss); color: white; padding: 8px 16px; border-radius: 99px;
    border: none; font-family: Karla; font-weight: 700; font-size: 12px;
    cursor: pointer; text-decoration: none; display: inline-block;
  }
  .btn:hover { background: var(--mossD); }
  .btn.secondary { background: var(--paper); color: var(--moss); border: 1px solid var(--paper3); }
  .btn.secondary:hover { background: var(--paper2); }
  .btn.danger { background: var(--rust); }
  .btn.danger:hover { background: var(--rustD); }
  .btn.gold { background: var(--gold); color: white; }
  .btn.small { padding: 5px 11px; font-size: 11px; }
  .panel {
    background: var(--paper); border: 1px solid var(--paper3);
    border-radius: 14px; padding: 22px; margin-bottom: 18px;
  }
  .panel h3 {
    font-family: Fraunces; font-size: 18px; margin: 0 0 12px; color: var(--ink);
  }
  .panel .lead { color: var(--faint); font-size: 13px; margin-bottom: 14px; }
  label.field { display: block; margin-bottom: 14px; font-family: Karla; font-size: 13px; color: var(--ink); }
  label.field .lab { display: block; font-weight: 600; margin-bottom: 4px; }
  label.field input[type=text], label.field input[type=email], label.field input[type=number], label.field select {
    width: 100%; padding: 9px 12px; border: 1px solid var(--paper3);
    border-radius: 8px; font-family: Karla; font-size: 14px;
    background: white; color: var(--ink); box-sizing: border-box;
  }
  label.field .help { display: block; margin-top: 4px; font-size: 11px; color: var(--faint); font-style: italic; }
  .row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .row3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
  .checkbox-row { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; font-family: Karla; font-size: 13px; }
  .actions-row { display: flex; gap: 10px; flex-wrap: wrap; }
  .empty { padding: 28px; text-align: center; color: var(--faint); font-style: italic; }
  .queue-row td.actions { font-family: Karla; font-size: 12px; white-space: nowrap; }
  .queue-row td.title a { color: var(--rust); text-decoration: none; font-weight: 600; }
  .queue-row td.title a:hover { text-decoration: underline; }
  .queue-row .hero-thumb { width: 56px; height: 56px; border-radius: 8px; background: var(--paper2); display: inline-block; vertical-align: middle; margin-right: 10px; overflow: hidden; }
  .queue-row .hero-thumb svg { width: 100%; height: 100%; display: block; }
  .queue-row .hero-thumb.empty-hero { background: linear-gradient(135deg, var(--paper2) 0%, var(--paper) 100%); }
  .history-row .story-thumb { width: 64px; height: 64px; border-radius: 10px; background: var(--paper2); display: inline-block; vertical-align: middle; margin-right: 12px; overflow: hidden; }
  .history-row .story-thumb svg { width: 100%; height: 100%; display: block; }
  .history-row .story-thumb.empty-hero { background: linear-gradient(135deg, var(--paper2) 0%, var(--paper) 100%); }
  .history-row td.title { font-family: Georgia, serif; }
  .history-row .preview { font-size: 12px; color: var(--faint); font-family: Georgia, serif; margin-top: 4px; line-height: 1.5; max-height: 60px; overflow: hidden; }
  details { margin-top: 8px; }
  details summary { cursor: pointer; font-size: 12px; color: var(--moss); font-family: Karla; font-weight: 600; padding: 4px 0; }
  details .full { font-family: Georgia, serif; font-size: 13px; line-height: 1.65; background: var(--cream); border: 1px solid var(--paper3); border-radius: 10px; padding: 16px; margin-top: 8px; }
  details .full p { margin: 0 0 12px; }
  details .full svg { max-width: 320px; display: block; margin: 12px 0; border-radius: 10px; border: 1px solid var(--paper3); }
  details .full img.hero { max-width: 320px; display: block; margin: 12px 0; border-radius: 10px; border: 1px solid var(--paper3); }
  .system-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .system-item { padding: 12px 14px; background: var(--cream); border-radius: 10px; border: 1px solid var(--paper3); }
  .system-item .lab { font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--faint); font-weight: 700; margin-bottom: 4px; }
  .system-item .val { font-family: Fraunces; font-weight: 600; font-size: 18px; color: var(--ink); }
  .system-item .val.mono { font-family: 'SF Mono', Menlo, monospace; font-size: 13px; }
  .errors { font-family: 'SF Mono', Menlo, monospace; font-size: 12px; color: var(--rustD); background: #fdf3dc; border: 1px solid #e0c98c; border-radius: 10px; padding: 12px 16px; }
  .errors .row { padding: 4px 0; border-bottom: 1px dotted #d8c898; }
  .errors .row:last-child { border-bottom: none; }
  .bulk-row { display: flex; gap: 10px; align-items: center; margin-bottom: 10px; font-family: Karla; font-size: 13px; }
  .tabs { display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap; }
  .tabs a {
    font-family: Karla; font-size: 12px; font-weight: 600;
    padding: 6px 14px; border-radius: 99px;
    background: var(--paper); color: var(--moss);
    border: 1px solid var(--paper3); text-decoration: none;
  }
  .tabs a:hover { background: var(--paper2); }
  .tabs a.active { background: var(--moss); color: white; border-color: var(--moss); }
  .tabs .count { font-size: 11px; font-weight: 400; margin-left: 5px; opacity: .85; }
  .flash { padding: 12px 16px; border-radius: 10px; margin-bottom: 14px; font-family: Karla; font-size: 13px; }
  .flash.ok { background: #d8e4d4; color: var(--mossD); border: 1px solid #a8c0a3; }
  .flash.err { background: #f0d3c4; color: var(--rustD); border: 1px solid var(--gold); }
</style>
</head>
<body>
<div class="header">
  <div class="wordmark">Pocket<i>Plot</i> · <span style="font-family:Karla;font-size:13px;color:var(--faint);font-weight:600;">Admin Dashboard</span></div>
  <nav class="nav">
    <a href="/admin/dashboard" class="active">Dashboard</a>
    <a href="/admin/queue">Queue</a>
    <a href="/admin">Subscribers</a>
    <a href="/admin/log">Activity</a>
    <a href="/admin/outbox">Outbox</a>
    <a href="/admin/logout" class="site">Log out</a>
    <a href="/" class="site">← Site</a>
  </nav>
</div>

<div class="wrap">

  {% if flash_ok %}<div class="flash ok">{{ flash_ok }}</div>{% endif %}
  {% if flash_err %}<div class="flash err">{{ flash_err }}</div>{% endif %}

  <!-- ============== OVERVIEW ============== -->
  <h2>Overview <span class="badge">live</span></h2>
  <div class="metrics-grid">
    <div class="metric accent-moss">
      <div class="label">Total users</div>
      <div class="value">{{ metrics.total_users }}</div>
      <div class="hint">{{ metrics.active_users }} active · {{ metrics.paused_users }} paused</div>
    </div>
    <div class="metric accent-gold">
      <div class="label">Pro users</div>
      <div class="value">{{ metrics.pro_users }}</div>
      <div class="hint">{{ metrics.free_users }} free</div>
    </div>
    <div class="metric accent-rust">
      <div class="label">Pending stories</div>
      <div class="value">{{ metrics.pending_stories }}</div>
      <div class="hint">awaiting your review</div>
    </div>
    <div class="metric">
      <div class="label">Stories sent</div>
      <div class="value">{{ metrics.sent_stories }}</div>
      <div class="hint">{{ metrics.delivered_24h }} in the last 24h</div>
    </div>
  </div>

  <!-- ============== USERS ============== -->
  <h2>Users <span class="badge">{{ users|length }}</span></h2>
  <div class="panel">
    {% if users %}
    <table>
      <thead><tr><th>Email</th><th>Child</th><th>Plan</th><th>Status</th><th>Joined</th><th>Last sent</th><th></th></tr></thead>
      <tbody>
      {% for u in users %}
        <tr>
          <td class="email">{{ u.email }}</td>
          <td>{{ u.child_name }} (age {{ u.child_age }})</td>
          <td>
            {% if u.plan == 'pro' %}
              <span class="badge pro">PRO{% if u.pro_tier %} · {{ u.pro_tier|upper }}{% endif %}</span>
            {% else %}<span class="badge">FREE</span>{% endif %}
          </td>
          <td>
            {% if u.active %}<span class="badge active">active</span>
            {% else %}<span class="badge paused">paused</span>{% endif %}
          </td>
          <td class="muted">{{ u.created_at[:10] if u.created_at else '—' }}</td>
          <td class="muted">{{ u.last_sent_at[:10] if u.last_sent_at else '—' }}</td>
          <td>
            <form method="POST" action="/admin/dashboard/users/{{ u.id }}/toggle" style="display:inline;">
              {% if u.active %}
                <button class="btn small secondary" type="submit">Pause</button>
              {% else %}
                <button class="btn small" type="submit">Resume</button>
              {% endif %}
            </form>
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}<div class="empty">No subscribers yet. /admin/subscribe or share the marketing landing page.</div>{% endif %}
  </div>

  <!-- ============== CONTENT QUEUE ============== -->
  <h2>Content queue <span class="badge">{{ queue_pending|length }} pending</span></h2>
  <div class="panel">
    {% if queue_pending %}
    <form method="POST" action="/admin/dashboard/queue/bulk-approve" id="bulk-form" class="bulk-row">
      <label><input type="checkbox" id="select-all"> Select all</label>
      <button class="btn gold" type="submit">Bulk approve &amp; send</button>
    </form>
    <table>
      <thead><tr><th style="width:30px"></th><th>Story</th><th>Word</th><th>For</th><th>Queued</th><th>Actions</th></tr></thead>
      <tbody>
      {% for q in queue_pending %}
        <tr class="queue-row">
          <td><input type="checkbox" name="qid" value="{{ q.id }}" form="bulk-form" class="row-check"></td>
          <td class="title">
            <div style="display:flex;align-items:center;">
              <span class="hero-thumb {% if not q.hero_svg %}empty-hero{% endif %}">
                {% if q.hero_svg %}{{ q.hero_svg|safe }}{% endif %}
              </span>
              <a href="/admin/queue/{{ q.id }}">{{ q.title }}</a>
            </div>
            <div class="muted" style="font-family:Karla;font-size:11px;margin-top:4px;">{{ q.child_name }} · {{ q.email }}</div>
          </td>
          <td><span style="font-style:italic;color:var(--rust);">{{ q.word }}</span></td>
          <td>{{ q.child_name }}</td>
          <td class="muted">{{ q.created_at[:10] }}</td>
          <td class="actions">
            <form method="POST" action="/admin/dashboard/queue/{{ q.id }}/approve" style="display:inline;">
              <button class="btn small">Approve &amp; send</button>
            </form>
            <form method="POST" action="/admin/dashboard/queue/{{ q.id }}/reject" style="display:inline;">
              <button class="btn small danger">Reject</button>
            </form>
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    <script>
      document.getElementById('select-all').addEventListener('change', function(e) {
        document.querySelectorAll('.row-check').forEach(function(cb){ cb.checked = e.target.checked; });
      });
    </script>
    {% else %}<div class="empty">No pending stories. The nightly run hasn't produced anything new since the last approval pass.</div>{% endif %}
  </div>

  <!-- ============== STORY HISTORY ============== -->
  <h2>Story history <span class="badge">last {{ history|length }}</span></h2>
  <div class="panel">
    {% if history %}
    <table>
      <thead><tr><th>Sent</th><th>Story</th><th>Word</th><th>For</th><th></th></tr></thead>
      <tbody>
      {% for h in history %}
        <tr class="history-row">
          <td class="muted">{{ h.sent_at[:16] }}</td>
          <td class="title">
            <div style="display:flex;align-items:flex-start;">
              <span class="story-thumb {% if not h.hero_svg %}empty-hero{% endif %}">
                {% if h.hero_svg %}{{ h.hero_svg|safe }}{% endif %}
              </span>
              <div>
                <div style="font-weight:600;">{{ h.story_title or '(untitled)' }}</div>
                <div class="preview">{{ h.body_preview }}…</div>
                <details>
                  <summary>View full story + illustration</summary>
                  <div class="full">
                    {% if h.hero_svg %}<div>{{ h.hero_svg|safe }}</div>{% endif %}
                    {% for p in h.body_paragraphs %}<p>{{ p }}</p>{% endfor %}
                    {% if h.word %}
                      <p style="background:#fdf3dc;padding:10px 14px;border-radius:8px;font-family:Georgia,serif;">
                        <strong>Word of the day:</strong> <em style="color:var(--rust);">{{ h.word }}</em>
                      </p>
                    {% endif %}
                  </div>
                </details>
              </div>
            </div>
          </td>
          <td>{% if h.word %}<span style="font-style:italic;color:var(--rust);">{{ h.word }}</span>{% endif %}</td>
          <td>
            {{ h.child_name }}
            {% if h.plan == 'pro' %}<div><span class="badge pro">PRO</span></div>{% endif %}
          </td>
          <td class="muted">{{ h.word_count or 0 }} words</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}<div class="empty">No deliveries yet. Approve items from the queue above to start building history.</div>{% endif %}
  </div>

  <!-- ============== SETTINGS ============== -->
  <h2>Settings</h2>
  <form method="POST" action="/admin/dashboard/settings">
    <div class="panel">
      <div class="lead">Runtime-configurable values. Persisted in the `settings` table. Hour/queue-target changes that need a restart are noted below.</div>
      <div class="row2">
        <label class="field">
          <span class="lab">Admin email (weekly digest destination)</span>
          <input type="email" name="admin_email" value="{{ settings.admin_email }}" required>
          <span class="help">Override via POCKETPLOT_ADMIN_EMAIL env var (env wins on startup; this stores the runtime value).</span>
        </label>
        <label class="field">
          <span class="lab">Word-count target (story band midpoint)</span>
          <input type="number" name="word_count_target" min="120" max="500" value="{{ settings.word_count_target }}" required>
          <span class="help">Sustainable generator aims for this ±50. Default 250 (so 200-300).</span>
        </label>
      </div>
      <div class="checkbox-row">
        <input type="checkbox" id="queue_toggle" name="review_queue_enabled" value="1" {% if settings.review_queue_enabled == '1' %}checked{% endif %}>
        <label for="queue_toggle"><strong>Review queue enabled</strong> &mdash; nightly-generated stories land in the admin queue instead of auto-sending.</label>
      </div>
      <div class="actions-row">
        <button class="btn" type="submit">Save settings</button>
        <a class="btn secondary" href="/admin/dashboard">Discard changes</a>
      </div>
    </div>
  </form>

  <!-- ============== SYSTEM STATUS ============== -->
  <h2>System status</h2>
  <div class="panel">
    <div class="system-grid">
      <div class="system-item">
        <div class="lab">Last cron / nightly run</div>
        <div class="val mono">{{ metrics.last_run_ts }}</div>
      </div>
      <div class="system-item">
        <div class="lab">Stories generated (24h)</div>
        <div class="val">{{ metrics.queued_24h }}</div>
      </div>
      <div class="system-item">
        <div class="lab">Stories delivered (24h)</div>
        <div class="val">{{ metrics.delivered_24h }}</div>
      </div>
      <div class="system-item">
        <div class="lab">Last run note</div>
        <div class="val mono" style="font-size:13px;">{{ metrics.last_run_note }}</div>
      </div>
    </div>
    {% if errors %}
      <h3 style="margin-top:18px;font-family:Fraunces;font-size:15px;color:var(--rustD);">Recent errors</h3>
      <div class="errors">
        {% for e in errors %}
          <div class="row"><span class="mono">{{ e.ts }}</span> · {{ e.note[:200] }}</div>
        {% endfor %}
      </div>
    {% endif %}
  </div>

</div>
</body></html>
"""

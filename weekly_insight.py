"""
PocketPlot — Weekly Insights email (Phase 8).

Sends each Pro subscriber a warm weekly digest every Sunday showing:
  - The 7 most recent Words of the Day they learned
  - Their Word Vault total (unique words)
  - Current streak
  - Badges earned so far
  - A short personalized blurb

Non-Pro subscribers are skipped. Subscribers with no engagement in the
last 7 days still get a "warm catch-up" message (so the cadence feels
predictable to parents), but with an encouraging note rather than stats.

APScheduler runs this every Sunday at 09:00 UTC via weekly_insights_job().
"""
import datetime as dt
import html as html_lib
import logging

log = logging.getLogger("pocketplot.insights")


# ---- The HTML template. Inline-styled for Gmail/Outlook compatibility. ----
WEEKLY_INSIGHT_HTML = """<!doctype html><html><body style="margin:0;padding:0;background:#f6f0e1;font-family:Georgia,serif;">
<div style="max-width:600px;margin:0 auto;padding:36px 28px;">

<div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#5c7c5a;margin-bottom:8px;">PocketPlot Weekly Insight</div>
<h1 style="font-family:Georgia,serif;font-size:26px;margin:0 0 14px;color:#1a241d;line-height:1.2;">
{heading}
</h1>

{intro}

<!-- Words learned this week -->
<div style="background:#fff;border:1px solid #d8cfb3;border-radius:12px;padding:20px;margin:20px 0;">
  <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#5c7c5a;font-weight:700;margin-bottom:10px;">Words learned this week</div>
  {word_chips}
</div>

<!-- Streak + Vault + Badges summary -->
<div style="display:flex;gap:14px;margin:20px 0;flex-wrap:wrap;">
  <div style="flex:1;min-width:140px;background:#fff;border:1px solid #d8cfb3;border-radius:12px;padding:18px;text-align:center;">
    <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#7a8a6a;font-weight:700;margin-bottom:6px;">Current streak</div>
    <div style="font-family:Georgia,serif;font-weight:600;font-size:32px;color:#c46a3f;line-height:1;">{streak}</div>
    <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;color:#7a8a6a;margin-top:4px;font-style:italic;">days in a row</div>
  </div>
  <div style="flex:1;min-width:140px;background:#fff;border:1px solid #d8cfb3;border-radius:12px;padding:18px;text-align:center;">
    <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#7a8a6a;font-weight:700;margin-bottom:6px;">Word Vault</div>
    <div style="font-family:Georgia,serif;font-weight:600;font-size:32px;color:#5c7c5a;line-height:1;">{word_count}</div>
    <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;color:#7a8a6a;margin-top:4px;font-style:italic;">unique words learned</div>
  </div>
  <div style="flex:1;min-width:140px;background:#fff;border:1px solid #d8cfb3;border-radius:12px;padding:18px;text-align:center;">
    <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#7a8a6a;font-weight:700;margin-bottom:6px;">Badges</div>
    <div style="font-family:Georgia,serif;font-weight:600;font-size:32px;color:#c9a96e;line-height:1;">{badge_count}</div>
    <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;color:#7a8a6a;margin-top:4px;font-style:italic;">earned to date</div>
  </div>
</div>

{badges_block}

<div style="text-align:center;margin:30px 0;">
  <a href="{dashboard_url}" style="display:inline-block;background:#c46a3f;color:#fff;padding:14px 28px;border-radius:999px;font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;font-weight:700;text-decoration:none;">See your dashboard</a>
</div>

<div style="font-family:Georgia,serif;font-size:13px;color:#7a8a6a;margin-top:24px;font-style:italic;line-height:1.6;">
  That's your week, {child_name}. A story a night, a word a night — and over time, a whole vocabulary.
  Thank you for reading together.
</div>

<div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:11px;color:#7a8a6a;margin-top:32px;text-align:center;">
  PocketPlot · manage your account: {account_url}
</div>

</div>
</body></html>"""


def render_weekly_insight_email(stats: dict, recent_words: list, badges: list,
                                child_name: str, dashboard_url: str,
                                account_url: str) -> str:
    """Render the full HTML for one subscriber's weekly insight."""
    if not recent_words:
        # Soft catch-up — warm, no stats to push.
        heading = f"A quiet week, {child_name}."
        intro = (
            "<p style=\"font-family:Georgia,serif;font-size:15px;color:#4a3a2a;"
            "line-height:1.6;margin:0 0 14px;\">"
            "No stories landed this week. That's okay — bedtime is busy. "
            "Whenever you're ready, the next story is just a tap away.</p>"
        )
        word_chips = ("<div style=\"font-family:Georgia,serif;font-style:italic;"
                      "color:#7a8a6a;font-size:13px;\">"
                      "No new words this week.</div>")
        streak_disp = "0"
        word_count_disp = str(stats.get("word_count", 0))
        badge_disp = str(stats.get("badge_count", 0))
        badges_block = ""
    else:
        heading = f"This week with {child_name}."
        intro = (
            "<p style=\"font-family:Georgia,serif;font-size:15px;color:#4a3a2a;"
            "line-height:1.6;margin:0 0 14px;\">"
            f"Seven nights, seven small goodnights. Here are the words "
            f"{child_name} met this week, and how the bigger picture is "
            f"shaping up.</p>"
        )
        chips = "".join(
            f'<span style="display:inline-block;margin:0 6px 6px 0;padding:6px 12px;'
            f'background:#fdf3dc;border-radius:99px;font-family:Georgia,serif;'
            f'font-style:italic;color:#c46a3f;font-size:14px;font-weight:600;">'
            f'{html_lib.escape(w["word"])}</span>'
            for w in recent_words
        )
        word_chips = f'<div style="margin-top:6px;">{chips}</div>'
        streak_disp = str(stats.get("streak_days", 0))
        word_count_disp = str(stats.get("word_count", 0))
        badge_disp = str(stats.get("badge_count", 0))
        # Badges block — only show the most recent three earned.
        if badges:
            recent_badge_chips = []
            for b in badges[-3:]:
                recent_badge_chips.append(
                    f'<div style="background:#fdf3dc;border:1px solid #c9a96e;border-radius:10px;'
                    f'padding:12px;text-align:center;width:120px;">'
                    f'<div style="font-size:28px;line-height:1;margin-bottom:4px;">{b["icon"]}</div>'
                    f'<div style="font-family:\'Helvetica Neue\',Arial,sans-serif;'
                    f'font-size:11px;font-weight:700;color:#1a241d;line-height:1.2;">{b["label"]}</div>'
                    f'</div>'
                )
            badges_block = (
                '<div style="background:#fff;border:1px solid #d8cfb3;border-radius:12px;'
                'padding:20px;margin:20px 0;">'
                '<div style="font-family:\'Helvetica Neue\',Arial,sans-serif;'
                'font-size:11px;letter-spacing:.14em;text-transform:uppercase;'
                'color:#5c7c5a;font-weight:700;margin-bottom:10px;">Recent badges</div>'
                f'<div style="display:flex;gap:14px;flex-wrap:wrap;">{"".join(recent_badge_chips)}</div>'
                '</div>'
            )
        else:
            badges_block = ""

    return WEEKLY_INSIGHT_HTML.format(
        heading=heading,
        intro=intro,
        word_chips=word_chips,
        streak=streak_disp,
        word_count=word_count_disp,
        badge_count=badge_disp,
        badges_block=badges_block,
        child_name=html_lib.escape(child_name),
        dashboard_url=html_lib.escape(dashboard_url),
        account_url=html_lib.escape(account_url),
    )


def render_weekly_insight_for_subscriber(db, sub_id: int, site_url: str,
                                          _send_email_fn, app_log) -> bool:
    """Build + send one Pro subscriber's weekly insight email.

    Returns True if an email was sent. _send_email_fn(to, subject,
    plain, html) is the same signature as app._send_raw_email so we
    don't import the Flask module here.
    """
    conn = db()
    sub = conn.execute("SELECT * FROM subscribers WHERE id=?", (sub_id,)).fetchone()
    conn.close()
    if not sub or sub["plan"] != "pro" or not sub["active"]:
        return False
    if dict(sub).get("avatar_json"):  # noqa — placeholder; keep imports happy
        pass

    import gamification as _gam
    stats = _gam.stats_for_subscriber(db, sub_id)
    recent = _gam.recent_words(db, sub_id, limit=7)
    badges = _gam.earned_badges(db, sub_id)

    child_name = sub["child_name"] or "your child"
    dashboard_url = site_url.rstrip("/") + "/me"
    account_url = site_url.rstrip("/") + "/me"

    subject = f"PocketPlot Weekly · {child_name}'s week"
    html_body = render_weekly_insight_email(
        stats=stats, recent_words=recent, badges=badges,
        child_name=child_name, dashboard_url=dashboard_url,
        account_url=account_url,
    )
    plain_body = (
        f"Hello! Here's {child_name}'s week on PocketPlot.\n\n"
        f"- Streak: {stats.get('streak_days', 0)} days\n"
        f"- Word Vault: {stats.get('word_count', 0)} unique words\n"
        f"- Badges earned: {stats.get('badge_count', 0)}\n\n"
        f"Open the dashboard: {dashboard_url}\n"
    )

    try:
        _send_email_fn(sub["email"], subject, plain_body, html_body)
        app_log.info("weekly insight sent to sub %s (%s)", sub_id, sub["email"])
        return True
    except Exception as e:
        app_log.warning("weekly insight failed for sub %s: %s", sub_id, e)
        return False


def render_and_send_all(db, site_url, _send_email_fn, app_log,
                         only_pro_active: bool = True) -> int:
    """Send weekly insight to all active subscribers (or Pro-only).

    Returns count of emails sent.
    """
    conn = db()
    if only_pro_active:
        rows = conn.execute(
            "SELECT id FROM subscribers WHERE plan='pro' AND active=1"
        ).fetchall()
    else:
        rows = conn.execute("SELECT id FROM subscribers WHERE active=1").fetchall()
    conn.close()
    sent = 0
    for r in rows:
        if render_weekly_insight_for_subscriber(
            db, r["id"], site_url, _send_email_fn, app_log,
        ):
            sent += 1
    return sent

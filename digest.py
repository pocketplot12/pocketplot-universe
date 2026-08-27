"""Phase 4 — Weekly digest email renderer."""
import json
import html as html_lib


def render_digest_email(items, counts, site_url):
    """Render the digest email HTML (inline-styled for Gmail/Outlook).

    items: list of review_queue rows
    counts: dict from queue_counts()
    site_url: SITE_URL constant from app.py
    """
    rows_html = []
    for r in items:
        try:
            story_obj = json.loads(r["story_json"]) if r["story_json"] else {}
        except Exception:
            story_obj = {}
        try:
            w = json.loads(r["word_json"]) if r["word_json"] else {}
        except Exception:
            w = {}
        title = story_obj.get("title", "(untitled)")
        word = w.get("w", "")
        rows_html.append(
            '<tr><td style="padding:8px 12px;border-bottom:1px solid #e0d8c0;font-family:Georgia,serif;color:#1a241d;">'
            f'<a href="{site_url}/admin/queue/{r["id"]}" style="color:#c46a3f;text-decoration:none;font-weight:600;">{html_lib.escape(title)}</a>'
            f'</td><td style="padding:8px 12px;border-bottom:1px solid #e0d8c0;font-family:Georgia,serif;color:#5c7c5a;">{html_lib.escape(word)}</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid #e0d8c0;font-family:Georgia,serif;color:#4a3a2a;">{html_lib.escape(r["child_name"])}</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid #e0d8c0;font-family:Georgia,serif;color:#7a8a6a;font-size:12px;">{html_lib.escape(r["created_at"][:10])}</td>'
            '</tr>'
        )
    rows_str = "".join(rows_html) if rows_html else (
        '<tr><td colspan="4" style="padding:14px;text-align:center;color:#7a8a6a;font-style:italic;">No pending items.</td></tr>'
    )
    plural = "story" if counts["pending"] == 1 else "stories"
    return (
        '<!doctype html><html><body style="margin:0;padding:0;background:#f6f0e1;font-family:Georgia,serif;">'
        '<div style="max-width:640px;margin:0 auto;padding:36px 28px;">'
        '<div style="font-family:\'Helvetica Neue\',Arial,sans-serif;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:#5c7c5a;margin-bottom:8px;">PocketPlot Digest</div>'
        f'<h1 style="font-size:26px;margin:0 0 14px;color:#1a241d;">{counts["pending"]} {plural} awaiting review</h1>'
        '<p style="font-size:14px;color:#4a3a2a;line-height:1.55;">'
        "Weekly digest of new PocketPlot content your nightly run generated. Click any title to review the story, hero illustration, and game payload — approve to send."
        '</p>'
        '<div style="background:#fff;border:1px solid #d8cfb3;border-radius:12px;overflow:hidden;margin:20px 0;">'
        '<table style="width:100%;border-collapse:collapse;background:#fff;">'
        '<thead><tr style="background:#ecdfc3;">'
        '<th style="padding:10px 12px;text-align:left;font-family:\'Helvetica Neue\',Arial,sans-serif;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#5c7c5a;">Title</th>'
        '<th style="padding:10px 12px;text-align:left;font-family:\'Helvetica Neue\',Arial,sans-serif;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#5c7c5a;">Word</th>'
        '<th style="padding:10px 12px;text-align:left;font-family:\'Helvetica Neue\',Arial,sans-serif;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#5c7c5a;">For</th>'
        '<th style="padding:10px 12px;text-align:left;font-family:\'Helvetica Neue\',Arial,sans-serif;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#5c7c5a;">Queued</th>'
        '</tr></thead>'
        f'<tbody>{rows_str}</tbody>'
        '</table></div>'
        f'<a href="{site_url}/admin/queue" style="display:inline-block;background:#c46a3f;color:#fff;padding:12px 24px;border-radius:999px;font-family:\'Helvetica Neue\',Arial,sans-serif;font-size:14px;font-weight:700;text-decoration:none;">Open the review queue</a>'
        f'<p style="font-size:12px;color:#7a8a6a;margin-top:24px;font-style:italic;">Counts: {counts["pending"]} pending &middot; {counts["approved"]} approved &middot; {counts["rejected"]} rejected &middot; {counts["sent"]} sent.</p>'
        '</div></body></html>'
    )

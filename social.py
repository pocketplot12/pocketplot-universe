"""
PocketPlot Universe - social layer (v24): comments + reactions + cover generation.

Comments:
  - Threaded (top-level + replies)
  - Soft delete (body hidden, but thread structure preserved)
  - Audit logged

Reactions:
  - 6 emoji types: heart (love), fire (hot), sparkles (magical),
    rocket (awesome), mind_blown (epic), laughing (funny)
  - One per (world, subscriber, kind) - unique

Story covers:
  - 1200x630 PNG generated from world metadata
  - Pure PIL (no SVG-to-PNG conversion needed)
  - Stored in /covers/<world_id>.png
  - Cached in story_covers table
"""
import os
import re
import datetime as dt
from html import escape as _e


def _conn(db):
    if hasattr(db, 'execute'):
        return db
    if callable(db):
        return db()
    return db


# ====================================================================
# COMMENTS
# ====================================================================

REACTION_KINDS = [
    ('heart', '❤️', 'love'),
    ('fire', '🔥', 'hot'),
    ('sparkles', '✨', 'magical'),
    ('rocket', '🚀', 'awesome'),
    ('mind_blown', '🤯', 'epic'),
    ('laughing', '😂', 'funny'),
]


def add_comment(db, world_id, subscriber_id, body, parent_id=None):
    """Add a comment. Returns the comment id."""
    body = (body or '').strip()
    if not body:
        raise ValueError("Comment body required")
    if len(body) > 4000:
        body = body[:4000]
    c = _conn(db)
    cur = c.execute(
        "INSERT INTO comments(world_id, subscriber_id, parent_id, body, created_at) VALUES (?, ?, ?, ?, ?)",
        (world_id, subscriber_id, parent_id, body,
         dt.datetime.utcnow().isoformat(timespec='seconds')),
    )
    c.commit()
    return cur.lastrowid


def list_comments(db, world_id, include_deleted=False):
    """List all comments for a world (threaded). Returns top-level + replies nested."""
    c = _conn(db)
    rows = c.execute(
        "SELECT c.*, s.username, s.tier FROM comments c "
        "JOIN subscribers s ON c.subscriber_id = s.id "
        "WHERE c.world_id = ? AND c.parent_id IS NULL "
        "ORDER BY c.created_at ASC",
        (world_id,),
    ).fetchall()
    top = []
    for row in rows:
        d = dict(row)
        if d.get('is_deleted') and not include_deleted:
            d['body'] = '[deleted]'
            d['username'] = ''
        # Replies
        rrows = c.execute(
            "SELECT c.*, s.username FROM comments c "
            "JOIN subscribers s ON c.subscriber_id = s.id "
            "WHERE c.parent_id = ? ORDER BY c.created_at ASC",
            (d['id'],),
        ).fetchall()
        replies = []
        for r in rrows:
            rd = dict(r)
            if rd.get('is_deleted') and not include_deleted:
                rd['body'] = '[deleted]'
                rd['username'] = ''
            replies.append(rd)
        d['replies'] = replies
        top.append(d)
    return top


def soft_delete_comment(db, comment_id, subscriber_id, is_admin=False):
    """Soft-delete a comment. Returns True if deleted, False if not authorized."""
    c = _conn(db)
    row = c.execute("SELECT subscriber_id, is_deleted FROM comments WHERE id=?",
                    (comment_id,)).fetchone()
    if not row:
        return False
    if row['is_deleted']:
        return True  # already deleted
    if not is_admin and row['subscriber_id'] != subscriber_id:
        return False
    c.execute("UPDATE comments SET is_deleted=1, body='', updated_at=? WHERE id=?",
              (dt.datetime.utcnow().isoformat(timespec='seconds'), comment_id))
    c.commit()
    return True


# ====================================================================
# REACTIONS
# ====================================================================

def toggle_reaction(db, world_id, subscriber_id, kind):
    """Toggle a reaction. Returns the new state: 'added' or 'removed'."""
    valid_kinds = {r[0] for r in REACTION_KINDS}
    if kind not in valid_kinds:
        raise ValueError("Unknown reaction kind")
    c = _conn(db)
    row = c.execute(
        "SELECT id FROM reactions WHERE world_id=? AND subscriber_id=? AND kind=?",
        (world_id, subscriber_id, kind),
    ).fetchone()
    if row:
        c.execute("DELETE FROM reactions WHERE id=?", (row['id'],))
        c.commit()
        return 'removed'
    c.execute(
        "INSERT INTO reactions(world_id, subscriber_id, kind, created_at) VALUES (?, ?, ?, ?)",
        (world_id, subscriber_id, kind,
         dt.datetime.utcnow().isoformat(timespec='seconds')),
    )
    c.commit()
    return 'added'


def reaction_counts(db, world_id):
    """Return dict of {kind: count} for a world."""
    c = _conn(db)
    rows = c.execute(
        "SELECT kind, COUNT(*) AS n FROM reactions WHERE world_id=? GROUP BY kind",
        (world_id,),
    ).fetchall()
    out = {k: 0 for k, _, _ in REACTION_KINDS}
    for row in rows:
        out[row['kind']] = row['n']
    return out


def user_reactions(db, world_id, subscriber_id):
    """Return set of reaction kinds the user has given this world."""
    c = _conn(db)
    rows = c.execute(
        "SELECT kind FROM reactions WHERE world_id=? AND subscriber_id=?",
        (world_id, subscriber_id),
    ).fetchall()
    return {row['kind'] for row in rows}


# ====================================================================
# STORY COVERS
# ====================================================================

def _slugify(text):
    """Convert a title to a URL slug."""
    text = re.sub(r'[^\w\s-]', '', text or '').strip().lower()
    return re.sub(r'[-\s]+', '-', text)[:80] or 'story'


def _palette_for(genre):
    """Return (bg_top, bg_bot, accent, fg) for a genre."""
    palettes = {
        'fantasy':      ((15, 30, 60), (40, 20, 80), (201, 160, 78), (243, 233, 210)),
        'scifi':        ((10, 20, 40), (30, 50, 90), (93, 222, 240), (232, 216, 184)),
        'noir':         ((15, 15, 25), (35, 25, 30), (180, 140, 100), (220, 200, 180)),
        'romance':      ((40, 15, 35), (90, 30, 70), (255, 200, 160), (255, 230, 200)),
        'adventure':    ((15, 30, 20), (40, 70, 50), (180, 220, 100), (240, 230, 200)),
        'horror':       ((10, 5, 15), (35, 15, 30), (200, 100, 100), (220, 180, 160)),
        'cyberpunk':    ((20, 10, 35), (60, 20, 80), (93, 222, 240), (240, 230, 240)),
        'fairytales':   ((30, 25, 50), (80, 50, 100), (255, 200, 220), (255, 240, 230)),
        'superhero':    ((10, 20, 60), (200, 180, 60), (255, 220, 100), (255, 245, 220)),
        'chicklit':     ((40, 25, 35), (90, 60, 70), (240, 180, 200), (250, 220, 230)),
        'roleplaying':  ((15, 20, 30), (40, 50, 70), (160, 200, 220), (230, 240, 240)),
        'historical':   ((30, 20, 15), (70, 50, 35), (200, 160, 100), (240, 220, 200)),
        'thriller':     ((10, 15, 20), (30, 40, 50), (220, 220, 220), (240, 230, 230)),
        'comedy':       ((40, 30, 15), (80, 60, 40), (240, 200, 100), (255, 240, 220)),
        'drama':        ((20, 15, 25), (60, 35, 50), (220, 180, 200), (240, 220, 230)),
        'action':       ((15, 10, 10), (60, 25, 15), (255, 120, 80), (255, 220, 200)),
    }
    return palettes.get(genre, palettes['fantasy'])


def generate_cover(db, world_id, title, genre, tone, subtitle='', out_dir='/root/pocketplot/covers'):
    """Generate a 1200x630 cover PNG. Saves to disk + records in story_covers."""
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'{world_id}.png')

    # If already cached and recent, skip
    c = _conn(db)
    row = c.execute("SELECT image_path, generated_at FROM story_covers WHERE world_id=?",
                    (world_id,)).fetchone()
    if row and os.path.exists(row['image_path']):
        return row['image_path']

    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as e:
        return None

    W, H = 1200, 630
    bg_top, bg_bot, accent, fg = _palette_for(genre)
    img = Image.new('RGB', (W, H), bg_top)
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    for y in range(H):
        t = y / H
        r = int(bg_top[0] * (1 - t) + bg_bot[0] * t)
        g = int(bg_top[1] * (1 - t) + bg_bot[1] * t)
        b = int(bg_top[2] * (1 - t) + bg_bot[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Decorative: corner brackets
    bracket_color = accent
    bracket_len = 40
    inset = 30
    # Top-left
    draw.line([(inset, inset), (inset + bracket_len, inset)], fill=bracket_color, width=4)
    draw.line([(inset, inset), (inset, inset + bracket_len)], fill=bracket_color, width=4)
    # Top-right
    draw.line([(W - inset, inset), (W - inset - bracket_len, inset)], fill=bracket_color, width=4)
    draw.line([(W - inset, inset), (W - inset, inset + bracket_len)], fill=bracket_color, width=4)
    # Bottom-left
    draw.line([(inset, H - inset), (inset + bracket_len, H - inset)], fill=bracket_color, width=4)
    draw.line([(inset, H - inset), (inset, H - inset - bracket_len)], fill=bracket_color, width=4)
    # Bottom-right
    draw.line([(W - inset, H - inset), (W - inset - bracket_len, H - inset)], fill=bracket_color, width=4)
    draw.line([(W - inset, H - inset), (W - inset, H - inset - bracket_len)], fill=bracket_color, width=4)

    # Decorative horizontal line near top
    draw.line([(W//2 - 100, 70), (W//2 + 100, 70)], fill=accent, width=2)

    # Eyebrow text (genre + tone)
    eyebrow = f'{genre.upper()}  -  {tone.upper() if tone else "STORY"}'
    try:
        font_eyebrow = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 64)
        font_subtitle = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        font_footer = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except Exception:
        font_eyebrow = font_title = font_subtitle = font_footer = ImageFont.load_default()

    # Draw eyebrow
    bbox = draw.textbbox((0, 0), eyebrow, font=font_eyebrow)
    ew = bbox[2] - bbox[0]
    draw.text(((W - ew) / 2, 100), eyebrow, fill=accent, font=font_eyebrow)

    # Draw title (wrapped)
    title_lines = _wrap_text(title, font_title, W - 200, draw)[:3]  # max 3 lines
    y = 160
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) / 2, y), line, fill=fg, font=font_title)
        y += 80

    # Subtitle (italic-feel via lighter color)
    if subtitle:
        y += 20
        sub_lines = _wrap_text(subtitle, font_subtitle, W - 200, draw)[:2]
        for line in sub_lines:
            bbox = draw.textbbox((0, 0), line, font=font_subtitle)
            sw = bbox[2] - bbox[0]
            draw.text(((W - sw) / 2, y), line, fill=(fg[0], fg[1], fg[2], 200) if len(fg) > 3 else fg, font=font_subtitle)
            y += 36

    # Footer: POCKETPLOT UNIVERSE
    footer = 'POCKETPLOT UNIVERSE'
    bbox = draw.textbbox((0, 0), footer, font=font_footer)
    fw = bbox[2] - bbox[0]
    draw.text(((W - fw) / 2, H - 60), footer, fill=accent, font=font_footer)

    # Decorative line near bottom
    draw.line([(W//2 - 100, H - 90), (W//2 + 100, H - 90)], fill=accent, width=2)

    img.save(out_path, 'PNG', optimize=True)

    # Cache the path
    c.execute(
        "INSERT OR REPLACE INTO story_covers(world_id, image_path, width, height, generated_at) VALUES (?, ?, ?, ?, ?)",
        (world_id, out_path, W, H, dt.datetime.utcnow().isoformat(timespec='seconds')),
    )
    c.commit()
    return out_path


def _wrap_text(text, font, max_w, draw):
    """Wrap text to fit max_w pixels."""
    words = text.split()
    lines = []
    cur = []
    for wd in words:
        test = ' '.join(cur + [wd])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_w:
            if cur:
                lines.append(' '.join(cur))
                cur = [wd]
            else:
                lines.append(wd)
        else:
            cur.append(wd)
    if cur:
        lines.append(' '.join(cur))
    return lines

"""
PocketPlot — Avatar builder (Phase 6)

Privacy-first avatar system. No photo uploads, no PII. A child's avatar
is a small JSON object selecting one part per category from a generic SVG
parts library. The composer reads this and renders the main character
with those parts; the helper character stays independent (rotates from
story_pools.CHARACTERS as before).

Avatar shape:
{
    "skin":    "warm" | "light" | "olive" | "brown" | "deep",
    "hair":    "curly" | "short" | "long" | "bun" | "bald",
    "eyes":    "round" | "sparkle" | "sleepy" | "wide" | "closed_smile",
    "outfit":  "pajamas" | "adventure" | "robe" | "swimsuit" | "sweater",
    "accessory": "none" | "glasses" | "hat" | "cape" | "star_earrings",
    "expression": "smile" | "curious" | "wonder" | "cheerful",
}

Each part is an inline SVG fragment. The composer concatenates them into
a single <g> at the character's anchor point.

The defaults below are *required* — if any key is missing from a stored
avatar, the part corresponding to the default is substituted. This means
the system never breaks on legacy data.
"""
import json
import logging

log = logging.getLogger("pocketplot.avatar")


# ---- The parts library. Each part is a *fragment* (a <g> or two) drawn
# relative to (0,0) — the character's anchor. The composer wraps them in
# a <g transform="translate(X,Y) scale(S)"> so we draw at the origin.

SKIN_TONES = {
    "warm":  "#f4cba0",
    "light": "#f8d8b8",
    "olive": "#c89972",
    "brown": "#a87044",
    "deep":  "#7a4a2b",
}

HAIR = {
    # All drawn over the head (radius ~22 from anchor). Centered around y=-12.
    "curly": (
        '<g fill="#3a2418">'
        '  <circle cx="-12" cy="-22" r="9"/>'
        '  <circle cx="0"   cy="-26" r="10"/>'
        '  <circle cx="12"  cy="-22" r="9"/>'
        '  <circle cx="-16" cy="-12" r="6"/>'
        '  <circle cx="16"  cy="-12" r="6"/>'
        '</g>'
    ),
    "short": (
        '<g fill="#3a2418">'
        '  <ellipse cx="0" cy="-20" rx="22" ry="10"/>'
        '</g>'
    ),
    "long": (
        '<g fill="#3a2418">'
        '  <ellipse cx="0" cy="-20" rx="22" ry="10"/>'
        '  <rect x="-22" y="-22" width="6" height="32" rx="3"/>'
        '  <rect x="16"  y="-22" width="6" height="32" rx="3"/>'
        '</g>'
    ),
    "bun": (
        '<g fill="#3a2418">'
        '  <ellipse cx="0" cy="-20" rx="22" ry="10"/>'
        '  <circle cx="0" cy="-30" r="8"/>'
        '</g>'
    ),
    "bald": "",  # explicit no-hair option
}

EYES = {
    # Drawn at face center (y=-8). Each is a tiny pair of dots.
    "round": (
        '<g fill="#1a241d">'
        '  <circle cx="-7" cy="-8" r="2.5"/>'
        '  <circle cx="7"  cy="-8" r="2.5"/>'
        '  <circle cx="-6" cy="-9" r="0.7" fill="#fff8e7"/>'
        '  <circle cx="8"  cy="-9" r="0.7" fill="#fff8e7"/>'
        '</g>'
    ),
    "sparkle": (
        '<g fill="#1a241d">'
        '  <circle cx="-7" cy="-8" r="3"/>'
        '  <circle cx="7"  cy="-8" r="3"/>'
        '  <circle cx="-5" cy="-9" r="1" fill="#fff8e7"/>'
        '  <circle cx="9"  cy="-9" r="1" fill="#fff8e7"/>'
        '</g>'
    ),
    "sleepy": (
        '<g fill="none" stroke="#1a241d" stroke-width="1.6" stroke-linecap="round">'
        '  <path d="M -11 -8 q 4 4 8 0"/>'
        '  <path d="M 3 -8 q 4 4 8 0"/>'
        '</g>'
    ),
    "wide": (
        '<g fill="#1a241d">'
        '  <ellipse cx="-7" cy="-8" rx="3.5" ry="2.8"/>'
        '  <ellipse cx="7"  cy="-8" rx="3.5" ry="2.8"/>'
        '</g>'
    ),
    "closed_smile": (
        '<g fill="none" stroke="#1a241d" stroke-width="1.6" stroke-linecap="round">'
        '  <path d="M -10 -8 q 3 3 6 0"/>'
        '  <path d="M 4 -8 q 3 3 6 0"/>'
        '</g>'
    ),
}

EXPRESSION = {
    # Drawn at y=-2 to y=4 — the mouth area.
    "smile":     '<path d="M -6 0 q 6 6 12 0" fill="none" stroke="#1a241d" stroke-width="1.6" stroke-linecap="round"/>',
    "curious":   '<path d="M -5 0 q 5 3 10 0" fill="none" stroke="#1a241d" stroke-width="1.6" stroke-linecap="round"/><circle cx="6" cy="-3" r="1" fill="#1a241d"/>',
    "wonder":    '<ellipse cx="2" cy="1" rx="3" ry="4" fill="#3a2418"/>',
    "cheerful":  '<path d="M -7 0 q 7 8 14 0" fill="none" stroke="#1a241d" stroke-width="1.8" stroke-linecap="round"/>',
}

OUTFIT = {
    # Drawn around the torso (y=0 to y=18). Each is a colored body.
    "pajamas": (
        '<g>'
        '  <rect x="-15" y="0" width="30" height="20" fill="#7a9bc4" rx="6"/>'
        '  <circle cx="0" cy="10" r="2" fill="#5c7c5a"/>'
        '  <circle cx="-8" cy="10" r="1.5" fill="#5c7c5a"/>'
        '  <circle cx="8"  cy="10" r="1.5" fill="#5c7c5a"/>'
        '</g>'
    ),
    "adventure": (
        '<g>'
        '  <rect x="-15" y="0" width="30" height="20" fill="#7a5c3c" rx="6"/>'
        '  <rect x="-15" y="4" width="30" height="3" fill="#c9a96e"/>'
        '  <circle cx="0" cy="14" r="2" fill="#c46a3f"/>'
        '</g>'
    ),
    "robe": (
        '<g>'
        '  <path d="M -18 0 L -10 -2 L 10 -2 L 18 0 L 18 20 L -18 20 Z" fill="#5c4a7c" stroke="#3a2f5a" stroke-width="1.5"/>'
        '  <path d="M 0 -2 L 0 20" stroke="#c9a96e" stroke-width="2"/>'
        '</g>'
    ),
    "swimsuit": (
        '<g>'
        '  <rect x="-13" y="0" width="26" height="14" fill="#c46a3f" rx="4"/>'
        '  <path d="M -13 14 q 13 8 26 0" fill="#c46a3f"/>'
        '</g>'
    ),
    "sweater": (
        '<g>'
        '  <rect x="-15" y="0" width="30" height="20" fill="#a87044" rx="6"/>'
        '  <path d="M -10 5 q 10 2 20 0" stroke="#7a4a2b" stroke-width="1.2" fill="none"/>'
        '  <path d="M -10 11 q 10 2 20 0" stroke="#7a4a2b" stroke-width="1.2" fill="none"/>'
        '  <path d="M -10 17 q 10 2 20 0" stroke="#7a4a2b" stroke-width="1.2" fill="none"/>'
        '</g>'
    ),
}

ACCESSORY = {
    # Anchored relative to head (y < -10) or body (y in 0..16). Drawn last
    # so they sit on top.
    "none":           "",
    "glasses": (
        '<g fill="none" stroke="#1a241d" stroke-width="1.8">'
        '  <circle cx="-7" cy="-8" r="5"/>'
        '  <circle cx="7"  cy="-8" r="5"/>'
        '  <line x1="-2" y1="-8" x2="2" y2="-8"/>'
        '</g>'
    ),
    "hat": (
        '<g fill="#c46a3f" stroke="#1a241d" stroke-width="1.4">'
        '  <path d="M -18 -16 L 18 -16 L 14 -30 L -14 -30 Z"/>'
        '  <ellipse cx="0" cy="-15" rx="18" ry="3"/>'
        '  <circle cx="0" cy="-30" r="3" fill="#ffe5a0"/>'
        '</g>'
    ),
    "cape": (
        '<g fill="#c46a3f">'
        '  <path d="M -22 0 L -10 -2 L 10 -2 L 22 0 L 18 22 L -18 22 Z"/>'
        '  <circle cx="0" cy="2" r="2" fill="#c9a96e"/>'
        '</g>'
    ),
    "star_earrings": (
        '<g fill="#c9a96e">'
        '  <path d="M -22 -6 l -2 4 l -4 0 l 3 3 l -1 4 l 4 -2 l 4 2 l -1 -4 l 3 -3 l -4 0 z"/>'
        '  <path d="M 22 -6 l -2 4 l -4 0 l 3 3 l -1 4 l 4 -2 l 4 2 l -1 -4 l 3 -3 l -4 0 z"/>'
        '</g>'
    ),
}


# ---- Defaults. If a stored avatar is missing a key (or is the empty {}),
# we substitute the default for that key.

DEFAULTS = {
    "skin":       "warm",
    "hair":       "curly",
    "eyes":       "round",
    "outfit":     "pajamas",
    "accessory":  "none",
    "expression": "smile",
}


def normalize_avatar(avatar: dict | None) -> dict:
    """Return a complete avatar dict, substituting defaults for missing keys.
    Also clamps invalid values to the first option in each category (so
    legacy data never crashes the composer)."""
    av = dict(avatar or {})
    out = {}
    for k, default_v in DEFAULTS.items():
        v = av.get(k)
        if v and v in _valid_keys_for(k):
            out[k] = v
        else:
            out[k] = default_v
    return out


def _valid_keys_for(category: str):
    return {
        "skin":       list(SKIN_TONES.keys()),
        "hair":       list(HAIR.keys()),
        "eyes":       list(EYES.keys()),
        "outfit":     list(OUTFIT.keys()),
        "accessory":  list(ACCESSORY.keys()),
        "expression": list(EXPRESSION.keys()),
    }[category]


def avatar_options_for_ui() -> dict:
    """Return the catalog the /me builder needs (human-readable labels for
    each option, in each category)."""
    return {
        "skin":       [(k, k.capitalize()) for k in SKIN_TONES.keys()],
        "hair":       [(k, k.replace("_", " ").capitalize()) for k in HAIR.keys()],
        "eyes":       [(k, k.replace("_", " ").capitalize()) for k in EYES.keys()],
        "outfit":     [(k, k.replace("_", " ").capitalize()) for k in OUTFIT.keys()],
        "accessory":  [(k, k.replace("_", " ").capitalize()) for k in ACCESSORY.keys()],
        "expression": [(k, k.capitalize()) for k in EXPRESSION.keys()],
    }


def render_avatar_svg(avatar: dict, anchor_x: int, anchor_y: int,
                      scale: float = 1.0, facing_right: bool = True) -> str:
    """Compose the avatar into a single <g> fragment ready to drop into
    the procedural scene.

    The avatar is drawn relative to (0,0); the caller (the composer) wraps
    it in the same translate/scale transform used for any character. We
    mirror the X-axis when `facing_right` is False so the avatar can walk
    the other way.

    Drawing order (back to front):
        1. outfit
        2. head + skin
        3. hair
        4. expression
        5. eyes
        6. accessory
    """
    av = normalize_avatar(avatar)
    skin_fill = SKIN_TONES[av["skin"]]

    # The base "head + body" silhouette, generic across all avatars. Drawn
    # before the outfit so the outfit shows on top.
    base = (
        '<g>'  # body
        '  <rect x="-12" y="0" width="24" height="14" fill="{skin}" rx="6"/>'
        # head
        '  <circle cx="0" cy="-12" r="14" fill="{skin}"/>'
        # small arms
        '  <rect x="-16" y="2" width="4" height="12" rx="2" fill="{skin}"/>'
        '  <rect x="12"  y="2" width="4" height="12" rx="2" fill="{skin}"/>'
        # small legs
        '  <rect x="-8" y="14" width="6" height="6" rx="2" fill="{skin}"/>'
        '  <rect x="2"  y="14" width="6" height="6" rx="2" fill="{skin}"/>'
        '</g>'
    ).format(skin=skin_fill)

    parts = [
        base,
        OUTFIT[av["outfit"]],
        HAIR[av["hair"]],
        EXPRESSION[av["expression"]],
        EYES[av["eyes"]],
        ACCESSORY[av["accessory"]],
    ]
    body_inner = "".join(p for p in parts if p)
    transform = 'translate({x},{y}) scale({s})'.format(
        x=anchor_x, y=anchor_y, s=scale
    )
    if not facing_right:
        # Mirror around the character's local x=0 so we don't push them
        # off-canvas.
        transform += ' scale(-1,1)'
    return f'<g transform="{transform}">{body_inner}</g>'


def avatar_json_blob(avatar: dict) -> str:
    """Stable JSON serialization for storing in the subscribers table."""
    return json.dumps(normalize_avatar(avatar), ensure_ascii=False, sort_keys=True)


def parse_avatar_blob(blob: str | None) -> dict:
    """Read a stored avatar blob. Returns the default avatar if missing or
    malformed (so legacy subscribers get a sensible starting point)."""
    if not blob:
        return dict(DEFAULTS)
    try:
        return normalize_avatar(json.loads(blob))
    except Exception:
        return dict(DEFAULTS)

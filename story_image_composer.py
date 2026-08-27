"""
PocketPlot — Procedural SVG composer (Phase 2A/B)

Builds a unique 400×400 hero illustration for each generated story by composing
from a small library of modular SVG parts:
    - 8 backgrounds (selected by story.scene.time_of_day)
    - 5 characters × 3 poses (selected by story.scene.species + story.scene.emotion)
    - 6 props (randomly selected; some have natural setting affinities)

Every story produces a *different* image. None of the parts require external
assets — all SVG is hand-crafted and embedded as Python strings.

API:
    compose_story_image(story: dict) -> str   # returns an <svg>...</svg> string
"""

from __future__ import annotations
import random
import re
from typing import Optional

# ============================================================================
# PALETTE (locked, matches PocketPlot's warm-pastel KAK palette)
# ============================================================================
SKY_NIGHT = "#2B2347"
SKY_DUSK = "#553B62"
SKY_MORNING = "#F8D77E"
SKY_AFTERNOON = "#FFE5A0"
GROUND_HILL = "#92D4A8"
GROUND_DARK = "#5C7C5A"
TEXT_DARK = "#3A3633"

# ============================================================================
# BACKGROUNDS (8 modules)
# Each returns a complete <g>...</g> with a sky gradient + ground.
# Selected by time_of_day.
# ============================================================================

def _bg_starry_night():
    return f'''<g fill="#FFE5A0">
  <circle cx="60" cy="80" r="2"/>
  <circle cx="120" cy="50" r="1.6"/>
  <circle cx="200" cy="80" r="1.8"/>
  <circle cx="280" cy="60" r="1.4"/>
  <circle cx="340" cy="90" r="2"/>
</g>
<g transform="translate(330,80)">
  <circle r="14" fill="#FFE5A0"/>
  <circle cx="3" cy="-2" r="11" fill="{SKY_NIGHT}"/>
</g>
<path d="M 0 360 Q 100 320 200 340 Q 300 360 400 330 L 400 400 L 0 400 Z" fill="{GROUND_DARK}" stroke="{TEXT_DARK}" stroke-width="2"/>
<g stroke="{TEXT_DARK}" stroke-width="1.5" stroke-linecap="round" fill="none">
  <path d="M 40 340 q 1.5 -4 3 0"/>
  <path d="M 120 332 q 1.5 -4 3 0"/>
  <path d="M 280 336 q 1.5 -4 3 0"/>
  <path d="M 360 326 q 1.5 -4 3 0"/>
</g>'''

def _bg_dusk():
    return f'''<defs>
  <linearGradient id="duskGrad" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="{SKY_NIGHT}"/>
    <stop offset="1" stop-color="{SKY_DUSK}"/>
  </linearGradient>
</defs>

<g fill="#FFE5A0" opacity="0.7">
  <circle cx="80" cy="80" r="1.6"/>
  <circle cx="200" cy="60" r="1.4"/>
  <circle cx="320" cy="90" r="1.4"/>
</g>
<g transform="translate(80,100)">
  <circle r="20" fill="#FFCBA4"/>
  <circle cx="6" cy="-3" r="16" fill="url(#duskGrad)"/>
</g>
<path d="M 0 360 Q 100 330 200 350 Q 300 370 400 340 L 400 400 L 0 400 Z" fill="{GROUND_HILL}" stroke="{TEXT_DARK}" stroke-width="2"/>
<g stroke="{TEXT_DARK}" stroke-width="1.5" stroke-linecap="round" fill="none">
  <path d="M 50 340 q 1.5 -4 3 0"/>
  <path d="M 200 348 q 1.5 -4 3 0"/>
  <path d="M 340 350 q 1.5 -4 3 0"/>
</g>'''

def _bg_morning_meadow():
    return f'''<defs>
  <linearGradient id="morningGrad" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="#A8D8F0"/>
    <stop offset="0.6" stop-color="#FFE5A0"/>
    <stop offset="1" stop-color="{SKY_AFTERNOON}"/>
  </linearGradient>
</defs>

<g fill="#FFF8E7" opacity="0.9">
  <ellipse cx="60" cy="380" rx="14" ry="6"/>
  <ellipse cx="55" cy="372" rx="6" ry="5"/>
  <ellipse cx="68" cy="370" rx="6" ry="5"/>
  <ellipse cx="320" cy="380" rx="14" ry="6"/>
  <ellipse cx="315" cy="372" rx="6" ry="5"/>
  <ellipse cx="328" cy="370" rx="6" ry="5"/>
</g>
<path d="M 0 340 Q 100 310 200 330 Q 300 350 400 320 L 400 400 L 0 400 Z" fill="{GROUND_HILL}" stroke="{TEXT_DARK}" stroke-width="2"/>
<g stroke="{TEXT_DARK}" stroke-width="1.5" stroke-linecap="round" fill="none">
  <path d="M 40 330 q 1.5 -4 3 0"/>
  <path d="M 80 320 q 1.5 -4 3 0"/>
  <path d="M 180 325 q 1.5 -4 3 0"/>
  <path d="M 240 335 q 1.5 -4 3 0"/>
  <path d="M 320 325 q 1.5 -4 3 0"/>
</g>
'''  # noqa: E501

def _bg_winter_field():
    return f'''<defs>
  <linearGradient id="winterGrad" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="#322850"/>
    <stop offset="1" stop-color="#5A4A8A"/>
  </linearGradient>
</defs>

<g fill="#FFF8E7">
  <circle cx="80" cy="60" r="2.4"/>
  <circle cx="150" cy="40" r="2"/>
  <circle cx="240" cy="70" r="2.2"/>
  <circle cx="320" cy="50" r="1.8"/>
</g>
<g transform="translate(80,90)">
  <circle r="20" fill="#FFE5A0"/>
  <circle cx="6" cy="-3" r="16" fill="url(#winterGrad)"/>
</g>
<g fill="#FFF8E7" stroke="{TEXT_DARK}" stroke-width="1">
  <circle cx="80" cy="200" r="2.5"/>
  <circle cx="150" cy="240" r="2.5"/>
  <circle cx="240" cy="180" r="2.5"/>
  <circle cx="320" cy="220" r="2.5"/>
  <circle cx="60" cy="280" r="2.5"/>
  <circle cx="200" cy="290" r="2.5"/>
</g>
<path d="M 0 340 Q 100 320 200 335 Q 300 350 400 330 L 400 400 L 0 400 Z" fill="#FFF8E7" stroke="{TEXT_DARK}" stroke-width="2"/>
'''

def _bg_cozy_burrow():
    return f'''<defs>
  <radialGradient id="burrowGrad" cx="0.5" cy="0.5" r="0.7">
    <stop offset="0" stop-color="#FFE5A0"/>
    <stop offset="1" stop-color="#A87044"/>
  </radialGradient>
</defs>

<!-- soft floor curve suggesting a burrow wall -->
<path d="M 0 280 Q 200 240 400 280 L 400 400 L 0 400 Z" fill="#8B5E3C" stroke="{TEXT_DARK}" stroke-width="2"/>
<!-- a small lantern -->
<g transform="translate(330,150)">
  <line x1="0" y1="-20" x2="0" y2="0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <ellipse cx="0" cy="20" rx="14" ry="18" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2"/>
  <line x1="0" y1="-20" x2="0" y2="-30" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <circle cx="0" cy="-32" r="3" fill="#E8D78A"/>
</g>
<!-- a small shelf on the wall -->
<line x1="40" y1="180" x2="120" y2="180" stroke="{TEXT_DARK}" stroke-width="3"/>
<circle cx="60" cy="170" r="6" fill="#FFCBA4" stroke="{TEXT_DARK}" stroke-width="1.5"/>
<circle cx="100" cy="170" r="6" fill="#A8D8F0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
'''

def _bg_mushroom_ring():
    return f'''<defs>
  <linearGradient id="mrGrad" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="#5A4A8A"/>
    <stop offset="1" stop-color="#322850"/>
  </linearGradient>
</defs>

<g fill="#FFE5A0" opacity="0.9">
  <circle cx="80" cy="60" r="2"/>
  <circle cx="200" cy="40" r="1.5"/>
  <circle cx="320" cy="70" r="2"/>
  <circle cx="50" cy="100" r="1.5"/>
  <circle cx="350" cy="120" r="1.5"/>
</g>
<!-- mushroom ring -->
<g transform="translate(200,260)">
  <ellipse cx="0" cy="0" rx="160" ry="50" fill="{GROUND_DARK}" opacity="0.6"/>
  <ellipse cx="0" cy="-5" rx="140" ry="40" fill="{GROUND_HILL}" stroke="{TEXT_DARK}" stroke-width="2"/>
</g>
<!-- a few small mushrooms around -->
<g>
  <g transform="translate(80,300)">
    <ellipse cx="0" cy="-8" rx="14" ry="10" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2"/>
    <ellipse cx="-4" cy="-6" rx="2" ry="2" fill="#FFF8E7"/>
    <ellipse cx="4" cy="-8" rx="1.5" ry="1.5" fill="#FFF8E7"/>
    <rect x="-3" y="-2" width="6" height="10" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  </g>
  <g transform="translate(330,310)">
    <ellipse cx="0" cy="-10" rx="18" ry="13" fill="#FFCBA4" stroke="{TEXT_DARK}" stroke-width="2"/>
    <circle cx="-5" cy="-7" r="2" fill="#FFF8E7"/>
    <circle cx="6" cy="-10" r="1.5" fill="#FFF8E7"/>
    <rect x="-3" y="-3" width="6" height="12" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  </g>
</g>
'''

def _bg_willow_tunnel():
    return f'''<defs>
  <linearGradient id="willowGrad" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="#92D4A8"/>
    <stop offset="1" stop-color="#5C7C5A"/>
  </linearGradient>
</defs>

<!-- arching willow branches -->
<g stroke="#3D4F30" stroke-width="3" fill="none">
  <path d="M 60 0 Q 60 100 100 200"/>
  <path d="M 60 0 Q 100 80 140 220"/>
  <path d="M 340 0 Q 340 100 300 200"/>
  <path d="M 340 0 Q 300 80 260 220"/>
</g>
<!-- leaves -->
<g fill="#B8E5C8" stroke="#3D4F30" stroke-width="1">
  <ellipse cx="80" cy="60" rx="14" ry="6" transform="rotate(20 80 60)"/>
  <ellipse cx="110" cy="100" rx="14" ry="6" transform="rotate(-30 110 100)"/>
  <ellipse cx="320" cy="80" rx="14" ry="6" transform="rotate(-20 320 80)"/>
  <ellipse cx="290" cy="120" rx="14" ry="6" transform="rotate(30 290 120)"/>
</g>
<!-- floor -->
<path d="M 0 340 Q 200 320 400 340 L 400 400 L 0 400 Z" fill="{GROUND_DARK}" stroke="{TEXT_DARK}" stroke-width="2"/>
'''

def _bg_riverside():
    return f'''<defs>
  <linearGradient id="riverGrad" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="#A8D8F0"/>
    <stop offset="1" stop-color="#5A9BC4"/>
  </linearGradient>
</defs>
<rect width="400" height="280" fill="url(#riverGrad)"/>
<path d="M 0 280 Q 100 270 200 280 Q 300 290 400 280 L 400 400 L 0 400 Z" fill="{GROUND_HILL}" stroke="{TEXT_DARK}" stroke-width="2"/>
<!-- water ripples -->
<g stroke="#FFF8E7" stroke-width="1.5" stroke-linecap="round" fill="none" opacity="0.7">
  <path d="M 40 200 q 20 -3 40 0"/>
  <path d="M 120 220 q 20 -3 40 0"/>
  <path d="M 220 240 q 20 -3 40 0"/>
  <path d="M 320 200 q 20 -3 40 0"/>
</g>
<!-- a couple of pebbles -->
<ellipse cx="80" cy="320" rx="14" ry="6" fill="#FFCBA4" stroke="{TEXT_DARK}" stroke-width="1.5"/>
<ellipse cx="320" cy="340" rx="12" ry="5" fill="#A8D8F0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
'''

def _bg_garden_gate():
    return f'''<defs>
  <linearGradient id="gardenGrad" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="#FFE5A0"/>
    <stop offset="1" stop-color="#FFCBA4"/>
  </linearGradient>
</defs>

<!-- climbing roses on the sides -->
<g stroke="#5C7C5A" stroke-width="2" fill="none">
  <path d="M 30 80 Q 60 130 30 200 Q 60 270 30 360"/>
  <path d="M 370 80 Q 340 130 370 200 Q 340 270 370 360"/>
</g>
<g>
  <circle cx="35" cy="100" r="8" fill="#F8B7B0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <circle cx="30" cy="160" r="8" fill="#F8B7B0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <circle cx="40" cy="220" r="8" fill="#F8B7B0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <circle cx="35" cy="280" r="8" fill="#F8B7B0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <circle cx="370" cy="120" r="8" fill="#F8B7B0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <circle cx="365" cy="180" r="8" fill="#F8B7B0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <circle cx="370" cy="240" r="8" fill="#F8B7B0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <circle cx="365" cy="300" r="8" fill="#F8B7B0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
</g>
<!-- ground -->
<path d="M 0 340 Q 200 320 400 340 L 400 400 L 0 400 Z" fill="{GROUND_HILL}" stroke="{TEXT_DARK}" stroke-width="2"/>
'''

BACKGROUNDS = {
    "evening":      _bg_starry_night,
    "night":        _bg_starry_night,
    "winter night": _bg_winter_field,
    "dusk":         _bg_dusk,
    "morning":      _bg_morning_meadow,
    "afternoon":    _bg_morning_meadow,
    "twilight":     _bg_dusk,
    "cozy":         _bg_cozy_burrow,   # alias for evening if we ever want
}

# Two named "themes" the generator can also call by name (Pro pinned themes)
BACKGROUND_THEMES = {
    "forest":   _bg_willow_tunnel,
    "ocean":    _bg_riverside,
    "garden":   _bg_garden_gate,
    "winter":   _bg_winter_field,
    "meadow":   _bg_morning_meadow,
    "burrow":   _bg_cozy_burrow,
    "ring":     _bg_mushroom_ring,
    "mushroom": _bg_mushroom_ring,
}

# ============================================================================
# CHARACTERS (5 species × 3 poses)
# Each function returns a <g>...</g> string positioned at the given (x, y).
# Scale ~80-120 px tall.
# ============================================================================

def _char_fox_walking(x, y, scale=1.0, facing_right=True):
    """A small fox with a fluffy tail, walking pose."""
    # Build a single transform attribute. When facing left, we mirror
    # around x=0 (the character's local origin) AND translate first,
    # so the mirror doesn't push the figure off-canvas. Order matters:
    # translate(X,Y) then scale(-1*S, S) — the scale flips the X-axis
    # after positioning, which mirrors the figure in place.
    if facing_right:
        outer_transform = f'translate({x},{y}) scale({scale})'
    else:
        outer_transform = f'translate({x},{y}) scale(-{scale},{scale})'
    return f'''
<g transform="{outer_transform}">
  <!-- tail -->
  <path d="M -50 0 Q -90 -10 -80 -40 Q -70 -30 -50 -20 Z" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2.5" stroke-linejoin="round"/>
  <circle cx="-78" cy="-38" r="6" fill="#FFF8E7" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <!-- body -->
  <ellipse cx="0" cy="0" rx="40" ry="20" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <!-- legs -->
  <rect x="-22" y="15" width="6" height="20" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2" rx="2"/>
  <rect x="14" y="15" width="6" height="20" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2" rx="2"/>
  <!-- head -->
  <circle cx="35" cy="-8" r="22" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <!-- ears -->
  <path d="M 28 -28 L 26 -38 L 35 -28 Z" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2" stroke-linejoin="round"/>
  <path d="M 42 -28 L 44 -38 L 35 -28 Z" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2" stroke-linejoin="round"/>
  <!-- face: muzzle + eyes -->
  <ellipse cx="40" cy="-2" rx="10" ry="7" fill="#FFE5A0"/>
  <circle cx="32" cy="-10" r="2" fill="{TEXT_DARK}"/>
  <circle cx="32" cy="-11" r="0.6" fill="#FFF8E7"/>
  <ellipse cx="46" cy="-3" rx="1.5" ry="1" fill="{TEXT_DARK}"/>
  <!-- cheek blush -->
  <circle cx="38" cy="2" r="3" fill="#F8B7B0" opacity="0.7"/>
</g>'''

def _char_fox_sitting(x, y, scale=1.0, facing_right=True):
    # Build a single transform attribute. When facing left, we mirror
    # around x=0 (the character's local origin) AND translate first,
    # so the mirror doesn't push the figure off-canvas. Order matters:
    # translate(X,Y) then scale(-1*S, S) — the scale flips the X-axis
    # after positioning, which mirrors the figure in place.
    if facing_right:
        outer_transform = f'translate({x},{y}) scale({scale})'
    else:
        outer_transform = f'translate({x},{y}) scale(-{scale},{scale})'
    return f'''
<g transform="{outer_transform}">
  <!-- tail curled around -->
  <path d="M 5 35 Q 40 50 50 25 Q 60 35 45 50 Q 25 55 5 50 Z" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2.5" stroke-linejoin="round"/>
  <!-- body (sitting) -->
  <ellipse cx="0" cy="20" rx="30" ry="22" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <!-- head -->
  <circle cx="0" cy="-12" r="22" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <!-- ears -->
  <path d="M -14 -32 L -16 -42 L -6 -32 Z" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2" stroke-linejoin="round"/>
  <path d="M 6 -32 L 4 -42 L -6 -32 Z" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2" stroke-linejoin="round"/>
  <!-- muzzle -->
  <ellipse cx="0" cy="-6" rx="11" ry="7" fill="#FFE5A0"/>
  <!-- eyes (closed happy) -->
  <path d="M -10 -14 Q -7 -18 -4 -14" stroke="{TEXT_DARK}" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <path d="M 4 -14 Q 7 -18 10 -14" stroke="{TEXT_DARK}" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <!-- nose -->
  <ellipse cx="0" cy="-8" rx="1.8" ry="1.4" fill="{TEXT_DARK}"/>
  <!-- smile -->
  <path d="M -3 -3 Q 0 0 3 -3" stroke="{TEXT_DARK}" stroke-width="2" fill="none" stroke-linecap="round"/>
  <!-- cheek blush -->
  <circle cx="-12" cy="0" r="3" fill="#F8B7B0" opacity="0.7"/>
  <circle cx="12" cy="0" r="3" fill="#F8B7B0" opacity="0.7"/>
</g>'''

def _char_fox_sleeping(x, y, scale=1.0):
    """A small fox curled up sleeping. Symmetric (no flip)."""
    return f'''
<g transform="translate({x},{y}) scale({scale})">
  <!-- tail wrapped over nose -->
  <path d="M -30 -10 Q -60 -20 -55 -50 Q -40 -38 -20 -25 Z" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2.5" stroke-linejoin="round"/>
  <circle cx="-52" cy="-46" r="5" fill="#FFF8E7" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <!-- body (curled) -->
  <ellipse cx="0" cy="0" rx="48" ry="22" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <!-- head resting on body -->
  <circle cx="35" cy="-10" r="20" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <!-- ears -->
  <path d="M 28 -28 L 26 -36 L 34 -28 Z" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2" stroke-linejoin="round"/>
  <path d="M 42 -28 L 44 -36 L 36 -28 Z" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2" stroke-linejoin="round"/>
  <!-- muzzle -->
  <ellipse cx="38" cy="-4" rx="9" ry="6" fill="#FFE5A0"/>
  <!-- closed sleepy eyes -->
  <path d="M 30 -10 Q 32 -8 34 -10" stroke="{TEXT_DARK}" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M 42 -10 Q 44 -8 46 -10" stroke="{TEXT_DARK}" stroke-width="2" fill="none" stroke-linecap="round"/>
  <!-- nose -->
  <ellipse cx="42" cy="-6" rx="1.6" ry="1.2" fill="{TEXT_DARK}"/>
  <!-- smile -->
  <path d="M 39 0 Q 42 2 45 0" stroke="{TEXT_DARK}" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <!-- a small "Zzz" -->
  <g fill="none" stroke="{TEXT_DARK}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M 65 -50 L 72 -50 L 65 -43 L 72 -43"/>
  </g>
</g>'''


def _char_bear_walking(x, y, scale=1.0, facing_right=True):
    # Build a single transform attribute. When facing left, we mirror
    # around x=0 (the character's local origin) AND translate first,
    # so the mirror doesn't push the figure off-canvas. Order matters:
    # translate(X,Y) then scale(-1*S, S) — the scale flips the X-axis
    # after positioning, which mirrors the figure in place.
    if facing_right:
        outer_transform = f'translate({x},{y}) scale({scale})'
    else:
        outer_transform = f'translate({x},{y}) scale(-{scale},{scale})'
    return f'''
<g transform="{outer_transform}">
  <!-- body -->
  <ellipse cx="0" cy="0" rx="40" ry="24" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <!-- belly -->
  <ellipse cx="0" cy="6" rx="22" ry="14" fill="#E0B584" opacity="0.7"/>
  <!-- legs -->
  <rect x="-22" y="18" width="10" height="20" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2" rx="3"/>
  <rect x="12" y="18" width="10" height="20" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2" rx="3"/>
  <!-- arms -->
  <ellipse cx="-30" cy="10" rx="8" ry="14" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <ellipse cx="30" cy="10" rx="8" ry="14" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <!-- head -->
  <ellipse cx="0" cy="-22" rx="26" ry="22" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <!-- ears -->
  <circle cx="-18" cy="-40" r="8" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <circle cx="18" cy="-40" r="8" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <circle cx="-18" cy="-40" r="4" fill="#F8B7B0"/>
  <circle cx="18" cy="-40" r="4" fill="#F8B7B0"/>
  <!-- muzzle -->
  <ellipse cx="0" cy="-14" rx="14" ry="10" fill="#FFE5A0"/>
  <!-- eyes -->
  <circle cx="-9" cy="-22" r="2.4" fill="{TEXT_DARK}"/>
  <circle cx="9" cy="-22" r="2.4" fill="{TEXT_DARK}"/>
  <circle cx="-8.5" cy="-23" r="0.8" fill="#FFF8E7"/>
  <circle cx="9.5" cy="-23" r="0.8" fill="#FFF8E7"/>
  <!-- cheek blush -->
  <circle cx="-16" cy="-10" r="4" fill="#F8B7B0" opacity="0.7"/>
  <circle cx="16" cy="-10" r="4" fill="#F8B7B0" opacity="0.7"/>
  <!-- nose -->
  <ellipse cx="0" cy="-12" rx="3" ry="2" fill="{TEXT_DARK}"/>
  <!-- smile -->
  <path d="M -5 -6 Q 0 -2 5 -6" stroke="{TEXT_DARK}" stroke-width="2" fill="none" stroke-linecap="round"/>
</g>'''


def _char_bear_sitting(x, y, scale=1.0, facing_right=True):
    # Build a single transform attribute. When facing left, we mirror
    # around x=0 (the character's local origin) AND translate first,
    # so the mirror doesn't push the figure off-canvas. Order matters:
    # translate(X,Y) then scale(-1*S, S) — the scale flips the X-axis
    # after positioning, which mirrors the figure in place.
    if facing_right:
        outer_transform = f'translate({x},{y}) scale({scale})'
    else:
        outer_transform = f'translate({x},{y}) scale(-{scale},{scale})'
    return f'''
<g transform="{outer_transform}">
  <!-- body sitting -->
  <ellipse cx="0" cy="14" rx="32" ry="26" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <ellipse cx="0" cy="20" rx="18" ry="12" fill="#E0B584" opacity="0.7"/>
  <!-- arms -->
  <ellipse cx="-26" cy="20" rx="9" ry="16" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <ellipse cx="26" cy="20" rx="9" ry="16" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <!-- feet -->
  <ellipse cx="-12" cy="38" rx="10" ry="6" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <ellipse cx="12" cy="38" rx="10" ry="6" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <!-- head -->
  <ellipse cx="0" cy="-12" rx="26" ry="22" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <circle cx="-18" cy="-30" r="8" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <circle cx="18" cy="-30" r="8" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <circle cx="-18" cy="-30" r="4" fill="#F8B7B0"/>
  <circle cx="18" cy="-30" r="4" fill="#F8B7B0"/>
  <ellipse cx="0" cy="-4" rx="14" ry="10" fill="#FFE5A0"/>
  <!-- eyes (closed happy) -->
  <path d="M -10 -12 Q -7 -16 -4 -12" stroke="{TEXT_DARK}" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <path d="M 4 -12 Q 7 -16 10 -12" stroke="{TEXT_DARK}" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <circle cx="-16" cy="0" r="3.5" fill="#F8B7B0" opacity="0.7"/>
  <circle cx="16" cy="0" r="3.5" fill="#F8B7B0" opacity="0.7"/>
  <ellipse cx="0" cy="-2" rx="3" ry="2" fill="{TEXT_DARK}"/>
  <path d="M -4 4 Q 0 7 4 4" stroke="{TEXT_DARK}" stroke-width="2" fill="none" stroke-linecap="round"/>
</g>'''


def _char_bear_sleeping(x, y, scale=1.0):
    return f'''
<g transform="translate({x},{y}) scale({scale})">
  <ellipse cx="0" cy="0" rx="50" ry="22" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <ellipse cx="0" cy="0" rx="32" ry="14" fill="#E0B584" opacity="0.7"/>
  <ellipse cx="36" cy="-8" rx="20" ry="18" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <circle cx="22" cy="-22" r="7" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <circle cx="50" cy="-22" r="7" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <circle cx="22" cy="-22" r="3" fill="#F8B7B0"/>
  <circle cx="50" cy="-22" r="3" fill="#F8B7B0"/>
  <ellipse cx="40" cy="-2" rx="11" ry="7" fill="#FFE5A0"/>
  <path d="M 32 -10 Q 34 -8 36 -10" stroke="{TEXT_DARK}" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M 44 -10 Q 46 -8 48 -10" stroke="{TEXT_DARK}" stroke-width="2" fill="none" stroke-linecap="round"/>
  <g fill="none" stroke="{TEXT_DARK}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M 65 -50 L 72 -50 L 65 -43 L 72 -43"/>
  </g>
</g>'''


def _char_rabbit_walking(x, y, scale=1.0, facing_right=True):
    # Build a single transform attribute. When facing left, we mirror
    # around x=0 (the character's local origin) AND translate first,
    # so the mirror doesn't push the figure off-canvas. Order matters:
    # translate(X,Y) then scale(-1*S, S) — the scale flips the X-axis
    # after positioning, which mirrors the figure in place.
    if facing_right:
        outer_transform = f'translate({x},{y}) scale({scale})'
    else:
        outer_transform = f'translate({x},{y}) scale(-{scale},{scale})'
    return f'''
<g transform="{outer_transform}">
  <!-- body -->
  <ellipse cx="0" cy="0" rx="32" ry="18" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <!-- legs -->
  <ellipse cx="-18" cy="18" rx="8" ry="14" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2"/>
  <ellipse cx="18" cy="18" rx="8" ry="14" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2"/>
  <!-- head -->
  <circle cx="30" cy="-8" r="18" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <!-- long ears -->
  <ellipse cx="22" cy="-36" rx="5" ry="18" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2"/>
  <ellipse cx="22" cy="-36" rx="2" ry="12" fill="#F8B7B0" opacity="0.7"/>
  <ellipse cx="38" cy="-36" rx="5" ry="18" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2"/>
  <ellipse cx="38" cy="-36" rx="2" ry="12" fill="#F8B7B0" opacity="0.7"/>
  <!-- eyes -->
  <circle cx="28" cy="-12" r="2" fill="{TEXT_DARK}"/>
  <circle cx="28" cy="-13" r="0.7" fill="#FFF8E7"/>
  <circle cx="34" cy="-12" r="2" fill="{TEXT_DARK}"/>
  <circle cx="34" cy="-13" r="0.7" fill="#FFF8E7"/>
  <!-- nose + whiskers -->
  <ellipse cx="31" cy="-3" rx="2" ry="1.5" fill="#F8B7B0"/>
  <!-- cheek blush -->
  <circle cx="26" cy="0" r="2.5" fill="#F8B7B0" opacity="0.7"/>
  <circle cx="36" cy="0" r="2.5" fill="#F8B7B0" opacity="0.7"/>
  <!-- fluffy tail -->
  <circle cx="-30" cy="2" r="8" fill="#FFF8E7" stroke="{TEXT_DARK}" stroke-width="2"/>
</g>'''


def _char_rabbit_sitting(x, y, scale=1.0, facing_right=True):
    # Build a single transform attribute. When facing left, we mirror
    # around x=0 (the character's local origin) AND translate first,
    # so the mirror doesn't push the figure off-canvas. Order matters:
    # translate(X,Y) then scale(-1*S, S) — the scale flips the X-axis
    # after positioning, which mirrors the figure in place.
    if facing_right:
        outer_transform = f'translate({x},{y}) scale({scale})'
    else:
        outer_transform = f'translate({x},{y}) scale(-{scale},{scale})'
    return f'''
<g transform="{outer_transform}">
  <ellipse cx="0" cy="14" rx="26" ry="22" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <ellipse cx="-22" cy="34" rx="8" ry="14" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2"/>
  <ellipse cx="22" cy="34" rx="8" ry="14" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2"/>
  <circle cx="-30" cy="6" r="7" fill="#FFF8E7" stroke="{TEXT_DARK}" stroke-width="2"/>
  <circle cx="0" cy="-6" r="20" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <ellipse cx="-7" cy="-34" rx="5" ry="18" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2"/>
  <ellipse cx="7" cy="-34" rx="5" ry="18" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2"/>
  <ellipse cx="-7" cy="-34" rx="2" ry="12" fill="#F8B7B0" opacity="0.7"/>
  <ellipse cx="7" cy="-34" rx="2" ry="12" fill="#F8B7B0" opacity="0.7"/>
  <circle cx="-6" cy="-8" r="2" fill="{TEXT_DARK}"/>
  <circle cx="6" cy="-8" r="2" fill="{TEXT_DARK}"/>
  <path d="M -3 0 Q 0 3 3 0" stroke="{TEXT_DARK}" stroke-width="2" fill="none" stroke-linecap="round"/>
  <circle cx="-12" cy="-2" r="2.5" fill="#F8B7B0" opacity="0.7"/>
  <circle cx="12" cy="-2" r="2.5" fill="#F8B7B0" opacity="0.7"/>
</g>'''


def _char_hedgehog_walking(x, y, scale=1.0, facing_right=True):
    # Build a single transform attribute. When facing left, we mirror
    # around x=0 (the character's local origin) AND translate first,
    # so the mirror doesn't push the figure off-canvas. Order matters:
    # translate(X,Y) then scale(-1*S, S) — the scale flips the X-axis
    # after positioning, which mirrors the figure in place.
    if facing_right:
        outer_transform = f'translate({x},{y}) scale({scale})'
    else:
        outer_transform = f'translate({x},{y}) scale(-{scale},{scale})'
    return f'''
<g transform="{outer_transform}">
  <!-- spines (back) -->
  <path d="M -28 -8 L -20 -22 L -10 -8 Z M -14 -10 L -6 -24 L 4 -10 Z M 0 -10 L 8 -24 L 18 -10 Z M 14 -8 L 22 -22 L 30 -8 Z" fill="#8B5E3C" stroke="{TEXT_DARK}" stroke-width="1.5" stroke-linejoin="round"/>
  <!-- body -->
  <ellipse cx="0" cy="0" rx="34" ry="16" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <!-- face -->
  <circle cx="34" cy="-2" r="16" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <circle cx="44" cy="-12" r="3" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <circle cx="40" cy="-4" r="1.6" fill="{TEXT_DARK}"/>
  <ellipse cx="46" cy="2" rx="2.5" ry="2" fill="{TEXT_DARK}"/>
  <!-- legs -->
  <rect x="-18" y="14" width="6" height="14" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="1.5" rx="2"/>
  <rect x="12" y="14" width="6" height="14" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="1.5" rx="2"/>
</g>'''


def _char_mouse_sitting(x, y, scale=1.0, facing_right=True):
    # Build a single transform attribute. When facing left, we mirror
    # around x=0 (the character's local origin) AND translate first,
    # so the mirror doesn't push the figure off-canvas. Order matters:
    # translate(X,Y) then scale(-1*S, S) — the scale flips the X-axis
    # after positioning, which mirrors the figure in place.
    if facing_right:
        outer_transform = f'translate({x},{y}) scale({scale})'
    else:
        outer_transform = f'translate({x},{y}) scale(-{scale},{scale})'
    return f'''
<g transform="{outer_transform}">
  <ellipse cx="0" cy="14" rx="22" ry="20" fill="#FFCBA4" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <circle cx="0" cy="-10" r="18" fill="#FFCBA4" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <ellipse cx="-10" cy="-30" rx="5" ry="12" fill="#FFCBA4" stroke="{TEXT_DARK}" stroke-width="2"/>
  <ellipse cx="10" cy="-30" rx="5" ry="12" fill="#FFCBA4" stroke="{TEXT_DARK}" stroke-width="2"/>
  <circle cx="-10" cy="-30" r="3" fill="#F8B7B0"/>
  <circle cx="10" cy="-30" r="3" fill="#F8B7B0"/>
  <circle cx="-6" cy="-10" r="2" fill="{TEXT_DARK}"/>
  <circle cx="6" cy="-10" r="2" fill="{TEXT_DARK}"/>
  <circle cx="-6" cy="-11" r="0.7" fill="#FFF8E7"/>
  <circle cx="6" cy="-11" r="0.7" fill="#FFF8E7"/>
  <ellipse cx="0" cy="-2" rx="2" ry="1.5" fill="#F8B7B0"/>
  <path d="M -3 4 Q 0 7 3 4" stroke="{TEXT_DARK}" stroke-width="2" fill="none" stroke-linecap="round"/>
  <circle cx="-13" cy="0" r="3" fill="#F8B7B0" opacity="0.7"/>
  <circle cx="13" cy="0" r="3" fill="#F8B7B0" opacity="0.7"/>
  <path d="M -28 14 Q -38 30 -42 50" stroke="{TEXT_DARK}" stroke-width="2" fill="none" stroke-linecap="round"/>
</g>'''


def _char_owl_watching(x, y, scale=1.0, facing_right=True):
    """Owl perched on a branch, watching. Symmetric, so facing_right is ignored."""
    return f'''
<g transform="translate({x},{y}) scale({scale})">
  <ellipse cx="0" cy="0" rx="34" ry="36" fill="#A87044" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <ellipse cx="0" cy="6" rx="20" ry="22" fill="#FFE5A0"/>
  <circle cx="-12" cy="-12" r="14" fill="#A87044" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <circle cx="12" cy="-12" r="14" fill="#A87044" stroke="{TEXT_DARK}" stroke-width="2.5"/>
  <circle cx="-12" cy="-12" r="9" fill="#FFF8E7" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <circle cx="12" cy="-12" r="9" fill="#FFF8E7" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <circle cx="-12" cy="-12" r="4" fill="{TEXT_DARK}"/>
  <circle cx="12" cy="-12" r="4" fill="{TEXT_DARK}"/>
  <circle cx="-11" cy="-13" r="1" fill="#FFF8E7"/>
  <circle cx="13" cy="-13" r="1" fill="#FFF8E7"/>
  <path d="M 0 -2 L -5 4 L 5 4 Z" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2" stroke-linejoin="round"/>
  <path d="M -38 32 Q -10 40 38 32" stroke="#5A4030" stroke-width="6" fill="none" stroke-linecap="round"/>
  <line x1="-30" y1="34" x2="-30" y2="44" stroke="#5A4030" stroke-width="2"/>
  <line x1="30" y1="34" x2="30" y2="44" stroke="#5A4030" stroke-width="2"/>
</g>'''


# Map: species → (walking_fn, sitting_fn, sleeping_fn)
CHARACTER_FUNCTIONS = {
    "fox":     (_char_fox_walking, _char_fox_sitting, _char_fox_sleeping),
    "bear":    (_char_bear_walking, _char_bear_sitting, _char_bear_sleeping),
    "rabbit":  (_char_rabbit_walking, _char_rabbit_sitting, None),
    "hedgehog":(_char_hedgehog_walking, None, None),
    "mouse":   (None, _char_mouse_sitting, None),
    "wren":    (None, _char_owl_watching, None),   # treat small bird as owl
    "owl":     (None, _char_owl_watching, None),
    "mole":    (None, _char_mouse_sitting, None),  # similar small body
    "salamander": (None, _char_mouse_sitting, None),
    "lamb":    (_char_rabbit_walking, _char_rabbit_sitting, None),  # similar size
    "newt":    (None, _char_mouse_sitting, None),
    "squirrel": (None, _char_fox_sitting, None),  # small, sitting
    "junco":   (None, _char_owl_watching, None),
    "robin":   (None, _char_owl_watching, None),
    "bluebird": (None, _char_owl_watching, None),
    "firefly": (None, _char_mouse_sitting, None),
    "piglet":  (_char_bear_walking, _char_bear_sitting, _char_bear_sleeping),
    "turtle":  (None, _char_bear_sitting, _char_bear_sleeping),
    "deer":    (_char_fox_walking, _char_fox_sitting, _char_fox_sleeping),
    "elk":     (_char_bear_walking, _char_bear_sitting, _char_bear_sleeping),
    "otter":   (_char_fox_walking, _char_fox_sitting, None),
    "chipmunk": (None, _char_fox_sitting, None),
    "armadillo": (None, _char_hedgehog_walking, None),
    "marmot":  (_char_bear_walking, _char_bear_sitting, _char_bear_sleeping),
}

# ============================================================================
# PROPS (6 small additions to enrich the scene)
# ============================================================================

def _prop_lantern(x, y, scale=1.0):
    return f'''
<g transform="translate({x},{y}) scale({scale})">
  <line x1="0" y1="-20" x2="0" y2="0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <ellipse cx="0" cy="14" rx="14" ry="20" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="2"/>
  <line x1="0" y1="-20" x2="0" y2="-30" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <circle cx="0" cy="-32" r="3" fill="#E8D78A"/>
  <rect x="-2" y="22" width="4" height="6" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="1.5"/>
</g>'''

def _prop_basket(x, y, scale=1.0):
    return f'''
<g transform="translate({x},{y}) scale({scale})">
  <path d="M -20 0 L 20 0 L 16 18 L -16 18 Z" fill="#C89368" stroke="{TEXT_DARK}" stroke-width="2"/>
  <path d="M -20 0 Q 0 -8 20 0" fill="none" stroke="{TEXT_DARK}" stroke-width="2"/>
  <ellipse cx="-10" cy="2" rx="6" ry="4" fill="#FFE5A0"/>
  <ellipse cx="6" cy="2" rx="7" ry="4" fill="#F8B7B0"/>
  <ellipse cx="0" cy="0" rx="5" ry="3" fill="#92D4A8"/>
</g>'''

def _prop_leaf(x, y, scale=1.0):
    return f'''
<g transform="translate({x},{y}) scale({scale}) rotate(30)">
  <path d="M 0 0 Q 10 -12 0 -24 Q -10 -12 0 0 Z" fill="#92D4A8" stroke="{TEXT_DARK}" stroke-width="1.5"/>
  <line x1="0" y1="0" x2="0" y2="-20" stroke="{TEXT_DARK}" stroke-width="1"/>
</g>'''

def _prop_scarf(x, y, scale=1.0):
    return f'''
<g transform="translate({x},{y}) scale({scale})">
  <path d="M -16 -8 Q 0 -2 16 -8 L 18 6 Q 0 12 -18 6 Z" fill="#E88960" stroke="{TEXT_DARK}" stroke-width="2"/>
  <path d="M -14 6 Q -10 30 -4 50" stroke="#E88960" stroke-width="10" fill="none" stroke-linecap="round"/>
  <path d="M -14 6 Q -10 30 -4 50" stroke="{TEXT_DARK}" stroke-width="2" fill="none"/>
  <line x1="-14" y1="14" x2="-10" y2="14" stroke="#FFCBA4" stroke-width="2"/>
  <line x1="-12" y1="26" x2="-8" y2="26" stroke="#FFCBA4" stroke-width="2"/>
</g>'''

def _prop_candle(x, y, scale=1.0):
    return f'''
<g transform="translate({x},{y}) scale({scale})">
  <ellipse cx="0" cy="-22" r="2" fill="#FFE5A0"/>
  <line x1="0" y1="-20" x2="0" y2="-12" stroke="{TEXT_DARK}" stroke-width="1"/>
  <rect x="-6" y="-12" width="12" height="20" fill="#FFF8E7" stroke="{TEXT_DARK}" stroke-width="2"/>
  <ellipse cx="0" cy="8" rx="8" ry="2" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="1.5"/>
</g>'''

def _prop_star(x, y, scale=1.0):
    return f'''
<g transform="translate({x},{y}) scale({scale})">
  <path d="M 0 -10 L 3 -3 L 10 -3 L 4 2 L 6 9 L 0 5 L -6 9 L -4 2 L -10 -3 L -3 -3 Z" fill="#FFE5A0" stroke="{TEXT_DARK}" stroke-width="1.5" stroke-linejoin="round"/>
</g>'''

PROP_FUNCTIONS = [_prop_lantern, _prop_basket, _prop_leaf, _prop_scarf, _prop_candle, _prop_star]


# ============================================================================
# COMPOSER (the public API)
# ============================================================================

def compose_story_image(story: dict, seed: int | None = None,
                          avatar: dict | None = None) -> str:
    """Compose a unique 400×400 hero illustration for a story dict.

    Selection rules:
      - Background by story.scene.time_of_day (with theme overrides if set)
      - Main character by story.scene.species + story.scene.emotion (pose),
        OR by the subscriber's avatar (if `avatar` dict is passed and has
        any of the avatar keys) — Phase 6.
      - Helper character (optional, smaller) by helper_name fallback species
      - 1-2 props randomly chosen (with theme affinities)

    Returns a complete <svg>...</svg> string ready to embed in HTML/email.
    """
    rng = random.Random(seed) if seed is not None else random.Random()
    scene = story.get("scene", {})
    species = (scene.get("species") or "fox").lower()
    emotion = (scene.get("emotion") or "lost").lower()
    time_of_day = (scene.get("time_of_day") or "evening").lower()

    # ---- 1. background ----
    # Check explicit themes first (forest, ocean, etc.)
    chosen_bg_fn = None
    # The image_prompt hint (set by the story generator) gives us a hint
    image_prompt_hint = (story.get("image_prompt") or "").lower()
    for theme_key, fn in BACKGROUND_THEMES.items():
        if theme_key in image_prompt_hint:
            chosen_bg_fn = fn
            break
    if not chosen_bg_fn:
        chosen_bg_fn = BACKGROUNDS.get(time_of_day, _bg_starry_night)
    bg_svg = chosen_bg_fn()

    # ---- 2. main character + pose ----
    # If a custom avatar is provided, we use that INSTEAD of the species-
    # specific character. Helper character still rotates as before.
    has_avatar = bool(avatar and any(k in avatar for k in
                                      ("skin", "hair", "eyes", "outfit", "accessory", "expression")))
    if has_avatar:
        # Import locally to avoid a hard dependency at module load time
        # (avatar_builder is self-contained, this just keeps the import cost
        # off the cold path of unrelated composer calls).
        import avatar_builder as _ab
        main_char = _ab.render_avatar_svg(
            avatar, 130, 280, 1.0, facing_right=True,
        )
    else:
        poses = CHARACTER_FUNCTIONS.get(species, CHARACTER_FUNCTIONS["fox"])
        # Pick a pose based on the emotion
        emotion_to_pose = {
            "scared": poses[1] if len(poses) > 1 and poses[1] else poses[0],  # sitting
            "lonely": poses[1] if len(poses) > 1 and poses[1] else poses[0],  # sitting
            "lost": poses[0] if poses[0] else poses[1],                        # walking
            "unseen": poses[1] if len(poses) > 1 and poses[1] else poses[0],
            "hurting": poses[1] if len(poses) > 1 and poses[1] else poses[0],
            "hungry": poses[0] if poses[0] else poses[1],
            "cold": poses[1] if len(poses) > 1 and poses[1] else poses[0],
            "stubborn": poses[0] if poses[0] else poses[1],
            "impatient": poses[0] if poses[0] else poses[1],
            "quiet": poses[1] if len(poses) > 1 and poses[1] else poses[0],
            "broken": poses[1] if len(poses) > 1 and poses[1] else poses[0],
            "stuck": poses[0] if poses[0] else poses[1],
            "mistaken": poses[0] if poses[0] else poses[1],
            "left-out": poses[0] if poses[0] else poses[1],
            "unkind": poses[1] if len(poses) > 1 and poses[1] else poses[0],
        }
        char_fn = emotion_to_pose.get(emotion, poses[0] or poses[1])
        if char_fn is None:
            char_fn = _char_fox_walking  # ultimate fallback

        # Position the main character on the left third, facing right (toward center)
        main_scale = 1.0
        main_x, main_y = 130, 280
        main_char = char_fn(main_x, main_y, main_scale, facing_right=True)

    # ---- 3. helper character (smaller, opposite side) ----
    helper_species = "rabbit" if species in ("fox", "bear") else "hedgehog"
    if helper_species not in CHARACTER_FUNCTIONS:
        helper_species = "mouse"
    helper_poses = CHARACTER_FUNCTIONS[helper_species]
    helper_pose = helper_poses[1] if len(helper_poses) > 1 and helper_poses[1] else helper_poses[0]
    if helper_pose is None:
        helper_pose = _char_fox_walking
    helper_x, helper_y = 280, 290
    helper_char = helper_pose(helper_x, helper_y, 0.7, facing_right=False)

    # ---- 4. props (1-2, randomly chosen) ----
    props = []
    n_props = rng.choice([1, 1, 2])
    prop_pool = list(PROP_FUNCTIONS)
    rng.shuffle(prop_pool)
    for i in range(n_props):
        fn = prop_pool[i]
        # Place props in the lower half of the canvas, away from the characters
        if i == 0:
            x, y, scale = 220, 350, 0.8
        else:
            x, y, scale = rng.choice([(60, 350, 0.7), (340, 360, 0.7), (200, 380, 0.6)])
        props.append(fn(x, y, scale))

    # ---- 5. assemble the SVG ----
    # We collect ALL <defs> blocks from the parts (bg may define its own
    # gradient) into a single root <defs>, then draw a solid bg-color card
    # underneath, then the body (which doesn't include any <defs> anymore),
    # then a translucent warm overlay to give the whole card a coherent
    # cream glow. The body parts only draw inside the card; the bg <rect>
    # is clipped to the rounded card shape because we removed the leading
    # full-canvas rect from each bg function.
    title = story.get("title", "A bedtime story")
    parts = [bg_svg, main_char, helper_char, *props]
    defs_blocks = []
    body_blocks = []
    for p in parts:
        ip = 0
        while True:
            start = p.find("<defs>", ip)
            if start < 0:
                body_blocks.append(p[ip:])
                break
            body_blocks.append(p[ip:start])
            end = p.find("</defs>", start)
            if end < 0:
                break
            # Extract ONLY the content between <defs> and </defs> — the wrapper
            # tags themselves must NOT be concatenated inside the OUTER <defs>
            # block, or we'll produce nested <defs><defs>...</defs></defs>
            # which the browser rejects.
            defs_blocks.append(p[start + len("<defs>"):end].strip())
            ip = end + len("</defs>")
    body = "".join(body_blocks)
    # Build via chr(10) joining to avoid escape confusion. The title contains
    # an apostrophe so we escape it as &#39; for safety in attribute values.
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;")
    svg = chr(10).join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" role="img" aria-label="A scene from today&#39;s story: ' + safe_title + '">',
        '  <title>' + safe_title + '</title>',
        '  <defs>',
        '    <linearGradient id="cardGrad" x1="0" x2="0" y1="0" y2="1">',
        '      <stop offset="0" stop-color="#FFF8E7"/>',
        '      <stop offset="1" stop-color="#FFE5A0"/>',
        '    </linearGradient>',
        "".join(defs_blocks),
        '  </defs>',
        '  <rect width="400" height="400" rx="32" fill="#A87044"/>',
        body,
        '  <rect width="400" height="400" rx="32" fill="url(#cardGrad)" opacity="0.18"/>',
        '</svg>',
        '',
    ])

    return svg


# ============================================================================
# Standalone smoke test
# ============================================================================
if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/root/pocketplot")
    from story_gen import generate_new_story

    print(f"Backgrounds: {len(BACKGROUNDS)} main + {len(BACKGROUND_THEMES)} themes")
    print(f"Characters:   {len(CHARACTER_FUNCTIONS)} species")
    print(f"Props:        {len(PROP_FUNCTIONS)}")
    print()
    for i in range(3):
        s = generate_new_story(child_name="Wren", child_age=5, seed=i * 100)
        svg = compose_story_image(s, seed=i * 100)
        out_path = f"/tmp/test_hero_{i}.svg"
        with open(out_path, "w") as f:
            f.write(svg)
        print(f"  story {i+1}: {s['title']!r} ({s['scene']['species']}/{s['scene']['emotion']}) -> {out_path} ({len(svg)} bytes)")


# ============================================================================
# Phase 11 (v11) — Composer v2.0
# Three new backgrounds (castle, cyberpunk, magical library) and three new
# species (robot, dragon, knight) — built using the same primitive style as
# the original composer, so existing callers don't need to know about them.
# Plus a `compose_scene_svg()` helper that builds a full scene (background +
# characters + props) from a `story` dict — used by the StoryWorld pages.
# ============================================================================

def _bg_castle():
    """A moonlit castle silhouette: keep walls + towers, a tall gate, a thin
    lit window. Atmospheric for the fantasy / mystery genre."""
    return """<g>
      <defs>
        <linearGradient id="sky_castle" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1a1f3a"/>
          <stop offset="60%" stop-color="#3a3a5e"/>
          <stop offset="100%" stop-color="#0a1428"/>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#sky_castle)"/>
      <circle cx="320" cy="70" r="26" fill="#e8d8a8"/>
      <circle cx="320" cy="70" r="36" fill="none" stroke="#d4c8a0" stroke-width="1.5" opacity=".55"/>
      <g fill="#0a1428">
        <rect x="60" y="170" width="280" height="90"/>
        <rect x="80" y="130" width="40" height="130"/>
        <rect x="280" y="120" width="40" height="140"/>
        <rect x="180" y="110" width="40" height="150"/>
      </g>
      <g fill="#e8d8a8">
        <rect x="194" y="140" width="12" height="20"/>
        <rect x="92" y="160" width="16" height="22"/>
        <rect x="292" y="150" width="16" height="22"/>
      </g>
      <polygon points="180,110 200,90 220,110" fill="#0a1428"/>
      <polygon points="80,130 100,110 120,130" fill="#0a1428"/>
      <polygon points="280,120 300,100 320,120" fill="#0a1428"/>
      <g stroke="#3a3a5e" stroke-width=".8" opacity=".4">
        <line x1="0" y1="200" x2="400" y2="200"/>
        <line x1="0" y1="220" x2="400" y2="220"/>
        <line x1="0" y1="240" x2="400" y2="240"/>
      </g>
    </g>"""


def _bg_cyberpunk():
    """A neon-lit alley: deep purple, magenta/cyan glow strips, a distant
    skyline of silhouetted buildings. Atmospheric for the scifi / noir genre."""
    return """<g>
      <defs>
        <linearGradient id="sky_cyberpunk" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1a0830"/>
          <stop offset="60%" stop-color="#3a1850"/>
          <stop offset="100%" stop-color="#080820"/>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#sky_cyberpunk)"/>
      <g fill="#0a0420">
        <rect x="20" y="140" width="40" height="120"/>
        <rect x="80" y="100" width="60" height="160"/>
        <rect x="160" y="160" width="30" height="100"/>
        <rect x="210" y="80" width="80" height="180"/>
        <rect x="310" y="130" width="50" height="130"/>
      </g>
      <g fill="#ff3a8a" opacity=".85">
        <rect x="25" y="170" width="6" height="4"/>
        <rect x="85" y="130" width="6" height="4"/>
        <rect x="170" y="190" width="4" height="3"/>
        <rect x="220" y="110" width="6" height="4"/>
        <rect x="240" y="140" width="6" height="4"/>
        <rect x="320" y="160" width="6" height="4"/>
      </g>
      <g fill="#44f0ff" opacity=".85">
        <rect x="50" y="190" width="5" height="3"/>
        <rect x="105" y="150" width="5" height="3"/>
        <rect x="200" y="120" width="5" height="3"/>
        <rect x="270" y="170" width="5" height="3"/>
        <rect x="335" y="200" width="5" height="3"/>
      </g>
      <rect x="0" y="250" width="400" height="10" fill="#2a0a40" opacity=".7"/>
    </g>"""


def _bg_magical_library():
    """Tall bookshelves lit by warm candle-glow. Atmospheric for fantasy +
    mystery + cozy horror."""
    return """<g>
      <defs>
        <radialGradient id="lib_glow" cx=".5" cy=".4" r=".8">
          <stop offset="0%" stop-color="#e8d8a8" stop-opacity=".4"/>
          <stop offset="100%" stop-color="#1a1410" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="#1a1410"/>
      <rect x="0" y="0" width="400" height="260" fill="url(#lib_glow)"/>
      <g fill="#2a2018">
        <rect x="20" y="30" width="80" height="220"/>
        <rect x="120" y="30" width="80" height="220"/>
        <rect x="220" y="30" width="80" height="220"/>
        <rect x="320" y="30" width="60" height="220"/>
      </g>
      <g stroke="#3a2818" stroke-width="1">
        <line x1="20" y1="80" x2="100" y2="80"/>
        <line x1="20" y1="130" x2="100" y2="130"/>
        <line x1="20" y1="180" x2="100" y2="180"/>
        <line x1="20" y1="230" x2="100" y2="230"/>
        <line x1="120" y1="80" x2="200" y2="80"/>
        <line x1="120" y1="130" x2="200" y2="130"/>
        <line x1="120" y1="180" x2="200" y2="180"/>
        <line x1="120" y1="230" x2="200" y2="230"/>
        <line x1="220" y1="80" x2="300" y2="80"/>
        <line x1="220" y1="130" x2="300" y2="130"/>
        <line x1="220" y1="180" x2="300" y2="180"/>
        <line x1="220" y1="230" x2="300" y2="230"/>
      </g>
      <g fill="#8a6444">
        <rect x="28" y="50" width="14" height="28"/>
        <rect x="48" y="55" width="10" height="23"/>
        <rect x="62" y="48" width="16" height="30"/>
        <rect x="128" y="55" width="12" height="22"/>
        <rect x="146" y="48" width="14" height="30"/>
        <rect x="164" y="55" width="12" height="23"/>
        <rect x="228" y="50" width="12" height="28"/>
        <rect x="244" y="55" width="14" height="23"/>
        <rect x="262" y="48" width="12" height="30"/>
        <rect x="278" y="55" width="14" height="22"/>
      </g>
      <ellipse cx="200" cy="245" rx="35" ry="6" fill="#e8c870" opacity=".6"/>
    </g>"""


def _char_robot(x, y, scale=1.0, facing_right=True):
    """A friendly robot with antenna, glowing eye, jointed arms. Used for
    scifi / cyberpunk scenes."""
    flip = "" if facing_right else ' transform="scale(-1,1) translate(-160,0)"'
    return f"""<g transform="translate({x},{y}) scale({scale})"{flip}>
      <rect x="-22" y="-30" width="44" height="44" rx="8" fill="#7a8aa8" stroke="#3a3a5e" stroke-width="2"/>
      <rect x="-18" y="-26" width="36" height="20" rx="4" fill="#1a1f3a"/>
      <circle cx="0" cy="-16" r="6" fill="#44f0ff"/>
      <line x1="0" y1="-44" x2="0" y2="-58" stroke="#3a3a5e" stroke-width="2"/>
      <circle cx="0" cy="-62" r="4" fill="#ff3a8a"/>
      <rect x="-26" y="14" width="52" height="32" rx="6" fill="#5a6a8a" stroke="#3a3a5e" stroke-width="2"/>
      <rect x="-22" y="20" width="14" height="8" rx="2" fill="#44f0ff" opacity=".7"/>
      <rect x="-4" y="20" width="14" height="8" rx="2" fill="#ff3a8a" opacity=".7"/>
      <rect x="-30" y="2" width="8" height="20" rx="3" fill="#5a6a8a" stroke="#3a3a5e" stroke-width="1.5"/>
      <rect x="22" y="2" width="8" height="20" rx="3" fill="#5a6a8a" stroke="#3a3a5e" stroke-width="1.5"/>
      <rect x="-12" y="46" width="8" height="14" fill="#5a6a8a" stroke="#3a3a5e" stroke-width="1.5"/>
      <rect x="4" y="46" width="8" height="14" fill="#5a6a8a" stroke="#3a3a5e" stroke-width="1.5"/>
    </g>"""


def _char_dragon(x, y, scale=1.0, facing_right=True):
    """A small dragon: round body, two wings, a curling tail, a flame-flick
    breath. Atmospheric for fantasy / adventure."""
    flip = "" if facing_right else ' transform="scale(-1,1) translate(-160,0)"'
    return f"""<g transform="translate({x},{y}) scale({scale})"{flip}>
      <ellipse cx="60" cy="-6" rx="40" ry="22" fill="#7a3a3a" stroke="#3a1a1a" stroke-width="2"/>
      <path d="M 80 -10 q 14 -8 24 -2 q -4 8 -22 8 z" fill="#7a3a3a" stroke="#3a1a1a" stroke-width="2"/>
      <circle cx="100" cy="-12" r="6" fill="#e8c870"/>
      <ellipse cx="104" cy="-12" rx="5" ry="4" fill="#fff8d8"/>
      <circle cx="105" cy="-13" r="1.5" fill="#1a1a1a"/>
      <path d="M 30 -10 q -16 -10 -32 -2 q 8 12 28 14 z" fill="#7a3a3a" stroke="#3a1a1a" stroke-width="2"/>
      <path d="M 50 -22 q 8 -14 22 -16 q 6 12 -10 22 z" fill="#a85040" stroke="#3a1a1a" stroke-width="1.5"/>
      <path d="M 70 -22 q 8 -14 22 -16 q 6 12 -10 22 z" fill="#a85040" stroke="#3a1a1a" stroke-width="1.5"/>
      <path d="M 20 8 q -12 14 -2 24 q 14 -2 18 -14 z" fill="#7a3a3a" stroke="#3a1a1a" stroke-width="2"/>
      <path d="M 18 -2 q -16 4 -20 16 q 4 6 14 4 q 6 -10 6 -20 z" fill="#a85040" stroke="#3a1a1a" stroke-width="1.5"/>
      <line x1="50" y1="16" x2="48" y2="32" stroke="#3a1a1a" stroke-width="2"/>
      <line x1="65" y1="16" x2="68" y2="32" stroke="#3a1a1a" stroke-width="2"/>
      <circle cx="48" cy="34" r="3" fill="#3a1a1a"/>
      <circle cx="68" cy="34" r="3" fill="#3a1a1a"/>
      <path d="M 100 -14 q 6 -2 10 -6 q -2 6 -8 8 z" fill="#e8c870" opacity=".85"/>
    </g>"""


def _char_knight(x, y, scale=1.0, facing_right=True):
    """A small armored knight: helm with visor, cape, sword. Atmospheric
    for fantasy / adventure."""
    flip = "" if facing_right else ' transform="scale(-1,1) translate(-160,0)"'
    return f"""<g transform="translate({x},{y}) scale({scale})"{flip}>
      <rect x="-18" y="-46" width="36" height="28" rx="6" fill="#9aa6b8" stroke="#3a3a5e" stroke-width="2"/>
      <rect x="-14" y="-42" width="28" height="6" fill="#1a1f3a"/>
      <rect x="-3" y="-44" width="6" height="14" fill="#1a1f3a"/>
      <line x1="0" y1="-46" x2="0" y2="-58" stroke="#3a3a5e" stroke-width="1.5"/>
      <rect x="-2" y="-62" width="4" height="8" fill="#c44a3a"/>
      <path d="M -18 -18 q -22 -2 -28 8 q 6 4 16 4 q 12 -2 14 -10 z" fill="#c44a3a" stroke="#3a1a1a" stroke-width="1.5"/>
      <rect x="-22" y="-18" width="44" height="40" rx="4" fill="#9aa6b8" stroke="#3a3a5e" stroke-width="2"/>
      <line x1="-22" y1="-8" x2="22" y2="-8" stroke="#3a3a5e" stroke-width="1"/>
      <line x1="0" y1="-18" x2="0" y2="22" stroke="#3a3a5e" stroke-width="1"/>
      <circle cx="-12" cy="-2" r="3" fill="#e8c870"/>
      <rect x="-26" y="-12" width="6" height="32" rx="2" fill="#9aa6b8" stroke="#3a3a5e" stroke-width="1.5"/>
      <rect x="20" y="-12" width="6" height="32" rx="2" fill="#9aa6b8" stroke="#3a3a5e" stroke-width="1.5"/>
      <rect x="-12" y="22" width="9" height="22" fill="#9aa6b8" stroke="#3a3a5e" stroke-width="1.5"/>
      <rect x="3" y="22" width="9" height="22" fill="#9aa6b8" stroke="#3a3a5e" stroke-width="1.5"/>
      <line x1="30" y1="-26" x2="36" y2="6" stroke="#9aa6b8" stroke-width="3"/>
      <line x1="30" y1="-26" x2="28" y2="-30" stroke="#9aa6b8" stroke-width="3"/>
      <polygon points="34,4 38,4 36,10" fill="#e8e0c0" stroke="#3a3a5e" stroke-width="0.5"/>
    </g>"""


# ---- v2.0 helpers used by story_world.py ----

# New backgrounds registered into the BACKGROUNDS lookup. Existing
# callers that pass a known scene.setting still find their original
# background; new scenes tagged with these keywords route here.
BACKGROUNDS_V2 = {
    "castle":            _bg_castle,
    "cyberpunk":         _bg_cyberpunk,
    "magical_library":   _bg_magical_library,
    "lantern_quarter":   _bg_magical_library,   # alias
    "docks":             _bg_cyberpunk,         # alias
    "orbital_station":   _bg_cyberpunk,         # alias
    "satellite_array":   _bg_cyberpunk,         # alias
    "shipwreck_library": _bg_magical_library,   # alias
}


def compose_scene_svg(story: dict, seed: int = None) -> str:
    """High-level helper used by the StoryWorld UI: takes a story dict
    (with `scene` keys: time_of_day, species, emotion, setting) and
    returns a full 400×400 scene SVG.

    Differs from `compose_story_image()` only in that it consults the
    v2.0 background catalog first (for cyberpunk / castle / library
    scenes) and falls back to the original BACKGROUNDS dict otherwise.
    """
    # First, see if this scene matches a v2 background.
    scene = story.get("scene") or {}
    setting = (scene.get("setting") or "").lower()
    bg_fn = None
    for keyword, fn in BACKGROUNDS_V2.items():
        if keyword in setting:
            bg_fn = fn
            break
    if bg_fn is None:
        # Delegate to the v1 composer for everything else.
        return compose_story_image(story, seed=seed)
    # Build the v2 scene inline.
    import random as _r
    rng = _r.Random(seed if seed is not None else 0)
    bg = bg_fn()
    # Pick species-specific character.
    species = (scene.get("species") or "fox").lower()
    char_pool = {
        "robot":  _char_robot,
        "dragon": _char_dragon,
        "knight": _char_knight,
        # Fallbacks for unknown species — use the original cast.
        "fox":      None,
        "bear":     None,
        "rabbit":   None,
        "hedgehog": None,
        "mouse":    None,
        "owl":      None,
    }
    char_fn = char_pool.get(species)
    if char_fn is None:
        # Unknown species or v1 species — use the original composer for
        # the main character.
        return compose_story_image(story, seed=seed)
    main = char_fn(180, 280, 1.0, facing_right=True)
    # A small helper character (opposite-facing) for v2 species.
    helper_map = {
        "robot":  (_char_dragon, False),
        "dragon": (_char_knight, False),
        "knight": (_char_robot, False),
    }
    helper_fn, helper_facing = helper_map.get(species, (_char_robot, False))
    helper = helper_fn(290, 280, 0.85, facing_right=helper_facing)
    return f'''<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
  {bg}
  {main}
  {helper}
</svg>'''


# Alias to keep story_world.py readable.
compose_v2_scene_svg = compose_scene_svg

# ============================================================================
# Phase 14 — Layered scene composer (v14)
# ============================================================================
# Each scene is composed of three explicit layers: BACKGROUND (sky + far),
# MIDGROUND (architecture + landscape), FOREGROUND (characters + props + light).
# The "depth" comes from gradient shifts and overlapping silhouettes.

def _layered_fantasy():
    """Mountain keep at dawn. A dragon silhouette on a parapet, a lit
    arrow-slit window. Three depth layers."""
    return """<g>
      <defs>
        <linearGradient id="lf_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#2a1830"/>
          <stop offset="60%" stop-color="#7a3a3a"/>
          <stop offset="100%" stop-color="#e8a868"/>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#lf_bg)"/>
      <g fill="#1a1428" opacity="0.7">
        <path d="M 0 200 L 60 170 L 130 195 L 200 165 L 270 190 L 340 168 L 400 195 L 400 240 L 0 240 Z"/>
      </g>
      <g fill="#0a0a14">
        <path d="M 140 240 L 140 120 Q 140 90 200 90 Q 260 90 260 120 L 260 240 Z"/>
        <rect x="130" y="100" width="140" height="20"/>
      </g>
      <g fill="#0a0a14" stroke="#e6c879" stroke-width="1.2">
        <rect x="130" y="90" width="14" height="14"/>
        <rect x="148" y="90" width="14" height="14"/>
        <rect x="166" y="90" width="14" height="14"/>
        <rect x="184" y="90" width="14" height="14"/>
        <rect x="202" y="90" width="14" height="14"/>
        <rect x="220" y="90" width="14" height="14"/>
        <rect x="238" y="90" width="14" height="14"/>
        <rect x="256" y="90" width="14" height="14"/>
      </g>
      <rect x="194" y="142" width="12" height="26" fill="#e6c879"/>
      <rect x="194" y="142" width="12" height="26" fill="#fff3c4" opacity="0.5"/>
      <line x1="220" y1="120" x2="240" y2="180" stroke="#c44a3a" stroke-width="2"/>
      <path d="M 222 122 L 240 145 L 222 168 Z" fill="#c44a3a" stroke="#e6c879" stroke-width="0.5"/>
      <g transform="translate(160,110)">
        <ellipse cx="20" cy="6" rx="20" ry="10" fill="#0a0a14"/>
        <path d="M 32 6 q 12 -4 18 0 q -4 8 -18 8 z" fill="#0a0a14"/>
        <path d="M 0 6 q -8 -6 -16 0 q 4 10 14 8 z" fill="#0a0a14"/>
        <path d="M 8 -2 q 6 -10 14 -10 q 4 8 -8 14 z" fill="#1a1428"/>
        <path d="M 24 -2 q 6 -10 14 -10 q 4 8 -8 14 z" fill="#1a1428"/>
        <circle cx="46" cy="2" r="2" fill="#e6c879"/>
        <path d="M 50 4 q 8 0 8 -6 q -4 4 -8 6 z" fill="#e6c879" opacity="0.85"/>
      </g>
      <path d="M 0 260 L 400 260 L 400 320 L 0 320 Z" fill="#1a2c14"/>
      <path d="M 200 260 L 130 320 L 270 320 Z" fill="#3a3a5e" opacity="0.7"/>
    </g>"""


def _layered_scifi():
    """Cyberpunk alley. Foreground rain streaks, midground neon shopfront,
    background magenta sky."""
    return """<g>
      <defs>
        <linearGradient id="ls_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1a0830"/>
          <stop offset="60%" stop-color="#3a1850"/>
          <stop offset="100%" stop-color="#5a2a4a"/>
        </linearGradient>
        <radialGradient id="ls_glow" cx="0.3" cy="0.7" r="0.5">
          <stop offset="0%" stop-color="#ff3a8a" stop-opacity="0.4"/>
          <stop offset="100%" stop-color="#ff3a8a" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#ls_bg)"/>
      <rect x="0" y="100" width="400" height="160" fill="url(#ls_glow)"/>
      <g fill="#0a0420">
        <rect x="10" y="120" width="40" height="140"/>
        <rect x="60" y="80" width="60" height="180"/>
        <rect x="130" y="140" width="40" height="120"/>
        <rect x="180" y="100" width="50" height="160"/>
        <rect x="240" y="60" width="80" height="200"/>
        <rect x="330" y="110" width="60" height="150"/>
      </g>
      <rect x="50" y="140" width="120" height="120" fill="#15243f"/>
      <rect x="55" y="155" width="110" height="22" fill="#ff3a8a"/>
      <text x="110" y="172" font-family="monospace" font-size="11" font-weight="700" fill="#fff3c4" text-anchor="middle">HOSHI-NO</text>
      <g fill="#44f0ff" opacity="0.8">
        <rect x="62" y="186" width="8" height="8"/>
        <rect x="80" y="186" width="8" height="8"/>
        <rect x="98" y="186" width="8" height="8"/>
        <rect x="62" y="202" width="8" height="8"/>
        <rect x="80" y="202" width="8" height="8"/>
        <rect x="98" y="202" width="8" height="8"/>
        <rect x="62" y="218" width="8" height="8"/>
        <rect x="80" y="218" width="8" height="8"/>
        <rect x="98" y="218" width="8" height="8"/>
      </g>
      <rect x="180" y="170" width="80" height="90" fill="#0a1428" stroke="#44f0ff" stroke-width="1"/>
      <rect x="185" y="180" width="70" height="20" fill="#44f0ff" opacity="0.7"/>
      <text x="220" y="195" font-family="monospace" font-size="9" fill="#0a1428" font-weight="700" text-anchor="middle">ARCADE</text>
      <g stroke="#a8f0ff" stroke-width="0.6" opacity="0.4">
        <line x1="40"  y1="40"  x2="32"  y2="80"/>
        <line x1="80"  y1="20"  x2="72"  y2="60"/>
        <line x1="120" y1="50"  x2="112" y2="90"/>
        <line x1="170" y1="30"  x2="162" y2="70"/>
        <line x1="220" y1="60"  x2="212" y2="100"/>
        <line x1="270" y1="20"  x2="262" y2="60"/>
        <line x1="320" y1="50"  x2="312" y2="90"/>
        <line x1="370" y1="30"  x2="362" y2="70"/>
      </g>
      <rect x="0" y="260" width="400" height="2" fill="#5a2a4a" opacity="0.5"/>
      <rect x="0" y="260" width="400" height="60" fill="#0a1428"/>
      <g opacity="0.4">
        <rect x="50" y="280" width="120" height="20" fill="#ff3a8a"/>
        <rect x="180" y="290" width="80" height="14" fill="#44f0ff"/>
      </g>
    </g>"""


def _layered_noir():
    """Rainy alley. Lamp glow, brick wall, fog curl at the base."""
    return """<g>
      <defs>
        <linearGradient id="ln_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#0a0420"/>
          <stop offset="60%" stop-color="#1a1428"/>
          <stop offset="100%" stop-color="#3a1a2a"/>
        </linearGradient>
        <radialGradient id="ln_lamp" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stop-color="#f3a4b8" stop-opacity="0.6"/>
          <stop offset="60%" stop-color="#f3a4b8" stop-opacity="0.18"/>
          <stop offset="100%" stop-color="#f3a4b8" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#ln_bg)"/>
      <g fill="#0a0a14" opacity="0.85">
        <rect x="0" y="100" width="80" height="160"/>
        <rect x="90" y="80" width="100" height="180"/>
        <rect x="200" y="120" width="80" height="140"/>
        <rect x="290" y="100" width="110" height="160"/>
      </g>
      <g fill="#f3a4b8" opacity="0.55">
        <rect x="20" y="140" width="6" height="6"/>
        <rect x="40" y="170" width="6" height="6"/>
        <rect x="120" y="120" width="6" height="6"/>
        <rect x="150" y="160" width="6" height="6"/>
        <rect x="220" y="150" width="6" height="6"/>
        <rect x="320" y="130" width="6" height="6"/>
        <rect x="350" y="160" width="6" height="6"/>
      </g>
      <rect x="80" y="120" width="40" height="140" fill="#3a1a1a" stroke="#1a0a0a" stroke-width="1"/>
      <rect x="290" y="120" width="40" height="140" fill="#3a1a1a" stroke="#1a0a0a" stroke-width="1"/>
      <circle cx="200" cy="170" r="80" fill="url(#ln_lamp)"/>
      <line x1="200" y1="50" x2="200" y2="170" stroke="#3a1a2a" stroke-width="3"/>
      <circle cx="200" cy="40" r="8" fill="#f3a4b8"/>
      <circle cx="200" cy="40" r="14" fill="#f3a4b8" opacity="0.3"/>
      <rect x="170" y="180" width="20" height="80" fill="#0a0a14" stroke="#f3a4b8" stroke-width="1"/>
      <rect x="173" y="220" width="14" height="40" fill="#1a0a14"/>
      <g transform="translate(220,260)">
        <ellipse cx="0" cy="-2" rx="20" ry="2" fill="#000" opacity="0.5"/>
        <path d="M -8 -2 L -10 -50 L 10 -50 L 8 -2 Z" fill="#000"/>
        <circle cx="0" cy="-58" r="6" fill="#000"/>
        <ellipse cx="-12" cy="-30" rx="6" ry="3" fill="#000" transform="rotate(-20 -12 -30)"/>
      </g>
      <rect x="0" y="260" width="400" height="2" fill="#f3a4b8" opacity="0.3"/>
      <ellipse cx="200" cy="280" rx="40" ry="3" fill="#f3a4b8" opacity="0.3"/>
      <g stroke="#f3a4b8" stroke-width="0.5" opacity="0.4">
        <line x1="60"  y1="40"  x2="55"  y2="80"/>
        <line x1="100" y1="20"  x2="95"  y2="60"/>
        <line x1="140" y1="50"  x2="135" y2="90"/>
        <line x1="180" y1="30"  x2="175" y2="70"/>
        <line x1="230" y1="60"  x2="225" y2="100"/>
        <line x1="280" y1="20"  x2="275" y2="60"/>
        <line x1="320" y1="50"  x2="315" y2="90"/>
        <line x1="370" y1="30"  x2="365" y2="70"/>
      </g>
    </g>"""


def _layered_romance():
    """Golden-hour rooftop. Two silhouettes looking at a sunset."""
    return """<g>
      <defs>
        <linearGradient id="lr_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#5a3a8a"/>
          <stop offset="40%" stop-color="#e87a4a"/>
          <stop offset="80%" stop-color="#f8c870"/>
          <stop offset="100%" stop-color="#f8a850"/>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#lr_bg)"/>
      <circle cx="200" cy="220" r="42" fill="#fff3c4"/>
      <circle cx="200" cy="220" r="56" fill="#fff3c4" opacity="0.4"/>
      <g fill="#3a1a3a" opacity="0.85">
        <rect x="0"   y="180" width="50" height="40"/>
        <rect x="55"  y="170" width="60" height="50"/>
        <rect x="120" y="190" width="40" height="30"/>
        <rect x="240" y="190" width="40" height="30"/>
        <rect x="285" y="170" width="60" height="50"/>
        <rect x="350" y="180" width="50" height="40"/>
      </g>
      <g fill="#fff3c4" opacity="0.85">
        <rect x="60"  y="180" width="4" height="6"/>
        <rect x="80"  y="200" width="4" height="6"/>
        <rect x="130" y="200" width="4" height="6"/>
        <rect x="260" y="200" width="4" height="6"/>
        <rect x="310" y="185" width="4" height="6"/>
        <rect x="330" y="205" width="4" height="6"/>
      </g>
      <rect x="0" y="240" width="400" height="3" fill="#1a0a14"/>
      <g stroke="#1a0a14" stroke-width="2">
        <line x1="20"  y1="243" x2="20"  y2="260"/>
        <line x1="60"  y1="243" x2="60"  y2="260"/>
        <line x1="100" y1="243" x2="100" y2="260"/>
        <line x1="140" y1="243" x2="140" y2="260"/>
        <line x1="180" y1="243" x2="180" y2="260"/>
        <line x1="220" y1="243" x2="220" y2="260"/>
        <line x1="260" y1="243" x2="260" y2="260"/>
        <line x1="300" y1="243" x2="300" y2="260"/>
        <line x1="340" y1="243" x2="340" y2="260"/>
        <line x1="380" y1="243" x2="380" y2="260"/>
      </g>
      <line x1="0" y1="240" x2="400" y2="240" stroke="#1a0a14" stroke-width="2"/>
      <g transform="translate(170,238)">
        <ellipse cx="0" cy="2" rx="6" ry="1" fill="#000" opacity="0.35"/>
        <path d="M -5 0 L -6 -22 L 6 -22 L 5 0 Z" fill="#1a0a14"/>
        <circle cx="0" cy="-26" r="5" fill="#1a0a14"/>
      </g>
      <g transform="translate(195,238)">
        <ellipse cx="0" cy="2" rx="6" ry="1" fill="#000" opacity="0.35"/>
        <path d="M -5 0 L -6 -22 L 6 -22 L 5 0 Z" fill="#1a0a14"/>
        <circle cx="0" cy="-26" r="5" fill="#1a0a14"/>
      </g>
    </g>"""


def _layered_adventure():
    """Ship deck at sunset. Rope, mast, ocean, distant islands."""
    return """<g>
      <defs>
        <linearGradient id="lad_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#3a3a6a"/>
          <stop offset="50%" stop-color="#e87a4a"/>
          <stop offset="100%" stop-color="#f8c870"/>
        </linearGradient>
        <linearGradient id="lad_ocean" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#5a4a8a"/>
          <stop offset="100%" stop-color="#1a1a3a"/>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="400" height="200" fill="url(#lad_bg)"/>
      <circle cx="320" cy="180" r="38" fill="#fff3c4"/>
      <circle cx="320" cy="180" r="50" fill="#fff3c4" opacity="0.3"/>
      <g fill="#1a0a2a" opacity="0.75">
        <path d="M 0 180 Q 60 150 130 180 Q 200 200 280 170 Q 340 150 400 180 L 400 220 L 0 220 Z"/>
      </g>
      <rect x="0" y="200" width="400" height="120" fill="url(#lad_ocean)"/>
      <g fill="#fff3c4" opacity="0.5">
        <path d="M 280 200 L 360 200 L 360 204 L 280 204 Z"/>
        <path d="M 240 220 L 340 220 L 340 223 L 240 223 Z"/>
        <path d="M 290 240 L 380 240 L 380 243 L 290 243 Z"/>
        <path d="M 220 260 L 320 260 L 320 263 L 220 263 Z"/>
      </g>
      <line x1="120" y1="20" x2="120" y2="260" stroke="#1a0a14" stroke-width="3"/>
      <line x1="120" y1="60" x2="60"  y2="240" stroke="#1a0a14" stroke-width="1.5"/>
      <line x1="120" y1="60" x2="180" y2="240" stroke="#1a0a14" stroke-width="1.5"/>
      <path d="M 120 40 L 200 200 L 120 200 Z" fill="#fff3c4" opacity="0.85"/>
      <path d="M 120 40 L 200 200" stroke="#1a0a14" stroke-width="0.8" fill="none"/>
      <ellipse cx="120" cy="56" rx="14" ry="4" fill="#1a0a14"/>
      <rect x="0" y="260" width="400" height="60" fill="#5a3a1a"/>
      <line x1="0" y1="260" x2="400" y2="260" stroke="#1a0a14" stroke-width="2"/>
      <line x1="0" y1="280" x2="400" y2="280" stroke="#3a2a1a" stroke-width="1"/>
      <g transform="translate(60,290)" stroke="#3a2a1a" stroke-width="1.5" fill="none">
        <circle cx="0" cy="0" r="8"/>
        <circle cx="0" cy="0" r="4"/>
      </g>
      <g transform="translate(320,290)">
        <rect x="-4" y="-12" width="8" height="12" fill="#e6c879"/>
        <rect x="-4" y="-12" width="8" height="12" fill="#fff3c4" opacity="0.4"/>
        <line x1="0" y1="-12" x2="0" y2="-18" stroke="#3a2a1a" stroke-width="1"/>
      </g>
    </g>"""


def _layered_horror():
    """Foggy graveyard. Tombstones, dead tree, moon behind clouds."""
    return """<g>
      <defs>
        <linearGradient id="lh_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#0a0a14"/>
          <stop offset="60%" stop-color="#1a0a20"/>
          <stop offset="100%" stop-color="#3a1a2a"/>
        </linearGradient>
        <radialGradient id="lh_moon" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stop-color="#f8eccb"/>
          <stop offset="100%" stop-color="#b88f48"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#lh_bg)"/>
      <circle cx="280" cy="80" r="34" fill="url(#lh_moon)"/>
      <g fill="#1a1428" opacity="0.6">
        <ellipse cx="260" cy="80"  rx="40" ry="14"/>
        <ellipse cx="120" cy="120" rx="60" ry="20"/>
      </g>
      <g stroke="#3a2a3a" stroke-width="1" fill="none">
        <line x1="0" y1="200" x2="400" y2="200"/>
        <line x1="40"  y1="200" x2="40"  y2="220" stroke-width="1.5"/>
        <line x1="100" y1="200" x2="100" y2="220" stroke-width="1.5"/>
        <line x1="160" y1="200" x2="160" y2="220" stroke-width="1.5"/>
        <line x1="220" y1="200" x2="220" y2="220" stroke-width="1.5"/>
        <line x1="280" y1="200" x2="280" y2="220" stroke-width="1.5"/>
        <line x1="340" y1="200" x2="340" y2="220" stroke-width="1.5"/>
      </g>
      <g fill="#3a3a5e" stroke="#1a1428" stroke-width="1">
        <rect x="60"  y="200" width="22" height="50" rx="2"/>
        <rect x="56"  y="194" width="30" height="8" rx="2"/>
        <text x="71"  y="220" font-family="serif" font-size="8" fill="#5a4a6a" text-anchor="middle">RIP</text>
        <rect x="170" y="190" width="28" height="60" rx="2"/>
        <rect x="166" y="184" width="36" height="8" rx="2"/>
        <text x="184" y="216" font-family="serif" font-size="8" fill="#5a4a6a" text-anchor="middle">J.S.</text>
        <rect x="280" y="198" width="24" height="52" rx="2"/>
        <rect x="276" y="192" width="32" height="8" rx="2"/>
        <text x="292" y="220" font-family="serif" font-size="8" fill="#5a4a6a" text-anchor="middle">1807</text>
      </g>
      <g stroke="#1a0a14" stroke-width="3" fill="none" stroke-linecap="round">
        <line x1="60" y1="260" x2="60" y2="60"/>
        <line x1="60" y1="120" x2="20" y2="80"/>
        <line x1="60" y1="120" x2="100" y2="70"/>
        <line x1="60" y1="90" x2="40" y2="50"/>
        <line x1="60" y1="90" x2="80" y2="40"/>
        <line x1="60" y1="80" x2="30" y2="40"/>
        <line x1="60" y1="80" x2="100" y2="30"/>
      </g>
      <ellipse cx="200" cy="280" rx="200" ry="20" fill="#5a4a6a" opacity="0.5"/>
      <ellipse cx="100" cy="290" rx="120" ry="14" fill="#3a3a5e" opacity="0.6"/>
      <path d="M 320 60 q 6 -2 12 0 l -3 4 l -3 -4 z" fill="#0a0a14"/>
      <path d="M 326 56 q 4 -2 8 0 l -2 3 l -2 -3 z" fill="#0a0a14"/>
    </g>"""


LAYERED_SCENES = {
    "fantasy":   _layered_fantasy,
    "scifi":     _layered_scifi,
    "noir":      _layered_noir,
    "romance":   _layered_romance,
    "adventure": _layered_adventure,
    "horror":    _layered_horror,
}


def compose_layered_scene(genre: str) -> str:
    """Return a full 400x400 layered SVG scene for the given genre."""
    fn = LAYERED_SCENES.get(genre, _layered_fantasy)
    return (
        '<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">'
        + fn()
        + '<path d="M 0 320 L 400 320 L 400 400 L 0 400 Z" '
          'fill="#15243f" opacity="0.55"/>'
        + '</svg>'
    )



# ============================================================================


# ============================================================================
# Phase 16 — 16-genre vocabulary
# (v15 had 6 layered scenes; v16 adds 10 more — cyberpunk, action, drama,
# thriller, comedy, detective, fairytales, superhero, chicklit, roleplaying,
# historical — plus a dispatcher that covers all 16.)
# ============================================================================

def _layered_cyberpunk_v16():
    return """<g>
      <defs>
        <linearGradient id="lcp_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#0a0420"/>
          <stop offset="60%" stop-color="#3a1850"/>
          <stop offset="100%" stop-color="#5a2a4a"/>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#lcp_bg)"/>
      <g fill="#0a0420">
        <rect x="0"   y="80"  width="60"  height="180"/>
        <rect x="70"  y="60"  width="80"  height="200"/>
        <rect x="160" y="100" width="60"  height="160"/>
        <rect x="230" y="40"  width="100" height="220"/>
        <rect x="340" y="90"  width="60"  height="170"/>
      </g>
      <rect x="180" y="120" width="180" height="140" fill="#15243f"/>
      <rect x="180" y="125" width="180" height="32" fill="#ff3a8a"/>
      <text x="270" y="148" font-family="monospace" font-size="14" font-weight="700" fill="#0a1428" text-anchor="middle">CYBER</text>
      <g fill="#44f0ff" opacity="0.8">
        <rect x="20" y="120" width="6" height="6"/>
        <rect x="36" y="140" width="6" height="6"/>
        <rect x="80" y="100" width="6" height="6"/>
        <rect x="120" y="120" width="6" height="6"/>
        <rect x="260" y="180" width="8" height="8"/>
        <rect x="280" y="180" width="8" height="8"/>
        <rect x="300" y="180" width="8" height="8"/>
      </g>
      <g stroke="#a8f0ff" stroke-width="0.6" opacity="0.4">
        <line x1="40" y1="30" x2="32" y2="70"/>
        <line x1="100" y1="20" x2="92" y2="60"/>
        <line x1="160" y1="40" x2="152" y2="80"/>
        <line x1="220" y1="20" x2="212" y2="60"/>
        <line x1="280" y1="50" x2="272" y2="90"/>
        <line x1="340" y1="30" x2="332" y2="70"/>
      </g>
      <rect x="0" y="260" width="400" height="60" fill="#0a1428"/>
      <rect x="180" y="280" width="180" height="14" fill="#ff3a8a" opacity="0.4"/>
      <rect x="260" y="298" width="60" height="6" fill="#44f0ff" opacity="0.4"/>
      <g transform="translate(80,260)">
        <ellipse cx="0" cy="2" rx="6" ry="1" fill="#000" opacity="0.4"/>
        <path d="M -6 0 L -6 -30 L 6 -30 L 6 0 Z" fill="#0a0a14" stroke="#44f0ff" stroke-width="0.8" opacity="0.85"/>
        <circle cx="0" cy="-36" r="5" fill="#0a0a14" stroke="#44f0ff" stroke-width="0.8" opacity="0.85"/>
      </g>
    </g>"""


def _layered_action_v16():
    return """<g>
      <defs>
        <linearGradient id="lact_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#0a0420"/>
          <stop offset="60%" stop-color="#1a1428"/>
          <stop offset="100%" stop-color="#3a1a1a"/>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#lact_bg)"/>
      <g fill="#1a1428">
        <rect x="0"   y="120" width="50"  height="140"/>
        <rect x="60"  y="80"  width="70"  height="180"/>
        <rect x="140" y="100" width="60"  height="160"/>
        <rect x="210" y="60"  width="80"  height="200"/>
        <rect x="300" y="100" width="100" height="160"/>
      </g>
      <g fill="#e6c879" opacity="0.55">
        <rect x="20" y="160" width="6" height="6"/>
        <rect x="80" y="120" width="6" height="6"/>
        <rect x="100" y="160" width="6" height="6"/>
        <rect x="160" y="140" width="6" height="6"/>
        <rect x="240" y="100" width="6" height="6"/>
        <rect x="270" y="140" width="6" height="6"/>
        <rect x="330" y="160" width="6" height="6"/>
        <rect x="370" y="120" width="6" height="6"/>
      </g>
      <path d="M 0 260 L 400 260 L 320 320 L 80 320 Z" fill="#1a0a14"/>
      <line x1="200" y1="260" x2="200" y2="320" stroke="#e6c879" stroke-width="1" stroke-dasharray="8 6" opacity="0.7"/>
      <g transform="translate(110,260)">
        <ellipse cx="20" cy="6" rx="28" ry="3" fill="#000" opacity="0.45"/>
        <rect x="0" y="-10" width="40" height="14" fill="#c44a3a" stroke="#1a0a14" stroke-width="0.5"/>
        <rect x="6" y="-6" width="14" height="8" fill="#7a3a3a"/>
        <circle cx="6" cy="6" r="3" fill="#1a0a14"/>
        <circle cx="34" cy="6" r="3" fill="#1a0a14"/>
      </g>
      <g transform="translate(250,250)">
        <ellipse cx="20" cy="6" rx="28" ry="3" fill="#000" opacity="0.45"/>
        <rect x="0" y="-10" width="40" height="14" fill="#3a4a5a" stroke="#1a0a14" stroke-width="0.5"/>
        <rect x="6" y="-6" width="14" height="8" fill="#5a6a7a"/>
        <circle cx="6" cy="6" r="3" fill="#1a0a14"/>
        <circle cx="34" cy="6" r="3" fill="#1a0a14"/>
      </g>
      <path d="M 90 252 L 0 200 L 0 240 Z" fill="#fff3c4" opacity="0.22"/>
    </g>"""


def _layered_drama_v16():
    return """<g>
      <defs>
        <linearGradient id="ldr_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#3a1a2a"/>
          <stop offset="60%" stop-color="#5a2a44"/>
          <stop offset="100%" stop-color="#1a1428"/>
        </linearGradient>
        <radialGradient id="ldr_spot" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stop-color="#fff3c4" stop-opacity="0.55"/>
          <stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#ldr_bg)"/>
      <path d="M 0 0 L 80 0 Q 60 80 50 200 Q 40 260 0 260 Z" fill="#5a1a3a" opacity="0.85"/>
      <path d="M 400 0 L 320 0 Q 340 80 350 200 Q 360 260 400 260 Z" fill="#5a1a3a" opacity="0.85"/>
      <circle cx="200" cy="180" r="80" fill="url(#ldr_spot)"/>
      <rect x="0" y="220" width="400" height="40" fill="#1a0a14"/>
      <g transform="translate(200,210)">
        <ellipse cx="0" cy="2" rx="20" ry="2" fill="#000" opacity="0.5"/>
        <rect x="-12" y="-30" width="24" height="32" fill="#5a3a1a" stroke="#1a0a14" stroke-width="1"/>
        <line x1="0" y1="-30" x2="0" y2="2" stroke="#1a0a14" stroke-width="2"/>
        <line x1="-14" y1="2" x2="-14" y2="10" stroke="#1a0a14" stroke-width="2"/>
        <line x1="14" y1="2" x2="14" y2="10" stroke="#1a0a14" stroke-width="2"/>
      </g>
      <g fill="#0a0420">
        <path d="M 0 260 L 0 250 L 20 246 L 20 260 Z"/>
        <path d="M 30 260 L 30 248 L 50 244 L 50 260 Z"/>
        <path d="M 60 260 L 60 250 L 80 246 L 80 260 Z"/>
        <path d="M 320 260 L 320 250 L 340 246 L 340 260 Z"/>
        <path d="M 350 260 L 350 248 L 370 244 L 370 260 Z"/>
        <path d="M 380 260 L 380 250 L 400 246 L 400 260 Z"/>
      </g>
      <g fill="#e6c879" opacity="0.7">
        <circle cx="60"  cy="20" r="2"/>
        <circle cx="100" cy="10" r="2"/>
        <circle cx="200" cy="8"  r="2.4"/>
        <circle cx="300" cy="10" r="2"/>
        <circle cx="340" cy="20" r="2"/>
      </g>
    </g>"""


def _layered_thriller_v16():
    return """<g>
      <defs>
        <linearGradient id="lthr_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1a0a14"/>
          <stop offset="60%" stop-color="#3a0a1a"/>
          <stop offset="100%" stop-color="#1a0a14"/>
        </linearGradient>
        <radialGradient id="lthr_bulb" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stop-color="#fff3c4" stop-opacity="0.55"/>
          <stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#lthr_bg)"/>
      <path d="M 0 0 L 140 110 L 140 200 L 0 260 Z" fill="#0a0a14"/>
      <path d="M 400 0 L 260 110 L 260 200 L 400 260 Z" fill="#0a0a14"/>
      <path d="M 0 260 L 140 200 L 260 200 L 400 260 Z" fill="#1a0a14"/>
      <path d="M 0 0 L 140 110 L 260 110 L 400 0 Z" fill="#0a0a14"/>
      <line x1="200" y1="0" x2="206" y2="100" stroke="#1a0a14" stroke-width="1"/>
      <circle cx="206" cy="100" r="48" fill="url(#lthr_bulb)"/>
      <circle cx="206" cy="100" r="6" fill="#fff3c4"/>
      <rect x="190" y="140" width="20" height="60" fill="#c44a3a" stroke="#1a0a14" stroke-width="1"/>
      <ellipse cx="200" cy="220" rx="80" ry="3" fill="#0a0a14" opacity="0.7"/>
      <g transform="translate(160,200)">
        <ellipse cx="0" cy="2" rx="8" ry="1.5" fill="#000" opacity="0.6"/>
        <path d="M -5 0 L -6 -22 L 6 -22 L 5 0 Z" fill="#0a0a14"/>
        <circle cx="0" cy="-26" r="4" fill="#0a0a14"/>
      </g>
    </g>"""


def _layered_comedy_v16():
    return """<g>
      <defs>
        <linearGradient id="lcom_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#5a1a4a"/>
          <stop offset="50%" stop-color="#c44a8a"/>
          <stop offset="100%" stop-color="#e6c879"/>
        </linearGradient>
        <radialGradient id="lcom_spot" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stop-color="#fff8d8" stop-opacity="0.7"/>
          <stop offset="100%" stop-color="#fff8d8" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#lcom_bg)"/>
      <path d="M 200 30 L 100 260 L 300 260 Z" fill="url(#lcom_spot)" opacity="0.8"/>
      <g>
        <rect x="40" y="40" width="6" height="3" fill="#fff3c4" transform="rotate(20 43 41)"/>
        <rect x="80" y="60" width="6" height="3" fill="#ff3a8a" transform="rotate(-30 83 61)"/>
        <rect x="120" y="40" width="6" height="3" fill="#44f0ff" transform="rotate(45 123 41)"/>
        <rect x="160" y="50" width="6" height="3" fill="#9ad6a4" transform="rotate(-15 163 51)"/>
        <rect x="240" y="40" width="6" height="3" fill="#fff3c4" transform="rotate(60 243 41)"/>
        <rect x="280" y="60" width="6" height="3" fill="#ff3a8a" transform="rotate(-40 283 61)"/>
        <rect x="320" y="40" width="6" height="3" fill="#44f0ff" transform="rotate(20 323 41)"/>
        <rect x="360" y="60" width="6" height="3" fill="#fff3c4" transform="rotate(-50 363 61)"/>
      </g>
      <rect x="0" y="220" width="400" height="40" fill="#3a1a2a"/>
      <g transform="translate(110,220)">
        <line x1="0" y1="0" x2="0" y2="-50" stroke="#1a0a14" stroke-width="2"/>
        <ellipse cx="0" cy="0" rx="8" ry="2" fill="#1a0a14"/>
        <circle cx="0" cy="-50" r="6" fill="#5a4a6a" stroke="#1a0a14" stroke-width="1"/>
      </g>
      <g transform="translate(240,220)">
        <ellipse cx="0" cy="2" rx="14" ry="2" fill="#000" opacity="0.5"/>
        <path d="M -10 0 L -10 -30 L 10 -30 L 10 0 Z" fill="#3a3a5e"/>
        <circle cx="0" cy="-36" r="8" fill="#3a3a5e"/>
        <circle cx="0" cy="-36" r="9" fill="#fff3c4" stroke="#c8764a" stroke-width="0.5"/>
      </g>
    </g>"""


def _layered_detective_v16():
    return """<g>
      <defs>
        <linearGradient id="ldet_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1a1428"/>
          <stop offset="60%" stop-color="#3a1a2a"/>
          <stop offset="100%" stop-color="#1a0a14"/>
        </linearGradient>
        <radialGradient id="ldet_lamp" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stop-color="#fff3c4" stop-opacity="0.7"/>
          <stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#ldet_bg)"/>
      <rect x="0" y="80" width="400" height="120" fill="#1a0a14"/>
      <rect x="20" y="100" width="80" height="80" fill="#3a1a2a" stroke="#1a0a14" stroke-width="1"/>
      <line x1="60" y1="100" x2="60" y2="180" stroke="#1a0a14" stroke-width="1"/>
      <g stroke="#1a0a14" stroke-width="1.5">
        <line x1="20" y1="110" x2="100" y2="110"/>
        <line x1="20" y1="118" x2="100" y2="118"/>
        <line x1="20" y1="126" x2="100" y2="126"/>
        <line x1="20" y1="150" x2="100" y2="150"/>
        <line x1="20" y1="158" x2="100" y2="158"/>
        <line x1="20" y1="166" x2="100" y2="166"/>
      </g>
      <path d="M 0 200 L 400 200 L 400 260 L 0 260 Z" fill="#3a1a1a" stroke="#1a0a14" stroke-width="1"/>
      <circle cx="240" cy="120" r="70" fill="url(#ldet_lamp)"/>
      <path d="M 230 80 L 250 80 L 256 100 L 224 100 Z" fill="#5a3a1a" stroke="#1a0a14" stroke-width="1"/>
      <line x1="240" y1="100" x2="240" y2="200" stroke="#5a3a1a" stroke-width="2"/>
      <ellipse cx="240" cy="200" rx="14" ry="3" fill="#1a0a14"/>
      <rect x="60" y="180" width="120" height="40" fill="#d8c8a4" stroke="#1a0a14" stroke-width="1" transform="rotate(-4 120 200)"/>
      <circle cx="120" cy="198" r="14" stroke="#1a0a14" stroke-width="2" fill="rgba(255,255,255,0.1)" transform="rotate(-4 120 200)"/>
      <circle cx="120" cy="198" r="2" fill="#c44a3a" transform="rotate(-4 120 200)"/>
      <line x1="130" y1="208" x2="142" y2="220" stroke="#1a0a14" stroke-width="3" stroke-linecap="round"/>
    </g>"""


def _layered_fairytales_v16():
    return """<g>
      <defs>
        <linearGradient id="lft_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#3a2a4a"/>
          <stop offset="60%" stop-color="#7a4a8a"/>
          <stop offset="100%" stop-color="#e6c879"/>
        </linearGradient>
        <radialGradient id="lft_window" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stop-color="#fff3c4" stop-opacity="0.8"/>
          <stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#lft_bg)"/>
      <circle cx="60" cy="50" r="14" fill="#fff3c4"/>
      <circle cx="66" cy="46" r="12" fill="#3a2a4a"/>
      <g transform="translate(180,140)">
        <ellipse cx="20" cy="60" rx="60" ry="40" fill="url(#lft_window)"/>
        <rect x="0" y="40" width="80" height="60" fill="#5a3a1a" stroke="#1a0a14" stroke-width="1"/>
        <path d="M -10 40 L 20 0 L 50 0 L 90 40 Z" fill="#3a1a1a" stroke="#1a0a14" stroke-width="1"/>
        <rect x="10" y="56" width="18" height="22" fill="#fff3c4" stroke="#1a0a14" stroke-width="1"/>
        <rect x="52" y="56" width="18" height="22" fill="#fff3c4" stroke="#1a0a14" stroke-width="1"/>
        <rect x="34" y="74" width="14" height="26" fill="#1a0a14"/>
      </g>
      <path d="M 200 220 Q 220 200 180 180 Q 160 160 200 140 Q 240 130 220 100" stroke="#d8c8a4" stroke-width="6" fill="none" opacity="0.7"/>
      <g transform="translate(40,230)">
        <rect x="-2" y="-6" width="4" height="8" fill="#f8eccb"/>
        <ellipse cx="0" cy="-6" rx="8" ry="4" fill="#c44a3a"/>
      </g>
    </g>"""


def _layered_superhero_v16():
    return """<g>
      <defs>
        <linearGradient id="lsh_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1a0850"/>
          <stop offset="50%" stop-color="#5a2a8a"/>
          <stop offset="100%" stop-color="#e87a4a"/>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#lsh_bg)"/>
      <g fill="#1a0850">
        <rect x="0"   y="160" width="60"  height="100"/>
        <rect x="70"  y="140" width="80"  height="120"/>
        <rect x="160" y="170" width="60"  height="90"/>
        <rect x="230" y="120" width="80"  height="140"/>
        <rect x="320" y="150" width="80"  height="110"/>
      </g>
      <g fill="#fff3c4" opacity="0.7">
        <rect x="20" y="180" width="4" height="6"/>
        <rect x="90" y="160" width="4" height="6"/>
        <rect x="260" y="140" width="4" height="6"/>
        <rect x="350" y="170" width="4" height="6"/>
      </g>
      <path d="M 80 60 L 86 80 L 102 80 L 90 92 L 96 112 L 80 100 L 64 112 L 70 92 L 58 80 L 74 80 Z" fill="#fff3c4"/>
      <g transform="translate(80,260)">
        <ellipse cx="0" cy="2" rx="20" ry="2" fill="#000" opacity="0.5"/>
        <path d="M -10 0 L -10 -50 L 10 -50 L 10 0 Z" fill="#1a0850"/>
        <path d="M -8 -10 L -22 -30 L -12 -30 L -4 -16 Z" fill="#c44a3a"/>
        <path d="M 8 -10 L 22 -30 L 12 -30 L 4 -16 Z" fill="#c44a3a"/>
        <circle cx="0" cy="-58" r="7" fill="#1a0850"/>
        <path d="M -7 -56 L 0 -64 L 7 -56 L 0 -50 Z" fill="#e6c879"/>
      </g>
    </g>"""


def _layered_chicklit_v16():
    return """<g>
      <defs>
        <linearGradient id="lcl_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#5a3a4a"/>
          <stop offset="60%" stop-color="#c47a4a"/>
          <stop offset="100%" stop-color="#e6a868"/>
        </linearGradient>
        <radialGradient id="lcl_light" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stop-color="#fff3c4" stop-opacity="0.6"/>
          <stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#lcl_bg)"/>
      <rect x="0" y="160" width="400" height="100" fill="#3a2a1a"/>
      <circle cx="120" cy="180" r="60" fill="url(#lcl_light)"/>
      <path d="M 80 200 L 100 184 L 140 184 L 160 200 L 140 216 L 100 216 Z" fill="#fff3c4" stroke="#1a0a14" stroke-width="1"/>
      <path d="M 100 184 Q 120 180 140 184 L 140 200 Q 120 204 100 200 Z" fill="#3a1a1a"/>
      <ellipse cx="120" cy="194" rx="14" ry="8" fill="#fff8d8" stroke="#1a0a14" stroke-width="0.5"/>
      <path d="M 113 194 Q 120 184 127 194 Q 120 200 113 194 Z" fill="#5a3a1a" opacity="0.6"/>
      <rect x="180" y="184" width="100" height="50" fill="#3a2a4a" stroke="#1a0a14" stroke-width="1" transform="rotate(-3 230 209)"/>
      <g transform="translate(340,160)">
        <ellipse cx="0" cy="44" rx="20" ry="3" fill="#000" opacity="0.4"/>
        <rect x="-3" y="20" width="6" height="24" fill="#5a3a1a"/>
        <ellipse cx="0" cy="14" rx="22" ry="6" fill="#3a5a2a" stroke="#1a0a14" stroke-width="1"/>
        <ellipse cx="0" cy="8" rx="20" ry="6" fill="#5a7a3a" stroke="#1a0a14" stroke-width="1"/>
      </g>
      <text x="200" y="60" font-family="Fraunces, Georgia, serif" font-style="italic" font-size="16" fill="#fff3c4" opacity="0.7" text-anchor="middle">a quiet afternoon</text>
    </g>"""


def _layered_roleplaying_v16():
    return """<g>
      <defs>
        <linearGradient id="lrp_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1a0850"/>
          <stop offset="60%" stop-color="#3a1a4a"/>
          <stop offset="100%" stop-color="#1a0a14"/>
        </linearGradient>
        <radialGradient id="lrp_fire" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stop-color="#fff3c4" stop-opacity="0.85"/>
          <stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#lrp_bg)"/>
      <g stroke="#5a4a6a" stroke-width="0.6" fill="rgba(230,200,121,0.04)">
        <polygon points="80,80 110,80 125,105 110,130 80,130 65,105"/>
        <polygon points="140,80 170,80 185,105 170,130 140,130 125,105"/>
        <polygon points="200,80 230,80 245,105 230,130 200,130 185,105"/>
        <polygon points="260,80 290,80 305,105 290,130 260,130 245,105"/>
        <polygon points="320,80 350,80 365,105 350,130 320,130 305,105"/>
      </g>
      <circle cx="200" cy="170" r="60" fill="url(#lrp_fire)"/>
      <g transform="translate(200,180)">
        <ellipse cx="0" cy="6" rx="14" ry="2" fill="#000" opacity="0.5"/>
        <path d="M -8 4 L -10 -16 L 10 -16 L 8 4 Z" fill="#5a3a1a" stroke="#1a0a14" stroke-width="1"/>
        <path d="M -8 -10 L 0 -24 L 8 -10 L 4 -2 L -4 -2 Z" fill="#e6a868"/>
        <path d="M -4 -16 L 0 -22 L 4 -16 L 2 -10 L -2 -10 Z" fill="#fff3c4"/>
      </g>
      <g transform="translate(110,200)">
        <path d="M -8 0 L -10 -36 L 10 -36 L 8 0 Z" fill="#1a0850" stroke="#e6c879" stroke-width="0.8"/>
        <circle cx="0" cy="-44" r="6" fill="#1a0850" stroke="#e6c879" stroke-width="0.8"/>
      </g>
      <g transform="translate(290,200)">
        <path d="M -8 0 L -10 -36 L 10 -36 L 8 0 Z" fill="#3a2a1a" stroke="#e6c879" stroke-width="0.8"/>
        <circle cx="0" cy="-44" r="6" fill="#3a2a1a" stroke="#e6c879" stroke-width="0.8"/>
      </g>
      <g transform="translate(60,40)">
        <polygon points="0,-12 14,0 0,12 -14,0" fill="#c44a3a" stroke="#1a0a14" stroke-width="1"/>
        <text x="0" y="3" font-family="monospace" font-size="10" font-weight="700" fill="#fff3c4" text-anchor="middle">20</text>
      </g>
      <g transform="translate(340,40)">
        <polygon points="0,-12 14,0 0,12 -14,0" fill="#5a4a6a" stroke="#1a0a14" stroke-width="1"/>
        <text x="0" y="3" font-family="monospace" font-size="10" font-weight="700" fill="#fff3c4" text-anchor="middle">14</text>
      </g>
    </g>"""


def _layered_historical_v16():
    return """<g>
      <defs>
        <linearGradient id="lhst_bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1a0a14"/>
          <stop offset="60%" stop-color="#3a1a1a"/>
          <stop offset="100%" stop-color="#5a3a1a"/>
        </linearGradient>
        <radialGradient id="lhst_lamp" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0%" stop-color="#fff3c4" stop-opacity="0.7"/>
          <stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="400" height="260" fill="url(#lhst_bg)"/>
      <g fill="#1a0a14" opacity="0.8">
        <rect x="0"   y="40" width="60"  height="180"/>
        <rect x="60"  y="20" width="80"  height="200"/>
        <rect x="140" y="50" width="60"  height="170"/>
        <rect x="200" y="30" width="80"  height="190"/>
        <rect x="280" y="40" width="60"  height="180"/>
        <rect x="340" y="20" width="60"  height="200"/>
      </g>
      <g fill="#3a1a1a">
        <rect x="6" y="50" width="48" height="6"/>
        <rect x="6" y="60" width="48" height="6"/>
        <rect x="6" y="70" width="48" height="6"/>
        <rect x="66" y="30" width="68" height="6"/>
        <rect x="66" y="40" width="68" height="6"/>
        <rect x="206" y="40" width="68" height="6"/>
        <rect x="206" y="50" width="68" height="6"/>
        <rect x="346" y="30" width="48" height="6"/>
        <rect x="346" y="40" width="48" height="6"/>
      </g>
      <rect x="0" y="180" width="400" height="80" fill="#3a1a1a" stroke="#1a0a14" stroke-width="1"/>
      <circle cx="240" cy="180" r="80" fill="url(#lhst_lamp)"/>
      <g transform="translate(240,180)">
        <ellipse cx="0" cy="20" rx="14" ry="3" fill="#1a0a14"/>
        <path d="M -8 0 L -10 -28 L 10 -28 L 8 0 Z" fill="#5a3a1a" stroke="#1a0a14" stroke-width="1"/>
        <ellipse cx="0" cy="-30" rx="10" ry="4" fill="#1a0a14"/>
        <rect x="-4" y="-44" width="8" height="14" fill="#1a0a14"/>
        <ellipse cx="0" cy="-46" rx="3" ry="2" fill="#fff3c4"/>
        <line x1="0" y1="-48" x2="-2" y2="-56" stroke="#fff3c4" stroke-width="1"/>
      </g>
      <g transform="translate(80,180)">
        <rect x="-12" y="-30" width="24" height="30" fill="#3a4a5a" stroke="#1a0a14" stroke-width="1"/>
        <line x1="-12" y1="-24" x2="12" y2="-24" stroke="#e6c879" stroke-width="0.8"/>
        <line x1="-12" y1="-18" x2="12" y2="-18" stroke="#e6c879" stroke-width="0.8"/>
      </g>
    </g>"""


# The 11 v16-only composers.
_LAYERED_V16 = {
    "cyberpunk":   _layered_cyberpunk_v16,
    "action":      _layered_action_v16,
    "drama":       _layered_drama_v16,
    "thriller":    _layered_thriller_v16,
    "comedy":      _layered_comedy_v16,
    "detective":   _layered_detective_v16,
    "fairytales":  _layered_fairytales_v16,
    "superhero":   _layered_superhero_v16,
    "chicklit":    _layered_chicklit_v16,
    "roleplaying": _layered_roleplaying_v16,
    "historical":  _layered_historical_v16,
}


def compose_layered_scene_v16(genre: str) -> str:
    """v16 layered scene composer - supports all 16 brief-listed genres."""
    fn = LAYERED_SCENES.get(genre) or _LAYERED_V16.get(genre)
    if fn is None:
        fn = LAYERED_SCENES.get("fantasy")
    return (
        '<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">'
        + fn()
        + '<path d="M 0 320 L 400 320 L 400 400 L 0 400 Z" '
          'fill="#15243f" opacity="0.55"/>'
        + '</svg>'
    )


# The 16 brief-listed genres. Order matches the homepage card layout.
GENRES_V16 = [
    "cyberpunk", "romance", "action", "drama",
    "thriller", "fantasy", "comedy", "scifi",
    "horror", "detective", "fairytales", "superhero",
    "chicklit", "adventure", "roleplaying", "historical",
]


GENRE_LABELS = {
    "cyberpunk":   "Cyberpunk",
    "romance":     "Romance",
    "action":      "Action",
    "drama":       "Drama",
    "thriller":    "Thriller",
    "fantasy":     "Fantasy",
    "comedy":      "Comedy",
    "scifi":       "Sci-Fi",
    "horror":      "Horror",
    "detective":   "Detective",
    "fairytales":  "Fairytales",
    "superhero":   "Superhero",
    "chicklit":    "Chick-lit",
    "adventure":   "Adventure",
    "roleplaying": "Roleplaying",
    "historical":  "Historical Fiction",
}

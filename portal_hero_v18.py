"""
PocketPlot Universe - v18 hero SVG.

A 'Tech-Victorian' cinematic scene. The v17 glowing book + cosmic
interior is now framed inside an open Victorian library: a dark
walnut floor and bookcase, brass compass elements at the corners,
subtle clockwork gears in the background, warm amber light from a
banker's lamp mixed with cool neon, all behind the book portal.

Composition (back to front):
  1. Deep navy + faint warm gradient (room interior)
  2. Wood floor (warm walnut plank lines) at the bottom
  3. Bookcase behind the book (rows of spine-coloured rectangles)
  4. Clockwork gears (3 sizes, slow rotation) drifting in the air
  5. Brass compass elements (small) at top-left and bottom-right
  6. Banker's lamp glow (top-right warm pool of amber light)
  7. Cool neon circuit lines (subtle, left side)
  8. The cosmic book portal (from v17) in the center
  9. A thin ornate brass border around the entire scene

The art is rendered into a 400x400 viewBox to match v17.
"""

PORTAL_HERO_V18 = '''<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="A glowing book opening to a cosmic interior, framed by a Victorian library with brass instruments and clockwork gears">
  <defs>
    <!-- Room interior gradient: deep navy ceiling to warm oak floor -->
    <linearGradient id="v18_room" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"   stop-color="#0a0f1c"/>
      <stop offset="40%"  stop-color="#0e1a2e"/>
      <stop offset="70%"  stop-color="#1a2440"/>
      <stop offset="92%"  stop-color="#3a2818"/>
      <stop offset="100%" stop-color="#4a2c1a"/>
    </linearGradient>

    <!-- Wood floor planks -->
    <pattern id="v18_planks" patternUnits="userSpaceOnUse" width="80" height="20" x="0" y="280">
      <rect width="80" height="20" fill="#3a2010"/>
      <line x1="0" y1="0" x2="80" y2="0" stroke="#1a0e08" stroke-width="0.5"/>
      <line x1="0" y1="20" x2="80" y2="20" stroke="#1a0e08" stroke-width="0.5"/>
      <!-- wood grain: thin diagonal stripes -->
      <line x1="6"  y1="0" x2="14" y2="20" stroke="#1a0e08" stroke-width="0.3" opacity="0.6"/>
      <line x1="22" y1="0" x2="30" y2="20" stroke="#1a0e08" stroke-width="0.3" opacity="0.6"/>
      <line x1="40" y1="0" x2="48" y2="20" stroke="#1a0e08" stroke-width="0.3" opacity="0.6"/>
      <line x1="58" y1="0" x2="66" y2="20" stroke="#1a0e08" stroke-width="0.3" opacity="0.6"/>
    </pattern>

    <!-- Bookcase rows (varying spine colors) -->
    <pattern id="v18_bookcase" patternUnits="userSpaceOnUse" width="40" height="30" x="0" y="40">
      <rect width="40" height="30" fill="#1a2440"/>
      <rect x="0"  y="0" width="6" height="28" fill="#0f3a2a" rx="0.5"/>
      <rect x="7"  y="0" width="5" height="28" fill="#8a6a26" rx="0.5"/>
      <rect x="13" y="0" width="4" height="28" fill="#5a2010" rx="0.5"/>
      <rect x="18" y="0" width="6" height="28" fill="#4a2c1a" rx="0.5"/>
      <rect x="25" y="0" width="5" height="28" fill="#0f3a2a" rx="0.5"/>
      <rect x="31" y="0" width="4" height="28" fill="#3a2010" rx="0.5"/>
      <rect x="36" y="0" width="4" height="28" fill="#8a6a26" rx="0.5"/>
      <!-- top shelf line -->
      <line x1="0" y1="29" x2="40" y2="29" stroke="#0a0f1c" stroke-width="0.5"/>
    </pattern>

    <!-- Banker's lamp glow -->
    <radialGradient id="v18_lamp" cx="0.85" cy="0.18" r="0.6">
      <stop offset="0%"  stop-color="#ffd47a" stop-opacity="0.55"/>
      <stop offset="40%" stop-color="#f0b54a" stop-opacity="0.20"/>
      <stop offset="100%" stop-color="#f0b54a" stop-opacity="0"/>
    </radialGradient>

    <!-- Cool neon glow (left side) -->
    <radialGradient id="v18_neon" cx="0.12" cy="0.4" r="0.45">
      <stop offset="0%"  stop-color="#5ddef0" stop-opacity="0.32"/>
      <stop offset="100%" stop-color="#5ddef0" stop-opacity="0"/>
    </radialGradient>

    <!-- Brass gradient (for compass + frame) -->
    <linearGradient id="v18_brass" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#e8c879"/>
      <stop offset="50%" stop-color="#c9a04e"/>
      <stop offset="100%" stop-color="#8a6a26"/>
    </linearGradient>
    <linearGradient id="v18_brass_h" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%"  stop-color="#8a6a26"/>
      <stop offset="50%" stop-color="#e8c879"/>
      <stop offset="100%" stop-color="#8a6a26"/>
    </linearGradient>

    <!-- Cosmic book glow (carry-over from v17) -->
    <radialGradient id="v18_book_glow" cx="0.5" cy="0.55" r="0.5">
      <stop offset="0%"  stop-color="#ffd47a" stop-opacity="0.95"/>
      <stop offset="35%" stop-color="#f0b54a" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#f0b54a" stop-opacity="0"/>
    </radialGradient>

    <!-- Vignette (frame edges) -->
    <radialGradient id="v18_vignette" cx="0.5" cy="0.5" r="0.7">
      <stop offset="60%" stop-color="#000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000" stop-opacity="0.55"/>
    </radialGradient>

    <!-- Reusable gear (drawn in a 100x100 box, scaled by use) -->
    <symbol id="v18_gear" viewBox="-50 -50 100 100">
      <g fill="none" stroke="url(#v18_brass_h)" stroke-width="1.5">
        <circle r="38"/>
        <circle r="22"/>
        <circle r="8" fill="url(#v18_brass)"/>
        <!-- 12 teeth -->
        <g>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v18_brass)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v18_brass)" transform="rotate(30)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v18_brass)" transform="rotate(60)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v18_brass)" transform="rotate(90)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v18_brass)" transform="rotate(120)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v18_brass)" transform="rotate(150)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v18_brass)" transform="rotate(180)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v18_brass)" transform="rotate(210)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v18_brass)" transform="rotate(240)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v18_brass)" transform="rotate(270)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v18_brass)" transform="rotate(300)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v18_brass)" transform="rotate(330)"/>
        </g>
      </g>
    </symbol>

    <!-- Reusable compass (rose + needle) -->
    <symbol id="v18_compass" viewBox="-30 -30 60 60">
      <circle r="26" fill="url(#v18_brass)" stroke="#8a6a26" stroke-width="1"/>
      <circle r="22" fill="none" stroke="#5a4a18" stroke-width="0.5"/>
      <circle r="18" fill="none" stroke="#5a4a18" stroke-width="0.5"/>
      <!-- cardinal ticks -->
      <g stroke="#3a2a10" stroke-width="1">
        <line x1="0" y1="-22" x2="0" y2="-18"/>
        <line x1="0" y1="22"  x2="0" y2="18"/>
        <line x1="-22" y1="0" x2="-18" y2="0"/>
        <line x1="22" y1="0"  x2="18" y2="0"/>
      </g>
      <!-- N E S W letters -->
      <g font-family="Cinzel,serif" font-size="6" fill="#3a2a10" text-anchor="middle">
        <text x="0" y="-11">N</text>
        <text x="11" y="2">E</text>
        <text x="0" y="15">S</text>
        <text x="-11" y="2">W</text>
      </g>
      <!-- needle -->
      <g transform="rotate(35)">
        <path d="M 0 -16 L 3 0 L 0 16 L -3 0 Z" fill="#5a2010" stroke="#3a1408" stroke-width="0.5"/>
        <path d="M 0 -16 L 3 0 L -3 0 Z" fill="#c44a3a"/>
        <circle r="2" fill="url(#v18_brass)" stroke="#3a2a10" stroke-width="0.5"/>
      </g>
      <circle r="1.2" fill="#3a2a10"/>
    </symbol>
  </defs>

  <!-- 1. Room interior -->
  <rect x="0" y="0" width="400" height="400" fill="url(#v18_room)"/>

  <!-- 2. Bookcase behind the book (top half of the room) -->
  <rect x="0" y="0" width="400" height="220" fill="url(#v18_bookcase)" opacity="0.5"/>

  <!-- 3. Wood floor (bottom) -->
  <rect x="0" y="280" width="400" height="120" fill="url(#v18_planks)"/>
  <!-- floor highlight (warm amber light from the book) -->
  <ellipse cx="200" cy="320" rx="180" ry="30" fill="url(#v18_book_glow)" opacity="0.6"/>

  <!-- 4. Cool neon glow (left) -->
  <rect x="0" y="0" width="400" height="400" fill="url(#v18_neon)"/>

  <!-- 5. Banker's lamp glow (top-right) -->
  <rect x="0" y="0" width="400" height="400" fill="url(#v18_lamp)"/>

  <!-- 6. Clockwork gears drifting in the background -->
  <g opacity="0.7">
    <g class="gear slow" transform="translate(60 70) scale(0.5)">
      <use href="#v18_gear"/>
    </g>
    <g class="gear ccw"  transform="translate(330 100) scale(0.4)">
      <use href="#v18_gear"/>
    </g>
    <g class="gear med"  transform="translate(80 250) scale(0.35)">
      <use href="#v18_gear"/>
    </g>
    <g class="gear fast" transform="translate(330 230) scale(0.45)">
      <use href="#v18_gear"/>
    </g>
  </g>

  <!-- 7. Brass compass elements (corners) -->
  <g class="compass-tl" transform="translate(40 40) scale(0.7)">
    <use href="#v18_compass"/>
  </g>
  <g class="compass-br" transform="translate(360 360) scale(0.7)">
    <use href="#v18_compass"/>
  </g>

  <!-- 8. Subtle circuit lines (left side) -->
  <g stroke="#5ddef0" stroke-width="0.6" fill="none" opacity="0.4">
    <path d="M 0 180 L 40 180 L 50 170 L 90 170 L 100 180 L 140 180"/>
    <circle cx="50" cy="170" r="2" fill="#5ddef0" opacity="0.6"/>
    <circle cx="100" cy="180" r="2" fill="#5ddef0" opacity="0.6"/>
  </g>
  <!-- right side neon -->
  <g stroke="#e85a8a" stroke-width="0.6" fill="none" opacity="0.35">
    <path d="M 260 200 L 300 200 L 310 210 L 360 210 L 370 200 L 400 200"/>
    <circle cx="310" cy="210" r="2" fill="#e85a8a" opacity="0.6"/>
    <circle cx="360" cy="200" r="2" fill="#e85a8a" opacity="0.6"/>
  </g>

  <!-- 9. The cosmic book portal (centered, ~200-320 vertically) -->
  <g transform="translate(200 230)">
    <!-- glow halo behind -->
    <ellipse cx="0" cy="0" rx="120" ry="80" fill="url(#v18_book_glow)"/>
    <!-- book pages (open, V shape) -->
    <g>
      <!-- left page -->
      <path d="M -78 28 Q -50 -30 -10 -28 L -10 30 Q -50 28 -78 28 Z"
            fill="#1a0a04" stroke="url(#v18_brass_h)" stroke-width="1.5"/>
      <!-- right page -->
      <path d="M  10 -28 Q 50 -30 78 28 Q 50 28 10 30 Z"
            fill="#1a0a04" stroke="url(#v18_brass_h)" stroke-width="1.5"/>
      <!-- page text lines (left) -->
      <g stroke="#f3e9d2" stroke-width="0.5" opacity="0.5">
        <line x1="-66" y1="-6" x2="-22" y2="-8"/>
        <line x1="-66" y1="2"  x2="-22" y2="0"/>
        <line x1="-66" y1="10" x2="-22" y2="8"/>
        <line x1="-66" y1="18" x2="-40" y2="16"/>
      </g>
      <!-- page text lines (right) -->
      <g stroke="#f3e9d2" stroke-width="0.5" opacity="0.5">
        <line x1="22" y1="-8" x2="66" y2="-6"/>
        <line x1="22" y1="0"  x2="66" y2="2"/>
        <line x1="22" y1="8"  x2="66" y2="10"/>
        <line x1="22" y1="16" x2="48" y2="18"/>
      </g>
      <!-- center spine (brass) -->
      <line x1="0" y1="-28" x2="0" y2="30" stroke="url(#v18_brass_h)" stroke-width="2"/>
    </g>

    <!-- cosmic interior above the book (v17 carryover) -->
    <g transform="translate(0 -30)">
      <!-- crescent moon (offset darker circle) -->
      <g>
        <circle r="14" fill="#fff5d6"/>
        <circle cx="6" cy="-2" r="12" fill="#0a0f1c"/>
        <circle r="14" fill="none" stroke="url(#v18_brass_h)" stroke-width="0.6" opacity="0.6"/>
      </g>
      <!-- stars (sparse, small) -->
      <g fill="#f3e9d2">
        <circle cx="-50" cy="-30" r="0.6"/>
        <circle cx="-30" cy="-50" r="0.8"/>
        <circle cx="-15" cy="-15" r="0.5"/>
        <circle cx="20"  cy="-45" r="0.7"/>
        <circle cx="40"  cy="-25" r="0.6"/>
        <circle cx="55"  cy="-50" r="0.5"/>
        <circle cx="-60" cy="-55" r="0.5"/>
        <circle cx="35"  cy="-65" r="0.5"/>
        <circle cx="-40" cy="-65" r="0.4"/>
        <circle cx="50"  cy="-10" r="0.4"/>
        <circle cx="-50" cy="-10" r="0.4"/>
        <circle cx="0"   cy="-50" r="0.5"/>
        <circle cx="-25" cy="-35" r="0.4"/>
        <circle cx="25"  cy="-30" r="0.4"/>
      </g>
      <!-- 3 small glowing doorways floating up -->
      <g>
        <rect x="-50" y="-100" width="14" height="22" fill="none" stroke="url(#v18_brass_h)" stroke-width="0.8" rx="2"/>
        <rect x="-50" y="-100" width="14" height="22" fill="#ffd47a" opacity="0.25" rx="2"/>
        <line x1="-43" y1="-100" x2="-43" y2="-130" stroke="#ffd47a" stroke-width="0.4" opacity="0.5"/>
        <rect x="-7"  y="-110" width="14" height="22" fill="none" stroke="url(#v18_brass_h)" stroke-width="0.8" rx="2"/>
        <rect x="-7"  y="-110" width="14" height="22" fill="#5ddef0" opacity="0.25" rx="2"/>
        <line x1="0"   y1="-110" x2="0"   y2="-140" stroke="#5ddef0" stroke-width="0.4" opacity="0.5"/>
        <rect x="36"  y="-100" width="14" height="22" fill="none" stroke="url(#v18_brass_h)" stroke-width="0.8" rx="2"/>
        <rect x="36"  y="-100" width="14" height="22" fill="#e85a8a" opacity="0.25" rx="2"/>
        <line x1="43"  y1="-100" x2="43"  y2="-130" stroke="#e85a8a" stroke-width="0.4" opacity="0.5"/>
      </g>
    </g>
  </g>

  <!-- 10. Floor reflection of the book (subtle) -->
  <ellipse cx="200" cy="340" rx="80" ry="6" fill="#000" opacity="0.4"/>

  <!-- 11. Vignette to focus the eye -->
  <rect x="0" y="0" width="400" height="400" fill="url(#v18_vignette)"/>

  <!-- 12. Thin ornate brass border around the entire scene -->
  <g fill="none" stroke="url(#v18_brass_h)" stroke-width="1.2">
    <rect x="6" y="6" width="388" height="388" rx="4"/>
    <rect x="10" y="10" width="380" height="380" rx="2" stroke-width="0.4" opacity="0.6"/>
  </g>
  <!-- corner ornaments -->
  <g fill="url(#v18_brass)" stroke="#8a6a26" stroke-width="0.5">
    <circle cx="6"  cy="6"  r="3"/>
    <circle cx="394" cy="6"  r="3"/>
    <circle cx="6"  cy="394" r="3"/>
    <circle cx="394" cy="394" r="3"/>
  </g>
</svg>'''

if __name__ == "__main__":
    from pathlib import Path
    out = Path("/root/pocketplot/portal_hero_v18.py")
    out.write_text(__doc__ + "\n\nPORTAL_HERO_V18 = '''" + PORTAL_HERO_V18 + "'''\n")
    print(f"wrote portal_hero_v18.py ({len(PORTAL_HERO_V18)} chars)")

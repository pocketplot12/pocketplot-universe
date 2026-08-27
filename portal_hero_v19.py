"""
PocketPlot Universe - v19 hero: "The Story Engine" book.

A futuristic book with 19th-century pages. Open at the center,
the cream parchment pages have visible printed text in a Victorian
serif. Circuit lines (cyan + magenta) thread through the page
edges and the spine. Above the open book, holographic glyphs
(story symbols) float up and out, glowing amber. A subtle
holographic disc (the "imagination field") sits above the book.
The whole thing is framed in brass + walnut, sitting on a
Victorian desk, with a banker's lamp glow from the top-right
and 2 floating clockwork gears in the upper corners.

The composition (back to front):
  1. Deep navy room (radial gradient + amber top-right lamp)
  2. Walnut desk surface (lower third)
  3. Bookcase silhouette behind (top half, dim)
  4. 2 clockwork gears (top-left + top-right, slow rotation)
  5. The brass book base/stand (under the book)
  6. The open book (the focal point):
     - Cream parchment pages with visible printed text in serif
     - A subtle yellowed edge (the aged paper look)
     - Gilt (gold) page edges visible at the bottom
     - Circuit lines threading the spine + page margins
     - A holographic disc (the "imagination field") floating above
  7. Holographic glyphs floating up from the pages (story symbols):
     - A crescent moon (mystery genre)
     - A lightning bolt (action)
     - A heart (romance)
     - A skull (horror)
     - A crown (fantasy)
     - A rocket (sci-fi)
  8. The orbital brass frame around the entire scene
"""

PORTAL_HERO_V19 = '''<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="An open Victorian book with cream parchment pages and circuit lines, holographic story glyphs floating up from the pages, framed by a brass bookstand">
  <defs>
    <!-- Room interior gradient -->
    <linearGradient id="v19_room" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"   stop-color="#0a0f1c"/>
      <stop offset="35%"  stop-color="#0e1a2e"/>
      <stop offset="70%"  stop-color="#1a2440"/>
      <stop offset="100%" stop-color="#3a2010"/>
    </linearGradient>

    <!-- Walnut desk surface -->
    <pattern id="v19_desk" patternUnits="userSpaceOnUse" width="80" height="22" x="0" y="270">
      <rect width="80" height="22" fill="#3a2010"/>
      <line x1="0" y1="0"  x2="80" y2="0"  stroke="#1a0e08" stroke-width="0.5"/>
      <line x1="0" y1="22" x2="80" y2="22" stroke="#1a0e08" stroke-width="0.5"/>
      <line x1="6"  y1="0"  x2="14" y2="22" stroke="#1a0e08" stroke-width="0.3" opacity="0.5"/>
      <line x1="22" y1="0"  x2="30" y2="22" stroke="#1a0e08" stroke-width="0.3" opacity="0.5"/>
      <line x1="40" y1="0"  x2="48" y2="22" stroke="#1a0e08" stroke-width="0.3" opacity="0.5"/>
      <line x1="58" y1="0"  x2="66" y2="22" stroke="#1a0e08" stroke-width="0.3" opacity="0.5"/>
    </pattern>

    <!-- Bookcase silhouette (top, dim) -->
    <pattern id="v19_bookcase" patternUnits="userSpaceOnUse" width="40" height="30" x="0" y="20">
      <rect width="40" height="30" fill="#1a0e14" opacity="0.7"/>
      <rect x="0"  y="0" width="6" height="28" fill="#0f3a2a" opacity="0.5" rx="0.5"/>
      <rect x="7"  y="0" width="5" height="28" fill="#8a6a26" opacity="0.5" rx="0.5"/>
      <rect x="13" y="0" width="4" height="28" fill="#5a2010" opacity="0.5" rx="0.5"/>
      <rect x="18" y="0" width="6" height="28" fill="#4a2c1a" opacity="0.5" rx="0.5"/>
      <rect x="25" y="0" width="5" height="28" fill="#0f3a2a" opacity="0.5" rx="0.5"/>
      <rect x="31" y="0" width="4" height="28" fill="#3a2010" opacity="0.5" rx="0.5"/>
      <rect x="36" y="0" width="4" height="28" fill="#8a6a26" opacity="0.5" rx="0.5"/>
      <line x1="0" y1="29" x2="40" y2="29" stroke="#0a0a04" stroke-width="0.4"/>
    </pattern>

    <!-- Brass gradient -->
    <linearGradient id="v19_brass" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#e8c879"/>
      <stop offset="50%" stop-color="#c9a04e"/>
      <stop offset="100%" stop-color="#8a6a26"/>
    </linearGradient>
    <linearGradient id="v19_brass_h" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%"  stop-color="#8a6a26"/>
      <stop offset="50%" stop-color="#e8c879"/>
      <stop offset="100%" stop-color="#8a6a26"/>
    </linearGradient>

    <!-- Parchment page (cream with yellowed edge) -->
    <linearGradient id="v19_page" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#f3e9d2"/>
      <stop offset="80%" stop-color="#ede1c4"/>
      <stop offset="100%" stop-color="#c9a04e"/>
    </linearGradient>
    <linearGradient id="v19_page_dark" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#e8d8b8"/>
      <stop offset="80%" stop-color="#d4b88a"/>
      <stop offset="100%" stop-color="#8a6a26"/>
    </linearGradient>

    <!-- Gilt page edges -->
    <linearGradient id="v19_gilt" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"   stop-color="#8a6a26"/>
      <stop offset="50%"  stop-color="#ffd47a"/>
      <stop offset="100%" stop-color="#8a6a26"/>
    </linearGradient>

    <!-- Holographic disc (the "imagination field") -->
    <radialGradient id="v19_holo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%"  stop-color="#ffd47a" stop-opacity="0.45"/>
      <stop offset="40%" stop-color="#f0b54a" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#f0b54a" stop-opacity="0"/>
    </radialGradient>

    <!-- Banker's lamp glow (top-right) -->
    <radialGradient id="v19_lamp" cx="0.85" cy="0.18" r="0.55">
      <stop offset="0%"  stop-color="#ffd47a" stop-opacity="0.55"/>
      <stop offset="40%" stop-color="#f0b54a" stop-opacity="0.20"/>
      <stop offset="100%" stop-color="#f0b54a" stop-opacity="0"/>
    </radialGradient>

    <!-- Cool neon glow (left) -->
    <radialGradient id="v19_neon_l" cx="0.12" cy="0.4" r="0.4">
      <stop offset="0%"  stop-color="#5ddef0" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="#5ddef0" stop-opacity="0"/>
    </radialGradient>

    <!-- Vignette -->
    <radialGradient id="v19_vignette" cx="0.5" cy="0.5" r="0.7">
      <stop offset="60%" stop-color="#000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000" stop-opacity="0.5"/>
    </radialGradient>

    <!-- Reusable gear -->
    <symbol id="v19_gear" viewBox="-50 -50 100 100">
      <g fill="none" stroke="url(#v19_brass_h)" stroke-width="1.5">
        <circle r="38"/>
        <circle r="22"/>
        <circle r="8" fill="url(#v19_brass)"/>
        <g>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v19_brass)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v19_brass)" transform="rotate(30)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v19_brass)" transform="rotate(60)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v19_brass)" transform="rotate(90)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v19_brass)" transform="rotate(120)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v19_brass)" transform="rotate(150)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v19_brass)" transform="rotate(180)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v19_brass)" transform="rotate(210)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v19_brass)" transform="rotate(240)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v19_brass)" transform="rotate(270)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v19_brass)" transform="rotate(300)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v19_brass)" transform="rotate(330)"/>
        </g>
      </g>
    </symbol>

    <!-- Holographic glyph: glowing text symbol (reusable for floating story icons) -->
    <filter id="v19_glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="1.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- 1. Room interior -->
  <rect x="0" y="0" width="400" height="400" fill="url(#v19_room)"/>

  <!-- 2. Bookcase behind (top half, dim) -->
  <rect x="0" y="0" width="400" height="200" fill="url(#v19_bookcase)" opacity="0.55"/>

  <!-- 3. Walnut desk (lower third) -->
  <rect x="0" y="270" width="400" height="130" fill="url(#v19_desk)"/>

  <!-- 4. Cool neon (left) + banker's lamp (right) -->
  <rect x="0" y="0" width="400" height="400" fill="url(#v19_neon_l)"/>
  <rect x="0" y="0" width="400" height="400" fill="url(#v19_lamp)"/>

  <!-- 5. Two clockwork gears (corners) -->
  <g class="gear slow">
    <g transform="translate(56 70) scale(0.45)">
      <use href="#v19_gear"/>
    </g>
  </g>
  <g class="gear ccw">
    <g transform="translate(344 70) scale(0.4)">
      <use href="#v19_gear"/>
    </g>
  </g>

  <!-- 6. The book (focal point) -->
  <g transform="translate(200 240)">
    <!-- book shadow on the desk -->
    <ellipse cx="0" cy="58" rx="120" ry="6" fill="#000" opacity="0.45"/>

    <!-- 6a. Gilt (gold) page edges - the visible page-stack on the right -->
    <g>
      <path d="M 22 30 L 116 22 L 116 30 L 22 38 Z" fill="url(#v19_gilt)" opacity="0.85"/>
      <path d="M 22 30 L 116 22 L 116 30 L 22 38 Z" fill="none" stroke="url(#v19_brass_d)" stroke-width="0.3"/>
      <!-- additional page lines (very thin) -->
      <g stroke="#5a4a18" stroke-width="0.2" opacity="0.6">
        <line x1="22" y1="30" x2="116" y2="22"/>
        <line x1="22" y1="32" x2="116" y2="24"/>
        <line x1="22" y1="34" x2="116" y2="26"/>
        <line x1="22" y1="36" x2="116" y2="28"/>
      </g>
    </g>

    <!-- 6b. Left page (open, tilted slightly to suggest the book is laying flat) -->
    <!-- Page shape: parallelogram suggesting perspective -->
    <g>
      <!-- page base -->
      <path d="M -110 30 L -22 38 L -22 50 L -110 42 Z" fill="url(#v19_page)" stroke="#8a6a26" stroke-width="0.6"/>
      <!-- yellowed edge tint -->
      <path d="M -110 38 L -22 46 L -22 50 L -110 42 Z" fill="url(#v19_gilt)" opacity="0.5"/>
      <!-- printed text lines (visible body text in a Victorian serif) -->
      <g fill="#3a2a10">
        <!-- top heading line (slightly larger, ornate) -->
        <text x="-100" y="22" font-family="Cinzel,serif" font-size="6" font-weight="600" fill="#5a2010" letter-spacing="0.5">CHAPTER  ONE</text>
        <!-- paragraph lines as rects (so they don't depend on fonts) -->
        <g>
          <rect x="-100" y="26" width="60" height="0.8" fill="#3a2010"/>
          <rect x="-100" y="28" width="68" height="0.8" fill="#3a2010"/>
          <rect x="-100" y="30" width="58" height="0.8" fill="#3a2010"/>
          <rect x="-100" y="32" width="64" height="0.8" fill="#3a2010"/>
          <rect x="-100" y="34" width="50" height="0.8" fill="#3a2010"/>
        </g>
      </g>
      <!-- circuit lines (modern tech) threading the page margins -->
      <g stroke="#5ddef0" stroke-width="0.4" fill="none" opacity="0.55">
        <line x1="-104" y1="36" x2="-80" y2="38"/>
        <line x1="-72" y1="38" x2="-32" y2="40"/>
        <circle cx="-78" cy="38" r="0.8" fill="#5ddef0"/>
      </g>
    </g>

    <!-- 6c. Right page (open) -->
    <g>
      <!-- page base -->
      <path d="M 22 38 L 110 30 L 110 42 L 22 50 Z" fill="url(#v19_page)" stroke="#8a6a26" stroke-width="0.6"/>
      <!-- yellowed edge tint -->
      <path d="M 22 46 L 110 38 L 110 42 L 22 50 Z" fill="url(#v19_gilt)" opacity="0.5"/>
      <!-- printed text (Victorian serif) -->
      <g fill="#3a2a10">
        <text x="32" y="22" font-family="Cinzel,serif" font-size="6" font-weight="600" fill="#5a2010" letter-spacing="0.5">CHAPTER  ONE</text>
        <text x="32" y="14" font-family="Cinzel,serif" font-size="3.6" fill="#8a6a26" font-style="italic">~ continued ~</text>
        <g>
          <rect x="32" y="26" width="62" height="0.8" fill="#3a2010"/>
          <rect x="32" y="28" width="68" height="0.8" fill="#3a2010"/>
          <rect x="32" y="30" width="58" height="0.8" fill="#3a2010"/>
          <rect x="32" y="32" width="64" height="0.8" fill="#3a2010"/>
          <rect x="32" y="34" width="52" height="0.8" fill="#3a2010"/>
        </g>
      </g>
      <!-- circuit lines (magenta) -->
      <g stroke="#e85a8a" stroke-width="0.4" fill="none" opacity="0.55">
        <line x1="32" y1="36" x2="60" y2="38"/>
        <line x1="68" y1="38" x2="100" y2="40"/>
        <circle cx="62" cy="38" r="0.8" fill="#e85a8a"/>
      </g>
    </g>

    <!-- 6d. Spine (brass-bordered center gutter) -->
    <g>
      <path d="M -22 38 L 22 38 L 22 50 L -22 50 Z" fill="url(#v19_page_dark)" stroke="url(#v19_brass_h)" stroke-width="0.8"/>
      <line x1="0" y1="38" x2="0" y2="50" stroke="url(#v19_brass_h)" stroke-width="0.6"/>
    </g>

    <!-- 6e. Holographic disc floating above the book (the "imagination field") -->
    <ellipse cx="0" cy="-4" rx="78" ry="22" fill="url(#v19_holo)"/>
    <ellipse cx="0" cy="-4" rx="60" ry="14" fill="url(#v19_holo)" opacity="0.7"/>
    <ellipse cx="0" cy="-4" rx="100" ry="28" fill="none" stroke="url(#v19_brass_h)" stroke-width="0.3" opacity="0.4" stroke-dasharray="2 2"/>
    <ellipse cx="0" cy="-4" rx="80" ry="20" fill="none" stroke="url(#v19_brass_h)" stroke-width="0.3" opacity="0.4" stroke-dasharray="2 2"/>

    <!-- 6f. Holographic glyphs floating up from the book (story symbols) -->
    <g filter="url(#v19_glow)">
      <!-- crescent moon (mystery) - top center, larger -->
      <g transform="translate(0 -50)">
        <circle r="10" fill="#ffd47a"/>
        <circle cx="4" cy="-2" r="8" fill="#0a0f1c"/>
        <circle r="10" fill="none" stroke="url(#v19_brass_h)" stroke-width="0.4" opacity="0.7"/>
      </g>
      <!-- lightning bolt (action) - left -->
      <g transform="translate(-46 -36)">
        <path d="M -4 -8 L -8 0 L -2 0 L -6 8 L 4 -2 L -2 -2 Z" fill="#5ddef0"/>
      </g>
      <!-- heart (romance) - right -->
      <g transform="translate(46 -36)">
        <path d="M 0 4 C -6 -2 -8 -6 -4 -8 C -2 -9 0 -7 0 -5 C 0 -7 2 -9 4 -8 C 8 -6 6 -2 0 4 Z" fill="#e85a8a"/>
      </g>
      <!-- skull (horror) - top-left -->
      <g transform="translate(-72 -64)">
        <path d="M -3 -3 Q -3 -7 0 -7 Q 3 -7 3 -3 L 3 0 L 2 0 L 2 2 L 1 2 L 1 0 L 0 0 L -1 0 L -1 2 L -2 2 L -2 0 L -3 0 Z" fill="#c9a04e"/>
        <circle cx="-1.5" cy="-4" r="0.6" fill="#0a0f1c"/>
        <circle cx="1.5"  cy="-4" r="0.6" fill="#0a0f1c"/>
      </g>
      <!-- crown (fantasy) - top-right -->
      <g transform="translate(72 -64)">
        <path d="M -5 0 L -4 -4 L -2 -2 L 0 -5 L 2 -2 L 4 -4 L 5 0 Z M -5 0 L 5 0 L 5 1 L -5 1 Z" fill="#ffd47a"/>
      </g>
      <!-- rocket (sci-fi) - left side, lower -->
      <g transform="translate(-58 -16)">
        <path d="M 0 0 L 0 -8 L 3 -5 L 3 0 Z" fill="#5ddef0"/>
        <path d="M 0 0 L -2 1 L 3 1 Z" fill="#e85a8a"/>
      </g>
      <!-- compass (adventure) - right side, lower -->
      <g transform="translate(58 -16)">
        <circle r="5" fill="none" stroke="url(#v19_brass_h)" stroke-width="0.6"/>
        <path d="M 0 -4 L 1 0 L 0 4 L -1 0 Z" fill="#c44a3a"/>
        <circle r="0.5" fill="#0a0f1c"/>
      </g>
    </g>

    <!-- 6g. Sparkles rising from the page edges (the imagination spark) -->
    <g fill="#ffd47a" opacity="0.85">
      <circle cx="-72" cy="20" r="0.6"/>
      <circle cx="-58" cy="14" r="0.4"/>
      <circle cx="-44" cy="8"  r="0.6"/>
      <circle cx="-30" cy="2"  r="0.5"/>
      <circle cx="30"  cy="2"  r="0.5"/>
      <circle cx="44"  cy="8"  r="0.6"/>
      <circle cx="58"  cy="14" r="0.4"/>
      <circle cx="72"  cy="20" r="0.6"/>
    </g>
  </g>

  <!-- 7. Vignette to focus the eye on the book -->
  <rect x="0" y="0" width="400" height="400" fill="url(#v19_vignette)"/>

  <!-- 8. Ornate brass border + corner gems -->
  <g fill="none" stroke="url(#v19_brass_h)" stroke-width="1.2">
    <rect x="6" y="6" width="388" height="388" rx="4"/>
    <rect x="10" y="10" width="380" height="380" rx="2" stroke-width="0.4" opacity="0.6"/>
  </g>
  <g fill="url(#v19_brass)" stroke="#8a6a26" stroke-width="0.5">
    <circle cx="6"   cy="6"   r="3"/>
    <circle cx="394" cy="6"   r="3"/>
    <circle cx="6"   cy="394" r="3"/>
    <circle cx="394" cy="394" r="3"/>
  </g>

  <!-- 9. Title plate (subtle "PocketPlot Universe" inset at the bottom) -->
  <g transform="translate(200 372)">
    <rect x="-72" y="-8" width="144" height="16" fill="#0a0f1c" stroke="url(#v19_brass_h)" stroke-width="0.6" rx="2" opacity="0.7"/>
    <text x="0" y="3" font-family="Cinzel,serif" font-size="7" fill="url(#v19_brass_h)" text-anchor="middle" letter-spacing="2">POCKETPLOT  UNIVERSE</text>
  </g>
</svg>'''

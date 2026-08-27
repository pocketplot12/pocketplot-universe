"""
PocketPlot Universe - v20 hero: 'The Split Book'.

A literal split between two worlds in one book. The left page is
a 19th-century Victorian volume: cream parchment, hand-set Cinzel
serif text, a hand-drawn illustration (a crescent moon + stars,
representing the romantic literature of that era), gilt edges,
and a quill resting on the page. The right page is a futuristic
high-tech panel: deep-navy substrate, cyan + magenta circuit
lines as the 'text', glowing neon edge, holographic glyphs as
the 'marginalia', and a small holographic projection rising
from the page.

The two halves share a single spine in the center. The spine
itself is split: the left half is dark walnut with brass
corner-binding posts (the Victorian bookbinder's tool), the
right half is dark navy with a glowing cyan seam (the
futuristic binding's energy feed). They meet at the center
where the brass post meets the cyan glow.

The book sits on a Victorian walnut desk, framed by a brass
border. A banker's lamp glows from the top-right, a cool neon
glints from the left, and two clockwork gears (one brass, one
cyan) rotate in the top corners - the right one has its teeth
in a glowing neon outline.

This is the heart of the Tech-Victorian visual identity:
two eras meeting in one artifact.
"""

PORTAL_HERO_V20 = '''<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="An open book split down the middle: the left page is a 19th-century Victorian volume with cream parchment and serif text, the right page is a futuristic high-tech panel with glowing circuit lines and holographic glyphs">
  <defs>
    <!-- Room interior -->
    <linearGradient id="v20_room" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"   stop-color="#0a0f1c"/>
      <stop offset="35%"  stop-color="#0e1a2e"/>
      <stop offset="70%"  stop-color="#1a2440"/>
      <stop offset="100%" stop-color="#3a2010"/>
    </linearGradient>

    <!-- Walnut desk -->
    <pattern id="v20_desk" patternUnits="userSpaceOnUse" width="80" height="22" x="0" y="270">
      <rect width="80" height="22" fill="#3a2010"/>
      <line x1="0" y1="0"  x2="80" y2="0"  stroke="#1a0e08" stroke-width="0.5"/>
      <line x1="0" y1="22" x2="80" y2="22" stroke="#1a0e08" stroke-width="0.5"/>
      <line x1="6"  y1="0"  x2="14" y2="22" stroke="#1a0e08" stroke-width="0.3" opacity="0.5"/>
      <line x1="22" y1="0"  x2="30" y2="22" stroke="#1a0e08" stroke-width="0.3" opacity="0.5"/>
      <line x1="40" y1="0"  x2="48" y2="22" stroke="#1a0e08" stroke-width="0.3" opacity="0.5"/>
      <line x1="58" y1="0"  x2="66" y2="22" stroke="#1a0e08" stroke-width="0.3" opacity="0.5"/>
    </pattern>

    <!-- Bookcase silhouette behind (top, dim) -->
    <pattern id="v20_bookcase" patternUnits="userSpaceOnUse" width="40" height="30" x="0" y="20">
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

    <!-- Brass -->
    <linearGradient id="v20_brass" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#e8c879"/>
      <stop offset="50%" stop-color="#c9a04e"/>
      <stop offset="100%" stop-color="#8a6a26"/>
    </linearGradient>
    <linearGradient id="v20_brass_h" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%"  stop-color="#8a6a26"/>
      <stop offset="50%" stop-color="#e8c879"/>
      <stop offset="100%" stop-color="#8a6a26"/>
    </linearGradient>

    <!-- Cream parchment (Victorian page) -->
    <linearGradient id="v20_parchment" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#f3e9d2"/>
      <stop offset="80%" stop-color="#ede1c4"/>
      <stop offset="100%" stop-color="#c9a04e"/>
    </linearGradient>
    <linearGradient id="v20_parchment_dark" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#e8d8b8"/>
      <stop offset="80%" stop-color="#d4b88a"/>
      <stop offset="100%" stop-color="#8a6a26"/>
    </linearGradient>

    <!-- Futuristic page substrate (deep navy) -->
    <linearGradient id="v20_fut_page" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#0a1430"/>
      <stop offset="80%" stop-color="#0a0f1c"/>
      <stop offset="100%" stop-color="#1a0a14"/>
    </linearGradient>

    <!-- Gilt page edges -->
    <linearGradient id="v20_gilt" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"   stop-color="#8a6a26"/>
      <stop offset="50%"  stop-color="#ffd47a"/>
      <stop offset="100%" stop-color="#8a6a26"/>
    </linearGradient>

    <!-- Holographic field (above the right page) -->
    <radialGradient id="v20_holo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%"  stop-color="#5ddef0" stop-opacity="0.45"/>
      <stop offset="50%" stop-color="#5ddef0" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#5ddef0" stop-opacity="0"/>
    </radialGradient>

    <!-- Amber ink-quill smoke (above the left page) -->
    <radialGradient id="v20_amber_field" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%"  stop-color="#ffd47a" stop-opacity="0.40"/>
      <stop offset="50%" stop-color="#f0b54a" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="#f0b54a" stop-opacity="0"/>
    </radialGradient>

    <!-- Banker's lamp glow (top-right) -->
    <radialGradient id="v20_lamp" cx="0.85" cy="0.18" r="0.55">
      <stop offset="0%"  stop-color="#ffd47a" stop-opacity="0.55"/>
      <stop offset="40%" stop-color="#f0b54a" stop-opacity="0.20"/>
      <stop offset="100%" stop-color="#f0b54a" stop-opacity="0"/>
    </radialGradient>

    <!-- Cool neon (left) -->
    <radialGradient id="v20_neon_l" cx="0.12" cy="0.4" r="0.4">
      <stop offset="0%"  stop-color="#5ddef0" stop-opacity="0.30"/>
      <stop offset="100%" stop-color="#5ddef0" stop-opacity="0"/>
    </radialGradient>

    <!-- Right-side neon (magenta, near the futuristic page) -->
    <radialGradient id="v20_neon_r" cx="0.88" cy="0.45" r="0.3">
      <stop offset="0%"  stop-color="#e85a8a" stop-opacity="0.32"/>
      <stop offset="100%" stop-color="#e85a8a" stop-opacity="0"/>
    </radialGradient>

    <!-- Vignette -->
    <radialGradient id="v20_vignette" cx="0.5" cy="0.5" r="0.7">
      <stop offset="60%" stop-color="#000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000" stop-opacity="0.5"/>
    </radialGradient>

    <!-- Reusable gear (brass) -->
    <symbol id="v20_gear_brass" viewBox="-50 -50 100 100">
      <g fill="none" stroke="url(#v20_brass_h)" stroke-width="1.5">
        <circle r="38"/>
        <circle r="22"/>
        <circle r="8" fill="url(#v20_brass)"/>
        <g>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v20_brass)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v20_brass)" transform="rotate(30)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v20_brass)" transform="rotate(60)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v20_brass)" transform="rotate(90)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v20_brass)" transform="rotate(120)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v20_brass)" transform="rotate(150)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v20_brass)" transform="rotate(180)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v20_brass)" transform="rotate(210)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v20_brass)" transform="rotate(240)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v20_brass)" transform="rotate(270)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v20_brass)" transform="rotate(300)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="url(#v20_brass)" transform="rotate(330)"/>
        </g>
      </g>
    </symbol>

    <!-- Reusable gear (cyan) -->
    <symbol id="v20_gear_cyan" viewBox="-50 -50 100 100">
      <g fill="none" stroke="#5ddef0" stroke-width="1.5">
        <circle r="38"/>
        <circle r="22"/>
        <circle r="8" fill="#5ddef0"/>
        <g>
          <rect x="-4" y="-44" width="8" height="8" fill="#5ddef0"/>
          <rect x="-4" y="-44" width="8" height="8" fill="#5ddef0" transform="rotate(30)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="#5ddef0" transform="rotate(60)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="#5ddef0" transform="rotate(90)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="#5ddef0" transform="rotate(120)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="#5ddef0" transform="rotate(150)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="#5ddef0" transform="rotate(180)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="#5ddef0" transform="rotate(210)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="#5ddef0" transform="rotate(240)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="#5ddef0" transform="rotate(270)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="#5ddef0" transform="rotate(300)"/>
          <rect x="-4" y="-44" width="8" height="8" fill="#5ddef0" transform="rotate(330)"/>
        </g>
      </g>
    </symbol>

    <!-- Soft glow filter for holographic glyphs -->
    <filter id="v20_glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="1.2" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- 1. Room interior -->
  <rect x="0" y="0" width="400" height="400" fill="url(#v20_room)"/>

  <!-- 2. Bookcase behind (top, dim) -->
  <rect x="0" y="0" width="400" height="200" fill="url(#v20_bookcase)" opacity="0.55"/>

  <!-- 3. Walnut desk (lower third) -->
  <rect x="0" y="270" width="400" height="130" fill="url(#v20_desk)"/>

  <!-- 4. Cool neon (left) + banker's lamp (right) + magenta (right) -->
  <rect x="0" y="0" width="400" height="400" fill="url(#v20_neon_l)"/>
  <rect x="0" y="0" width="400" height="400" fill="url(#v20_lamp)"/>
  <rect x="0" y="0" width="400" height="400" fill="url(#v20_neon_r)"/>

  <!-- 5. Two gears - brass on the left, cyan on the right -->
  <g class="gear slow">
    <g transform="translate(56 70) scale(0.45)">
      <use href="#v20_gear_brass"/>
    </g>
  </g>
  <g class="gear ccw">
    <g transform="translate(344 70) scale(0.4)">
      <use href="#v20_gear_cyan"/>
    </g>
  </g>

  <!-- 6. The split book -->
  <g transform="translate(200 240)">
    <!-- shadow under the book -->
    <ellipse cx="0" cy="62" rx="135" ry="6" fill="#000" opacity="0.5"/>

    <!-- ============================================== -->
    <!-- LEFT PAGE: 19TH-CENTURY VICTORIAN            -->
    <!-- ============================================== -->
    <g>
      <!-- left page base (cream parchment) -->
      <path d="M -132 30 L -22 38 L -22 50 L -132 42 Z" fill="url(#v20_parchment)" stroke="url(#v20_brass_h)" stroke-width="0.8"/>
      <!-- yellowed gilt edge along the bottom -->
      <path d="M -132 38 L -22 46 L -22 50 L -132 42 Z" fill="url(#v20_gilt)" opacity="0.55"/>
      <!-- page-stack indicator: thin horizontal lines along the bottom -->
      <g stroke="#5a4a18" stroke-width="0.2" opacity="0.6">
        <line x1="-132" y1="38" x2="-22" y2="46"/>
        <line x1="-132" y1="40" x2="-22" y2="48"/>
      </g>
      <!-- inner page border (ornamental frame) -->
      <path d="M -126 22 L -28 30 L -28 36 L -126 28 Z" fill="none" stroke="url(#v20_brass_h)" stroke-width="0.3" opacity="0.5"/>

      <!-- CHAPTER header (Victorian serif) -->
      <text x="-122" y="14" font-family="Cinzel,serif" font-size="6" font-weight="600" fill="#5a2010" letter-spacing="1.5">CHAPTER  ONE</text>
      <!-- decorative rule under the chapter header -->
      <line x1="-122" y1="16" x2="-30" y2="18" stroke="url(#v20_brass_h)" stroke-width="0.4" opacity="0.7"/>
      <line x1="-122" y1="17" x2="-50" y2="19" stroke="url(#v20_brass_h)" stroke-width="0.2" opacity="0.5"/>

      <!-- paragraph text lines (printed body) -->
      <g fill="#3a2010">
        <rect x="-120" y="22" width="86" height="0.8"/>
        <rect x="-120" y="24" width="92" height="0.8"/>
        <rect x="-120" y="26" width="84" height="0.8"/>
        <rect x="-120" y="28" width="88" height="0.8"/>
        <rect x="-120" y="30" width="78" height="0.8"/>
        <rect x="-120" y="32" width="86" height="0.8"/>
        <rect x="-120" y="34" width="68" height="0.8"/>
      </g>

      <!-- hand-drawn illustration: a crescent moon + stars -->
      <g transform="translate(-72 30)">
        <!-- crescent moon (hand-drawn, not perfect circle) -->
        <path d="M -2 0 Q -2 -5 2 -5 Q 6 -5 6 0 Q 6 5 2 5 Q -2 5 -2 0 Z" fill="none" stroke="#3a2010" stroke-width="0.6"/>
        <path d="M 0 0 Q 0 -3 3 -3 Q 6 -3 6 0 Q 6 3 3 3 Q 0 3 0 0 Z" fill="#3a2010" opacity="0.15"/>
        <!-- a few stars (4-pointed) -->
        <g fill="#3a2010">
          <path d="M -10 -3 L -9 -1 L -7 0 L -9 1 L -10 3 L -11 1 L -13 0 L -11 -1 Z"/>
          <path d="M 12 -6 L 12.5 -5 L 13.5 -4.5 L 12.5 -4 L 12 -3 L 11.5 -4 L 10.5 -4.5 L 11.5 -5 Z"/>
          <path d="M -4 6 L -3.5 7 L -2.5 7.5 L -3.5 8 L -4 9 L -4.5 8 L -5.5 7.5 L -4.5 7 Z"/>
        </g>
        <!-- a small flourish (decorative typographic ornament) -->
        <path d="M 8 4 Q 10 2 12 4 Q 10 5 8 4" fill="none" stroke="#3a2010" stroke-width="0.4"/>
      </g>

      <!-- ink well or quill mark in the margin (bottom right of the page) -->
      <g transform="translate(-50 38)">
        <!-- a small ink splatter -->
        <circle r="1.4" fill="#3a2010" opacity="0.7"/>
        <circle cx="2" cy="-0.5" r="0.6" fill="#3a2010" opacity="0.5"/>
        <circle cx="-1.5" cy="1.2" r="0.4" fill="#3a2010" opacity="0.5"/>
      </g>

      <!-- Victorian marginalia: page number "I" in Roman numerals (top right of left page) -->
      <text x="-30" y="14" font-family="Cinzel,serif" font-size="5" fill="#8a6a26" text-anchor="end" font-style="italic">I</text>
    </g>

    <!-- LEFT PAGE-EDGE: visible page-stack on the left (the 19th-century volume's thickness) -->
    <g>
      <path d="M -132 30 L -22 38 L -22 46 L -132 38 Z" fill="url(#v20_gilt)" opacity="0.85"/>
      <path d="M -132 30 L -22 38 L -22 46 L -132 38 Z" fill="none" stroke="#5a4a18" stroke-width="0.3"/>
      <g stroke="#3a2010" stroke-width="0.2" opacity="0.7">
        <line x1="-132" y1="30" x2="-22" y2="38"/>
        <line x1="-132" y1="32" x2="-22" y2="40"/>
        <line x1="-132" y1="34" x2="-22" y2="42"/>
        <line x1="-132" y1="36" x2="-22" y2="44"/>
      </g>
    </g>

    <!-- ============================================== -->
    <!-- RIGHT PAGE: FUTURISTIC HIGH-TECH             -->
    <!-- ============================================== -->
    <g>
      <!-- right page base (deep navy substrate) -->
      <path d="M 22 38 L 132 30 L 132 42 L 22 50 Z" fill="url(#v20_fut_page)" stroke="#5ddef0" stroke-width="0.8"/>
      <!-- glowing edge (neon underlight along the bottom) -->
      <path d="M 22 46 L 132 38 L 132 42 L 22 50 Z" fill="#5ddef0" opacity="0.45"/>
      <path d="M 22 46 L 132 38 L 132 42 L 22 50 Z" fill="none" stroke="#5ddef0" stroke-width="0.5"/>
      <!-- inner tech frame (subtle inset) -->
      <path d="M 28 30 L 126 22 L 126 36 L 28 28 Z" fill="none" stroke="#5ddef0" stroke-width="0.3" opacity="0.5"/>

      <!-- HEADER: data block at the top (in lieu of a chapter header) -->
      <g>
        <text x="32" y="14" font-family="'JetBrains Mono',monospace" font-size="4" fill="#5ddef0" letter-spacing="0.5">// CH.01 0x01</text>
        <text x="32" y="18" font-family="'JetBrains Mono',monospace" font-size="3.6" fill="#5ddef0" opacity="0.7">// story://init</text>
        <line x1="32" y1="20" x2="120" y2="22" stroke="#5ddef0" stroke-width="0.4" opacity="0.6"/>
        <line x1="32" y1="21" x2="80"  y2="23" stroke="#e85a8a" stroke-width="0.3" opacity="0.5"/>
      </g>

      <!-- 'Text' rendered as circuit-line glyphs (cyan + magenta, jagged) -->
      <g stroke="#5ddef0" stroke-width="0.7" fill="none" opacity="0.95">
        <path d="M 32 26 L 120 28"/>
        <path d="M 32 28 L 100 30"/>
        <path d="M 32 30 L 116 32"/>
        <path d="M 32 32 L 92 34"/>
      </g>
      <g stroke="#e85a8a" stroke-width="0.7" fill="none" opacity="0.85">
        <path d="M 38 34 L 122 36"/>
        <path d="M 60 35 L 110 37"/>
      </g>
      <!-- node dots -->
      <g fill="#5ddef0">
        <circle cx="32" cy="26" r="0.8"/>
        <circle cx="120" cy="28" r="0.8"/>
        <circle cx="32" cy="32" r="0.8"/>
        <circle cx="92" cy="34" r="0.8"/>
      </g>
      <g fill="#e85a8a">
        <circle cx="60" cy="35" r="0.8"/>
        <circle cx="110" cy="37" r="0.8"/>
      </g>

      <!-- holographic projection: a small symbol rising from the page -->
      <g transform="translate(80 26)" filter="url(#v20_glow)">
        <circle r="3.5" fill="none" stroke="#5ddef0" stroke-width="0.6"/>
        <circle r="1.5" fill="#5ddef0"/>
      </g>

      <!-- data readouts in the bottom-right (instead of a marginalia illustration) -->
      <g transform="translate(116 38)" font-family="'JetBrains Mono',monospace" font-size="3" fill="#5ddef0" opacity="0.7" text-anchor="end">
        <text x="0" y="0">78°</text>
        <text x="0" y="3.5">14:02</text>
      </g>

      <!-- small tech annotation in the top-right corner -->
      <text x="124" y="14" font-family="'JetBrains Mono',monospace" font-size="4" fill="#e85a8a" text-anchor="end" letter-spacing="0.5">P.01</text>
    </g>

    <!-- RIGHT PAGE-EDGE: visible tech substrate edge (the futuristic volume's thickness) -->
    <g>
      <path d="M 22 38 L 132 30 L 132 38 L 22 46 Z" fill="#0a1430" opacity="0.95"/>
      <path d="M 22 38 L 132 30 L 132 38 L 22 46 Z" fill="none" stroke="#5ddef0" stroke-width="0.4"/>
      <!-- thin cyan glow lines (page-stack as data-stream) -->
      <g stroke="#5ddef0" stroke-width="0.3" opacity="0.7">
        <line x1="22" y1="40" x2="132" y2="32"/>
        <line x1="22" y1="42" x2="132" y2="34"/>
        <line x1="22" y1="44" x2="132" y2="36"/>
      </g>
    </g>

    <!-- ============================================== -->
    <!-- SPINE: THE LITERAL SPLIT                      -->
    <!-- ============================================== -->
    <g>
      <!-- spine base (parchment) -->
      <path d="M -22 38 L 22 38 L 22 50 L -22 50 Z" fill="url(#v20_parchment_dark)"/>
      <!-- spine split: left half (Victorian), right half (futuristic) -->
      <!-- left half of spine: dark walnut with brass corner-binding posts -->
      <rect x="-22" y="38" width="11" height="12" fill="#3a2010" stroke="url(#v20_brass_h)" stroke-width="0.5"/>
      <!-- right half of spine: dark navy with glowing cyan seam -->
      <rect x="0" y="38" width="22" height="12" fill="#0a1430" stroke="#5ddef0" stroke-width="0.5"/>
      <!-- the meeting point: a brass post on the Victorian side touches a cyan glow on the futuristic side -->
      <line x1="-11" y1="38" x2="-11" y2="50" stroke="url(#v20_brass_h)" stroke-width="1.2"/>
      <line x1="0"   y1="38" x2="0"   y2="50" stroke="#5ddef0" stroke-width="1.2"/>
      <!-- brass binding post (left) -->
      <rect x="-13" y="36" width="2" height="2" fill="url(#v20_brass)"/>
      <rect x="-13" y="48" width="2" height="2" fill="url(#v20_brass)"/>
      <!-- cyan terminal node (right) -->
      <circle cx="2" cy="37" r="1" fill="#5ddef0"/>
      <circle cx="2" cy="49" r="1" fill="#5ddef0"/>
      <!-- the center seam (where the two eras meet) -->
      <line x1="-11" y1="38" x2="0" y2="38" stroke="#5a4a18" stroke-width="0.4" opacity="0.6"/>
      <line x1="-11" y1="50" x2="0" y2="50" stroke="#5a4a18" stroke-width="0.4" opacity="0.6"/>
    </g>

    <!-- ============================================== -->
    <!-- ABOVE THE BOOK: two emerging fields           -->
    <!-- ============================================== -->
    <!-- LEFT: amber ink-quill field (Victorian) -->
    <ellipse cx="-50" cy="-12" rx="68" ry="22" fill="url(#v20_amber_field)"/>
    <ellipse cx="-50" cy="-12" rx="40" ry="12" fill="url(#v20_amber_field)" opacity="0.6"/>

    <!-- RIGHT: cyan holographic field (futuristic) -->
    <ellipse cx="50" cy="-12" rx="68" ry="22" fill="url(#v20_holo)"/>
    <ellipse cx="50" cy="-12" rx="40" ry="12" fill="url(#v20_holo)" opacity="0.6"/>

    <!-- LEFT: quill + ink (rising from the left page) -->
    <g transform="translate(-72 -28) rotate(-25)">
      <!-- quill body -->
      <path d="M 0 0 L 0 -22 Q 2 -22 2 -20 L 2 0 Z" fill="#f3e9d2" stroke="#5a4a18" stroke-width="0.4"/>
      <!-- feathered plume -->
      <path d="M 0 -22 Q -3 -28 -6 -34 Q -4 -36 -2 -32 Q 0 -28 2 -22 Z" fill="#5a4a18" opacity="0.7"/>
      <path d="M 0 -22 Q 3 -28 6 -34 Q 4 -36 2 -32 Q 0 -28 -2 -22 Z" fill="#5a4a18" opacity="0.5"/>
      <!-- brass nib -->
      <path d="M -1 0 L 1 0 L 0 4 Z" fill="url(#v20_brass)"/>
    </g>
    <!-- ink drops rising from the left page -->
    <g fill="#3a2010" opacity="0.7">
      <circle cx="-44" cy="-2" r="0.6"/>
      <circle cx="-58" cy="-12" r="0.5"/>
      <circle cx="-66" cy="-22" r="0.4"/>
    </g>

    <!-- RIGHT: holographic symbols (rising from the right page) -->
    <g filter="url(#v20_glow)">
      <!-- a data orb (small) -->
      <g transform="translate(70 -30)">
        <circle r="4" fill="none" stroke="#5ddef0" stroke-width="0.5"/>
        <circle r="2" fill="#5ddef0"/>
        <circle cx="0" cy="0" r="6" fill="none" stroke="#5ddef0" stroke-width="0.3" opacity="0.5"/>
      </g>
      <!-- a small bracket symbol -->
      <g transform="translate(50 -50)">
        <path d="M -3 -3 L 0 -3 L 0 3 L -3 3" fill="none" stroke="#e85a8a" stroke-width="0.6"/>
        <path d="M 3 -3 L 6 -3 L 6 3 L 3 3" fill="none" stroke="#e85a8a" stroke-width="0.6"/>
      </g>
    </g>

    <!-- Sparkles on the right (the data stream) -->
    <g fill="#5ddef0" opacity="0.85">
      <circle cx="44" cy="0" r="0.6"/>
      <circle cx="56" cy="-8" r="0.5"/>
      <circle cx="68" cy="-16" r="0.6"/>
      <circle cx="80" cy="-22" r="0.5"/>
    </g>
    <!-- Sparkles on the left (ink quill drops) -->
    <g fill="#3a2010" opacity="0.6">
      <circle cx="-44" cy="0" r="0.5"/>
      <circle cx="-58" cy="-8" r="0.4"/>
      <circle cx="-66" cy="-18" r="0.4"/>
    </g>
  </g>

  <!-- 7. Vignette -->
  <rect x="0" y="0" width="400" height="400" fill="url(#v20_vignette)"/>

  <!-- 8. Brass border + corner gems -->
  <g fill="none" stroke="url(#v20_brass_h)" stroke-width="1.2">
    <rect x="6" y="6" width="388" height="388" rx="4"/>
    <rect x="10" y="10" width="380" height="380" rx="2" stroke-width="0.4" opacity="0.6"/>
  </g>
  <g fill="url(#v20_brass)" stroke="#8a6a26" stroke-width="0.5">
    <circle cx="6"   cy="6"   r="3"/>
    <circle cx="394" cy="6"   r="3"/>
    <circle cx="6"   cy="394" r="3"/>
    <circle cx="394" cy="394" r="3"/>
  </g>
  <!-- cyan accent on the right corners (tech detail) -->
  <g fill="#5ddef0" opacity="0.6">
    <circle cx="394" cy="6"   r="1"/>
    <circle cx="394" cy="394" r="1"/>
  </g>

  <!-- 9. Title plate -->
  <g transform="translate(200 372)">
    <rect x="-72" y="-8" width="144" height="16" fill="#0a0f1c" stroke="url(#v20_brass_h)" stroke-width="0.6" rx="2" opacity="0.7"/>
    <text x="0" y="3" font-family="Cinzel,serif" font-size="7" fill="url(#v20_brass_h)" text-anchor="middle" letter-spacing="2">POCKETPLOT  UNIVERSE</text>
  </g>
</svg>'''

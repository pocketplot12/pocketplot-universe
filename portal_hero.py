"""
PocketPlot Universe - v17 'Portal to Stories' hero SVG.

A cinematic scene: a giant open book floats in the lower foreground.
Its pages form a glowing platform. Above the book, a vast cosmic
interior unfolds - stars, a crescent moon, three glowing doorways, a
writing quill orbiting, faint writing instruments floating in space.
The mood is "unlimited creative potential" - cinematic, dreamlike,
concept-art quality.
"""
PORTAL_HERO_SVG = '''<svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet" role="img" aria-label="A glowing book opening to a universe of stories">
  <defs>
    <!-- Cosmic interior gradient: deep navy at top, warm violet-plum,
         then warm horizon near the book -->
    <linearGradient id="ph_sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#040810"/>
      <stop offset="40%" stop-color="#0e1a2e"/>
      <stop offset="65%" stop-color="#1f1538"/>
      <stop offset="85%" stop-color="#5a2a4a"/>
      <stop offset="100%" stop-color="#c8764a"/>
    </linearGradient>
    <!-- Soft glow halo where the book opens -->
    <radialGradient id="ph_book_glow" cx="0.5" cy="0.85" r="0.55">
      <stop offset="0%" stop-color="#fff3c4" stop-opacity=".55"/>
      <stop offset="60%" stop-color="#e6c879" stop-opacity=".18"/>
      <stop offset="100%" stop-color="#e6c879" stop-opacity="0"/>
    </radialGradient>
    <!-- Book page glow -->
    <linearGradient id="ph_page" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#fff8d8"/>
      <stop offset="100%" stop-color="#e6c879"/>
    </linearGradient>
    <!-- Book cover dark navy with gold trim -->
    <linearGradient id="ph_cover" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#1f3460"/>
      <stop offset="100%" stop-color="#0e1a2e"/>
    </linearGradient>
    <!-- Moon halo -->
    <radialGradient id="ph_moon_halo1" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="#f8eccb" stop-opacity=".35"/>
      <stop offset="100%" stop-color="#f8eccb" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="ph_moon_halo2" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="#e6c879" stop-opacity=".14"/>
      <stop offset="100%" stop-color="#e6c879" stop-opacity="0"/>
    </radialGradient>
    <!-- Crescent moon -->
    <radialGradient id="ph_moon_core" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="#fff8d8"/>
      <stop offset="80%" stop-color="#f0d8a4"/>
      <stop offset="100%" stop-color="#b88f48"/>
    </radialGradient>
    <!-- Doorway glows (cyan / warm / rose) -->
    <radialGradient id="ph_door_cyan" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="#a8f0ff" stop-opacity=".95"/>
      <stop offset="100%" stop-color="#a8f0ff" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="ph_door_warm" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="#fff3c4" stop-opacity=".95"/>
      <stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="ph_door_rose" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="#f8c8d4" stop-opacity=".95"/>
      <stop offset="100%" stop-color="#f8c8d4" stop-opacity="0"/>
    </radialGradient>
    <!-- Nebula swirls -->
    <radialGradient id="ph_nebula1" cx="0.2" cy="0.2" r="0.55">
      <stop offset="0%" stop-color="#c46a8a" stop-opacity=".45"/>
      <stop offset="40%" stop-color="#5c3a6a" stop-opacity=".22"/>
      <stop offset="100%" stop-color="#0e1a2e" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="ph_nebula2" cx="0.78" cy="0.30" r="0.42">
      <stop offset="0%" stop-color="#4470a8" stop-opacity=".4"/>
      <stop offset="50%" stop-color="#1a2a44" stop-opacity=".18"/>
      <stop offset="100%" stop-color="#0e1a2e" stop-opacity="0"/>
    </radialGradient>
    <!-- Atmospheric haze near the book -->
    <radialGradient id="ph_atm" cx="0.5" cy="0.55" r="0.6">
      <stop offset="0%" stop-color="#c8764a" stop-opacity=".22"/>
      <stop offset="100%" stop-color="#0e1a2e" stop-opacity="0"/>
    </radialGradient>
    <!-- Floating star halo (used for the quill) -->
    <radialGradient id="ph_star" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="#fff" stop-opacity="1"/>
      <stop offset="100%" stop-color="#fff" stop-opacity="0"/>
    </radialGradient>
    <!-- Vignette -->
    <radialGradient id="ph_vignette" cx="0.5" cy="0.5" r="0.7">
      <stop offset="50%" stop-color="#0e1a2e" stop-opacity="0"/>
      <stop offset="100%" stop-color="#040810" stop-opacity=".55"/>
    </radialGradient>
  </defs>

  <!-- 1. Cosmic interior background -->
  <rect x="0" y="0" width="400" height="400" fill="url(#ph_sky)"/>

  <!-- 2. Nebulae (galaxy swirls) -->
  <rect x="0" y="0" width="400" height="280" fill="url(#ph_nebula1)"/>
  <rect x="0" y="0" width="400" height="280" fill="url(#ph_nebula2)"/>

  <!-- 3. Starfield - dense, with key-stars and cross flares -->
  <g fill="#f8eccb">
    <g transform="translate(60,40)">
      <circle r="2.4" fill="#fff8d8"/>
      <path d="M -16 0 L 16 0 M 0 -16 L 0 16" stroke="#fff8d8" stroke-width="1" stroke-linecap="round" opacity=".9"/>
    </g>
    <g transform="translate(150,20)">
      <circle r="2" fill="#fff8d8"/>
      <path d="M -14 0 L 14 0 M 0 -14 L 0 14" stroke="#fff8d8" stroke-width=".8" stroke-linecap="round" opacity=".85"/>
    </g>
    <g transform="translate(248,42)">
      <circle r="2.2" fill="#fff8d8"/>
      <path d="M -15 0 L 15 0 M 0 -15 L 0 15" stroke="#fff8d8" stroke-width=".9" stroke-linecap="round" opacity=".88"/>
    </g>
    <g transform="translate(330,18)">
      <circle r="1.8" fill="#fff8d8"/>
      <path d="M -12 0 L 12 0 M 0 -12 L 0 12" stroke="#fff8d8" stroke-width=".7" stroke-linecap="round" opacity=".78"/>
    </g>
    <g transform="translate(370,80)">
      <circle r="1.6" fill="#a8d4ff"/>
      <path d="M -10 0 L 10 0 M 0 -10 L 0 10" stroke="#a8d4ff" stroke-width=".6" stroke-linecap="round" opacity=".7"/>
    </g>
    <g transform="translate(28,110)">
      <circle r="1.6" fill="#a8d4ff"/>
      <path d="M -10 0 L 10 0 M 0 -10 L 0 10" stroke="#a8d4ff" stroke-width=".6" stroke-linecap="round" opacity=".7"/>
    </g>
    <!-- Medium stars -->
    <circle cx="100" cy="68" r="1.0" opacity=".75"/>
    <circle cx="180" cy="84" r="0.9" opacity=".7"/>
    <circle cx="208" cy="62" r="1.0" opacity=".75"/>
    <circle cx="284" cy="78" r="0.9" opacity=".7"/>
    <circle cx="320" cy="100" r="0.9" opacity=".7"/>
    <circle cx="368" cy="138" r="0.9" opacity=".7"/>
    <circle cx="42" cy="148" r="0.9" opacity=".7"/>
    <circle cx="86" cy="160" r="0.7" opacity=".6"/>
    <circle cx="170" cy="148" r="0.7" opacity=".6"/>
    <circle cx="252" cy="158" r="0.7" opacity=".6"/>
    <circle cx="306" cy="142" r="0.7" opacity=".6"/>
    <circle cx="20" cy="180" r="0.6" opacity=".55"/>
    <circle cx="120" cy="172" r="0.6" opacity=".55"/>
    <circle cx="226" cy="180" r="0.5" opacity=".5"/>
    <circle cx="290" cy="178" r="0.6" opacity=".55"/>
    <circle cx="350" cy="186" r="0.5" opacity=".5"/>
    <!-- Dust -->
    <circle cx="48" cy="20" r=".3" opacity=".4"/>
    <circle cx="80" cy="50" r=".3" opacity=".4"/>
    <circle cx="124" cy="80" r=".3" opacity=".4"/>
    <circle cx="216" cy="20" r=".3" opacity=".4"/>
    <circle cx="290" cy="60" r=".3" opacity=".4"/>
    <circle cx="380" cy="60" r=".3" opacity=".4"/>
    <circle cx="6" cy="100" r=".3" opacity=".4"/>
    <circle cx="160" cy="116" r=".3" opacity=".4"/>
  </g>

  <!-- 4. Crescent moon - upper-right -->
  <circle cx="320" cy="100" r="120" fill="url(#ph_moon_halo2)"/>
  <circle cx="320" cy="100" r="78" fill="url(#ph_moon_halo1)"/>
  <circle cx="320" cy="100" r="32" fill="url(#ph_moon_core)"/>
  <!-- Crescent shadow -->
  <circle cx="332" cy="94" r="30" fill="#0e1a2e"/>
  <!-- Craters -->
  <ellipse cx="310" cy="94" rx="3" ry="2" fill="#caa858" opacity=".35"/>
  <ellipse cx="324" cy="106" rx="2.5" ry="2" fill="#caa858" opacity=".3"/>

  <!-- 5. Three doorways (small, glowing) - representing the genre choices -->
  <circle cx="80"  cy="220" r="36" fill="url(#ph_door_warm)" opacity=".7"/>
  <circle cx="200" cy="206" r="40" fill="url(#ph_door_cyan)" opacity=".75"/>
  <circle cx="320" cy="220" r="36" fill="url(#ph_door_rose)" opacity=".7"/>
  <g transform="translate(80,224)">
    <path d="M -10 18 L -10 -8 Q -10 -16 0 -16 Q 10 -16 10 -8 L 10 18 Z" fill="#0a0a14" stroke="#e6c879" stroke-width="1.2"/>
    <rect x="-2" y="-2" width="4" height="8" fill="#e6c879"/>
  </g>
  <g transform="translate(200,210)">
    <path d="M -8 22 L -8 -6 L 0 -14 L 8 -6 L 8 22 Z" fill="#070318" stroke="#44f0ff" stroke-width="1.2"/>
    <line x1="0" y1="-14" x2="0" y2="-22" stroke="#44f0ff" stroke-width="1"/>
    <circle cx="0" cy="-24" r="1.5" fill="#ff3a8a"/>
  </g>
  <g transform="translate(320,224)">
    <line x1="-10" y1="-14" x2="-10" y2="20" stroke="#3a1a2a" stroke-width="2"/>
    <circle cx="-10" cy="-18" r="3" fill="#f3a4b8"/>
    <rect x="-6" y="-2" width="6" height="22" fill="#0a0a14" stroke="#f3a4b8" stroke-width="1"/>
  </g>

  <!-- 6. Floating writing instruments (cosmic interior) -->
  <!-- A quill orbiting the upper-left -->
  <g transform="translate(120,148) rotate(-30)">
    <line x1="0" y1="0" x2="32" y2="0" stroke="#e6c879" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M 32 0 q -8 -10 -18 -10 q 6 8 18 10 z" fill="url(#ph_page)" opacity=".85"/>
    <circle cx="0" cy="0" r="2" fill="#e6c879"/>
  </g>
  <!-- A fountain pen nib floating right -->
  <g transform="translate(280,180) rotate(40)">
    <line x1="0" y1="0" x2="20" y2="0" stroke="#fff3c4" stroke-width="1.4" stroke-linecap="round"/>
    <path d="M 0 0 L -10 -4 L -10 4 Z" fill="#15243f" stroke="#fff3c4" stroke-width=".8"/>
    <line x1="-2" y1="0" x2="-8" y2="0" stroke="#fff3c4" stroke-width=".5"/>
  </g>
  <!-- An ink bottle -->
  <g transform="translate(70,260)">
    <ellipse cx="0" cy="0" rx="6" ry="1.5" fill="#000" opacity=".3"/>
    <rect x="-5" y="-9" width="10" height="9" fill="#15243f" stroke="#e6c879" stroke-width=".8"/>
    <rect x="-3" y="-12" width="6" height="3" fill="#1a1428" stroke="#e6c879" stroke-width=".5"/>
    <circle cx="0" cy="-13" r="1" fill="#e6c879"/>
  </g>
  <!-- A page corner with writing on it -->
  <g transform="translate(330,278) rotate(-12)">
    <rect x="-12" y="-12" width="24" height="24" fill="url(#ph_page)" stroke="#c89e54" stroke-width=".6"/>
    <line x1="-8" y1="-6" x2="8" y2="-6" stroke="#c89e54" stroke-width=".4"/>
    <line x1="-8" y1="-2" x2="8" y2="-2" stroke="#c89e54" stroke-width=".4"/>
    <line x1="-8" y1="2"  x2="6" y2="2"  stroke="#c89e54" stroke-width=".4"/>
    <line x1="-8" y1="6"  x2="8" y2="6"  stroke="#c89e54" stroke-width=".4"/>
  </g>

  <!-- 7. The GIANT OPEN BOOK (foreground) -->
  <!-- Glow behind the book -->
  <ellipse cx="200" cy="350" rx="220" ry="90" fill="url(#ph_book_glow)"/>

  <!-- Book shadow -->
  <ellipse cx="200" cy="380" rx="160" ry="10" fill="#000" opacity=".4"/>

  <!-- Book base - the closed spine bottom -->
  <g transform="translate(200,320)">
    <!-- Left page -->
    <path d="M -150 0 L -8 -8 L -8 60 L -150 52 Z" fill="url(#ph_page)"
          stroke="#c89e54" stroke-width="1.2"/>
    <!-- Right page -->
    <path d="M 150 0 L 8 -8 L 8 60 L 150 52 Z" fill="url(#ph_page)"
          stroke="#c89e54" stroke-width="1.2"/>
    <!-- Page text - left -->
    <g stroke="#c89e54" stroke-width=".5" opacity=".75">
      <line x1="-130" y1="6"  x2="-22" y2="-1"/>
      <line x1="-130" y1="14" x2="-22" y2="7"/>
      <line x1="-130" y1="22" x2="-22" y2="15"/>
      <line x1="-130" y1="30" x2="-30" y2="23"/>
      <line x1="-130" y1="38" x2="-22" y2="31"/>
      <line x1="-130" y1="46" x2="-22" y2="39"/>
    </g>
    <!-- Page text - right -->
    <g stroke="#c89e54" stroke-width=".5" opacity=".75">
      <line x1="22" y1="-1" x2="130" y2="6"/>
      <line x1="22" y1="7"  x2="130" y2="14"/>
      <line x1="22" y1="15" x2="130" y2="22"/>
      <line x1="22" y1="23" x2="100" y2="29"/>
      <line x1="22" y1="31" x2="130" y2="38"/>
      <line x1="22" y1="39" x2="130" y2="46"/>
    </g>
    <!-- Spine fold (gold) -->
    <path d="M -8 -8 L 8 -8 L 8 60 L -8 60 Z" fill="#0e1a2e"/>
    <line x1="-8" y1="-8" x2="8" y2="-8" stroke="#e6c879" stroke-width="1.5"/>
    <line x1="-8" y1="60" x2="8" y2="60" stroke="#e6c879" stroke-width="1.5"/>
  </g>

  <!-- Book cover edges (slightly behind the open pages) -->
  <path d="M 60 320 L 340 320 L 350 360 L 50 360 Z" fill="url(#ph_cover)"
        stroke="#c89e54" stroke-width="1"/>
  <path d="M 60 320 L 50 360" stroke="#e6c879" stroke-width="1"/>
  <path d="M 340 320 L 350 360" stroke="#e6c879" stroke-width="1"/>
  <!-- Cover ornament -->
  <circle cx="200" cy="340" r="4" fill="#e6c879"/>
  <circle cx="200" cy="340" r="2" fill="#fff3c4"/>

  <!-- 8. Atmospheric haze near the book -->
  <ellipse cx="200" cy="335" rx="200" ry="50" fill="url(#ph_atm)"/>

  <!-- 9. The literary "ink particles" rising from the book pages -->
  <g fill="#fff8d8">
    <circle cx="120" cy="290" r="1" opacity=".6"/>
    <circle cx="160" cy="282" r="1.2" opacity=".7"/>
    <circle cx="200" cy="288" r="1" opacity=".6"/>
    <circle cx="240" cy="284" r="1.2" opacity=".7"/>
    <circle cx="280" cy="290" r="1" opacity=".6"/>
    <circle cx="100" cy="278" r=".8" opacity=".55"/>
    <circle cx="300" cy="280" r=".8" opacity=".55"/>
  </g>

  <!-- 10. Cinematic vignette -->
  <rect x="0" y="0" width="400" height="400" fill="url(#ph_vignette)"/>

  <!-- 11. Corner brandmark -->
  <g font-family="Fraunces, Georgia, serif" font-style="italic" fill="#f8eccb" opacity=".85">
    <text x="14" y="388" font-size="9">PocketPlot <tspan font-weight="700">Universe</tspan></text>
  </g>
</svg>'''


if __name__ == "__main__":
    import pathlib
    out = pathlib.Path(__file__).parent / "portal_hero.svg"
    out.write_text(PORTAL_HERO_SVG)
    print(f"wrote {out}: {len(PORTAL_HERO_SVG)} bytes")

"""
PocketPlot Universe - v18 genre icons.

16 scene-like genre icons, each framed in a brass border with subtle
tech-library elements (circuit lines, holographic glow, compass
markers, gear teeth on the corners).

Each icon is 96x96 viewBox with:
  - A brass frame border (ornate corners)
  - The genre's main scene from v17
  - 4 small corner gems in brass
  - 2-3 circuit lines (neon cyan) at the bottom
"""

# Each entry: (genre_key, svg_body, label)
# The frame + tech detail is shared; only the inner scene varies.

def _gradient_defs(uid):
    return f"""
  <defs>
    <linearGradient id="v18_g_brass_{uid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#e8c879"/>
      <stop offset="50%" stop-color="#c9a04e"/>
      <stop offset="100%" stop-color="#8a6a26"/>
    </linearGradient>
    <linearGradient id="v18_g_brass_h_{uid}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%"  stop-color="#8a6a26"/>
      <stop offset="50%" stop-color="#e8c879"/>
      <stop offset="100%" stop-color="#8a6a26"/>
    </linearGradient>
  </defs>
"""

# Frame: brass border with ornate corners + circuit lines at the bottom.
def _frame(uid):
    return f"""
  <rect x="2" y="2" width="92" height="92" rx="6" fill="#0a0f1c" stroke="url(#v18_g_brass_h_{uid})" stroke-width="1.5"/>
  <rect x="4" y="4" width="88" height="88" rx="5" fill="none" stroke="url(#v18_g_brass_h_{uid})" stroke-width="0.5" opacity="0.5"/>
  <!-- corner gems -->
  <circle cx="6" cy="6" r="1.6" fill="url(#v18_g_brass_{uid})"/>
  <circle cx="90" cy="6" r="1.6" fill="url(#v18_g_brass_{uid})"/>
  <circle cx="6" cy="90" r="1.6" fill="url(#v18_g_brass_{uid})"/>
  <circle cx="90" cy="90" r="1.6" fill="url(#v18_g_brass_{uid})"/>
  <!-- bottom circuit detail (neon) -->
  <g stroke="#5ddef0" stroke-width="0.4" fill="none" opacity="0.55">
    <line x1="10" y1="86" x2="40" y2="86"/>
    <line x1="50" y1="86" x2="86" y2="86"/>
    <circle cx="44" cy="86" r="1.2" fill="#5ddef0"/>
  </g>
  <g stroke="#e85a8a" stroke-width="0.4" fill="none" opacity="0.45">
    <line x1="30" y1="90" x2="66" y2="90"/>
    <circle cx="48" cy="90" r="1" fill="#e85a8a"/>
  </g>
"""

# Each scene is 80x80 centered (margin 8). The frame is at 2-94.
SCENES = {}

# 1. cyberpunk: skyline with neon
SCENES["cyberpunk"] = lambda: '''
  <g transform="translate(8 8)">
    <!-- sky gradient -->
    <defs><linearGradient id="v18_sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#1a0a2a"/>
      <stop offset="60%" stop-color="#2a1a44"/>
      <stop offset="100%" stop-color="#5a2a44"/>
    </linearGradient></defs>
    <rect width="80" height="80" fill="url(#v18_sky)"/>
    <!-- moon -->
    <circle cx="58" cy="22" r="6" fill="#e8c879"/>
    <circle cx="60" cy="20" r="5" fill="#2a1a44"/>
    <!-- skyline -->
    <g fill="#0a0f1c" stroke="url(#v18_g_brass)" stroke-width="0.4">
      <rect x="6"  y="48" width="8"  height="32"/>
      <rect x="16" y="38" width="10" height="42"/>
      <rect x="28" y="44" width="8"  height="36"/>
      <rect x="38" y="30" width="12" height="50"/>
      <rect x="52" y="40" width="9"  height="40"/>
      <rect x="63" y="34" width="11" height="46"/>
    </g>
    <!-- neon windows -->
    <g fill="#5ddef0" opacity="0.85">
      <rect x="40" y="36" width="1.5" height="2"/>
      <rect x="44" y="40" width="1.5" height="2"/>
      <rect x="48" y="34" width="1.5" height="2"/>
      <rect x="64" y="42" width="1.5" height="2"/>
      <rect x="68" y="46" width="1.5" height="2"/>
      <rect x="20" y="48" width="1.5" height="2"/>
      <rect x="32" y="52" width="1.5" height="2"/>
    </g>
    <!-- magenta signs -->
    <g fill="#e85a8a" opacity="0.85">
      <rect x="40" y="46" width="6" height="1"/>
      <rect x="40" y="50" width="4" height="1"/>
      <rect x="60" y="50" width="3" height="1"/>
    </g>
  </g>
'''

# 2. romance: couple on a bench at sunset
SCENES["romance"] = lambda: '''
  <g transform="translate(8 8)">
    <defs><linearGradient id="v18_sunset" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#3a1a2a"/>
      <stop offset="55%" stop-color="#a86a3a"/>
      <stop offset="100%" stop-color="#e8c879"/>
    </linearGradient></defs>
    <rect width="80" height="80" fill="url(#v18_sunset)"/>
    <!-- sun -->
    <circle cx="40" cy="38" r="10" fill="#ffd47a"/>
    <circle cx="40" cy="38" r="14" fill="#ffd47a" opacity="0.3"/>
    <!-- bench -->
    <line x1="22" y1="56" x2="58" y2="56" stroke="#0a0f1c" stroke-width="1.2"/>
    <line x1="22" y1="56" x2="22" y2="64" stroke="#0a0f1c" stroke-width="1"/>
    <line x1="58" y1="56" x2="58" y2="64" stroke="#0a0f1c" stroke-width="1"/>
    <!-- two figures -->
    <g fill="#0a0f1c">
      <ellipse cx="34" cy="50" rx="3" ry="3.5"/>
      <path d="M 30 52 Q 30 60 32 60 L 36 60 Q 38 60 38 52 Z"/>
      <ellipse cx="46" cy="50" rx="3" ry="3.5"/>
      <path d="M 42 52 Q 42 60 44 60 L 48 60 Q 50 60 50 52 Z"/>
    </g>
    <!-- ground -->
    <line x1="0" y1="64" x2="80" y2="64" stroke="#0a0f1c" stroke-width="1.2"/>
  </g>
'''

# 3. action: car chase with headlight beams
SCENES["action"] = lambda: '''
  <g transform="translate(8 8)">
    <rect width="80" height="80" fill="#0a0f1c"/>
    <!-- speed lines -->
    <g stroke="#e8c879" stroke-width="0.6" opacity="0.6">
      <line x1="0" y1="20" x2="30" y2="20"/>
      <line x1="50" y1="20" x2="80" y2="20"/>
      <line x1="0" y1="34" x2="20" y2="34"/>
      <line x1="60" y1="34" x2="80" y2="34"/>
      <line x1="0" y1="50" x2="25" y2="50"/>
      <line x1="55" y1="50" x2="80" y2="50"/>
    </g>
    <!-- car 1 (lead) -->
    <g transform="translate(30 30)">
      <path d="M 0 0 L 16 -6 L 22 -6 L 24 0 L 24 6 L 0 6 Z" fill="#8a6a26" stroke="#0a0f1c" stroke-width="0.5"/>
      <circle cx="6"  cy="6" r="2" fill="#0a0f1c" stroke="#e8c879" stroke-width="0.5"/>
      <circle cx="20" cy="6" r="2" fill="#0a0f1c" stroke="#e8c879" stroke-width="0.5"/>
    </g>
    <!-- headlight beams -->
    <g fill="#ffd47a" opacity="0.4">
      <polygon points="54,30 80,20 80,40"/>
      <polygon points="54,36 80,46 80,66"/>
    </g>
    <!-- car 2 (chasing) -->
    <g transform="translate(8 50)">
      <path d="M 0 0 L 14 -5 L 20 -5 L 22 0 L 22 5 L 0 5 Z" fill="#5a2010" stroke="#0a0f1c" stroke-width="0.5"/>
      <circle cx="5"  cy="5" r="1.6" fill="#0a0f1c"/>
      <circle cx="18" cy="5" r="1.6" fill="#0a0f1c"/>
    </g>
  </g>
'''

# 4. drama: stage with curtains + spotlight
SCENES["drama"] = lambda: '''
  <g transform="translate(8 8)">
    <rect width="80" height="80" fill="#0a0f1c"/>
    <!-- stage floor -->
    <path d="M 10 60 L 70 60 L 76 70 L 4 70 Z" fill="#4a2c1a"/>
    <!-- back curtain -->
    <rect x="10" y="10" width="60" height="50" fill="#5a2010"/>
    <!-- spotlight -->
    <polygon points="40,4 32,60 48,60" fill="#ffd47a" opacity="0.4"/>
    <!-- side curtains -->
    <path d="M 0 0 L 12 0 Q 14 30 10 60 L 10 60 L 0 60 Z" fill="#7a1a2a"/>
    <path d="M 80 0 L 68 0 Q 66 30 70 60 L 70 60 L 80 60 Z" fill="#7a1a2a"/>
    <!-- chair -->
    <rect x="36" y="44" width="8" height="14" fill="#0a0f1c"/>
    <!-- mask -->
    <ellipse cx="40" cy="36" rx="6" ry="3" fill="#e8c879"/>
    <ellipse cx="40" cy="36" rx="3" ry="1.4" fill="#0a0f1c"/>
  </g>
'''

# 5. thriller: corridor with swinging bulb + red door
SCENES["thriller"] = lambda: '''
  <g transform="translate(8 8)">
    <defs><linearGradient id="v18_thriller" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#1a0a04"/>
      <stop offset="100%" stop-color="#3a1a1a"/>
    </linearGradient></defs>
    <rect width="80" height="80" fill="url(#v18_thriller)"/>
    <!-- corridor lines (perspective) -->
    <line x1="0" y1="20" x2="40" y2="50" stroke="#5a4a3a" stroke-width="0.6"/>
    <line x1="80" y1="20" x2="40" y2="50" stroke="#5a4a3a" stroke-width="0.6"/>
    <line x1="0" y1="60" x2="40" y2="50" stroke="#5a4a3a" stroke-width="0.6"/>
    <line x1="80" y1="60" x2="40" y2="50" stroke="#5a4a3a" stroke-width="0.6"/>
    <!-- red door at end -->
    <rect x="34" y="38" width="12" height="14" fill="#c44a3a" stroke="#0a0f1c" stroke-width="0.5"/>
    <!-- swinging bulb (top center) -->
    <line x1="40" y1="0" x2="40" y2="14" stroke="#8a6a26" stroke-width="0.6"/>
    <ellipse cx="40" cy="20" rx="6" ry="4" fill="#ffd47a"/>
    <ellipse cx="40" cy="20" rx="12" ry="8" fill="#ffd47a" opacity="0.25"/>
    <!-- figure approaching -->
    <g fill="#0a0f1c">
      <ellipse cx="40" cy="58" rx="3" ry="2"/>
      <path d="M 36 58 L 35 70 L 39 70 L 40 64 L 41 70 L 45 70 L 44 58 Z"/>
      <circle cx="40" cy="52" r="3"/>
    </g>
  </g>
'''

# 6. fantasy: castle + dragon
SCENES["fantasy"] = lambda: '''
  <g transform="translate(8 8)">
    <defs><linearGradient id="v18_fantasy" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#2a1a44"/>
      <stop offset="100%" stop-color="#5a3a2a"/>
    </linearGradient></defs>
    <rect width="80" height="80" fill="url(#v18_fantasy)"/>
    <!-- moon -->
    <circle cx="58" cy="18" r="6" fill="#e8c879"/>
    <!-- mountains -->
    <polygon points="0,70 20,40 40,60 60,30 80,60 80,80 0,80" fill="#0a0f1c"/>
    <!-- castle -->
    <g fill="#3a2010" stroke="#8a6a26" stroke-width="0.5">
      <rect x="32" y="50" width="16" height="20"/>
      <rect x="28" y="48" width="6"  height="6"/>
      <rect x="46" y="48" width="6"  height="6"/>
      <rect x="30" y="46" width="2"  height="2"/>
      <rect x="34" y="46" width="2"  height="2"/>
      <rect x="44" y="46" width="2"  height="2"/>
      <rect x="48" y="46" width="2"  height="2"/>
    </g>
    <!-- window glow -->
    <rect x="38" y="58" width="4" height="6" fill="#ffd47a"/>
    <!-- dragon silhouette -->
    <g fill="#0a0f1c">
      <path d="M 14 56 Q 16 52 20 54 Q 22 50 26 52 Q 28 50 30 53 L 30 56 L 28 56 L 26 58 L 22 58 Z"/>
      <circle cx="22" cy="54" r="0.6" fill="#c44a3a"/>
    </g>
    <!-- banner -->
    <line x1="36" y1="42" x2="44" y2="42" stroke="#5a2010" stroke-width="0.5"/>
    <path d="M 44 42 L 50 44 L 50 48 L 44 50 Z" fill="#7a1a2a"/>
  </g>
'''

# 7. comedy: pie-in-the-face + mic + confetti
SCENES["comedy"] = lambda: '''
  <g transform="translate(8 8)">
    <rect width="80" height="80" fill="#0a0f1c"/>
    <!-- confetti -->
    <g fill="#ffd47a">
      <rect x="10" y="10" width="2" height="2" transform="rotate(20 11 11)"/>
      <rect x="20" y="6"  width="2" height="2" transform="rotate(45 21 7)"/>
      <rect x="35" y="12" width="2" height="2" transform="rotate(15 36 13)"/>
      <rect x="55" y="8"  width="2" height="2" transform="rotate(60 56 9)"/>
      <rect x="65" y="16" width="2" height="2" transform="rotate(30 66 17)"/>
    </g>
    <g fill="#e85a8a">
      <rect x="14" y="18" width="2" height="2" transform="rotate(45 15 19)"/>
      <rect x="48" y="14" width="2" height="2" transform="rotate(20 49 15)"/>
      <rect x="70" y="22" width="2" height="2" transform="rotate(35 71 23)"/>
    </g>
    <g fill="#5ddef0">
      <rect x="24" y="20" width="2" height="2" transform="rotate(40 25 21)"/>
      <rect x="58" y="20" width="2" height="2" transform="rotate(55 59 21)"/>
    </g>
    <!-- mic stand -->
    <line x1="40" y1="34" x2="40" y2="68" stroke="#8a6a26" stroke-width="1"/>
    <ellipse cx="40" cy="32" rx="3" ry="4" fill="#c9a04e" stroke="#0a0f1c" stroke-width="0.5"/>
    <!-- face with pie -->
    <g fill="#0a0f1c">
      <circle cx="40" cy="58" r="10"/>
      <ellipse cx="36" cy="56" rx="1" ry="1.5" fill="#fff"/>
      <ellipse cx="44" cy="56" rx="1" ry="1.5" fill="#fff"/>
      <path d="M 36 62 Q 40 64 44 62" stroke="#fff" stroke-width="0.6" fill="none"/>
    </g>
    <!-- pie splash -->
    <ellipse cx="42" cy="50" rx="6" ry="4" fill="#ffd47a"/>
    <ellipse cx="40" cy="48" rx="3" ry="2" fill="#c9a04e"/>
  </g>
'''

# 8. sci-fi: planet + rocket + Saturn ring
SCENES["scifi"] = lambda: '''
  <g transform="translate(8 8)">
    <defs><radialGradient id="v18_scifi" cx="0.5" cy="0.5" r="0.7">
      <stop offset="0%"  stop-color="#1a0a2a"/>
      <stop offset="100%" stop-color="#0a0f1c"/>
    </radialGradient></defs>
    <rect width="80" height="80" fill="url(#v18_scifi)"/>
    <!-- stars -->
    <g fill="#f3e9d2" opacity="0.7">
      <circle cx="12" cy="14" r="0.6"/>
      <circle cx="22" cy="20" r="0.4"/>
      <circle cx="68" cy="12" r="0.6"/>
      <circle cx="60" cy="30" r="0.4"/>
      <circle cx="14" cy="56" r="0.5"/>
      <circle cx="74" cy="50" r="0.5"/>
      <circle cx="32" cy="68" r="0.4"/>
    </g>
    <!-- Saturn -->
    <g transform="translate(56 56)">
      <ellipse rx="20" ry="3" fill="none" stroke="#c9a04e" stroke-width="1"/>
      <circle r="10" fill="#a87c52"/>
      <path d="M -10 0 Q -5 -3 0 0 Q 5 3 10 0" stroke="#5a4a3a" stroke-width="0.5" fill="none"/>
    </g>
    <!-- rocket -->
    <g transform="translate(20 38) rotate(35)">
      <path d="M 0 0 L 0 -14 L 4 -10 L 4 0 Z" fill="#e8c879" stroke="#8a6a26" stroke-width="0.5"/>
      <path d="M 0 0 L -2 2 L 4 2 Z" fill="#c44a3a"/>
      <circle cx="2" cy="-6" r="1" fill="#5ddef0"/>
    </g>
    <!-- planet -->
    <circle cx="26" cy="62" r="8" fill="#5a4a3a" stroke="#8a6a26" stroke-width="0.5"/>
    <ellipse cx="26" cy="62" rx="14" ry="1.5" fill="none" stroke="#c9a04e" stroke-width="0.5" opacity="0.6"/>
  </g>
'''

# 9. horror: graveyard with tombstones + dead tree + fog
SCENES["horror"] = lambda: '''
  <g transform="translate(8 8)">
    <defs><linearGradient id="v18_horror" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#0a0a14"/>
      <stop offset="100%" stop-color="#1a0a14"/>
    </linearGradient></defs>
    <rect width="80" height="80" fill="url(#v18_horror)"/>
    <!-- moon behind clouds -->
    <circle cx="58" cy="20" r="8" fill="#f3e9d2" opacity="0.7"/>
    <ellipse cx="50" cy="22" rx="12" ry="4" fill="#0a0a14"/>
    <ellipse cx="64" cy="18" rx="10" ry="3" fill="#0a0a14"/>
    <!-- fog curl -->
    <ellipse cx="20" cy="62" rx="20" ry="4" fill="#5a4a5a" opacity="0.4"/>
    <ellipse cx="58" cy="66" rx="24" ry="5" fill="#5a4a5a" opacity="0.4"/>
    <!-- tombstones -->
    <g fill="#3a3a4a" stroke="#5a4a5a" stroke-width="0.5">
      <path d="M 16 70 Q 16 56 22 56 Q 28 56 28 70 Z"/>
      <path d="M 38 72 Q 38 60 44 60 Q 50 60 50 72 Z"/>
      <path d="M 56 68 Q 56 54 62 54 Q 68 54 68 68 Z"/>
    </g>
    <!-- RIP text -->
    <g font-family="Cinzel,serif" font-size="3" fill="#1a0a14" text-anchor="middle">
      <text x="22" y="68">RIP</text>
      <text x="44" y="70">J.S.</text>
      <text x="62" y="66">1807</text>
    </g>
    <!-- dead tree -->
    <g stroke="#0a0a14" stroke-width="1.2" fill="none">
      <line x1="6" y1="50" x2="6" y2="68"/>
      <line x1="6" y1="58" x2="12" y2="54"/>
      <line x1="6" y1="56" x2="0"  y2="52"/>
      <line x1="6" y1="54" x2="14" y2="48"/>
    </g>
    <!-- crow -->
    <g fill="#0a0a14">
      <ellipse cx="14" cy="48" rx="2" ry="1"/>
      <path d="M 12 48 L 16 47 L 16 49 Z"/>
    </g>
  </g>
'''

# 10. detective: office with map + magnifier + lamp + hat
SCENES["detective"] = lambda: '''
  <g transform="translate(8 8)">
    <rect width="80" height="80" fill="#1a0e08"/>
    <!-- desk -->
    <rect x="0" y="60" width="80" height="20" fill="#4a2c1a"/>
    <!-- map (paper) -->
    <g transform="translate(8 38)">
      <rect width="22" height="20" fill="#f3e9d2" stroke="#8a6a26" stroke-width="0.5"/>
      <g stroke="#5a4a3a" stroke-width="0.3">
        <line x1="2" y1="6" x2="20" y2="6"/>
        <line x1="2" y1="12" x2="20" y2="12"/>
        <line x1="6" y1="2" x2="6" y2="18"/>
        <line x1="14" y1="2" x2="14" y2="18"/>
      </g>
      <path d="M 4 4 Q 10 8 18 4" stroke="#c44a3a" stroke-width="0.5" fill="none"/>
    </g>
    <!-- magnifier -->
    <g transform="translate(46 40)">
      <circle r="8" fill="none" stroke="#c9a04e" stroke-width="1.5"/>
      <circle r="6" fill="rgba(93,222,240,0.15)"/>
      <line x1="6" y1="6" x2="14" y2="14" stroke="#c9a04e" stroke-width="2"/>
    </g>
    <!-- lamp -->
    <g transform="translate(62 30)">
      <line x1="0" y1="0" x2="0" y2="20" stroke="#8a6a26" stroke-width="0.8"/>
      <path d="M -6 0 L 6 0 L 4 -6 L -4 -6 Z" fill="#c9a04e"/>
      <ellipse cx="0" cy="-6" rx="4" ry="1.5" fill="#ffd47a" opacity="0.5"/>
    </g>
    <!-- detective hat -->
    <g transform="translate(20 70)">
      <ellipse rx="10" ry="2" fill="#0a0a04"/>
      <path d="M -6 0 Q -7 -6 0 -7 Q 7 -6 6 0 Z" fill="#0a0a04"/>
    </g>
  </g>
'''

# 11. fairytales: cottage with smoke + mushrooms + path
SCENES["fairytales"] = lambda: '''
  <g transform="translate(8 8)">
    <defs><linearGradient id="v18_fairy" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#2a4a3a"/>
      <stop offset="100%" stop-color="#3a2a44"/>
    </linearGradient></defs>
    <rect width="80" height="80" fill="url(#v18_fairy)"/>
    <!-- moon -->
    <circle cx="58" cy="20" r="6" fill="#e8c879"/>
    <!-- hills -->
    <path d="M 0 60 Q 20 50 40 60 Q 60 50 80 60 L 80 80 L 0 80 Z" fill="#0a1a14"/>
    <!-- cottage -->
    <g transform="translate(26 38)">
      <rect x="0" y="10" width="20" height="16" fill="#4a2c1a"/>
      <path d="M -2 10 L 10 0 L 22 10 Z" fill="#5a2010"/>
      <rect x="4" y="14" width="4" height="6" fill="#ffd47a"/>
      <rect x="12" y="14" width="4" height="6" fill="#5a4a3a"/>
      <line x1="10" y1="2" x2="10" y2="-2" stroke="#3a2010" stroke-width="0.8"/>
      <ellipse cx="10" cy="-4" rx="2" ry="1" fill="#5a4a4a" opacity="0.5"/>
      <ellipse cx="14" cy="-8" rx="2" ry="1" fill="#5a4a4a" opacity="0.4"/>
    </g>
    <!-- mushrooms -->
    <g>
      <rect x="14" y="64" width="2" height="6" fill="#f3e9d2"/>
      <ellipse cx="15" cy="64" rx="4" ry="2" fill="#c44a3a"/>
      <rect x="60" y="68" width="2" height="5" fill="#f3e9d2"/>
      <ellipse cx="61" cy="68" rx="3" ry="1.6" fill="#e8c879"/>
    </g>
    <!-- path -->
    <path d="M 36 78 Q 40 70 44 78" stroke="#c9a04e" stroke-width="0.5" fill="none"/>
  </g>
'''

# 12. superhero: lightning bolt + city silhouette
SCENES["superhero"] = lambda: '''
  <g transform="translate(8 8)">
    <defs><linearGradient id="v18_super" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#0a0a2a"/>
      <stop offset="100%" stop-color="#1a0a44"/>
    </linearGradient></defs>
    <rect width="80" height="80" fill="url(#v18_super)"/>
    <!-- moon behind -->
    <circle cx="58" cy="22" r="8" fill="#1a0a44"/>
    <circle cx="60" cy="22" r="6" fill="#5a4a8a"/>
    <!-- city silhouette -->
    <g fill="#0a0a14">
      <rect x="0"  y="56" width="6"  height="24"/>
      <rect x="8"  y="48" width="8"  height="32"/>
      <rect x="18" y="54" width="6"  height="26"/>
      <rect x="26" y="42" width="10" height="38"/>
      <rect x="38" y="50" width="8"  height="30"/>
      <rect x="48" y="46" width="10" height="34"/>
      <rect x="60" y="52" width="6"  height="28"/>
      <rect x="68" y="48" width="8"  height="32"/>
      <rect x="78" y="56" width="2"  height="24"/>
    </g>
    <!-- windows -->
    <g fill="#ffd47a" opacity="0.7">
      <rect x="10" y="52" width="1.5" height="2"/>
      <rect x="14" y="56" width="1.5" height="2"/>
      <rect x="28" y="46" width="1.5" height="2"/>
      <rect x="32" y="50" width="1.5" height="2"/>
      <rect x="50" y="50" width="1.5" height="2"/>
      <rect x="70" y="52" width="1.5" height="2"/>
    </g>
    <!-- lightning bolt (foreground) -->
    <path d="M 38 4 L 30 28 L 36 28 L 30 50 L 44 22 L 38 22 L 44 4 Z"
          fill="#ffd47a" stroke="#e8c879" stroke-width="0.6"/>
  </g>
'''

# 13. chicklit: coffee cup + journal + plant + italic text
SCENES["chicklit"] = lambda: '''
  <g transform="translate(8 8)">
    <defs><linearGradient id="v18_chick" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#3a2a44"/>
      <stop offset="100%" stop-color="#2a1a3a"/>
    </linearGradient></defs>
    <rect width="80" height="80" fill="url(#v18_chick)"/>
    <!-- table -->
    <line x1="0" y1="60" x2="80" y2="60" stroke="#4a2c1a" stroke-width="1.2"/>
    <!-- coffee cup -->
    <g transform="translate(16 42)">
      <path d="M 0 0 L 16 0 L 14 14 L 2 14 Z" fill="#f3e9d2" stroke="#8a6a26" stroke-width="0.5"/>
      <ellipse cx="8" cy="0" rx="8" ry="2" fill="#4a2c1a"/>
      <path d="M 16 4 Q 22 4 22 8 Q 22 12 16 12" stroke="#f3e9d2" stroke-width="1.5" fill="none"/>
      <!-- steam -->
      <path d="M 4 -4 Q 6 -8 4 -12" stroke="#f3e9d2" stroke-width="0.4" fill="none" opacity="0.5"/>
      <path d="M 8 -4 Q 10 -8 8 -12" stroke="#f3e9d2" stroke-width="0.4" fill="none" opacity="0.5"/>
    </g>
    <!-- open journal -->
    <g transform="translate(36 42)">
      <path d="M 0 0 L 18 2 L 18 16 L 0 14 Z" fill="#f3e9d2" stroke="#8a6a26" stroke-width="0.5"/>
      <path d="M 18 2 L 30 0 L 30 14 L 18 16 Z" fill="#f3e9d2" stroke="#8a6a26" stroke-width="0.5"/>
      <line x1="2" y1="5" x2="14" y2="6" stroke="#5a4a3a" stroke-width="0.3"/>
      <line x1="2" y1="8" x2="14" y2="9" stroke="#5a4a3a" stroke-width="0.3"/>
      <line x1="22" y1="4" x2="28" y2="3" stroke="#5a4a3a" stroke-width="0.3"/>
      <line x1="22" y1="7" x2="28" y2="6" stroke="#5a4a3a" stroke-width="0.3"/>
    </g>
    <!-- plant -->
    <g transform="translate(66 30)">
      <ellipse rx="6" ry="2" fill="#4a2c1a"/>
      <path d="M 0 0 Q -4 -8 -2 -14" stroke="#0f3a2a" stroke-width="1" fill="none"/>
      <path d="M 0 0 Q 0 -10 4 -16" stroke="#0f3a2a" stroke-width="1" fill="none"/>
      <path d="M 0 0 Q 4 -8 6 -12" stroke="#0f3a2a" stroke-width="1" fill="none"/>
      <ellipse cx="-2" cy="-14" rx="2" ry="3" fill="#0f3a2a" transform="rotate(-30 -2 -14)"/>
      <ellipse cx="4" cy="-16" rx="2" ry="3" fill="#1d6b50" transform="rotate(20 4 -16)"/>
      <ellipse cx="6" cy="-12" rx="2" ry="3" fill="#0f3a2a" transform="rotate(45 6 -12)"/>
    </g>
    <!-- italic text -->
    <g font-family="Fraunces,serif" font-style="italic" font-size="6" fill="#e85a8a">
      <text x="40" y="76" text-anchor="middle">once upon a time</text>
    </g>
  </g>
'''

# 14. adventure: pirate ship + sail + flag
SCENES["adventure"] = lambda: '''
  <g transform="translate(8 8)">
    <defs><linearGradient id="v18_sea" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"  stop-color="#0a1a2a"/>
      <stop offset="100%" stop-color="#1a0a1a"/>
    </linearGradient></defs>
    <rect width="80" height="80" fill="url(#v18_sea)"/>
    <!-- sun -->
    <circle cx="64" cy="20" r="6" fill="#ffd47a"/>
    <circle cx="64" cy="20" r="9" fill="#ffd47a" opacity="0.3"/>
    <!-- waves -->
    <g stroke="#5ddef0" stroke-width="0.4" fill="none" opacity="0.4">
      <path d="M 0 50 Q 10 48 20 50 T 40 50 T 60 50 T 80 50"/>
      <path d="M 0 60 Q 10 58 20 60 T 40 60 T 60 60 T 80 60"/>
      <path d="M 0 70 Q 10 68 20 70 T 40 70 T 60 70 T 80 70"/>
    </g>
    <!-- ship hull -->
    <g transform="translate(20 40)">
      <path d="M 0 0 L 40 0 L 36 8 L 4 8 Z" fill="#4a2c1a"/>
      <path d="M 4 8 L 36 8 L 30 12 L 10 12 Z" fill="#3a2010"/>
      <!-- mast -->
      <line x1="20" y1="0" x2="20" y2="-30" stroke="#3a2010" stroke-width="1.5"/>
      <!-- sail -->
      <path d="M 20 -30 L 32 -10 L 20 -10 Z" fill="#f3e9d2" stroke="#5a4a3a" stroke-width="0.5"/>
      <line x1="22" y1="-26" x2="22" y2="-12" stroke="#5a4a3a" stroke-width="0.3"/>
      <line x1="24" y1="-22" x2="24" y2="-12" stroke="#5a4a3a" stroke-width="0.3"/>
      <line x1="26" y1="-18" x2="26" y2="-12" stroke="#5a4a3a" stroke-width="0.3"/>
      <!-- flag -->
      <line x1="20" y1="-30" x2="20" y2="-36" stroke="#3a2010" stroke-width="0.6"/>
      <path d="M 20 -36 L 30 -34 L 30 -32 L 20 -30 Z" fill="#0a0a14"/>
      <circle cx="25" cy="-33" r="0.8" fill="#fff"/>
    </g>
  </g>
'''

# 15. roleplaying: hex grid + campfire + dice
SCENES["roleplaying"] = lambda: '''
  <g transform="translate(8 8)">
    <rect width="80" height="80" fill="#0a0f1c"/>
    <!-- hex grid -->
    <g stroke="#5a4a3a" stroke-width="0.3" fill="none" opacity="0.6">
      <polygon points="20,12 28,16 28,24 20,28 12,24 12,16"/>
      <polygon points="36,12 44,16 44,24 36,28 28,24 28,16"/>
      <polygon points="52,12 60,16 60,24 52,28 44,24 44,16"/>
      <polygon points="28,28 36,32 36,40 28,44 20,40 20,32"/>
      <polygon points="44,28 52,32 52,40 44,44 36,40 36,32"/>
      <polygon points="20,44 28,48 28,56 20,60 12,56 12,48"/>
      <polygon points="36,44 44,48 44,56 36,60 28,56 28,48"/>
      <polygon points="52,44 60,48 60,56 52,60 44,56 44,48"/>
    </g>
    <!-- campfire (center) -->
    <g transform="translate(40 38)">
      <ellipse rx="6" ry="2" fill="#5a4a3a"/>
      <ellipse rx="4" ry="1" fill="#3a2010"/>
      <path d="M 0 -2 Q -3 -8 0 -14 Q 3 -8 0 -2 Z" fill="#c44a3a"/>
      <path d="M 0 -4 Q -2 -8 0 -12 Q 2 -8 0 -4 Z" fill="#ffd47a"/>
      <ellipse cx="0" cy="-2" rx="3" ry="0.8" fill="#ffd47a" opacity="0.4"/>
    </g>
    <!-- dice -->
    <g transform="translate(60 56)">
      <rect width="8" height="8" fill="#f3e9d2" stroke="#8a6a26" stroke-width="0.5" transform="rotate(15 4 4)"/>
      <circle cx="2" cy="2" r="0.5" fill="#0a0a04"/>
      <circle cx="6" cy="6" r="0.5" fill="#0a0a04"/>
    </g>
    <g transform="translate(12 56)">
      <rect width="8" height="8" fill="#f3e9d2" stroke="#8a6a26" stroke-width="0.5" transform="rotate(-10 4 4)"/>
      <circle cx="2" cy="4" r="0.5" fill="#0a0a04"/>
      <circle cx="4" cy="2" r="0.5" fill="#0a0a04"/>
      <circle cx="6" cy="6" r="0.5" fill="#0a0a04"/>
    </g>
  </g>
'''

# 16. historical: candlelit library + oil lamp + candle
SCENES["historical"] = lambda: '''
  <g transform="translate(8 8)">
    <defs><radialGradient id="v18_hist" cx="0.5" cy="0.5" r="0.7">
      <stop offset="0%"  stop-color="#5a3a1a"/>
      <stop offset="100%" stop-color="#1a0a04"/>
    </radialGradient></defs>
    <rect width="80" height="80" fill="url(#v18_hist)"/>
    <!-- bookcase -->
    <g fill="#4a2c1a" stroke="#8a6a26" stroke-width="0.4">
      <rect x="2"  y="2" width="76" height="76" rx="2"/>
    </g>
    <g>
      <rect x="6"  y="6"  width="4" height="68" fill="#0f3a2a"/>
      <rect x="11" y="6"  width="3" height="68" fill="#8a6a26"/>
      <rect x="15" y="6"  width="4" height="68" fill="#5a2010"/>
      <rect x="20" y="6"  width="3" height="68" fill="#4a2c1a"/>
      <rect x="24" y="6"  width="4" height="68" fill="#0f3a2a"/>
      <rect x="29" y="6"  width="3" height="68" fill="#3a2010"/>
      <rect x="33" y="6"  width="4" height="68" fill="#8a6a26"/>
      <rect x="38" y="6"  width="3" height="68" fill="#5a2010"/>
      <rect x="42" y="6"  width="4" height="68" fill="#4a2c1a"/>
      <rect x="47" y="6"  width="3" height="68" fill="#0f3a2a"/>
      <rect x="51" y="6"  width="4" height="68" fill="#3a2010"/>
      <rect x="56" y="6"  width="3" height="68" fill="#8a6a26"/>
      <rect x="60" y="6"  width="4" height="68" fill="#5a2010"/>
      <rect x="65" y="6"  width="3" height="68" fill="#4a2c1a"/>
      <rect x="69" y="6"  width="4" height="68" fill="#0f3a2a"/>
      <rect x="74" y="6"  width="3" height="68" fill="#3a2010"/>
    </g>
    <!-- candle (foreground) -->
    <g transform="translate(40 30)">
      <rect x="-2" y="-8" width="4" height="14" fill="#f3e9d2"/>
      <ellipse cx="0" cy="-9" rx="1" ry="1.5" fill="#ffd47a"/>
      <ellipse cx="0" cy="-9" rx="3" ry="2" fill="#ffd47a" opacity="0.4"/>
      <line x1="0" y1="-10" x2="0" y2="-12" stroke="#0a0a04" stroke-width="0.4"/>
    </g>
    <!-- oil lamp -->
    <g transform="translate(60 14)">
      <ellipse rx="4" ry="1" fill="#c9a04e"/>
      <rect x="-2" y="-4" width="4" height="4" fill="#c9a04e"/>
      <ellipse cx="0" cy="-5" rx="1.5" ry="1" fill="#ffd47a" opacity="0.7"/>
    </g>
  </g>
'''

GENRES = [
    "cyberpunk", "romance", "action", "drama", "thriller", "fantasy",
    "comedy", "scifi", "horror", "detective", "fairytales", "superhero",
    "chicklit", "adventure", "roleplaying", "historical",
]

GENRE_LABELS_V18 = {
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
    "chicklit":    "Chick-Lit",
    "adventure":   "Adventure",
    "roleplaying": "Roleplaying",
    "historical":  "Historical",
}


def _genre_icon(key):
    """Return the v18 SVG for one genre (with shared brass frame + tech detail)."""
    body = SCENES[key]()
    return (
        '<svg viewBox="0 0 96 96" xmlns="http://www.w3.org/2000/svg">\n'
        f'{_gradient_defs(key)}\n'
        f'{_frame(key)}\n'
        f'{body}\n'
        '</svg>'
    )


def render_genre_grid():
    cards = []
    for g in GENRES:
        icon = _genre_icon(g)
        label = GENRE_LABELS_V18.get(g, g.title())
        cards.append(
            '<a class="genre-card v18" href="/worlds/new?genre=' + g + '" data-genre="' + g + '">'
            + icon
            + '<div class="genre-label">' + label + '</div>'
            + '</a>'
        )
    return '<div class="genre-grid v18">' + "".join(cards) + '</div>'


if __name__ == "__main__":
    import sys
    g = render_genre_grid()
    Path("/tmp/pp_v18_grid.html").write_text(
        '<html><body style="background:#0a0f1c;padding:30px">' + g + '</body></html>'
    ) if False else None
    from pathlib import Path
    Path("/tmp/pp_v18_grid.html").write_text(
        '<html><body style="background:#0a0f1c;padding:30px">' + g + '</body></html>'
    )
    print(f"rendered grid: {len(g)} bytes")
    print(f"  {GENRES[0]} icon: {len(_genre_icon(GENRES[0]))} bytes")

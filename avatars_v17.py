"""
PocketPlot Universe - Stylized SVG avatars (v17).

Distinct, personality-driven avatars for the testimonial cards.
Each avatar is a 64x64 SVG portrait with its own color palette and
silhouette feature (glasses, hat, hair color, beard, etc.).
"""

# Each avatar is a 64x64 viewBox with a colored circular background
# + a stylized portrait (head + shoulders + one signature feature).


def avatar_j_reyes() -> str:
    """Screenwriter avatar - dark hair, square glasses, navy bg."""
    return '''<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="30" fill="#15243f" stroke="#e6c879" stroke-width="2"/>
      <!-- Body / shoulders -->
      <path d="M 8 60 Q 8 44 24 42 Q 32 40 40 42 Q 56 44 56 60 Z" fill="#0e1a2e"/>
      <!-- Neck -->
      <rect x="28" y="36" width="8" height="8" fill="#c89e74"/>
      <!-- Head -->
      <ellipse cx="32" cy="26" rx="10" ry="12" fill="#d4a8a0"/>
      <!-- Hair (short, dark, parted) -->
      <path d="M 22 18 Q 24 14 32 14 Q 40 14 42 18 Q 42 22 40 22 Q 38 18 32 18 Q 26 18 24 22 Q 22 22 22 18 Z" fill="#1a0a14"/>
      <!-- Glasses (signature) -->
      <circle cx="28" cy="26" r="3.2" fill="none" stroke="#e6c879" stroke-width="1"/>
      <circle cx="36" cy="26" r="3.2" fill="none" stroke="#e6c879" stroke-width="1"/>
      <line x1="31.2" y1="26" x2="32.8" y2="26" stroke="#e6c879" stroke-width="1"/>
      <!-- Eyes (behind glasses) -->
      <circle cx="28" cy="26" r="0.8" fill="#1a0a14"/>
      <circle cx="36" cy="26" r="0.8" fill="#1a0a14"/>
      <!-- Smile -->
      <path d="M 28 32 Q 32 34 36 32" stroke="#7a3a3a" stroke-width=".8" fill="none"/>
    </svg>'''


def avatar_k_voss() -> str:
    """Novelist avatar - red hair, freckles, gold bg."""
    return '''<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="30" fill="#5a2a44" stroke="#e6c879" stroke-width="2"/>
      <!-- Shoulders -->
      <path d="M 8 60 Q 8 44 24 42 Q 32 40 40 42 Q 56 44 56 60 Z" fill="#3a1a2a"/>
      <!-- Neck -->
      <rect x="28" y="36" width="8" height="8" fill="#e6b89a"/>
      <!-- Head -->
      <ellipse cx="32" cy="26" rx="10" ry="12" fill="#f0c8b4"/>
      <!-- Red hair (long, wavy) -->
      <path d="M 22 22 Q 22 12 32 12 Q 42 12 42 22 L 42 30 Q 44 36 40 38 Q 38 32 38 26 Q 36 22 32 22 Q 28 22 26 26 Q 26 32 24 38 Q 20 36 22 30 Z" fill="#c44a3a"/>
      <!-- Bangs across forehead -->
      <path d="M 24 18 Q 32 14 40 18 Q 38 22 32 22 Q 26 22 24 18 Z" fill="#c44a3a"/>
      <!-- Freckles -->
      <circle cx="27" cy="28" r=".4" fill="#7a3a3a"/>
      <circle cx="30" cy="29" r=".4" fill="#7a3a3a"/>
      <circle cx="33" cy="28" r=".4" fill="#7a3a3a"/>
      <circle cx="36" cy="29" r=".4" fill="#7a3a3a"/>
      <!-- Eyes -->
      <circle cx="28" cy="26" r="0.9" fill="#1a5a4a"/>
      <circle cx="36" cy="26" r="0.9" fill="#1a5a4a"/>
      <!-- Smile -->
      <path d="M 27 32 Q 32 35 37 32" stroke="#7a3a3a" stroke-width=".8" fill="none"/>
    </svg>'''


def avatar_m_aoki() -> str:
    """Roleplayer avatar - blue hair, headphones, cyan bg."""
    return '''<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="30" fill="#1a2a4a" stroke="#44f0ff" stroke-width="2"/>
      <!-- Shoulders -->
      <path d="M 8 60 Q 8 44 24 42 Q 32 40 40 42 Q 56 44 56 60 Z" fill="#0a1428"/>
      <!-- Headphones (signature) -->
      <path d="M 16 24 Q 16 14 32 14 Q 48 14 48 24" stroke="#0a0a14" stroke-width="3" fill="none"/>
      <ellipse cx="14" cy="28" rx="4" ry="6" fill="#0a0a14"/>
      <ellipse cx="50" cy="28" rx="4" ry="6" fill="#0a0a14"/>
      <ellipse cx="14" cy="28" rx="2" ry="4" fill="#44f0ff"/>
      <ellipse cx="50" cy="28" rx="2" ry="4" fill="#44f0ff"/>
      <!-- Neck -->
      <rect x="28" y="36" width="8" height="8" fill="#d4a878"/>
      <!-- Head -->
      <ellipse cx="32" cy="26" rx="10" ry="12" fill="#e8c4a0"/>
      <!-- Blue hair -->
      <path d="M 22 22 Q 22 12 32 12 Q 42 12 42 22 Q 42 26 38 24 Q 36 20 32 20 Q 28 20 26 24 Q 22 26 22 22 Z" fill="#4470a8"/>
      <!-- Eyes -->
      <circle cx="28" cy="26" r="0.9" fill="#1a0a14"/>
      <circle cx="36" cy="26" r="0.9" fill="#1a0a14"/>
      <!-- Glasses (subtle) -->
      <line x1="25" y1="26" x2="31" y2="26" stroke="#1a0a14" stroke-width=".4"/>
      <line x1="33" y1="26" x2="39" y2="26" stroke="#1a0a14" stroke-width=".4"/>
      <!-- Smile -->
      <path d="M 27 32 Q 32 35 37 32" stroke="#7a3a3a" stroke-width=".8" fill="none"/>
    </svg>'''


def avatar_t_ojo() -> str:
    """Poet avatar - dreadlocks, green jacket, deep purple bg."""
    return '''<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="30" fill="#2a1a3a" stroke="#e6c879" stroke-width="2"/>
      <!-- Shoulders -->
      <path d="M 8 60 Q 8 44 24 42 Q 32 40 40 42 Q 56 44 56 60 Z" fill="#3a4a2a"/>
      <!-- Neck -->
      <rect x="28" y="36" width="8" height="8" fill="#9a6a4a"/>
      <!-- Head -->
      <ellipse cx="32" cy="26" rx="10" ry="12" fill="#a87858"/>
      <!-- Dreadlocks -->
      <path d="M 22 22 Q 18 22 18 28 L 16 36" stroke="#1a0a14" stroke-width="2" fill="none"/>
      <path d="M 22 24 Q 17 24 16 32 L 14 40" stroke="#1a0a14" stroke-width="2" fill="none"/>
      <path d="M 24 22 Q 22 22 22 30 L 20 42" stroke="#1a0a14" stroke-width="2" fill="none"/>
      <path d="M 40 22 Q 44 22 44 28 L 46 36" stroke="#1a0a14" stroke-width="2" fill="none"/>
      <path d="M 40 24 Q 45 24 46 32 L 48 40" stroke="#1a0a14" stroke-width="2" fill="none"/>
      <path d="M 38 22 Q 40 22 40 30 L 42 42" stroke="#1a0a14" stroke-width="2" fill="none"/>
      <!-- Eyes -->
      <circle cx="28" cy="26" r="0.9" fill="#1a0a14"/>
      <circle cx="36" cy="26" r="0.9" fill="#1a0a14"/>
      <!-- Smile -->
      <path d="M 27 32 Q 32 34 37 32" stroke="#7a3a3a" stroke-width=".8" fill="none"/>
    </svg>'''


def avatar_l_park() -> str:
    """Designer avatar - short bob, glasses, pink bg."""
    return '''<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="30" fill="#3a2a44" stroke="#f3a4b8" stroke-width="2"/>
      <!-- Shoulders -->
      <path d="M 8 60 Q 8 44 24 42 Q 32 40 40 42 Q 56 44 56 60 Z" fill="#1a2a3a"/>
      <!-- Neck -->
      <rect x="28" y="36" width="8" height="8" fill="#e8c4a0"/>
      <!-- Head -->
      <ellipse cx="32" cy="26" rx="10" ry="12" fill="#f0d4b8"/>
      <!-- Bob (short hair) -->
      <path d="M 22 18 Q 22 14 32 14 Q 42 14 42 18 Q 44 22 42 30 L 42 32 Q 38 28 32 28 Q 26 28 22 32 L 22 30 Q 20 22 22 18 Z" fill="#1a0a14"/>
      <!-- Round glasses -->
      <circle cx="28" cy="26" r="3" fill="none" stroke="#e6c879" stroke-width=".8"/>
      <circle cx="36" cy="26" r="3" fill="none" stroke="#e6c879" stroke-width=".8"/>
      <line x1="31" y1="26" x2="33" y2="26" stroke="#e6c879" stroke-width=".8"/>
      <!-- Eyes -->
      <circle cx="28" cy="26" r="0.8" fill="#1a0a14"/>
      <circle cx="36" cy="26" r="0.8" fill="#1a0a14"/>
      <!-- Smile -->
      <path d="M 28 32 Q 32 34 36 32" stroke="#c44a3a" stroke-width=".8" fill="none"/>
    </svg>'''


def avatar_a_chen() -> str:
    """Game master avatar - long hair, beard, gold bg."""
    return '''<svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
      <circle cx="32" cy="32" r="30" fill="#5a4a1a" stroke="#e6c879" stroke-width="2"/>
      <!-- Shoulders -->
      <path d="M 8 60 Q 8 44 24 42 Q 32 40 40 42 Q 56 44 56 60 Z" fill="#3a2a1a"/>
      <!-- Neck -->
      <rect x="28" y="36" width="8" height="8" fill="#a87858"/>
      <!-- Head -->
      <ellipse cx="32" cy="26" rx="10" ry="12" fill="#c89e74"/>
      <!-- Long hair (dark) -->
      <path d="M 22 22 Q 22 12 32 12 Q 42 12 42 22 Q 44 32 42 38 L 42 36 Q 38 32 32 30 Q 26 32 22 36 L 22 38 Q 20 32 22 22 Z" fill="#1a0a14"/>
      <!-- Beard -->
      <path d="M 24 32 Q 26 38 32 40 Q 38 38 40 32 Q 38 36 32 36 Q 26 36 24 32 Z" fill="#1a0a14"/>
      <!-- Eyes -->
      <circle cx="28" cy="26" r="0.9" fill="#1a0a14"/>
      <circle cx="36" cy="26" r="0.9" fill="#1a0a14"/>
      <!-- Eyebrows -->
      <line x1="25" y1="22" x2="31" y2="22" stroke="#1a0a14" stroke-width="1"/>
      <line x1="33" y1="22" x2="39" y2="22" stroke="#1a0a14" stroke-width="1"/>
      <!-- Smile -->
      <path d="M 29 35 Q 32 36 35 35" stroke="#7a3a3a" stroke-width=".8" fill="none"/>
    </svg>'''


AVATARS = {
    "j_reyes":  avatar_j_reyes,
    "k_voss":   avatar_k_voss,
    "m_aoki":   avatar_m_aoki,
    "t_ojo":    avatar_t_ojo,
    "l_park":   avatar_l_park,
    "a_chen":   avatar_a_chen,
}


# ---- Testimonial data ----

TESTIMONIALS = [
    {"id": "j_reyes",  "name": "J. Reyes",  "role": "screenwriter",
     "quote": "I started a noir world to map out a screenplay. The procedural beats got me unstuck twice."},
    {"id": "k_voss",   "name": "K. Voss",   "role": "novelist",
     "quote": "The branching choices feel real, not random. The system actually learns what kind of story I'm trying to tell."},
    {"id": "m_aoki",   "name": "M. Aoki",   "role": "roleplayer",
     "quote": "I plugged in my OpenRouter key and the world went from procedural sketches to fully-voiced prose in one afternoon."},
    {"id": "t_ojo",    "name": "T. Ojo",    "role": "poet",
     "quote": "The avatar builder respects my privacy. No photos, no PII. Just my choices."},
    {"id": "l_park",   "name": "L. Park",   "role": "designer",
     "quote": "Each genre feels like a different movie set. I keep finding new corners I hadn't explored."},
    {"id": "a_chen",   "name": "A. Chen",   "role": "game master",
     "quote": "I run sessions from /seed prompts. My players walk in with character sheets they didn't write themselves."},
]


def render_testimonials_grid() -> str:
    """HTML for the v17 testimonials grid (3 cards visible, 3 hidden behind
    a 'more' link in v17 — but we just show 3 like v16 did)."""
    cards = []
    for t in TESTIMONIALS[:3]:
        avatar = AVATARS.get(t["id"], lambda: "")()
        cards.append(
            '<div class="quote v17">'
            + '<div class="avatar v17">' + avatar + '</div>'
            + '<p class="text">' + t["quote"] + '</p>'
            + '<div class="who">— ' + t["name"] + ', ' + t["role"] + '</div>'
            + '</div>'
        )
    return '<div class="testimonials v17">' + "".join(cards) + '</div>'

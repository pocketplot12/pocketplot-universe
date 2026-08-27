"""
PocketPlot Universe - Upgraded genre icons (v17).

Each genre icon is now a 96x96 scene-like miniature rather than a
flat shape. Designed to read at the homepage card size but reveal
more detail when inspected closely.
"""
from pathlib import Path

# 96x96 viewBox for richer detail. Each card keeps the same hover
# behavior as v16.
ICON_SIZE = 96


def _genre_icon(genre: str) -> str:
    g = genre.lower()
    return {
        "cyberpunk": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_cp" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#1a0a2e"/>'
            '<stop offset="100%" stop-color="#3a1850"/>'
            '</linearGradient>'
            '<radialGradient id="v17_cp_glow" cx="0.5" cy="0.5" r="0.5">'
            '<stop offset="0%" stop-color="#ff3a8a" stop-opacity=".5"/>'
            '<stop offset="100%" stop-color="#ff3a8a" stop-opacity="0"/>'
            '</radialGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_cp)"/>'
            '<circle cx="48" cy="56" r="32" fill="url(#v17_cp_glow)" opacity=".5"/>'
            # Skyline silhouettes
            '<g fill="#0a0420">'
            '<rect x="8" y="44" width="14" height="40"/>'
            '<rect x="24" y="32" width="18" height="52"/>'
            '<rect x="44" y="40" width="16" height="44"/>'
            '<rect x="62" y="28" width="22" height="56"/>'
            '<rect x="84" y="44" width="8" height="40"/>'
            '</g>'
            # Neon signs
            '<rect x="27" y="40" width="13" height="2" fill="#ff3a8a"/>'
            '<rect x="27" y="46" width="13" height="2" fill="#44f0ff"/>'
            '<rect x="65" y="36" width="16" height="2" fill="#44f0ff"/>'
            '<rect x="65" y="42" width="16" height="2" fill="#ff3a8a"/>'
            # A neon circle ("sun") in the sky
            '<circle cx="48" cy="22" r="6" fill="#e6c879" opacity=".5"/>'
            '<circle cx="48" cy="22" r="3" fill="#fff3c4"/>'
            # Ground
            '<rect x="0" y="80" width="96" height="16" fill="#0a1428"/>'
            # A neon "road" line
            '<line x1="0" y1="86" x2="96" y2="86" stroke="#ff3a8a" stroke-width=".5"/>'
            '</svg>'
        ),
        "romance": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_rom" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#7a4a4a"/>'
            '<stop offset="100%" stop-color="#c47a6a"/>'
            '</linearGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_rom)"/>'
            # Sun
            '<circle cx="68" cy="30" r="10" fill="#fff3c4" opacity=".6"/>'
            '<circle cx="68" cy="30" r="6" fill="#fff3c4"/>'
            # Distant trees
            '<g fill="#5a3a3a" opacity=".6">'
            '<circle cx="12" cy="56" r="6"/><rect x="11" y="56" width="2" height="14"/>'
            '<circle cx="22" cy="58" r="4"/><rect x="21" y="58" width="2" height="12"/>'
            '<circle cx="84" cy="56" r="6"/><rect x="83" y="56" width="2" height="14"/>'
            '</g>'
            # Horizon
            '<rect x="0" y="68" width="96" height="2" fill="#e6c879" opacity=".4"/>'
            # Two silhouettes on a bench
            '<rect x="40" y="62" width="18" height="6" fill="#3a1a2a"/>'
            '<rect x="38" y="68" width="2" height="10" fill="#3a1a2a"/>'
            '<rect x="58" y="68" width="2" height="10" fill="#3a1a2a"/>'
            # Couple silhouettes
            '<g fill="#1a0a14">'
            '<circle cx="44" cy="56" r="4"/>'
            '<path d="M 40 60 L 40 70 L 48 70 L 48 60 Z"/>'
            '<circle cx="54" cy="56" r="4"/>'
            '<path d="M 50 60 L 50 70 L 58 70 L 58 60 Z"/>'
            '</g>'
            # A floating heart between them
            '<path d="M 49 50 C 47 47 47 44 49 43 C 50 42 51 43 49 45 '
            'C 47 43 48 42 49 43 C 51 44 51 47 49 50 Z" fill="#ff8aa8" opacity=".7"/>'
            # Foreground grass
            '<g stroke="#3a4a2a" stroke-width=".5">'
            '<line x1="10" y1="84" x2="10" y2="78"/>'
            '<line x1="20" y1="86" x2="20" y2="80"/>'
            '<line x1="78" y1="84" x2="78" y2="78"/>'
            '<line x1="88" y1="86" x2="88" y2="80"/>'
            '</g>'
            '</svg>'
        ),
        "action": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_act" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#1a1428"/>'
            '<stop offset="100%" stop-color="#3a1a1a"/>'
            '</linearGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_act)"/>'
            # City silhouettes
            '<g fill="#0a0a14">'
            '<rect x="6" y="44" width="14" height="40"/>'
            '<rect x="22" y="34" width="14" height="50"/>'
            '<rect x="38" y="48" width="14" height="36"/>'
            '<rect x="54" y="30" width="14" height="54"/>'
            '<rect x="70" y="44" width="14" height="40"/>'
            '<rect x="86" y="50" width="8" height="34"/>'
            '</g>'
            # Lit windows
            '<g fill="#e6c879" opacity=".5">'
            '<rect x="9" y="50" width="2" height="2"/>'
            '<rect x="13" y="56" width="2" height="2"/>'
            '<rect x="25" y="40" width="2" height="2"/>'
            '<rect x="29" y="48" width="2" height="2"/>'
            '<rect x="41" y="54" width="2" height="2"/>'
            '<rect x="57" y="36" width="2" height="2"/>'
            '<rect x="61" y="44" width="2" height="2"/>'
            '<rect x="73" y="52" width="2" height="2"/>'
            '</g>'
            # A car (foreground)
            '<rect x="32" y="74" width="32" height="12" fill="#c44a3a" stroke="#1a0a14" stroke-width=".5"/>'
            '<rect x="38" y="68" width="20" height="8" fill="#7a3a3a" stroke="#1a0a14" stroke-width=".5"/>'
            '<circle cx="38" cy="86" r="2" fill="#1a0a14"/>'
            '<circle cx="58" cy="86" r="2" fill="#1a0a14"/>'
            # Headlight beam
            '<path d="M 64 78 L 96 70 L 96 82 Z" fill="#fff3c4" opacity=".25"/>'
            # Speed lines
            '<g stroke="#e6c879" stroke-width=".5" opacity=".5">'
            '<line x1="6" y1="80" x2="22" y2="80"/>'
            '<line x1="10" y1="86" x2="24" y2="86"/>'
            '</g>'
            '</svg>'
        ),
        "drama": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_dram" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#3a1a2a"/>'
            '<stop offset="100%" stop-color="#5a2a44"/>'
            '</linearGradient>'
            '<radialGradient id="v17_dram_spot" cx="0.5" cy="0.5" r="0.5">'
            '<stop offset="0%" stop-color="#fff3c4" stop-opacity=".5"/>'
            '<stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>'
            '</radialGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_dram)"/>'
            # Curtains pulled back
            '<path d="M 0 0 L 22 0 Q 16 30 12 80 Q 10 96 0 96 Z" fill="#5a1a3a" opacity=".85"/>'
            '<path d="M 96 0 L 74 0 Q 80 30 84 80 Q 86 96 96 96 Z" fill="#5a1a3a" opacity=".85"/>'
            # Spotlight
            '<circle cx="48" cy="64" r="40" fill="url(#v17_dram_spot)"/>'
            # Stage floor
            '<rect x="0" y="80" width="96" height="16" fill="#1a0a14"/>'
            # A single chair
            '<g transform="translate(48,72)">'
            '<ellipse cx="0" cy="2" rx="14" ry="1.5" fill="#000" opacity=".4"/>'
            '<rect x="-7" y="-16" width="14" height="18" fill="#5a3a1a" stroke="#1a0a14" stroke-width=".8"/>'
            '<line x1="0" y1="-16" x2="0" y2="2" stroke="#1a0a14" stroke-width="1.4"/>'
            '<line x1="-9" y1="2" x2="-9" y2="6" stroke="#1a0a14" stroke-width="1.4"/>'
            '<line x1="9"  y1="2" x2="9"  y2="6" stroke="#1a0a14" stroke-width="1.4"/>'
            '</g>'
            # A single mask hanging above
            '<g transform="translate(48,28)">'
            '<ellipse cx="0" cy="0" rx="10" ry="12" fill="#fff3c4" stroke="#c89e54" stroke-width="1"/>'
            '<ellipse cx="-3" cy="-2" rx="2" ry="1" fill="#1a0a14"/>'
            '<ellipse cx="3"  cy="-2" rx="2" ry="1" fill="#1a0a14"/>'
            '<path d="M -3 4 Q 0 6 3 4" stroke="#1a0a14" stroke-width=".8" fill="none"/>'
            '</g>'
            '<line x1="48" y1="10" x2="48" y2="18" stroke="#fff3c4" stroke-width=".5"/>'
            '</svg>'
        ),
        "thriller": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_thr" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#0a0420"/>'
            '<stop offset="60%" stop-color="#1a0a14"/>'
            '<stop offset="100%" stop-color="#3a0a1a"/>'
            '</linearGradient>'
            '<radialGradient id="v17_thr_bulb" cx="0.5" cy="0.5" r="0.5">'
            '<stop offset="0%" stop-color="#fff3c4" stop-opacity=".65"/>'
            '<stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>'
            '</radialGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_thr)"/>'
            # Corridor walls converging
            '<path d="M 0 0 L 36 38 L 36 60 L 0 96 Z" fill="#0a0a14"/>'
            '<path d="M 96 0 L 60 38 L 60 60 L 96 96 Z" fill="#0a0a14"/>'
            '<path d="M 0 96 L 36 60 L 60 60 L 96 96 Z" fill="#1a0a14"/>'
            # Hanging bulb with halo
            '<line x1="48" y1="0" x2="50" y2="30" stroke="#1a0a14" stroke-width="1"/>'
            '<circle cx="50" cy="30" r="32" fill="url(#v17_thr_bulb)"/>'
            '<circle cx="50" cy="30" r="4" fill="#fff3c4"/>'
            # A red door at the end of the corridor
            '<rect x="44" y="44" width="8" height="22" fill="#c44a3a" stroke="#1a0a14" stroke-width="1"/>'
            '<circle cx="50" cy="56" r=".6" fill="#e6c879"/>'
            # Long shadow
            '<ellipse cx="48" cy="76" rx="32" ry="2" fill="#000" opacity=".5"/>'
            # A figure approaching
            '<g transform="translate(36,68)">'
            '<ellipse cx="0" cy="2" rx="4" ry="1" fill="#000" opacity=".6"/>'
            '<path d="M -3 0 L -4 -10 L 4 -10 L 3 0 Z" fill="#000"/>'
            '<circle cx="0" cy="-13" r="2" fill="#000"/>'
            '</g>'
            '</svg>'
        ),
        "fantasy": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_fan" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#2a1830"/>'
            '<stop offset="60%" stop-color="#7a3a3a"/>'
            '<stop offset="100%" stop-color="#e8a868"/>'
            '</linearGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_fan)"/>'
            # Mountains
            '<path d="M 0 60 L 18 40 L 36 56 L 54 36 L 72 56 L 96 40 L 96 80 L 0 80 Z" fill="#1a1428"/>'
            '<path d="M 18 40 L 36 56 L 54 36 L 72 56 L 96 40" stroke="#a86a8a" stroke-width=".4" opacity=".5"/>'
            # Castle silhouette
            '<g fill="#0a0a14">'
            '<rect x="36" y="50" width="24" height="32"/>'
            '<rect x="34" y="46" width="28" height="6"/>'
            '<rect x="36" y="42" width="6" height="6"/>'
            '<rect x="42" y="40" width="6" height="8"/>'
            '<rect x="48" y="38" width="6" height="10"/>'
            '<rect x="54" y="40" width="6" height="8"/>'
            '</g>'
            # Crenellation gold
            '<g stroke="#e6c879" stroke-width=".5">'
            '<rect x="36" y="42" width="6" height="6"/>'
            '<rect x="42" y="40" width="6" height="8"/>'
            '<rect x="48" y="38" width="6" height="10"/>'
            '<rect x="54" y="40" width="6" height="8"/>'
            '</g>'
            # Lit window
            '<rect x="46" y="60" width="4" height="8" fill="#e6c879"/>'
            # Banner
            '<line x1="56" y1="46" x2="62" y2="64" stroke="#c44a3a" stroke-width="1"/>'
            '<path d="M 56 48 L 62 56 L 56 62 Z" fill="#c44a3a"/>'
            # Dragon silhouette on the keep
            '<g transform="translate(46,46)">'
            '<ellipse cx="6" cy="2" rx="6" ry="3" fill="#0a0a14"/>'
            '<path d="M 10 2 q 6 -2 10 0 q -2 4 -10 4 z" fill="#0a0a14"/>'
            '<circle cx="18" cy="0" r=".8" fill="#e6c879"/>'
            '</g>'
            # Sun
            '<circle cx="80" cy="20" r="6" fill="#fff3c4" opacity=".7"/>'
            '<circle cx="80" cy="20" r="3" fill="#fff3c4"/>'
            '</svg>'
        ),
        "comedy": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_com" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#5a1a4a"/>'
            '<stop offset="50%" stop-color="#c44a8a"/>'
            '<stop offset="100%" stop-color="#e6c879"/>'
            '</linearGradient>'
            '<radialGradient id="v17_com_spot" cx="0.5" cy="0.5" r="0.5">'
            '<stop offset="0%" stop-color="#fff8d8" stop-opacity=".6"/>'
            '<stop offset="100%" stop-color="#fff8d8" stop-opacity="0"/>'
            '</radialGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_com)"/>'
            # Spotlight cone
            '<path d="M 48 18 L 22 80 L 74 80 Z" fill="url(#v17_com_spot)" opacity=".7"/>'
            # Confetti
            '<rect x="14" y="14" width="4" height="2" fill="#fff3c4" transform="rotate(20 16 15)"/>'
            '<rect x="78" y="20" width="4" height="2" fill="#ff3a8a" transform="rotate(-20 80 21)"/>'
            '<rect x="20" y="34" width="4" height="2" fill="#44f0ff" transform="rotate(45 22 35)"/>'
            '<rect x="74" y="38" width="4" height="2" fill="#9ad6a4" transform="rotate(-45 76 39)"/>'
            '<rect x="10" y="58" width="4" height="2" fill="#fff3c4"/>'
            '<rect x="82" y="62" width="4" height="2" fill="#ff3a8a"/>'
            # Mic stand
            '<g transform="translate(28,68)">'
            '<line x1="0" y1="0" x2="0" y2="-30" stroke="#1a0a14" stroke-width="1.5"/>'
            '<ellipse cx="0" cy="0" rx="5" ry="1.5" fill="#1a0a14"/>'
            '<circle cx="0" cy="-30" r="4" fill="#5a4a6a" stroke="#1a0a14" stroke-width="1"/>'
            '</g>'
            # Pie-in-the-face figure
            '<g transform="translate(64,68)">'
            '<ellipse cx="0" cy="2" rx="10" ry="1.5" fill="#000" opacity=".5"/>'
            '<rect x="-7" y="-18" width="14" height="18" fill="#3a3a5e" stroke="#1a0a14" stroke-width=".6"/>'
            '<circle cx="0" cy="-22" r="6" fill="#3a3a5e"/>'
            # Pie splat
            '<circle cx="0" cy="-22" r="7" fill="#fff3c4" stroke="#c8764a" stroke-width=".4"/>'
            '<ellipse cx="-2" cy="-19" rx="2" ry="1" fill="#c8764a" opacity=".6"/>'
            '<circle cx="-2" cy="-14" r=".8" fill="#fff3c4"/>'
            '<circle cx="2" cy="-12" r=".7" fill="#fff3c4"/>'
            '</g>'
            '</svg>'
        ),
        "scifi": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<radialGradient id="v17_sci" cx="0.5" cy="0.5" r="0.5">'
            '<stop offset="0%" stop-color="#1a0850"/>'
            '<stop offset="100%" stop-color="#040810"/>'
            '</radialGradient>'
            '<radialGradient id="v17_planet" cx="0.3" cy="0.3" r="0.7">'
            '<stop offset="0%" stop-color="#5a8ac4"/>'
            '<stop offset="100%" stop-color="#1a2a4a"/>'
            '</radialGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_sci)"/>'
            # Stars
            '<g fill="#fff" opacity=".8">'
            '<circle cx="14" cy="18" r="1"/>'
            '<circle cx="80" cy="14" r="1"/>'
            '<circle cx="22" cy="34" r=".8"/>'
            '<circle cx="74" cy="40" r=".8"/>'
            '<circle cx="18" cy="58" r=".8"/>'
            '<circle cx="84" cy="60" r=".8"/>'
            '</g>'
            # A planet (lower-left)
            '<circle cx="28" cy="74" r="14" fill="url(#v17_planet)" stroke="#a86a3a" stroke-width=".5"/>'
            '<ellipse cx="26" cy="70" rx="2" ry="1" fill="#a86a3a" opacity=".4"/>'
            '<ellipse cx="32" cy="76" rx="1.5" ry=".7" fill="#a86a3a" opacity=".4"/>'
            # Saturn-like planet (upper-right)
            '<circle cx="74" cy="32" r="9" fill="url(#v17_planet)" stroke="#e6c879" stroke-width=".5"/>'
            # Saturn ring
            '<ellipse cx="74" cy="32" rx="16" ry="3" fill="none" stroke="#e6c879" stroke-width="1" opacity=".6" transform="rotate(-15 74 32)"/>'
            # Rocket ship (center)
            '<g transform="translate(48,52)">'
            '<ellipse cx="0" cy="2" rx="6" ry="1.5" fill="#fff3c4" opacity=".4"/>'
            '<path d="M -4 -2 L -2 -12 Q 0 -16 2 -12 L 4 -2 Z" fill="#fff3c4" stroke="#c89e54" stroke-width=".6"/>'
            '<circle cx="0" cy="-8" r="2" fill="#44f0ff" opacity=".85"/>'
            # Flame
            '<path d="M -3 0 L -1 6 L 0 2 L 1 6 L 3 0 Z" fill="#ff8a3a"/>'
            '</g>'
            '</svg>'
        ),
        "horror": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_hor" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#040810"/>'
            '<stop offset="60%" stop-color="#1a0a14"/>'
            '<stop offset="100%" stop-color="#3a1a2a"/>'
            '</linearGradient>'
            '<radialGradient id="v17_hor_moon" cx="0.5" cy="0.5" r="0.5">'
            '<stop offset="0%" stop-color="#f8eccb"/>'
            '<stop offset="100%" stop-color="#5a4a4a"/>'
            '</radialGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_hor)"/>'
            # Moon behind clouds
            '<circle cx="68" cy="22" r="14" fill="url(#v17_hor_moon)"/>'
            '<ellipse cx="60" cy="22" rx="14" ry="6" fill="#1a1428" opacity=".6"/>'
            # Distant tree silhouette
            '<g stroke="#0a0a14" stroke-width="1.5" fill="none">'
            '<line x1="74" y1="50" x2="74" y2="68"/>'
            '<line x1="74" y1="60" x2="68" y2="56"/>'
            '<line x1="74" y1="60" x2="80" y2="56"/>'
            '<line x1="74" y1="54" x2="70" y2="50"/>'
            '<line x1="74" y1="54" x2="80" y2="50"/>'
            '</g>'
            # Three tombstones in a row
            '<g fill="#3a3a5e" stroke="#1a1428" stroke-width=".5">'
            '<rect x="14" y="68" width="14" height="22" rx="1"/>'
            '<rect x="12" y="66" width="18" height="3" rx="1"/>'
            '<rect x="40" y="64" width="14" height="26" rx="1"/>'
            '<rect x="38" y="62" width="18" height="3" rx="1"/>'
            '<rect x="64" y="68" width="14" height="22" rx="1"/>'
            '<rect x="62" y="66" width="18" height="3" rx="1"/>'
            '</g>'
            # Tombstone text
            '<g fill="#5a4a6a" font-family="serif" font-size="4" text-anchor="middle">'
            '<text x="21" y="80">RIP</text>'
            '<text x="47" y="78">J.S.</text>'
            '<text x="71" y="80">1807</text>'
            '</g>'
            # Fog curl
            '<ellipse cx="48" cy="88" rx="60" ry="6" fill="#5a4a6a" opacity=".5"/>'
            # A crow silhouette
            '<path d="M 80 38 q 4 -1 8 0 l -2 3 l -2 -3 z" fill="#0a0a14"/>'
            '</svg>'
        ),
        "detective": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_det" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#1a1428"/>'
            '<stop offset="100%" stop-color="#3a1a2a"/>'
            '</linearGradient>'
            '<radialGradient id="v17_det_lamp" cx="0.5" cy="0.5" r="0.5">'
            '<stop offset="0%" stop-color="#fff3c4" stop-opacity=".65"/>'
            '<stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>'
            '</radialGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_det)"/>'
            # Window with blinds (top)
            '<rect x="8" y="14" width="32" height="22" fill="#3a1a2a" stroke="#1a0a14" stroke-width=".6"/>'
            '<g stroke="#1a0a14" stroke-width=".8">'
            '<line x1="8" y1="20" x2="40" y2="20"/>'
            '<line x1="8" y1="26" x2="40" y2="26"/>'
            '<line x1="8" y1="32" x2="40" y2="32"/>'
            '</g>'
            # Desk
            '<rect x="0" y="68" width="96" height="28" fill="#3a1a1a" stroke="#1a0a14" stroke-width=".6"/>'
            # Lamp halo
            '<circle cx="68" cy="56" r="40" fill="url(#v17_det_lamp)"/>'
            # Lamp shade
            '<path d="M 64 38 L 72 38 L 74 48 L 62 48 Z" fill="#5a3a1a" stroke="#1a0a14" stroke-width=".6"/>'
            '<line x1="68" y1="48" x2="68" y2="68" stroke="#5a3a1a" stroke-width="1.5"/>'
            # A map spread
            '<rect x="14" y="64" width="40" height="14" fill="#d8c8a4" stroke="#1a0a14" stroke-width=".4" transform="rotate(-4 34 71)"/>'
            # Magnifying glass over red dot
            '<circle cx="34" cy="68" r="6" stroke="#1a0a14" stroke-width="1" fill="rgba(255,255,255,.1)" transform="rotate(-4 34 71)"/>'
            '<circle cx="34" cy="68" r="1.5" fill="#c44a3a" transform="rotate(-4 34 71)"/>'
            # Magnifying glass handle
            '<line x1="38" y1="72" x2="44" y2="78" stroke="#1a0a14" stroke-width="1.5"/>'
            # Detective hat silhouette (bottom-right)
            '<g transform="translate(82,82)">'
            '<ellipse cx="0" cy="0" rx="14" ry="2" fill="#0a0a14"/>'
            '<ellipse cx="0" cy="-2" rx="10" ry="3" fill="#0a0a14"/>'
            '</g>'
            # Cigarette smoke
            '<path d="M 18 76 Q 16 66 18 56" stroke="#e6c879" stroke-width=".5" fill="none" opacity=".4"/>'
            '</svg>'
        ),
        "fairytales": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_ft" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#3a2a4a"/>'
            '<stop offset="100%" stop-color="#e6c879"/>'
            '</linearGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_ft)"/>'
            # Stars + crescent moon
            '<circle cx="78" cy="18" r="6" fill="#fff3c4"/>'
            '<circle cx="82" cy="16" r="5" fill="#3a2a4a"/>'
            '<circle cx="20" cy="14" r=".6" fill="#fff3c4"/>'
            '<circle cx="36" cy="10" r=".5" fill="#fff3c4"/>'
            '<circle cx="60" cy="14" r=".5" fill="#fff3c4"/>'
            # Distant hills
            '<path d="M 0 60 Q 24 50 48 60 Q 72 70 96 56 L 96 80 L 0 80 Z" fill="#3a2a4a" opacity=".7"/>'
            # Cottage
            '<g transform="translate(36,42)">'
            '<ellipse cx="14" cy="32" rx="26" ry="14" fill="#fff3c4" opacity=".4"/>'
            '<rect x="0" y="20" width="36" height="28" fill="#5a3a1a" stroke="#1a0a14" stroke-width=".8"/>'
            '<path d="M -4 20 L 10 0 L 26 0 L 40 20 Z" fill="#3a1a1a" stroke="#1a0a14" stroke-width=".8"/>'
            '<rect x="60" y="0" width="6" height="12" fill="#1a0a14"/>'
            '<rect x="6" y="28" width="8" height="12" fill="#fff3c4" stroke="#1a0a14" stroke-width=".6"/>'
            '<rect x="22" y="28" width="8" height="12" fill="#fff3c4" stroke="#1a0a14" stroke-width=".6"/>'
            '<rect x="14" y="38" width="8" height="14" fill="#1a0a14" stroke="#1a0a14" stroke-width=".6"/>'
            '<circle cx="22" cy="44" r=".4" fill="#e6c879"/>'
            '</g>'
            # Mushroom
            '<g transform="translate(14,80)">'
            '<rect x="-1" y="-2" width="2" height="6" fill="#f8eccb"/>'
            '<ellipse cx="0" cy="-2" rx="4" ry="2" fill="#c44a3a"/>'
            '<circle cx="-1" cy="-3" r=".5" fill="#fff8d8"/>'
            '</g>'
            '<g transform="translate(82,82)">'
            '<rect x="-1" y="-3" width="2" height="6" fill="#f8eccb"/>'
            '<ellipse cx="0" cy="-3" rx="3" ry="1.6" fill="#c44a3a"/>'
            '</g>'
            # A winding path
            '<path d="M 80 88 Q 70 78 60 70 Q 50 60 60 50" stroke="#d8c8a4" stroke-width="2" fill="none" opacity=".6"/>'
            '</svg>'
        ),
        "superhero": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_sh" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#1a0850"/>'
            '<stop offset="50%" stop-color="#5a2a8a"/>'
            '<stop offset="100%" stop-color="#e87a4a"/>'
            '</linearGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_sh)"/>'
            # A lightning bolt
            '<path d="M 56 12 L 38 50 L 50 50 L 36 84 L 64 44 L 50 44 L 60 12 Z" fill="#fff3c4" stroke="#c89e54" stroke-width="1"/>'
            '<path d="M 56 12 L 38 50 L 50 50 L 36 84 L 64 44 L 50 44 L 60 12 Z" fill="#fff8d8" opacity=".5"/>'
            # Stars
            '<circle cx="14" cy="20" r="1.4" fill="#fff8d8"/>'
            '<circle cx="80" cy="22" r="1" fill="#fff8d8"/>'
            '<circle cx="18" cy="76" r="1" fill="#fff8d8"/>'
            '<circle cx="82" cy="76" r="1.2" fill="#fff8d8"/>'
            # City silhouette at bottom
            '<g fill="#1a0850">'
            '<rect x="4" y="80" width="14" height="14"/>'
            '<rect x="22" y="78" width="20" height="16"/>'
            '<rect x="46" y="82" width="14" height="12"/>'
            '<rect x="64" y="76" width="14" height="18"/>'
            '<rect x="82" y="80" width="12" height="14"/>'
            '</g>'
            # Lit windows
            '<g fill="#fff3c4" opacity=".7">'
            '<rect x="8" y="84" width="2" height="2"/>'
            '<rect x="26" y="82" width="2" height="2"/>'
            '<rect x="68" y="80" width="2" height="2"/>'
            '<rect x="86" y="84" width="2" height="2"/>'
            '</g>'
            '</svg>'
        ),
        "chicklit": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_cl" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#5a3a4a"/>'
            '<stop offset="100%" stop-color="#e6a868"/>'
            '</linearGradient>'
            '<radialGradient id="v17_cl_glow" cx="0.5" cy="0.5" r="0.5">'
            '<stop offset="0%" stop-color="#fff3c4" stop-opacity=".55"/>'
            '<stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>'
            '</radialGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_cl)"/>'
            # A coffee cup (foreground, right)
            '<g transform="translate(68,68)">'
            '<ellipse cx="0" cy="14" rx="14" ry="2" fill="#000" opacity=".3"/>'
            '<path d="M -12 -4 L -10 12 Q -10 14 -8 14 L 8 14 Q 10 14 10 12 L 12 -4 Z" fill="#fff3c4" stroke="#1a0a14" stroke-width="1"/>'
            '<ellipse cx="0" cy="-4" rx="12" ry="3" fill="#3a1a1a"/>'
            # Steam
            '<path d="M -4 -10 q -4 -4 0 -8 q 4 -4 0 -8" stroke="#fff" stroke-width=".5" fill="none" opacity=".4"/>'
            '<path d="M 4 -10 q 4 -4 0 -8 q -4 -4 0 -8" stroke="#fff" stroke-width=".5" fill="none" opacity=".4"/>'
            '</g>'
            # An open journal (left)
            '<g transform="translate(28,66) rotate(-8)">'
            '<rect x="-16" y="-8" width="32" height="22" fill="#fff8d8" stroke="#1a0a14" stroke-width=".6"/>'
            '<line x1="0" y1="-8" x2="0" y2="14" stroke="#1a0a14" stroke-width=".4"/>'
            '<g stroke="#c89e54" stroke-width=".4" opacity=".75">'
            '<line x1="-14" y1="-2" x2="-2" y2="-2"/>'
            '<line x1="-14" y1="2"  x2="-2" y2="2"/>'
            '<line x1="-14" y1="6"  x2="-4" y2="6"/>'
            '<line x1="2"  y1="-2" x2="14" y2="-2"/>'
            '<line x1="2"  y1="2"  x2="14" y2="2"/>'
            '<line x1="2"  y1="6"  x2="12" y2="6"/>'
            '</g>'
            '</g>'
            # Plant (top-right)
            '<g transform="translate(80,28)">'
            '<rect x="-5" y="2" width="10" height="10" fill="#5a3a1a" stroke="#1a0a14" stroke-width=".6"/>'
            '<ellipse cx="0" cy="-2" rx="10" ry="6" fill="#3a5a2a"/>'
            '<ellipse cx="0" cy="-8" rx="8" ry="5" fill="#5a7a3a"/>'
            '<ellipse cx="-2" cy="-14" rx="6" ry="3" fill="#3a5a2a"/>'
            '</g>'
            # Italic text overlay
            '<text x="48" y="22" font-family="Fraunces, serif" font-style="italic" font-size="9" fill="#fff3c4" opacity=".65" text-anchor="middle">hello</text>'
            '</svg>'
        ),
        "adventure": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_adv" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#3a3a6a"/>'
            '<stop offset="100%" stop-color="#e87a4a"/>'
            '</linearGradient>'
            '<linearGradient id="v17_adv_sea" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#5a4a8a"/>'
            '<stop offset="100%" stop-color="#1a1a3a"/>'
            '</linearGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_adv)"/>'
            # Sun
            '<circle cx="78" cy="22" r="8" fill="#fff3c4" opacity=".7"/>'
            '<circle cx="78" cy="22" r="5" fill="#fff3c4"/>'
            # Distant islands
            '<path d="M 0 56 Q 24 48 48 56 Q 72 64 96 54 L 96 70 L 0 70 Z" fill="#1a0a2a" opacity=".75"/>'
            # Ocean
            '<rect x="0" y="68" width="96" height="28" fill="url(#v17_adv_sea)"/>'
            # Mast + sail (center)
            '<line x1="34" y1="6" x2="34" y2="74" stroke="#1a0a14" stroke-width="1.4"/>'
            '<line x1="34" y1="22" x2="22" y2="60" stroke="#1a0a14" stroke-width=".6"/>'
            '<line x1="34" y1="22" x2="46" y2="60" stroke="#1a0a14" stroke-width=".6"/>'
            '<path d="M 34 14 L 50 56 L 34 56 Z" fill="#fff3c4" opacity=".85"/>'
            '<line x1="34" y1="14" x2="50" y2="56" stroke="#1a0a14" stroke-width=".4"/>'
            # A pirate flag
            '<line x1="34" y1="14" x2="34" y2="6" stroke="#1a0a14" stroke-width=".8"/>'
            '<rect x="32" y="6" width="10" height="6" fill="#1a0a14"/>'
            '<circle cx="37" cy="9" r="1" fill="#fff3c4"/>'
            # Wave highlights
            '<path d="M 60 72 L 80 72 L 80 73 L 60 73 Z" fill="#fff3c4" opacity=".4"/>'
            '<path d="M 18 80 L 38 80 L 38 81 L 18 81 Z" fill="#fff3c4" opacity=".3"/>'
            '</svg>'
        ),
        "roleplaying": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_rp" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#1a0850"/>'
            '<stop offset="100%" stop-color="#1a0a14"/>'
            '</linearGradient>'
            '<radialGradient id="v17_rp_fire" cx="0.5" cy="0.5" r="0.5">'
            '<stop offset="0%" stop-color="#fff3c4" stop-opacity=".7"/>'
            '<stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>'
            '</radialGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_rp)"/>'
            # Hex grid
            '<g stroke="#5a4a6a" stroke-width=".5" fill="rgba(230,200,121,.04)">'
            '<polygon points="18,20 30,20 36,30 30,40 18,40 12,30"/>'
            '<polygon points="42,20 54,20 60,30 54,40 42,40 36,30"/>'
            '<polygon points="66,20 78,20 84,30 78,40 66,40 60,30"/>'
            '<polygon points="30,40 42,40 48,50 42,60 30,60 24,50"/>'
            '<polygon points="54,40 66,40 72,50 66,60 54,60 48,50"/>'
            '</g>'
            # Campfire (center)
            '<circle cx="48" cy="68" r="14" fill="url(#v17_rp_fire)"/>'
            '<g transform="translate(48,72)">'
            '<ellipse cx="0" cy="2" rx="6" ry="1" fill="#000" opacity=".4"/>'
            '<path d="M -5 2 L -6 -8 L 6 -8 L 5 2 Z" fill="#5a3a1a" stroke="#1a0a14" stroke-width=".6"/>'
            '<path d="M -4 -6 L 0 -16 L 4 -6 L 2 -2 L -2 -2 Z" fill="#e6a868"/>'
            '<path d="M -2 -10 L 0 -14 L 2 -10 L 1 -6 L -1 -6 Z" fill="#fff3c4"/>'
            '</g>'
            # Dice
            '<g transform="translate(20,68) rotate(-12)">'
            '<polygon points="0,-8 7,-4 0,0 -7,-4" fill="#c44a3a" stroke="#1a0a14" stroke-width=".6"/>'
            '<text x="0" y="-3" font-family="monospace" font-size="6" font-weight="700" fill="#fff3c4" text-anchor="middle">12</text>'
            '</g>'
            '<g transform="translate(78,72) rotate(15)">'
            '<polygon points="0,-8 7,-4 0,0 -7,-4" fill="#5a4a6a" stroke="#1a0a14" stroke-width=".6"/>'
            '<text x="0" y="-3" font-family="monospace" font-size="6" font-weight="700" fill="#fff3c4" text-anchor="middle">8</text>'
            '</g>'
            '</svg>'
        ),
        "historical": (
            '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<defs>'
            '<linearGradient id="v17_hist" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0%" stop-color="#1a0a14"/>'
            '<stop offset="60%" stop-color="#3a1a1a"/>'
            '<stop offset="100%" stop-color="#5a3a1a"/>'
            '</linearGradient>'
            '<radialGradient id="v17_hist_lamp" cx="0.5" cy="0.5" r="0.5">'
            '<stop offset="0%" stop-color="#fff3c4" stop-opacity=".55"/>'
            '<stop offset="100%" stop-color="#fff3c4" stop-opacity="0"/>'
            '</radialGradient>'
            '</defs>'
            '<rect width="96" height="96" rx="10" fill="url(#v17_hist)"/>'
            # A bookshelf full of books
            '<g fill="#3a1a1a" opacity=".85">'
            '<rect x="2" y="14" width="14" height="36"/>'
            '<rect x="18" y="8" width="16" height="42"/>'
            '<rect x="36" y="16" width="12" height="34"/>'
            '<rect x="50" y="6" width="18" height="44"/>'
            '<rect x="70" y="14" width="14" height="36"/>'
            '<rect x="86" y="10" width="10" height="40"/>'
            '</g>'
            # Books
            '<g fill="#5a3a1a">'
            '<rect x="4" y="20" width="10" height="2"/>'
            '<rect x="4" y="28" width="10" height="2"/>'
            '<rect x="4" y="36" width="10" height="2"/>'
            '<rect x="20" y="14" width="12" height="2"/>'
            '<rect x="20" y="22" width="12" height="2"/>'
            '<rect x="20" y="30" width="12" height="2"/>'
            '<rect x="20" y="38" width="12" height="2"/>'
            '<rect x="38" y="22" width="8" height="2"/>'
            '<rect x="38" y="30" width="8" height="2"/>'
            '<rect x="38" y="38" width="8" height="2"/>'
            '<rect x="52" y="14" width="14" height="2"/>'
            '<rect x="52" y="22" width="14" height="2"/>'
            '<rect x="52" y="30" width="14" height="2"/>'
            '<rect x="52" y="38" width="14" height="2"/>'
            '<rect x="72" y="20" width="10" height="2"/>'
            '<rect x="72" y="28" width="10" height="2"/>'
            '<rect x="72" y="36" width="10" height="2"/>'
            '<rect x="88" y="16" width="6" height="2"/>'
            '<rect x="88" y="24" width="6" height="2"/>'
            '<rect x="88" y="32" width="6" height="2"/>'
            '</g>'
            # An oil lamp (foreground)
            '<circle cx="48" cy="68" r="22" fill="url(#v17_hist_lamp)"/>'
            '<g transform="translate(48,72)">'
            '<ellipse cx="0" cy="6" rx="6" ry="1" fill="#000" opacity=".5"/>'
            '<rect x="-4" y="-10" width="8" height="14" fill="#5a3a1a" stroke="#1a0a14" stroke-width=".6"/>'
            '<ellipse cx="0" cy="-12" rx="6" ry="2" fill="#1a0a14"/>'
            '<rect x="-2" y="-18" width="4" height="6" fill="#1a0a14"/>'
            '<ellipse cx="0" cy="-19" rx="1.5" ry="1" fill="#fff3c4"/>'
            '</g>'
            # Candle (left)
            '<g transform="translate(20,76)">'
            '<rect x="-1" y="-2" width="2" height="6" fill="#fff8d8"/>'
            '<ellipse cx="0" cy="-3" rx="1.2" ry="1.6" fill="#fff3c4"/>'
            '</g>'
            '</svg>'
        ),
    }.get(g, (
        '<svg viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="96" height="96" rx="10" fill="#15243f"/>'
        '<text x="48" y="56" font-family="Fraunces, serif" font-size="36" '
        'fill="#e6c879" text-anchor="middle">?</text>'
        '</svg>'
    ))


def render_genre_card(genre: str, label: str) -> str:
    icon = _genre_icon(genre)
    return (
        '<a class="genre-card v17" href="/signup?genre=' + genre + '">'
        + icon
        + '<div class="genre-label">' + label + '</div>'
        + '</a>'
    )


def render_genre_grid() -> str:
    from story_image_composer import GENRES_V16, GENRE_LABELS
    return (
        '<div class="genre-grid v17">'
        + "".join(render_genre_card(g, GENRE_LABELS[g]) for g in GENRES_V16)
        + '</div>'
    )


if __name__ == "__main__":
    from pathlib import Path
    out = Path(__file__).parent / "genre_icons_preview.html"
    cards = render_genre_grid()
    out.write_text(
        '<html><body style="background:#0e1a2e;padding:20px">'
        '<style>.genre-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}'
        '.genre-card{background:#15243f;border:1px solid #1f3460;border-radius:12px;'
        'padding:18px;text-align:center}.genre-card svg{width:64px;height:64px;margin:0 auto}'
        '.genre-label{font-family:Georgia,serif;color:#f3e9d2;font-size:13px;margin-top:8px}'
        '</style>' + cards + '</body></html>'
    )
    print(f"wrote preview: {out}")

"""
PocketPlot Universe - 16-genre animated grid SVG.

Each genre icon gets a subtle staggered pulse animation.
Icons drawn from the existing genre_icons_v17.py module.
"""

GENRE_GRID_SVG = '''<svg class="genre-grid reveal" viewBox="0 0 720 240" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Sixteen story genres" style="max-width:100%;height:auto">
  <style>
    .genre-grid .gen-cell {
      fill: var(--bg-elevated, #faf3e0);
      stroke: currentColor;
      stroke-width: 0.5;
      opacity: 0.85;
      transition: all 0.4s ease;
    }
    .genre-grid .gen-cell:hover {
      opacity: 1;
      transform: scale(1.05);
    }
    .genre-grid .gen-icon {
      fill: none;
      stroke: var(--brand, #c9a04e);
      stroke-width: 2;
      stroke-linecap: round;
      transform-origin: center;
      transform-box: fill-box;
      animation: genPop 3s ease-in-out infinite;
    }
    .genre-grid .gen-icon:hover {
      animation-duration: 1s;
    }
    .genre-grid .gen-label {
      font-family: 'Inter', sans-serif;
      font-size: 10px;
      letter-spacing: 0.08em;
      fill: var(--brand, #c9a04e);
      text-anchor: middle;
      text-transform: uppercase;
    }
    .genre-grid .gen-icon:nth-child(1) { animation-delay: 0s; }
    .genre-grid .gen-icon:nth-child(2) { animation-delay: 0.2s; }
    .genre-grid .gen-icon:nth-child(3) { animation-delay: 0.4s; }
    .genre-grid .gen-icon:nth-child(4) { animation-delay: 0.6s; }
    .genre-grid .gen-icon:nth-child(5) { animation-delay: 0.8s; }
    .genre-grid .gen-icon:nth-child(6) { animation-delay: 1s; }
    .genre-grid .gen-icon:nth-child(7) { animation-delay: 1.2s; }
    .genre-grid .gen-icon:nth-child(8) { animation-delay: 1.4s; }
    .genre-grid .gen-icon:nth-child(9) { animation-delay: 0s; }
    .genre-grid .gen-icon:nth-child(10) { animation-delay: 0.2s; }
    .genre-grid .gen-icon:nth-child(11) { animation-delay: 0.4s; }
    .genre-grid .gen-icon:nth-child(12) { animation-delay: 0.6s; }
    .genre-grid .gen-icon:nth-child(13) { animation-delay: 0.8s; }
    .genre-grid .gen-icon:nth-child(14) { animation-delay: 1s; }
    .genre-grid .gen-icon:nth-child(15) { animation-delay: 1.2s; }
    .genre-grid .gen-icon:nth-child(16) { animation-delay: 1.4s; }
    @keyframes genPop {
      0%, 100% { transform: scale(1); opacity: 0.7; }
      50% { transform: scale(1.08); opacity: 1; }
    }
    @media (prefers-reduced-motion: reduce) {
      .genre-grid .gen-icon { animation: none !important; opacity: 1; }
    }
  </style>

  <!-- 4 rows x 4 cols grid of cells, each 170x55 -->
'''

# 16 genre icons - simple geometry for each (just hint at what each genre is)
# Use simple pictograms: sword, planet, mask, heart, etc.

GENRES = [
    # name, svg shape
    ('FANTASY', '<polygon points="15,-12 5,8 -5,8 -15,-12 -7,-15 7,-15" />'),  # shield with sword
    ('SCIFI', '<circle r="14" /><circle r="8" /><circle cx="9" cy="-9" r="2" fill="currentColor"/>'),  # planet
    ('NOIR', '<rect x="-12" y="-9" width="24" height="18" rx="2" /><line x1="-12" y1="0" x2="12" y2="0" /><circle cx="0" cy="-4" r="3" />'),  # fedora
    ('ROMANCE', '<path d="M0,-8 C-8,-15 -15,-2 0,8 C15,-2 8,-15 0,-8 z" fill="currentColor" stroke="none"/>'),  # heart
    ('ADVENTURE', '<line x1="-12" y1="10" x2="12" y2="-10" /><circle cx="-12" cy="10" r="3" /><circle cx="12" cy="-10" r="3" />'),  # cross
    ('HORROR', '<polygon points="0,10 -6,-3 -14,4 -8,-12 8,-12 14,4" />'),  # haunted shape
    ('CYBERPUNK', '<rect x="-12" y="-12" width="24" height="24" /><line x1="-12" y1="-2" x2="12" y2="-2" /><line x1="-2" y1="-12" x2="-2" y2="-2" />'),  # mask
    ('ACTION', '<line x1="-12" y1="-12" x2="12" y2="12" /><line x1="12" y1="-12" x2="-12" y2="12" />'),  # X
    ('DRAMA', '<line x1="-12" y1="-2" x2="12" y2="-2" /><rect x="-10" y="-6" width="6" height="4" /><rect x="4" y="-2" width="6" height="6" />'),  # masks (happy/sad)
    ('THRILLER', '<line x1="0" y1="-14" x2="0" y2="-4" /><circle cx="0" cy="2" r="2" /><circle cx="0" cy="10" r="2" /><line x1="-3" y1="2" x2="3" y2="2" />'),  # exclamation
    ('COMEDY', '<circle cx="-5" cy="-5" r="2" fill="currentColor"/> <circle cx="5" cy="-5" r="2" fill="currentColor"/> <path d="M -8,4 Q 0,12 8,4" />'),  # smiley
    ('FAIRYTALE', '<polygon points="-12,2 -8,-6 -4,2 -4,-12 0,-8 4,-12 4,2 8,-6 12,2" />'),  # crown
    ('SUPERHERO', '<polygon points="0,-14 5,-4 14,-4 7,3 10,14 0,8 -10,14 -7,3 -14,-4 -5,-4" />'),  # star
    ('CHICKLIT', '<path d="M-10,-10 Q-10,0 0,0 Q-10,0 -10,10 M-10,-10 L-2,-10 L-10,0 L-2,0" />'),  # book spine
    ('ROLEPLAY', '<circle cx="0" cy="-8" r="6" /><path d="M-12,12 Q-12,0 0,0 Q12,0 12,12" />'),  # chess pawn-like
    ('HISTORICAL', '<rect x="-10" y="-10" width="20" height="20" /><line x1="-10" y1="-3" x2="10" y2="-3" /><line x1="-10" y1="3" x2="10" y2="3" />'),  # open book
]

svg_body = ''
for row in range(4):
    for col in range(4):
        idx = row * 4 + col
        if idx >= 16: break
        name, shape = GENRES[idx]
        cx = 90 + col * 180
        cy = 30 + row * 60
        svg_body += f'''
  <g class="gen-cell" transform="translate({cx-80}, {cy-25})">
    <rect x="0" y="0" width="160" height="50" rx="6" />
  </g>
  <g class="gen-icon" transform="translate({cx-65}, {cy})">
    {shape}
  </g>
  <text class="gen-label" x="{cx-25}" y="{cy+5}">{name}</text>'''

GENRE_GRID_HTML = GENRE_GRID_SVG + svg_body + '\n</svg>'

if __name__ == '__main__':
    Path = None
    from pathlib import Path as P
    Path = P
    # Write to file for reference
    (P('/root/pocketplot/genres_svg.py').parent / '_genres_svg.html').write_text(GENRE_GRID_HTML)
    print(f'Generated {len(GENRE_GRID_HTML)} bytes')

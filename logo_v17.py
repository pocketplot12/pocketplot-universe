"""
PocketPlot Universe - Refined logo (v17).

The v15 wordmark + a more elegant branching icon. The branching paths
now flow into the letters' negative space rather than sitting beside
the wordmark, creating a single composed mark.
"""
import pathlib

LOGO_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 64" role="img" aria-label="PocketPlot Universe">
  <defs>
    <linearGradient id="l_v17_gold" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#fff8d8"/>
      <stop offset="60%" stop-color="#e6c879"/>
      <stop offset="100%" stop-color="#c89e54"/>
    </linearGradient>
    <linearGradient id="l_v17_gold_soft" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#fff3c4" stop-opacity=".8"/>
      <stop offset="100%" stop-color="#e6c879" stop-opacity=".8"/>
    </linearGradient>
    <radialGradient id="l_v17_halo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="#e6c879" stop-opacity=".25"/>
      <stop offset="100%" stop-color="#e6c879" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <!-- Halo behind the branching icon -->
  <circle cx="32" cy="32" r="30" fill="url(#l_v17_halo)"/>

  <!-- Branching icon: three paths rising from a horizontal "river" at the
       bottom, converging at a small gateway / doorway. The doorway is
       placed to sit visually behind the wordmark's initial P. -->
  <g stroke="url(#l_v17_gold)" stroke-width="1.4" fill="none"
     stroke-linecap="round" stroke-linejoin="round">
    <!-- The three source dots (doors) at the bottom -->
    <circle cx="14" cy="54" r="2.4" fill="#e6c879"/>
    <circle cx="32" cy="54" r="2.4" fill="#e6c879"/>
    <circle cx="50" cy="54" r="2.4" fill="#e6c879"/>
    <!-- The three paths converging upward -->
    <path d="M 14 54 C 14 40, 26 36, 30 24"/>
    <path d="M 32 54 C 32 40, 32 38, 30 24"/>
    <path d="M 50 54 C 50 40, 38 36, 30 24"/>
    <!-- Small lit doorway at the convergence point -->
    <rect x="26" y="14" width="10" height="14" fill="#0e1a2e"
          stroke="url(#l_v17_gold_soft)" stroke-width="1.1"/>
    <line x1="31" y1="20" x2="31" y2="28" stroke="url(#l_v17_gold_soft)"
          stroke-width="0.8"/>
  </g>

  <!-- Wordmark -->
  <g font-family="Fraunces, Georgia, serif">
    <text x="62" y="40" font-size="22" font-weight="600"
          fill="url(#l_v17_gold)">PocketPlot</text>
    <text x="62" y="58" font-size="11" font-style="italic"
          fill="#9eb6d4" font-weight="400" letter-spacing="0.04em">Universe</text>
  </g>
</svg>
'''


def get_logo_svg() -> str:
    return LOGO_SVG


if __name__ == "__main__":
    out = pathlib.Path(__file__).parent / "logo.svg"
    out.write_text(LOGO_SVG)
    print(f"wrote {out}")

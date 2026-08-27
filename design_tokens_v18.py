"""
PocketPlot Universe - Tech-Victorian aesthetic (v18).

A unique blend of 19th-century library and modern tech. The
visual identity combines:
  - Warm wood tones (mahogany, walnut, oak) - the library
  - Brass accents - the bookbinder's tool
  - Amber and warm gold - the banker's lamp
  - Deep emerald green - the leather-bound folio
  - Cool neon cyan + magenta - the modern tech pulse
  - Cream parchment - the page surface

All values are stored as Python constants + CSS variable strings
so the v18 layer can be applied to any existing page by simply
swapping the :root block.
"""

# ---- Color tokens ----

# Backgrounds
NAVY_DEEP   = "#0a0f1c"   # deeper than v17 navy; near-black with a blue undertone
NAVY        = "#0e1a2e"   # primary brand navy
NAVY_2      = "#15243f"   # card / panel
NAVY_3      = "#1f3460"   # dividers / borders
NAVY_4      = "#2a4275"   # hover lift

# Wood tones (library)
WALNUT      = "#4a2c1a"   # deep wood frame
WALNUT_LIGHT= "#6b3f24"   # mid wood
OAK         = "#a87c52"   # light wood
OAK_LIGHT   = "#d4a878"   # pale wood

# Brass
BRASS       = "#c9a04e"
BRASS_DARK  = "#8a6a26"
BRASS_LIGHT = "#e8c879"

# Amber (lamp)
AMBER       = "#f0b54a"
AMBER_LIGHT = "#ffd47a"
AMBER_DARK  = "#8a5e1a"

# Emerald (banker's lamp shade)
EMERALD     = "#1d6b50"
EMERALD_DK  = "#0f3a2a"
EMERALD_LT  = "#3a8c6c"

# Tech neon (cool side of the palette)
NEON_CYAN   = "#5ddef0"
NEON_MAGENTA= "#e85a8a"

# Cream / parchment
CREAM       = "#f3e9d2"
CREAM_WARM  = "#e8d8b8"
PARCHMENT   = "#ede1c4"

# Text
INK         = "#f3e9d2"   # primary text (cream)
INK_SOFT    = "#c9bfa8"   # secondary text
INK_MUTED   = "#9eb6d4"   # tertiary text (cool blue)
INK_FAINT   = "#7a8aa8"   # quaternary text


# ---- Typography stack ----
FONT_SERIF  = "'Fraunces','Playfair Display',Georgia,serif"
FONT_SANS   = "'DM Sans','Inter','Karla',system-ui,-apple-system,sans-serif"
FONT_MONO   = "'JetBrains Mono','IBM Plex Mono',monospace"
FONT_DISPLAY= "'Cinzel','Playfair Display',Georgia,serif"  # for ornamental section dividers


# ---- CSS root block (paste-into-:root) ----

V18_CSS_ROOT = f"""
  /* Tech-Victorian palette (v18) */
  --navy-deep:  {NAVY_DEEP};
  --navy:       {NAVY};
  --navy-2:     {NAVY_2};
  --navy-3:     {NAVY_3};
  --navy-4:     {NAVY_4};

  --walnut:     {WALNUT};
  --walnut-lt:  {WALNUT_LIGHT};
  --oak:        {OAK};
  --oak-light:  {OAK_LIGHT};

  --brass:      {BRASS};
  --brass-d:    {BRASS_DARK};
  --brass-l:    {BRASS_LIGHT};
  --amber:      {AMBER};
  --amber-l:    {AMBER_LIGHT};
  --amber-d:    {AMBER_DARK};

  --emerald:    {EMERALD};
  --emerald-d:  {EMERALD_DK};
  --emerald-l:  {EMERALD_LT};

  --neon-c:     {NEON_CYAN};
  --neon-m:     {NEON_MAGENTA};

  --cream:      {CREAM};
  --cream-w:    {CREAM_WARM};
  --parchment:  {PARCHMENT};

  --ink:        {INK};
  --ink-soft:   {INK_SOFT};
  --ink-muted:  {INK_MUTED};
  --ink-faint:  {INK_FAINT};

  --font-serif:    {FONT_SERIF};
  --font-sans:     {FONT_SANS};
  --font-mono:     {FONT_MONO};
  --font-display:  {FONT_DISPLAY};
"""


# ---- v18 background patterns (CSS + inline SVG) ----

# Subtle wood grain (linear gradient + repeating)
WOOD_GRAIN_CSS = """background:
  /* horizontal warm stripe */
  linear-gradient(180deg, var(--walnut) 0%, var(--walnut-lt) 30%, var(--walnut) 100%),
  /* grain lines */
  repeating-linear-gradient(0deg,
    rgba(0,0,0,.04) 0px, rgba(0,0,0,.04) 1px,
    transparent 1px, transparent 7px);
  background-blend-mode: multiply, normal;"""

# Parchment (warm cream with subtle noise via SVG)
PARCHMENT_CSS = """background:
  /* warm cream base */
  linear-gradient(180deg, var(--parchment) 0%, var(--cream) 100%),
  /* subtle SVG noise texture */
  url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='120'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.6 0 0 0 0 0.5 0 0 0 0 0.3 0 0 0 0.06 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");"""

# Book spine pattern (vertical gradient lines on a deep walnut background)
BOOK_SPINE_CSS = """background:
  /* alternating book spines */
  repeating-linear-gradient(90deg,
    var(--walnut) 0px, var(--walnut) 24px,
    var(--walnut-lt) 24px, var(--walnut-lt) 26px,
    var(--walnut) 26px, var(--walnut) 50px,
    var(--emerald-d) 50px, var(--emerald-d) 76px,
    var(--walnut) 76px, var(--walnut) 102px,
    var(--brass-d) 102px, var(--brass-d) 104px,
    var(--walnut) 104px, var(--walnut) 128px
  );"""


# ---- Ornate border / filigree patterns ----

# Filigree corner (top-left of a card). Inline SVG that can be referenced
# as a background-image or rendered as actual SVG inside an element.
FILIGREE_CORNER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 60">
  <g fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round">
    <path d="M 0 0 L 0 24 M 0 0 L 24 0"/>
    <path d="M 4 0 L 4 18 Q 4 4 18 4 L 4 4"/>
    <circle cx="4" cy="4" r="2"/>
    <path d="M 12 0 Q 12 8 8 12 Q 4 16 0 16" />
    <path d="M 0 24 Q 8 24 12 20 Q 16 16 16 12" />
  </g>
</svg>"""


# Ornate divider: a horizontal rule with a centered emblem.
# Used between major sections. Inline SVG, scales with `width: 100%`.
ORNATE_DIVIDER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 30" preserveAspectRatio="xMidYMid meet">
  <defs>
    <linearGradient id="v18_div" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="var(--brass-d)" stop-opacity="0"/>
      <stop offset=".2" stop-color="var(--brass)" stop-opacity="1"/>
      <stop offset=".5" stop-color="var(--brass-l)" stop-opacity="1"/>
      <stop offset=".8" stop-color="var(--brass)" stop-opacity="1"/>
      <stop offset="1" stop-color="var(--brass-d)" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <line x1="0" y1="15" x2="600" y2="15" stroke="url(#v18_div)" stroke-width="1"/>
  <!-- center emblem: a small diamond inside a circle -->
  <g transform="translate(300 15)">
    <circle r="6" fill="none" stroke="var(--brass)" stroke-width="1"/>
    <circle r="3" fill="var(--brass-l)"/>
    <path d="M -10 0 L -7 0 M 7 0 L 10 0" stroke="var(--brass)" stroke-width="1"/>
    <circle cx="-12" cy="0" r="1.2" fill="var(--brass)"/>
    <circle cx="12" cy="0" r="1.2" fill="var(--brass)"/>
  </g>
  <!-- left filigree end -->
  <g transform="translate(20 15)">
    <path d="M 0 0 Q 8 -3 14 0 Q 8 3 0 0" fill="none" stroke="var(--brass)" stroke-width="1"/>
  </g>
  <g transform="translate(580 15) scale(-1 1)">
    <path d="M 0 0 Q 8 -3 14 0 Q 8 3 0 0" fill="none" stroke="var(--brass)" stroke-width="1"/>
  </g>
</svg>"""


# ---- Button styles ----

# A primary button (brass-bordered with amber glow on hover).
BUTTON_PRIMARY_CSS = f"""
  background: linear-gradient(180deg, var(--brass) 0%, var(--brass-d) 100%);
  color: var(--navy-deep);
  font-family: var(--font-sans);
  font-weight: 700;
  font-size: 13px;
  letter-spacing: .04em;
  text-decoration: none;
  padding: 12px 22px;
  border-radius: 4px;
  border: 1px solid var(--brass-d);
  box-shadow:
    0 0 0 1px var(--brass) inset,
    0 0 0 1px var(--brass-d),
    0 1px 0 var(--brass-l) inset,
    0 4px 16px rgba(0,0,0,.4);
  transition: box-shadow .2s, transform .15s;
  position: relative;
  display: inline-block;
  cursor: pointer;
"""
BUTTON_PRIMARY_HOVER = """
  box-shadow:
    0 0 0 1px var(--brass) inset,
    0 0 0 1px var(--brass-l),
    0 1px 0 var(--amber-l) inset,
    0 0 18px var(--amber),
    0 6px 24px rgba(0,0,0,.5);
  transform: translateY(-1px);
"""

# A secondary button (transparent, brass border, amber text).
BUTTON_SECONDARY_CSS = f"""
  background: transparent;
  color: var(--brass-l);
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 13px;
  letter-spacing: .04em;
  text-decoration: none;
  padding: 11px 20px;
  border-radius: 4px;
  border: 1px solid var(--brass);
  box-shadow: 0 0 0 1px var(--brass-d) inset;
  transition: box-shadow .2s, transform .15s, color .2s;
  display: inline-block;
  cursor: pointer;
"""
BUTTON_SECONDARY_HOVER = """
  color: var(--amber-l);
  border-color: var(--amber);
  box-shadow: 0 0 0 1px var(--amber) inset, 0 0 12px var(--amber);
  transform: translateY(-1px);
"""


# ---- Card styles ----

# A card with a thin brass border, slight parchment inset, and warm shadow.
CARD_CSS = f"""
  background: linear-gradient(180deg, var(--navy-2) 0%, var(--navy-3) 100%);
  border: 1px solid var(--brass-d);
  border-radius: 6px;
  padding: 20px 22px;
  position: relative;
  box-shadow:
    0 1px 0 var(--brass) inset,
    0 0 0 1px var(--navy-2) inset,
    0 8px 24px rgba(0,0,0,.4);
"""
CARD_HOVER = """
  border-color: var(--brass);
  box-shadow:
    0 1px 0 var(--amber-l) inset,
    0 0 0 1px var(--navy-2) inset,
    0 0 24px var(--amber-d),
    0 12px 32px rgba(0,0,0,.5);
"""


# ---- Animations ----

# A slow rotation for clockwork gears.
GEAR_ROTATE_CSS = """
@keyframes gear-rotate {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
.gear.slow { animation: gear-rotate 60s linear infinite; }
.gear.med  { animation: gear-rotate 30s linear infinite; }
.gear.fast { animation: gear-rotate 12s linear infinite; }
.gear.ccw  { animation: gear-rotate 45s linear infinite reverse; }
"""


# All in one CSS chunk for easy injection.
V18_BASE_CSS = (
    f"/* v18 base styles */\n"
    f":root {{\n{V18_CSS_ROOT}\n}}\n"
    f"body {{\n"
    f"  background: {NAVY};\n"
    f"  color: {INK};\n"
    f"  font-family: {FONT_SANS};\n"
    f"}}\n"
    f"h1, h2, h3, h4, h5, h6 {{\n"
    f"  font-family: {FONT_SERIF};\n"
    f"  letter-spacing: -0.01em;\n"
    f"  color: {INK};\n"
    f"}}\n"
    f"h1 i, h2 i, h3 i {{ color: {BRASS_LIGHT}; font-style: italic; }}\n"
    f"a {{ color: {BRASS_LIGHT}; }}\n"
    f"a:hover {{ color: {AMBER_LIGHT}; }}\n"
    f"code, pre {{ font-family: {FONT_MONO}; color: {AMBER_LIGHT}; }}\n"
    f"hr {{ border: none; height: 1px; background: linear-gradient(90deg, transparent 0%, {BRASS_DARK} 50%, transparent 100%); margin: 30px 0; }}\n"
    f"/* Buttons */\n"
    f".btn {{ {BUTTON_PRIMARY_CSS} }}\n"
    f".btn:hover {{ {BUTTON_PRIMARY_HOVER} }}\n"
    f".btn.secondary {{ {BUTTON_SECONDARY_CSS} }}\n"
    f".btn.secondary:hover {{ {BUTTON_SECONDARY_HOVER} }}\n"
    f"/* Cards */\n"
    f".card-v18 {{ {CARD_CSS} }}\n"
    f".card-v18:hover {{ {CARD_HOVER} }}\n"
    f"/* Animations */\n"
    f"{GEAR_ROTATE_CSS}\n"
)

if __name__ == "__main__":
    from pathlib import Path
    out = Path("/root/pocketplot/tokens_v18.py")
    out.write_text('"""v18 design tokens - re-exported from design_tokens_v18"""\nfrom design_tokens_v18 import *\n')
    # Also write the module file
    Path("/root/pocketplot/design_tokens_v18.py").write_text(__doc__ + "\n\n" + V18_BASE_CSS)
    print(f"wrote design_tokens_v18.py")

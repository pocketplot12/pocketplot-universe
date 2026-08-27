"""
PocketPlot Universe - v26 CSS revamp script.

Apple-style refinement: modern, techy, restrained.
Keeps the v18 Tech-Victorian palette + brand mark, refines the chrome.

Applies to:
  - index.html (homepage hero + sections)
  - pricing.html, faq.html, terms.html, how-it-works.html
  - 404.html, 500.html

Run:
  cd /root/pocketplot
  python3 apply_v26_revamp.py

This is a CSS overlay: existing styles stay (backward compatible),
new styles refine typography, cards, buttons, hero composition.
"""
import re
from pathlib import Path


# New CSS to inject at the START of <style> (after :root)
V26_TOKEN_OVERLAY = """
/* v26: Apple-style refinement overlay */
:root {
  /* Type scale - tighter, more disciplined */
  --type-xs:   0.75rem;     /* 12px */
  --type-sm:   0.875rem;    /* 14px */
  --type-base: 1rem;        /* 16px */
  --type-md:   1.125rem;    /* 18px */
  --type-lg:   1.25rem;     /* 20px */
  --type-xl:   1.5rem;      /* 24px */
  --type-2xl:  2rem;        /* 32px */
  --type-3xl:  2.75rem;     /* 44px */
  --type-4xl:  3.75rem;     /* 60px */
  --type-5xl:  5rem;        /* 80px */

  /* Spacing - 4px base */
  --space-1:   0.25rem;     /* 4px */
  --space-2:   0.5rem;      /* 8px */
  --space-3:   0.75rem;     /* 12px */
  --space-4:   1rem;        /* 16px */
  --space-5:   1.5rem;      /* 24px */
  --space-6:   2rem;        /* 32px */
  --space-7:   3rem;        /* 48px */
  --space-8:   4rem;        /* 64px */
  --space-9:   6rem;        /* 96px */

  /* Radii - Apple-style: tighter */
  --radius-sm:  6px;
  --radius:     10px;
  --radius-lg:  16px;
  --radius-xl:  22px;

  /* Shadows - subtle, layered */
  --shadow-sm:  0 1px 2px rgba(0,0,0,.18);
  --shadow:     0 4px 12px rgba(0,0,0,.22), 0 1px 3px rgba(0,0,0,.14);
  --shadow-lg:  0 14px 32px rgba(0,0,0,.32), 0 4px 10px rgba(0,0,0,.18);

  /* Muted accent (Apple-style: one restrained accent color) */
  --accent-cyan:    rgba(93, 222, 240, 0.55);
  --accent-cyan-2:  rgba(93, 222, 240, 0.85);
  --accent-magenta: rgba(232, 90, 138, 0.45);
  --accent-glow:    rgba(240, 181, 74, 0.18);

  /* Glass surface (frosted backdrop) */
  --glass:        rgba(15, 26, 46, 0.72);
  --glass-blur:   saturate(180%) blur(18px);

  /* Motion */
  --ease-out:    cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --dur-fast:    140ms;
  --dur:         220ms;
  --dur-slow:    400ms;
}
"""

# Hero + typography refinements (refines existing classes, doesn't replace)
V26_HERO_OVERLAY = """
/* v26 hero composition - Apple-style restraint */
.hero {
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: var(--space-7);
  align-items: center;
  padding: var(--space-9) 0 var(--space-8);
  position: relative;
}
@media (max-width: 880px) {
  .hero { grid-template-columns: 1fr; gap: var(--space-5); padding: var(--space-7) 0 var(--space-6); }
}

/* Subtle gradient mesh behind the hero - replaces ornate corner brackets */
.hero::before {
  content: '';
  position: absolute;
  top: -10%;
  left: 50%;
  transform: translateX(-50%);
  width: 140%;
  height: 120%;
  background:
    radial-gradient(ellipse 40% 50% at 25% 40%, rgba(93,222,240,0.06), transparent 60%),
    radial-gradient(ellipse 40% 50% at 75% 60%, rgba(240,181,74,0.06), transparent 60%),
    radial-gradient(ellipse 50% 60% at 50% 30%, rgba(232,200,121,0.04), transparent 70%);
  z-index: -1;
  pointer-events: none;
}

.eyebrow {
  font-family: var(--font-sans);
  font-size: var(--type-xs);
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--brass-l);
  font-weight: 500;
  margin-bottom: var(--space-3);
}

h1, .hero h1 {
  font-family: var(--font-serif);
  font-style: italic;
  font-weight: 500;
  font-size: clamp(2.75rem, 6vw, 5rem);
  letter-spacing: -0.025em;
  line-height: 1.05;
  color: var(--ink);
  margin: 0 0 var(--space-4);
}
.hero h1 em {
  font-style: italic;
  color: var(--brass-l);
  font-weight: 400;
}

.lead, .hero p {
  font-family: var(--font-sans);
  font-size: var(--type-md);
  line-height: 1.55;
  color: var(--ink-soft);
  margin: 0 0 var(--space-5);
  max-width: 30em;
}

.hero .art {
  display: flex;
  justify-content: center;
  align-items: center;
}
.hero-mark {
  width: 100%;
  max-width: 460px;
  height: auto;
  filter: drop-shadow(0 30px 60px rgba(240,181,74,.18)) drop-shadow(0 6px 12px rgba(0,0,0,.3));
  animation: hero-mark-float 8s ease-in-out infinite;
}
@keyframes hero-mark-float {
  0%, 100% { transform: translateY(0) rotate(0); }
  50%      { transform: translateY(-8px) rotate(-1deg); }
}
"""

# Buttons - Apple-style: gradient primary, hairline secondary
V26_BUTTON_OVERLAY = """
/* v26 buttons - Apple-style gradient + glow */
.btn, button.btn, a.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 14px 26px;
  font-family: var(--font-sans);
  font-size: var(--type-base);
  font-weight: 600;
  letter-spacing: -0.01em;
  border-radius: var(--radius);
  border: 1px solid transparent;
  cursor: pointer;
  text-decoration: none;
  transition: transform var(--dur) var(--ease-out),
              box-shadow var(--dur) var(--ease-out),
              background var(--dur) var(--ease-out);
  position: relative;
  -webkit-tap-highlight-color: transparent;
}
.btn:hover { transform: translateY(-1px); }
.btn:active { transform: translateY(0); }

/* Primary - brass gradient + soft glow */
.btn-primary, .btn:not(.secondary):not(.ghost) {
  background: linear-gradient(180deg, var(--brass-l) 0%, var(--brass) 60%, var(--amber) 100%);
  color: #1a1410;
  box-shadow:
    0 1px 0 rgba(255,255,255,.25) inset,
    0 0 0 1px rgba(201,160,78,.4),
    0 8px 22px rgba(240,181,74,.18),
    0 2px 6px rgba(0,0,0,.3);
}
.btn-primary:hover, .btn:not(.secondary):not(.ghost):hover {
  box-shadow:
    0 1px 0 rgba(255,255,255,.3) inset,
    0 0 0 1px rgba(232,200,121,.6),
    0 14px 32px rgba(240,181,74,.32),
    0 3px 8px rgba(0,0,0,.3);
}

/* Secondary - hairline outline, transparent fill */
.btn-secondary {
  background: transparent;
  color: var(--ink);
  border-color: rgba(232,200,121,.32);
  backdrop-filter: blur(8px);
}
.btn-secondary:hover {
  background: rgba(232,200,121,.08);
  border-color: rgba(232,200,121,.55);
}

/* Ghost - text only with subtle hover */
.btn-ghost {
  background: transparent;
  color: var(--brass-l);
  border: none;
  padding: 12px 18px;
}
.btn-ghost:hover { color: var(--amber-l); }
"""

# Cards - clean, lots of whitespace
V26_CARD_OVERLAY = """
/* v26 cards - clean hairline, generous whitespace */
.card, .panel, .feature {
  background: var(--navy-2);
  border: 1px solid rgba(201,160,78,.18);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  position: relative;
  transition: transform var(--dur) var(--ease-out),
              border-color var(--dur) var(--ease-out),
              background var(--dur) var(--ease-out);
}
.card:hover, .panel:hover, .feature:hover {
  transform: translateY(-2px);
  border-color: rgba(232,200,121,.36);
  background: linear-gradient(180deg, var(--navy-2) 0%, var(--navy-3) 100%);
}

/* Accent stripe (replaces heavy ornate top border) */
.card.accent, .feature.accent {
  position: relative;
  overflow: hidden;
}
.card.accent::before, .feature.accent::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent 0%, var(--brass) 50%, transparent 100%);
  opacity: 0.7;
}
"""

# Navigation - sticky + frosted glass
V26_NAV_OVERLAY = """
/* v26 navigation - sticky + frosted glass */
nav.main-nav, header.nav {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--glass);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-bottom: 1px solid rgba(201,160,78,.15);
  padding: var(--space-3) var(--space-6);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: var(--font-sans);
  font-size: var(--type-sm);
}

nav.main-nav .nav-link {
  color: var(--ink-soft);
  text-decoration: none;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  transition: color var(--dur-fast), background var(--dur-fast);
  position: relative;
}
nav.main-nav .nav-link:hover {
  color: var(--brass-l);
  background: rgba(232,200,121,.06);
}
nav.main-nav .nav-link.active::after {
  content: '';
  position: absolute;
  bottom: -3px; left: 50%; transform: translateX(-50%);
  width: 18px; height: 2px;
  background: var(--brass);
  border-radius: 1px;
}
"""

# Mobile bottom nav
V26_MOBILE_BOTTOM_NAV = """
/* v26 mobile bottom nav */
@media (max-width: 880px) {
  body { padding-bottom: 60px; }
  .mobile-bottom-nav {
    display: flex;
    position: fixed;
    bottom: 0; left: 0; right: 0;
    height: 56px;
    background: var(--glass);
    backdrop-filter: var(--glass-blur);
    -webkit-backdrop-filter: var(--glass-blur);
    border-top: 1px solid rgba(201,160,78,.15);
    z-index: 90;
    justify-content: space-around;
    align-items: center;
    padding-bottom: env(safe-area-inset-bottom, 0);
  }
  .mobile-bottom-nav a {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    color: var(--ink-faint);
    text-decoration: none;
    font-size: 11px;
    font-family: var(--font-sans);
    padding: 6px 12px;
    min-width: 56px;
    min-height: 44px;
    justify-content: center;
  }
  .mobile-bottom-nav a.active { color: var(--brass-l); }
  .mobile-bottom-nav a .icon { font-size: 18px; line-height: 1; }
}
@media (min-width: 881px) {
  .mobile-bottom-nav { display: none; }
}
"""

# Responsive typography
V26_RESPONSIVE = """
/* v26 responsive typography */
@media (max-width: 880px) {
  body { font-size: 16px; }
  h1 { font-size: 2.25rem; }
  h2 { font-size: 1.75rem; }
  h3 { font-size: 1.25rem; }
  .wrap { padding: 0 var(--space-4); }
}
"""

# Section dividers - replace ornate filigree with cleaner lines
V26_DIVIDER_OVERLAY = """
/* v26 section dividers - cleaner horizontal lines */
.divider, .section-divider, hr {
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, rgba(232,200,121,.4) 50%, transparent 100%);
  border: none;
  margin: var(--space-6) 0;
}
"""

# Combine all overlays
V26_FULL_OVERLAY = (
    V26_TOKEN_OVERLAY
    + V26_HERO_OVERLAY
    + V26_BUTTON_OVERLAY
    + V26_CARD_OVERLAY
    + V26_NAV_OVERLAY
    + V26_MOBILE_BOTTOM_NAV
    + V26_DIVIDER_OVERLAY
    + V26_RESPONSIVE
)


def revamp_index():
    """Apply v26 CSS to index.html. Inserts after the :root block."""
    path = Path('/root/pocketplot/index.html')
    src = path.read_text()
    # Idempotency: check if v26 overlay already exists
    if 'v26: Apple-style refinement overlay' in src:
        print('v26 overlay already applied to index.html')
        return
    # Find the end of the :root block
    i = src.find(':root {')
    depth = 0
    end = i
    for j in range(i, i + 4000):
        if src[j] == '{': depth += 1
        elif src[j] == '}':
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    # Insert after the :root block
    src = src[:end] + '\n\n' + V26_FULL_OVERLAY + src[end:]
    path.write_text(src)
    print(f'Updated {path.name} ({len(src)} bytes)')


def revamp_secondary():
    """Apply minimal v26 CSS to secondary pages (pricing, faq, etc.).
    These pages have different layouts; we add the v26 tokens + button/card
    refinements, but leave the existing layouts intact.
    """
    secondary_pages = [
        'pricing.html', 'faq.html', 'terms.html',
        'how-it-works.html', '404.html', '500.html',
        'signup.html', 'signup-pro.html',
    ]
    for name in secondary_pages:
        path = Path(f'/root/pocketplot/{name}')
        if not path.exists():
            continue
        src = path.read_text()
        if 'v26: Apple-style refinement overlay' in src:
            print(f'v26 overlay already applied to {name}')
            continue
        # Inject into the first <style> block (after :root or at the start)
        i = src.find('<style>')
        if i < 0:
            # Add a style block at the top of <head>
            head_end = src.find('</head>')
            if head_end > 0:
                new_style = f'<style>\n{V26_FULL_OVERLAY}\n</style>\n'
                src = src[:head_end] + new_style + src[head_end:]
        else:
            # Insert after the opening <style>
            style_end = src.find('>', i) + 1
            src = src[:style_end] + '\n\n' + V26_FULL_OVERLAY + src[style_end:]
        path.write_text(src)
        print(f'Updated {name} ({len(src)} bytes)')


if __name__ == '__main__':
    revamp_index()
    revamp_secondary()
    print('\nDone. All pages now have v26 styles.')

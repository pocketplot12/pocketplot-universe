"""
PocketPlot Universe - v30 design system tokens.

Complete semantic token system. Both themes share the SAME semantic names,
only the values change. Every surface uses these tokens, never raw hex colors.

Categories:
  - Backgrounds (page, elevated, overlay, surface)
  - Text hierarchy (heading, body, caption, faint)
  - Brand & actions (brand, brand-light, brand-deep, brand-soft, accent)
  - Status (success, warning, danger)
  - Surfaces (border, border-strong, shadow)
"""

# Default theme = warm-dark
WARM_DARK_TOKENS = """
:root, html[data-theme="warm-dark"] {
  /* === Backgrounds === */
  --bg:              #0a0f1c;       /* page background */
  --bg-elevated:     #15243f;       /* cards, surfaces, raised UI */
  --bg-overlay:      rgba(15, 26, 46, 0.78);  /* nav backdrop blur */
  --surface:         #1f3460;       /* hover states */
  --surface-strong:  #2a4275;       /* pressed/active */

  /* === Text hierarchy (4 tiers) === */
  --text-heading:    #f5ecd6;       /* h1, h2, page titles */
  --text-body:       #d8cba8;       /* paragraphs */
  --text-caption:    #9eb6d4;       /* hints, timestamps */
  --text-faint:      #6c7891;       /* footer, near-invisible */

  /* === Brand & actions === */
  --brand:           #c9a04e;       /* brass — the single brand color */
  --brand-light:     #e8c879;       /* hover, focus */
  --brand-deep:      #8a6a26;       /* pressed state */
  --brand-soft:      rgba(201, 160, 78, 0.18);  /* selection bg */
  --brand-text:      #1a1410;       /* text color on brass backgrounds */
  --accent:          #c9a04e;       /* alias of brand for clarity */

  /* === Status === */
  --success:         #1d6b50;       /* emerald - done, success */
  --success-light:   #3a8c6c;
  --warning:         #f0b54a;       /* amber - caution */
  --warning-deep:    #8a5e1a;
  --danger:          #a02020;       /* rust - delete, error */
  --danger-light:    #e07070;

  /* === Surfaces === */
  --border:          rgba(201, 160, 78, 0.18);
  --border-strong:   rgba(201, 160, 78, 0.45);
  --shadow-sm:       0 1px 3px rgba(0, 0, 0, 0.20);
  --shadow:          0 4px 12px rgba(0, 0, 0, 0.45);
  --shadow-lg:       0 14px 32px rgba(0, 0, 0, 0.55);
}
"""

# Kindle-e-ink warm-light theme
WARM_LIGHT_TOKENS = """
html[data-theme="warm-light"] {
  /* === Backgrounds === */
  --bg:              #f4ecd8;       /* warm cream paper */
  --bg-elevated:     #faf3e0;       /* lighter cream for cards */
  --bg-overlay:      rgba(244, 236, 216, 0.85);
  --surface:         #ebe0c8;
  --surface-strong:  #d8c8a8;

  /* === Text hierarchy === */
  --text-heading:    #3d2e1f;       /* warm dark brown - strongest */
  --text-body:       #5a4a35;       /* warm brown body */
  --text-caption:    #8b7558;       /* tertiary warm brown */
  --text-faint:      #a89579;       /* near-invisible warm brown */

  /* === Brand & actions === */
  --brand:           #b8842a;       /* brass - warmer/darker for cream bg */
  --brand-light:     #d4a04d;
  --brand-deep:      #7a5518;
  --brand-soft:      rgba(184, 132, 42, 0.14);
  --brand-text:      #fef9ec;       /* light text on brass button */
  --accent:          #b8842a;

  /* === Status === */
  --success:         #2d8a5e;       /* slightly darker emerald for cream */
  --success-light:   #4ca97a;
  --warning:         #c89030;       /* darker amber for cream */
  --warning-deep:    #a07020;
  --danger:          #b03030;       /* slightly brighter rust for cream */
  --danger-light:    #d05050;

  /* === Surfaces === */
  --border:          rgba(122, 98, 56, 0.20);
  --border-strong:   rgba(122, 98, 56, 0.55);
  --shadow-sm:       0 1px 3px rgba(60, 40, 15, 0.10);
  --shadow:          0 1px 3px rgba(60, 40, 15, 0.12), 0 4px 10px rgba(60, 40, 15, 0.06);
  --shadow-lg:       0 4px 12px rgba(60, 40, 15, 0.18), 0 14px 28px rgba(60, 40, 15, 0.12);
}
"""

# Component styles - applied across all pages using the tokens
COMPONENT_STYLES = """
/* === Base typography (resets existing colors to use new tokens) === */
html, body {
  background: var(--bg);
  color: var(--text-body);
  transition: background 220ms ease, color 220ms ease;
}
h1, h2, h3, h4 {
  color: var(--text-heading);
  font-family: var(--font-serif, Georgia, serif);
  font-weight: 500;
  letter-spacing: -0.02em;
}
p, li {
  color: var(--text-body);
}
small, .text-caption {
  color: var(--text-caption);
}
.text-faint {
  color: var(--text-faint);
}

/* === Buttons (3 tiers) === */
.btn-primary, button.btn-primary, a.btn-primary {
  background: linear-gradient(180deg, var(--brand-light) 0%, var(--brand) 70%, var(--brand-deep) 100%);
  color: var(--brand-text);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: var(--radius-pill, 999px);
  font-weight: 600;
  letter-spacing: -0.01em;
  padding: 14px 28px;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.20) inset,
    0 0 0 1px var(--border-strong),
    0 6px 18px var(--brand-soft),
    0 2px 6px var(--shadow-sm);
  transition: transform 200ms var(--ease-out), box-shadow 200ms;
}
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.30) inset,
    0 0 0 1px var(--brand-light),
    0 10px 24px rgba(201, 160, 78, 0.28),
    0 3px 8px var(--shadow);
}

.btn-secondary {
  background: transparent;
  color: var(--text-body);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
  padding: 13px 26px;
  font-weight: 600;
  transition: background 200ms, border-color 200ms, color 200ms;
}
.btn-secondary:hover {
  background: var(--brand-soft);
  border-color: var(--brand);
  color: var(--text-heading);
}

.btn-tertiary {
  background: transparent;
  color: var(--brand);
  text-decoration: none;
  font-weight: 500;
  padding: 8px 4px;
  border: none;
  border-bottom: 1px solid transparent;
  transition: border-color 200ms;
}
.btn-tertiary:hover {
  border-bottom-color: var(--brand);
}

/* === Status badges === */
.status-success, .badge-success {
  background: var(--brand-soft);
  color: var(--success-light);
  border: 1px solid var(--success);
}
.status-warning, .badge-warning {
  background: rgba(240, 181, 74, 0.10);
  color: var(--warning);
  border: 1px solid var(--warning);
}
.status-danger, .badge-danger {
  background: rgba(160, 32, 32, 0.10);
  color: var(--danger-light);
  border: 1px solid var(--danger);
}
html[data-theme="warm-light"] .status-warning {
  color: var(--warning-deep);
}

/* === Cards === */
.card, .panel {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg, 16px);
  padding: var(--space-6, 2rem);
  box-shadow: var(--shadow-sm);
}
.card:hover {
  border-color: var(--border-strong);
  background: linear-gradient(180deg, var(--bg-elevated) 0%, var(--surface) 100%);
}

/* === Links === */
a {
  color: var(--brand);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 200ms;
}
a:hover {
  border-bottom-color: var(--brand);
}

/* === Nav === */
.nav, header.nav {
  background: var(--bg-overlay);
  border-bottom: 1px solid var(--border);
}

/* === Inputs === */
input, textarea, select {
  background: var(--bg-elevated);
  color: var(--text-heading);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius, 8px);
}
input:focus, textarea:focus {
  border-color: var(--brand);
  outline: none;
  box-shadow: 0 0 0 3px var(--brand-soft);
}
::placeholder {
  color: var(--text-faint);
}

/* === Buttons (interactive ink) === */
button, a.btn {
  -webkit-tap-highlight-color: transparent;
}

/* === Selection === */
::selection {
  background: var(--brand-soft);
  color: var(--text-heading);
}
"""


if __name__ == '__main__':
    print('Theme v30 tokens defined.')
    print('Run apply_v30_design_system.py to inject into pages.')

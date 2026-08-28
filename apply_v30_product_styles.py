"""
PocketPlot Universe - v30 in-product template styling pass.

The in-product templates (LIBRARY_HTML, PLAY_HTML, etc.) define inline styles
using the v22 visual language (purple/orange gradients, dark navy bg). For v30,
we want them to:

  1. Use our new semantic tokens (--brand, --bg-elevated, --text-heading, etc.)
  2. Match the Apple/Kindle aesthetic of the marketing pages
  3. Toggle with the same theme system

Approach: add a CSS block at the top of each template that overrides the
specific style classes used in that template.

This is NOT a perfect refactor — it's a fast polish pass that makes the
in-product pages consistent with the marketing site without rewriting 40KB
of templates.

Run:
  cd /root/pocketplot
  python3 apply_v30_product_styles.py
"""
import re
from pathlib import Path

app = Path('/root/pocketplot/app.py')
src = app.read_text()

# Universal "v30 product polish" CSS block to inject at the top of every
# in-product template. Uses semantic tokens that adapt to both themes.
# The CSS targets generic class names used across templates (.card, .btn, etc.)
# plus any specific inline styles.

V30_PRODUCT_CSS = """<style>
/* v30 in-product styling - uses semantic tokens from the design system */
body { background: var(--bg); color: var(--text-body); }
h1, h2, h3 { color: var(--text-heading); font-family: var(--font-serif, Georgia, serif); }

/* Cards & surfaces */
.card, .surface {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg, 16px);
  color: var(--text-body);
}

/* Buttons - 3 tiers */
.btn-primary, button.primary, .primary {
  background: linear-gradient(180deg, var(--brand-light), var(--brand), var(--brand-deep));
  color: var(--brand-text);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
  font-weight: 600;
}
.btn-secondary, button.secondary, .secondary {
  background: transparent;
  color: var(--text-body);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill, 999px);
}
.btn-ghost, button.ghost, .ghost {
  background: transparent;
  color: var(--brand);
  border: none;
}
a { color: var(--brand); text-decoration: none; }
a:hover { border-bottom: 1px solid var(--brand); }

/* Status */
.success { color: var(--success-light); }
.warning { color: var(--warning); }
.danger  { color: var(--danger-light); }

/* Inputs */
input, textarea, select {
  background: var(--bg-elevated);
  color: var(--text-heading);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius, 8px);
}
input:focus { border-color: var(--brand); outline: none; box-shadow: 0 0 0 3px var(--brand-soft); }

.muted { color: var(--text-caption); }
.faint { color: var(--text-faint); }
</style>"""


def inject_at_template_start(template_name):
    """Insert V30_PRODUCT_CSS immediately after the template's opening doc tag."""
    global src
    # Pattern: TEMPLATE = """\n  <!doctype...
    # Insert our CSS right before the first <!doctype or after the doctype
    pat = re.compile(rf'({template_name}\s*=\s*""")(\s*<!doctype\s*html>)')
    new_src, count = pat.subn(rf'\1\n\n{V30_PRODUCT_CSS}\2', src, count=1)
    if count == 0:
        # Maybe pattern has CR, try alternative
        pat2 = re.compile(rf'({template_name}\s*=\s*""")\s*<')
        new_src, count = pat2.subn(rf'\1\n\n{V30_PRODUCT_CSS}\n<', src, count=1)
    if count > 0:
        src = new_src
        return True
    return False


TEMPLATES = [
    'LIBRARY_HTML',
    'PLAY_HTML',
    'READ_HTML',
    'WORLD_EDIT_HTML',
    'WORLD_CREATE_HTML',
    'INVENTORY_HTML',
    'ME_HTML',
    'STREAK_HTML',
    'ADMIN_HTML',
    'ADMIN_SEGMENTS_HTML',
    'ADMIN_PROMO_HTML',
    'ADMIN_NEWSLETTER_HTML',
    'GRAPH_HTML',
    'WORLD_INVENTORY_HTML',
]

print('=' * 60)
print('PocketPlot Universe - v30 in-product template polish')
print('=' * 60)

successes = 0
failures = []
for tname in TEMPLATES:
    if tname not in src:
        print(f'  [{tname}] NOT FOUND in app.py')
        failures.append(tname)
        continue
    # Check if v30_product CSS already injected (idempotent)
    if 'v30 in-product styling' in src and src.count('/* v30 in-product styling') >= src.count(tname):
        print(f'  [{tname}] already styled')
        successes += 1
        continue
    if inject_at_template_start(tname):
        print(f'  [{tname}] styled')
        successes += 1
    else:
        print(f'  [{tname}] failed to inject (pattern not matched)')
        failures.append(tname)

print(f'\nDone — {successes}/{len(TEMPLATES)} templates styled')
if failures:
    print(f'Failures: {failures}')

if successes > 0 and tname in src:
    app.write_text(src)
    print(f'\napp.py updated ({len(src)} bytes)')

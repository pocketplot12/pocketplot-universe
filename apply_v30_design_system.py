"""
PocketPlot Universe - v30 design system applier.

Idempotent. Adds the v30 design tokens + component styles to every HTML
page, AFTER the existing v29 theme system. This way the v30 tokens override
the v29 tokens where they overlap.

Run:
  cd /root/pocketplot
  python3 apply_v30_design_system.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from theme_v30 import WARM_DARK_TOKENS, WARM_LIGHT_TOKENS, COMPONENT_STYLES

PAGES = ['index.html', 'pricing.html', 'faq.html', 'terms.html',
         'how-it-works.html', '404.html', '500.html',
         'signup.html', 'signup-pro.html']

MARKER = 'v30 design system'

def apply_to_page(path: Path) -> bool:
    if not path.exists():
        return False
    src = path.read_text()
    if MARKER in src:
        return False
    # Find the v29 theme styles block (style starts with "/* v29 theme system")
    import re
    m = re.search(r'/\* v29 theme system[^/]*\*/', src)
    if not m:
        print(f'  [{path.name}] WARNING: no v29 theme found, skipping')
        return False
    # Insert v30 tokens + components AFTER v29 styles block
    insertion = (
        '\n\n' + MARKER + ' - layered on top of v29 */\n'
        + WARM_DARK_TOKENS
        + '\n'
        + WARM_LIGHT_TOKENS
        + '\n'
        + COMPONENT_STYLES
        + '\n'
    )
    insertion_point = m.end()
    new_src = src[:insertion_point] + insertion + src[insertion_point:]
    path.write_text(new_src)
    print(f'  [{path.name}] v30 design system applied')
    return True

def main():
    print('=' * 60)
    print('PocketPlot Universe - v30 design system applier')
    print('=' * 60)
    print()
    project = Path('/root/pocketplot')
    changed = 0
    for name in PAGES:
        if apply_to_page(project / name):
            changed += 1
    print(f'\nDone — {changed} page(s) updated.')

if __name__ == '__main__':
    main()

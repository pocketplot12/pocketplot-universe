"""
PocketPlot Universe - v29 token refactor (v2).

Replaces old (v27) tokens with new (v29) theme tokens.
Uses lookahead-based regex to avoid the \b / - word-boundary issue.

Run:
  cd /root/pocketplot
  python3 apply_v29_refactor.py
"""
import re
from pathlib import Path

PAGES = ['index.html', 'pricing.html', 'faq.html', 'terms.html',
         'how-it-works.html', '404.html', '500.html',
         'signup.html', 'signup-pro.html']

# Lookahead-based substitutions that handle CSS variable references
# Match `var(--OLD-TOKEN)` followed by a `)`.
TOKEN_SUBSTITUTIONS = [
    # Backgrounds
    (r'var\(\s*(--navy-deepest)\s*\)',          r'var(--bg)'),
    (r'var\(\s*(--navy-deep)\s*\)',             r'var(--bg)'),
    (r'var\(\s*(--navy)(?!\-)\s*\)',            r'var(--bg)'),  # --navy but not --navy-deep
    (r'var\(\s*(--navy-2)\s*\)',                r'var(--bg-elevated)'),
    (r'var\(\s*(--navy-3)\s*\)',                r'var(--surface)'),
    (r'var\(\s*(--navy-4)\s*\)',                r'var(--surface)'),
    # Text - same names, no refactor needed
    # Accents
    (r'var\(\s*(--brass)\s*\)',                 r'var(--accent)'),
    (r'var\(\s*(--brass-l)\s*\)',               r'var(--accent-light)'),
    (r'var\(\s*(--brass-d)\s*\)',               r'var(--accent-deep)'),
    (r'var\(\s*(--amber)\s*\)',                 r'var(--accent-warm)'),
]


def refactor(css: str) -> tuple:
    """Returns (new_css, num_changes)."""
    new = css
    count = 0
    for pattern, replacement in TOKEN_SUBSTITUTIONS:
        new, n = re.subn(pattern, replacement, new)
        count += n
    return new, count


def apply_to_page(path: Path) -> bool:
    if not path.exists():
        return False
    src = path.read_text()
    # Find all <style> blocks
    style_blocks = []
    i = 0
    while True:
        start = src.find('<style>', i)
        if start < 0:
            # Try self-closing
            start = src.find('<style ', i)
            if start < 0:
                break
        end = src.find('</style>', start)
        if end < 0:
            break
        body_start = start + len('<style>')
        style_blocks.append((start, end, body_start))
        i = end + 1

    if not style_blocks:
        return False

    new_src = src
    total = 0
    for start, end, body_start in style_blocks:
        old = src[start + (body_start - start):end]
        new, count = refactor(old)
        if count > 0:
            new_src = new_src[:start + (body_start - start)] + new + new_src[end:]
            total += count
            # Re-find next blocks after this position (offsets shifted)

    if total == 0:
        return False

    # Simpler: process all CSS at once
    new_src = src
    for pattern, replacement in TOKEN_SUBSTITUTIONS:
        new_src, _ = re.subn(pattern, replacement, new_src)
    # Check if anything changed
    if new_src == src:
        return False
    path.write_text(new_src)
    print(f'  [{path.name}] refactored')
    return True


def main():
    print('=' * 60)
    print('PocketPlot Universe - v29 token refactor (v2)')
    print('=' * 60)
    print('Replaces CSS variable references: --navy-X -> --bg-X, --brass-X -> --accent-X, etc.')
    print()
    project = Path('/root/pocketplot')
    changed = 0
    for name in PAGES:
        if apply_to_page(project / name):
            changed += 1
    print(f'\nDone — {changed} page(s) updated.')


if __name__ == '__main__':
    main()

"""
PocketPlot Universe - v33 motion system applier.

Injects animation tokens + scroll-reveal JS into all HTML pages.
Marks key elements with .reveal class so they animate on scroll.

Idempotent. Run:
  cd /root/pocketplot
  python3 apply_v33_motion.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from motion_v33 import ANIMATION_TOKENS, OBSERVER_JS

PAGES = ['index.html', 'pricing.html', 'faq.html', 'terms.html',
         'how-it-works.html', '404.html', '500.html',
         'signup.html', 'signup-pro.html']

MARKER = 'v33 motion system'


def apply_to_page(path: Path) -> bool:
    if not path.exists():
        return False
    src = path.read_text()

    if MARKER in src:
        return False

    # 1. Inject motion tokens into <style> (which is in external style.css)
    # 2. Inject observer JS just before </body>
    new_src = src
    if '</body>' in new_src:
        new_src = new_src.replace('</body>', OBSERVER_JS + '\n</body>')

    # 3. Add .reveal class to key section elements
    # Targets: section.sections, .feature, .tier, .stat, .hero h1, .stat
    import re

    # Add 'reveal' class to specific elements if they don't already have it
    # Be conservative — only target named sections to avoid breaking layout
    patterns_to_reveal = [
        ('class="hero"', 'class="hero reveal"'),
        ('class="section"', 'class="section reveal"'),
        ('class="tiers"', 'class="tiers reveal-stagger"'),
        ('class="tier feature"', 'class="tier featured reveal"'),
        ('class="tier ', 'class="tier reveal"'),  # catch both .tier and .tier.featured
        ('class="stat n-"', None),  # stats use n- prefix already
        ('class="stat"', 'class="stat reveal"'),
        ('class="cta-strip"', 'class="cta-strip reveal"'),
        ('class="features"', 'class="features reveal-stagger"'),
        ('class="faq"', 'class="faq reveal"'),  # actually class is "qa" inside
        ('class="qa "', 'class="qa reveal"'),
    ]

    for old, new in patterns_to_reveal:
        if new is None: continue
        # Only replace if .reveal isn't already there
        check_old = old
        check_new = new
        if check_new not in new_src and check_old in new_src:
            new_src = new_src.replace(check_old, check_new, 1)

    # 4. Add the v33 marker comment
    new_src = new_src.replace(
        '</body>',
        '<!-- ' + MARKER + ' applied -->\n</body>'
    )

    if new_src == src:
        return False

    path.write_text(new_src)
    print(f'  [{path.name}] motion applied')
    return True


def main():
    print('=' * 60)
    print('PocketPlot Universe - v33 motion applier')
    print('=' * 60)
    project = Path('/root/pocketplot')
    changed = 0
    for name in PAGES:
        if apply_to_page(project / name):
            changed += 1
    print(f'\nDone — {changed} page(s) updated.')


if __name__ == '__main__':
    main()
